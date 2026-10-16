# NeMo Guardrails input rail — what it is, where it goes, how to run it

Date: 2026-10-16 · Verified with `nemoguardrails==0.24.1` on Python 3.13.16 (not yet on your Python 3.14.6 or the Docker `python:3.12-slim`).

## What this adds

| File | Purpose |
|---|---|
| `guardrails/config.yml` | NeMo config (Colang 1.0, no LLM) that registers one input rail |
| `guardrails/rails.co` | The rail flow and the safe refusal message |
| `guardrails/actions.py` | The deterministic rules. Returns reason codes only, never the matched text |
| `backend/tests/test_nemo_guardrails.py` | 10 tests: real NeMo inside `run_approved`, provider never called on a block |
| `backend/requirements-guardrails.txt` | `nemoguardrails==0.24.1`, kept apart from the base requirements |

No Python in `backend/` was changed. `NemoAdapter` and `nemo_engine()` in `backend/integrations.py` already load a config directory from `NEMO_CONFIG_PATH`; this supplies that directory.

## Run it (Windows)

```powershell
pip install -r backend/requirements-guardrails.txt
python -m pytest -rs backend/tests/test_nemo_guardrails.py   # expect 10 passed and NO skips
$env:NEMO_CONFIG_PATH = "$PWD\guardrails"                     # must be set BEFORE the backend starts
./start.ps1                                                   # stop any old backend on :8000 first
```

`-rs` matters: if NeMo failed to install, the new tests are skipped, not failed. A skip means this is not verified on your machine.
After start, **Feature Demos → readiness** should show NeMo Guardrails as `configured`.

Docker (not tested here): add `COPY guardrails ./guardrails` to `Dockerfile.backend`, `RUN pip install --no-cache-dir -r backend/requirements-guardrails.txt` (copy that file first), and `NEMO_CONFIG_PATH: /app/guardrails` under `api.environment` in `docker-compose.yml`.

## Where it sits in the pipeline (`backend/approved_pipeline.py`)

`run_approved` calls the NeMo adapter twice, both through the same rail:
1. **Prompt:** the `nemo_input` stage, after authorization and before policy. BLOCK gives `INPUT_BLOCK`.
2. **Each authorized document:** the CTX-001 stage, before the provider call. BLOCK gives `CONTEXT_BLOCKED`.

Authorization runs first, so Bob never reaches NeMo for the restricted document.

## What each demo card does at the NeMo stage

| Cards | NeMo result | Who actually handles it |
|---|---|---|
| `inj-override`, `inj-persona`, `inj-zerowidth` | **BLOCK** | NeMo |
| `inj-indirect` (seeded `DOC-INJECTION`) | prompt allowed, **document BLOCK** | NeMo via CTX-001 |
| `benign-edu`, `rag-authorized` | ALLOW | n/a |
| `rag-denied` (Bob) | never reached | ACL (`AUTH-001`) |
| `aadhaar-valid/unverified`, `pan-tax`, `contact-pii`, `payment-card`, `banking-ifsc`, `secret-aws/openai/db/rsa/bearer` | ALLOW | **Laya (unimplemented)** |
| `approval-queue` | ALLOW | policy engine; no component detects "CONFIDENTIAL" yet (issue I-03) |
| `output-redact` | ALLOW | Regex + Presidio on output |

## Still blocking a live end-to-end run

With NeMo configured, `component_status()` is: NeMo `configured`; Presidio, Laya and Real LLM `missing`. `run_approved` returns NOT IMPLEMENTED for every request until all four are configured. The new tests bypass that by injecting a Laya double.

## Measured (2026-10-16, sandbox, through `NemoAdapter`)

Prompt about 90 chars: p50 7 ms, p95 10 ms. Full 19,994-char document: p50 17.5 ms, p95 24 ms (max 52 ms). n=150 each. These are rule-execution timings, not accuracy. Rules and tests were written together on synthetic data, so they show the rails behave as designed, not real-world detection rates.

## Changing the rules

Add a `(reason_code, risk, regex)` row to `_RULES` in `guardrails/actions.py` (`high` blocks, `medium` is only reported), then add a true-positive and a lookalike test. Hinglish coverage is a small starter set and unverified.

## Paste into `docs/New_ones/memory.md` (Rules §1.3)

**§9 session log:** 2026-10-16 — Added `guardrails/` (config.yml, rails.co, actions.py), `backend/tests/test_nemo_guardrails.py`, `backend/requirements-guardrails.txt`. No existing backend code changed. NeMo now `configured` when `NEMO_CONFIG_PATH` points at `guardrails/`. Verified in sandbox: `python -m pytest backend/tests -q` → 106 passed (96 existing + 10 new), Python 3.13.16, nemoguardrails 0.24.1. Real `NemoAdapter` blocks the 3 injection presets and `DOC-INJECTION`; allows `benign-edu` and the authorized Orion questions.
**§5 ledger:** `check_async` input-rail adapter in `backend/integrations.py` `[VERIFIED: nemoguardrails 0.24.1, 2026-10-16]`. Compatibility with Python 3.14.6 and `python:3.12-slim` `[UNVERIFIED]`.
**§4 decision:** NeMo input rail is deterministic (custom action in `guardrails/actions.py`), no LLM, no embeddings; rail length bound 20,000 chars to match the document upload limit. Dependency justification: `nemoguardrails==0.24.1` is the only input-rail engine named by Architecture v2.
**§7 open:** I-07 — 13 of 20 presets pass NeMo by design and depend on Laya/policy/Presidio; none can run live until Laya has an adapter.
**§1 next step:** unchanged — identify the Laya model/interface.

## Current repository integration

The ZIP-delivered runtime modules are now packaged under `backend/secure_layers`.
`LayaAdapter` can load the supplied scorer contract when `LAYA_MODEL_DIR` and
vault keys are configured; otherwise it remains explicitly unavailable. The
upload endpoint invokes the ZIP OCR layer for base64 file uploads and stores
only safe processing metadata when extraction is unavailable. The historical
notes above describe the state before this integration and are retained as an
audit record.
