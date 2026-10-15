"""Architecture-v2 tests use explicit test doubles, never claim live model verification."""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app, accounts, sessions, attempts, chat_attempts, db_session
from backend.database import Event, Document
from backend.evaluate import isolated_session
from backend.approved_pipeline import run_approved, policy_decision
from backend.privacy import Signal, transform
from backend.integrations import LayaAdapter, ComponentUnavailable, output_regex, NemoAdapter
from backend import providers


class InputDouble:
    def __init__(self, action="ALLOW", findings=None, fail=False):
        self.action, self.findings, self.fail = action, findings or [], fail
    async def inspect(self, text):
        if self.fail:
            raise RuntimeError("sensitive exception must not escape")
        return {"action": self.action, "findings": self.findings}


class OutputDouble:
    def __init__(self, fail=False): self.fail = fail
    def inspect(self, text):
        if self.fail: raise RuntimeError("private output failure")
        return output_regex(text)


@pytest.fixture
def setup(monkeypatch):
    db = isolated_session()
    provider = providers.MockProvider()
    monkeypatch.setattr(providers, "provider", provider)
    monkeypatch.setenv("AEGIS_DEMO_MODE", "true")
    monkeypatch.setenv("AEGIS_ENV", "development")
    monkeypatch.delenv("AEGIS_PIPELINE", raising=False)
    sessions.clear(); attempts.clear(); chat_attempts.clear()
    app.dependency_overrides[db_session] = lambda: db
    yield db, provider
    app.dependency_overrides.clear()
    db.close()


def execute(db, provider, user="bob", prompt="Hello", did=None, nemo=None, laya=None, output=None):
    return asyncio.run(run_approved(db, accounts[user], prompt, did, adapters=(
        nemo or InputDouble(), laya or InputDouble(), output or OutputDouble(), provider)))


def login(client, user):
    response = client.post("/api/auth/login", json={"username": user, "password": "AegisDemo!2026"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


@pytest.mark.parametrize("left", ["ALLOW", "MASK", "BLOCK", "APPROVAL"])
@pytest.mark.parametrize("right", ["ALLOW", "MASK", "BLOCK", "APPROVAL"])
def test_policy_denial_overrides_every_signal(left, right):
    assert policy_decision([{"action": left}, {"action": right}], denied=True) == "BLOCK"


def test_unknown_policy_action_fails():
    with pytest.raises(ValueError): policy_decision([{"action": "guessed_label"}])


def test_legitimate_prompt_allowed_with_test_doubles(setup):
    db, provider = setup
    result = execute(db, provider)
    assert result["action"] == "ALLOW" and result["execution_status"] == "COMPLETED"
    assert provider.calls == 1 and "output_presidio" in result["stages"]
    assert result["provider"] == "mock"  # Never a live-demo PASS.


def test_sensitive_spans_never_leave_gateway(setup):
    db, provider = setup
    prompt = "Email synthetic.person@example.test"
    finding = Signal("PII", "EMAIL_ADDRESS", 6, len(prompt))
    result = execute(db, provider, prompt=prompt, laya=InputDouble("MASK", [finding]))
    assert result["action"] == "MASK"
    assert "synthetic.person@example.test" not in provider.last_prompt
    assert "synthetic.person@example.test" not in json.dumps(result)


def test_detection_spans_cannot_be_allowed_unmasked(setup):
    db, provider = setup
    execute(db, provider, prompt="secret", laya=InputDouble("ALLOW", [Signal("PII", "TEST", 0, 6)]))
    assert provider.last_prompt == "[PROTECTED]"


@pytest.mark.parametrize("action", ["BLOCK", "APPROVAL"])
def test_preventive_actions_stop_provider(setup, action):
    db, provider = setup
    result = execute(db, provider, nemo=InputDouble(action))
    assert result["action"] == action and not result["model_called"] and provider.calls == 0


def test_masks_without_spans_fail_closed(setup):
    db, provider = setup
    result = execute(db, provider, laya=InputDouble("MASK"))
    assert result["execution_status"] == "ERROR" and provider.calls == 0


@pytest.mark.parametrize("user", ["bob", "individual"])
def test_denial_has_no_context_and_does_not_need_classifier(setup, user):
    db, provider = setup
    result = asyncio.run(run_approved(db, accounts[user], "Budget?", "DOC-RESTRICTED"))
    assert result["action"] == "BLOCK" and result["reason_code"] == "AUTHORIZATION_DENIED"
    assert result["context_count"] == 0 and provider.calls == 0
    assert "Orion" not in json.dumps(result) and "4.2" not in json.dumps(result)


def test_authorized_context_and_untrusted_delimiters(setup):
    db, provider = setup
    result = execute(db, provider, user="alice", did="DOC-RESTRICTED")
    assert result["action"] == "ALLOW" and result["context_count"] == 1
    assert provider.last_context[0].startswith("<untrusted_document>")


def test_context_input_failure_stops_provider(setup):
    db, provider = setup
    class ContextRail(InputDouble):
        async def inspect(self, text):
            return {"action": "BLOCK" if "Vendor delivery" in text else "ALLOW", "findings": []}
    result = execute(db, provider, user="alice", did="DOC-INJECTION", nemo=ContextRail())
    assert result["reason_code"] == "CONTEXT_BLOCKED" and provider.calls == 0


@pytest.mark.parametrize("stage", ["input", "output", "provider"])
def test_component_failures_do_not_leak(setup, stage):
    db, provider = setup
    async def failed(*args): raise RuntimeError("private exception")
    if stage == "provider": provider.generate = failed
    result = execute(db, provider, nemo=InputDouble(fail=stage == "input"), output=OutputDouble(stage == "output"))
    assert result["execution_status"] == "ERROR" and result["action"] == "BLOCK"
    assert "private" not in json.dumps(result)


def test_real_output_redaction_is_independent_of_input(setup):
    db, provider = setup
    async def leaked(*args): return "Contact planted.output@example.test"
    provider.generate = leaked
    result = execute(db, provider)
    assert result["reason_code"] == "OUTPUT_MASKED" and result["action"] == "MASK"
    assert "planted.output@example.test" not in json.dumps(result)


def test_secret_output_withheld(setup):
    db, provider = setup
    async def leaked(*args): return "password=synthetic-output-value"
    provider.generate = leaked
    result = execute(db, provider)
    assert result["reason_code"] == "OUTPUT_BLOCKED" and result["action"] == "BLOCK"
    assert "synthetic-output-value" not in json.dumps(result)


def test_no_sensitive_audit_content(setup):
    db, provider = setup
    prompt = "Contact synthetic.audit@example.test"
    execute(db, provider, prompt=prompt, laya=InputDouble("MASK", [Signal("PII", "EMAIL_ADDRESS", 8, len(prompt))]))
    rows = [{c.name: getattr(e, c.name) for c in e.__table__.columns} for e in db.query(Event)]
    assert "synthetic.audit@example.test" not in json.dumps(rows)
    assert "bob" not in json.dumps(rows)


def test_audit_failure_never_releases_answer(setup, monkeypatch):
    db, provider = setup
    def fail(): raise RuntimeError("database unavailable")
    monkeypatch.setattr(db, "commit", fail)
    with pytest.raises(RuntimeError): execute(db, provider)


def test_request_tokens_consistent_and_nonrecoverable():
    findings = [Signal("PII", "TEST", 0, 6), Signal("PII", "TEST", 7, 13)]
    first = transform("sample sample", findings, tokenize=True)
    assert first.split()[0] == first.split()[1] and "sample" not in first
    assert first != transform("sample sample", findings, tokenize=True)


def test_invalid_offsets_rejected():
    with pytest.raises(ValueError): transform("abc", [Signal("PII", "TEST", 0, 40)])


def test_missing_laya_is_not_guessed():
    with pytest.raises(ComponentUnavailable): asyncio.run(LayaAdapter().inspect("hello"))


def test_default_live_run_never_falls_back_to_mock(setup):
    db, provider = setup
    result = asyncio.run(run_approved(db, accounts["bob"], "Hello"))
    assert result["execution_status"] == "NOT IMPLEMENTED" and provider.calls == 0
    assert "Laya" in result["missing_components"]


def test_endpoints_use_verified_identity_and_safe_errors(setup):
    db, provider = setup
    client = TestClient(app)
    assert client.get("/api/demo/status").status_code == 401
    headers = login(client, "bob")
    assert not client.get("/api/demo/status", headers=headers).json()["pipeline_ready"]
    result = client.post("/api/demos/run", headers=headers, json={"preset_id":"preset-rag-denied", "prompt":"Budget?", "document_id":"DOC-RESTRICTED", "role":"admin", "user_id":"alice"}).json()
    assert result["identity"] == "bob" and result["reason_code"] == "AUTHORIZATION_DENIED"
    for endpoint in ("/api/chat", "/v1/chat"):
        result = client.post(endpoint, headers=headers, json={"prompt":"Hello"}).json()
        assert result["execution_status"] == "NOT IMPLEMENTED"
    response = client.post("/api/chat", headers=headers, json={"prompt":"planted-sensitive-value" * 1000})
    assert response.status_code == 422 and "planted-sensitive-value" not in response.text
    assert provider.calls == 0


def test_nonadmin_cannot_quick_switch_to_admin(setup):
    client = TestClient(app)
    headers = login(client, "bob")
    assert client.post("/api/auth/demo-switch", headers=headers, json={"username":"admin"}).status_code == 403


def test_admin_demo_switch_revokes_old_session(setup):
    client = TestClient(app)
    headers = login(client, "admin")
    response = client.post("/api/auth/demo-switch", headers=headers, json={"username":"alice"})
    assert response.status_code == 200 and response.json()["user"]["id"] == "alice"
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_production_disables_demo_auth(setup, monkeypatch):
    monkeypatch.setenv("AEGIS_ENV", "production")
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username":"admin", "password":"AegisDemo!2026"}).status_code == 403


def test_chat_rate_limit(setup):
    client = TestClient(app)
    headers = login(client, "bob")
    chat_attempts["bob"] = [__import__("time").time()] * 30
    assert client.post("/api/chat", headers=headers, json={"prompt":"Hello"}).status_code == 429
