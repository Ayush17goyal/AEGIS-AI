"""Architecture v2 orchestration, separate from the legacy evaluation prototype."""
import asyncio
import hashlib
import hmac
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from .database import Document, Event
from .gateway import permitted_documents, safe_event_title
from .integrations import ComponentUnavailable, LayaAdapter, NemoAdapter, OutputInspector, component_status
from .privacy import Signal, transform
from . import providers


def policy_decision(signals, denied=False):
    if denied:
        return "BLOCK"
    actions = [s["action"] for s in signals]
    if any(action not in {"ALLOW", "MASK", "BLOCK", "APPROVAL"} for action in actions):
        raise ValueError("Invalid classifier action")
    return max(actions, key={"ALLOW": 0, "MASK": 1, "APPROVAL": 2, "BLOCK": 3}.get, default="ALLOW")


def demo_enabled():
    return os.getenv("AEGIS_DEMO_MODE", "true").lower() == "true" and os.getenv("AEGIS_ENV", "development") != "production"


def status():
    components = component_status()
    return {"demo_login_enabled": demo_enabled(), "pipeline_ready": all(c["status"] == "configured" for c in components),
            "execution_mode": "mock" if providers.provider.name == "mock" else "live", "components": components}


def audit(db, user, result):
    key = os.getenv("AUDIT_HMAC_KEY", "local-demo-only").encode()
    identity = hmac.new(key, user["id"].encode(), hashlib.sha256).hexdigest()[:10]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=int(os.getenv("AUDIT_RETENTION_DAYS", "30")))).isoformat()
    db.execute(delete(Event).where(Event.timestamp < cutoff))
    db.add(Event(id=result["id"], timestamp=datetime.now(timezone.utc).isoformat(), user="usr-" + identity, title=result.get("title"), resource_id=result.get("document_id"),
                 categories=sorted({f["category"] for f in result["findings"]}), risk=result["risk"], severity=result["severity"],
                 policies=result["policies"], action=result["action"], outcome=result["execution_status"],
                 model_called=result["model_called"], provider=result["provider"], latency=result["latency"], reason=result["reason_code"]))
    db.commit()


async def run_approved(db, user, prompt, document_id=None, *, adapters=None):
    start = time.perf_counter()
    result = {"id": "REQ-" + uuid.uuid4().hex, "title": safe_event_title(prompt, document_id), "response": "Request withheld.", "risk": 0, "severity": "Low",
              "action": "BLOCK", "reason": "Required security components are unavailable.", "reason_code": "COMPONENT_UNAVAILABLE",
              "findings": [], "policies": [], "model_called": False, "provider": providers.provider.name,
              "latency": 0, "sanitized_prompt": None, "context_count": 0, "execution_status": "NOT IMPLEMENTED",
              "stages": ["auth"], "missing_components": [], "identity": user["id"], "document_id": document_id}

    def finish():
        result["latency"] = round((time.perf_counter() - start) * 1000, 2)
        audit(db, user, result)  # An audit failure prevents releasing the response.
        return result

    # Check permissions using a filtered query before touching any protected text.
    docs = permitted_documents(db, user, document_id=document_id) if document_id else []
    result["stages"].append("authorization")
    if document_id and not docs:
        result.update(reason="Resource unavailable for this account.", reason_code="AUTHORIZATION_DENIED",
                      execution_status="COMPLETED", risk=100, severity="Critical", policies=["AUTH-001"], provider="not_called")
        return finish()

    # Production calls never substitute the legacy detector suite or mock LLM.
    if adapters is None:
        missing = [c["name"] for c in component_status() if c["status"] != "configured"]
        if missing:
            result["missing_components"] = missing
            return finish()
        adapters = (NemoAdapter(), LayaAdapter(), OutputInspector(), providers.provider)
    nemo, laya, output_inspector, provider = adapters
    result["provider"] = provider.name
    findings = []
    try:
        signals = []
        for name, adapter in (("nemo_input", nemo), ("laya_input", laya)):
            signal = await asyncio.wait_for(adapter.inspect(prompt), timeout=15)
            findings.extend(signal.get("findings", []))
            signals.append(signal)
            result["stages"].append(name)
        action = policy_decision(signals)
        if findings and action == "ALLOW":
            action = "MASK"  # A classifier cannot waive protection of reported spans.
        if action == "MASK" and not findings:
            raise ValueError("Masking requires verified spans")
        result.update(action=action, findings=[f.safe() for f in findings], execution_status="COMPLETED")
        result["stages"].append("policy")
        if action in ("BLOCK", "APPROVAL"):
            result.update(reason="Input policy prevented model execution.", reason_code="INPUT_" + action,
                          response="Approval required; execution is held." if action == "APPROVAL" else "Request blocked by input policy.")
            return finish()
        vault_records = []
        if isinstance(laya, LayaAdapter) and getattr(laya, "_gate", None) is not None:
            protected = await laya.protect(prompt, user_id=user["id"], request_id=result["id"])
            sanitized = protected.masked_text
            vault_records.extend(protected.records)
        else:
            sanitized = transform(prompt, findings)
        result["stages"].append("privacy")
        context = []
        for doc_index, doc in enumerate(docs, 1):
            # Retrieved text has its own input inspections before leaving the gateway.
            checks = [await asyncio.wait_for(a.inspect(doc.content), timeout=15) for a in (nemo, laya)]
            if policy_decision(checks) in ("BLOCK", "APPROVAL"):
                result.update(action="BLOCK", reason="Untrusted context was withheld.", reason_code="CONTEXT_BLOCKED", policies=["CTX-001"])
                return finish()
            spans = [f for s in checks for f in s.get("findings", [])]
            if any(s["action"] == "MASK" for s in checks) and not spans:
                raise ValueError("Context masking requires spans")
            if isinstance(laya, LayaAdapter) and getattr(laya, "_gate", None) is not None:
                protected_doc = await laya.protect(doc.content, user_id=user["id"], request_id=result["id"], label_prefix=f"D{doc_index}_")
                context_text = protected_doc.masked_text
                vault_records.extend(protected_doc.records)
            else:
                context_text = transform(doc.content, spans)
            context.append("<untrusted_document>\n" + context_text + "\n</untrusted_document>")
        result["stages"].append("retrieval")
        result["model_called"] = True
        result["context_count"] = len(context)
        output = await asyncio.wait_for(provider.generate(sanitized, context), timeout=30)
        result["stages"].append("llm")
        if not isinstance(output, str) or len(output) > 100000:
            raise ValueError("Invalid provider output")
        if any(record.get("envelope", {}).get(key) and record["envelope"][key] in output
               for record in vault_records for key in ("ct", "nonce")):
            result.update(action="BLOCK", response="Unsafe model output was withheld.", reason_code="OUTPUT_BLOCKED")
            return finish()
        output_findings = output_inspector.inspect(output)
        result["stages"].extend(["output_regex", "output_presidio"])
        if document_id and not permitted_documents(db, user, document_id=document_id):
            result.update(action="BLOCK", response="Resource unavailable for this account.", reason="Access changed before disclosure.", reason_code="AUTHORIZATION_DENIED", policies=["AUTH-001"])
            return finish()
        result["findings"].extend(f.safe() for f in output_findings)
        if any(f.category == "SECRET" for f in output_findings):
            result.update(action="BLOCK", response="Unsafe model output was withheld.", reason_code="OUTPUT_BLOCKED")
        else:
            result["response"] = transform(output, output_findings)
            if output_findings:
                result.update(action="MASK", policies=["OUT-001"], reason_code="OUTPUT_MASKED")
            else:
                result["reason_code"] = "INPUT_MASKED" if findings else "INSPECTION_PASSED"
        result["reason"] = result["reason_code"].replace("_", " ").capitalize() + "."
        # Only already-protected text may become a client-side preview.
        result["sanitized_prompt"] = sanitized if findings else None
    except ComponentUnavailable:
        result.update(action="BLOCK", execution_status="NOT IMPLEMENTED", reason="A required security component is unavailable.", reason_code="COMPONENT_UNAVAILABLE", response="Request withheld.")
    except Exception:
        result.update(action="BLOCK", execution_status="ERROR", reason="Security processing failed closed.", reason_code="PIPELINE_ERROR", response="Request withheld.")
    return finish()
