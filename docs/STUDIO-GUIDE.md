# Feature Demonstration Studio — verified operation and remaining prerequisites

> Agent instruction: read `docs/New_ones/memory.md` and the finalized Architecture v2 before changes; record observed changes and test results in memory before reporting completion.

## Current result (15 October 2026)

The existing UI is repaired to show real assertion outcomes and component availability. **The complete live NeMo + Laya + real LLM + Presidio pipeline is NOT ready.** No Laya repository, model identifier, weights, task labels, inference interface or training configuration was supplied. NeMo and Presidio packages/configuration/local NLP model are missing in the observed Python runtime. The existing provider is an offline deterministic mock.

Do not present blocked requests caused by missing components as successful attack detection. Do not present the historical 46-case regex/mock evaluation as evidence for Architecture v2. The currently verified browser demonstration is Bob's server-side authorization refusal, plus truthful missing-component and error handling. Approved orchestration, masking, output inspection and hosted transport have automated tests with explicit doubles; those are not live-model runs.

## Install and start on Windows PowerShell

From the project directory:

```powershell
Set-Location 'C:\Users\goyal\OneDrive\Desktop\AEGIS-AI-Project\AEGIS-AI'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm.cmd ci
```

Base requirements are pinned to the versions observed in this session. Python 3.14.6 was used for tests; this is not evidence of NeMo/Presidio compatibility. Set environment variables explicitly; the Python entry point does not automatically load `.env`:

```powershell
$env:AEGIS_ENV = 'development'
$env:AEGIS_DEMO_MODE = 'true'
$env:AEGIS_PIPELINE = 'approved'
$env:DATABASE_URL = 'sqlite:///./aegis.db'
$env:DEMO_PASSWORD = 'AegisDemo!2026' # Synthetic local demo only
$env:AUDIT_HMAC_KEY = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:LLM_PROVIDER = 'mock' # Clearly unavailable for full live verification
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

SQLite tables and synthetic demo accounts/documents initialize automatically. No separate DB service is required for this prototype. Existing documents remain plaintext in SQLite. No PostgreSQL service or migration was added.

In a second PowerShell window, from the same directory:

```powershell
npm.cmd run dev
Start-Process 'http://127.0.0.1:5173'
```

The existing `./start.ps1` launches both servers in hidden windows and inherits environment settings, but explicit terminals make startup errors easier to inspect. Do not start duplicate servers on ports already in use.

## Prerequisites before a complete live demonstration

1. Supply the selected **Laya** repository/model or local implementation path, inference request/response examples, supported task and labels, confidence/span capabilities, and required weights/hardware. `backend/integrations.py::LayaAdapter` deliberately raises unavailable; it does not invent predictions. Configuring an arbitrary endpoint does not resolve that contract.
2. Install and validate a compatible **NeMo Guardrails** release in an isolated model environment. Provide a local input-rail configuration directory and set `NEMO_CONFIG_PATH`. No unreviewed safety-model prompt or extra input decision model has been substituted for Laya. A directory with no input flows is rejected. The adapter follows NVIDIA's validation-only `check_async` API; it is not verified against an installed release yet.
3. Install and validate **presidio-analyzer** with its supported local spaCy model; set `PRESIDIO_SPACY_MODEL` (default `en_core_web_sm`). The adapter refuses missing local models and does not download weights during requests. Indian identifiers and non-English coverage need explicit evaluation.
4. Configure the real provider in the backend terminal before starting FastAPI:

```powershell
$env:LLM_PROVIDER = 'hosted'
$taskProviderKey = Read-Host 'Provider API key' -AsSecureString
$env:LLM_API_KEY = [System.Net.NetworkCredential]::new('', $taskProviderKey).Password
$env:LLM_BASE_URL = Read-Host 'Approved HTTPS OpenAI-compatible base URL'
$env:LLM_MODEL = Read-Host 'Approved model identifier'
```

There is no fallback to an alternate provider. Real provider connectivity and live inference remain unverified. NeMo/Presidio installation commands cannot constitute a tested dependency lock until compatible releases/models are resolved; base `requirements.txt` intentionally does not claim to install those unavailable integrations.

5. Resolve confidential approval semantics and the controlled generated-output test fixture before enabling those two cards. Do not enable the old queue or input-mask fixture as substitutes.
6. Re-run the tests below and real labelled input/output evaluations before declaring live readiness. `GET /api/demo/status` reports actual initialization and unresolved components to authenticated users. A healthy HTTP server is not a ready security pipeline.

Production: set `AEGIS_ENV=production` and `AEGIS_DEMO_MODE=false`. This disables synthetic logins. A production identity provider is not implemented; the app must not be exposed as a production service with the shared demo accounts.

## Using the Studio

1. Open the site, choose **Open workspace**, select Company → Owner/Administrator, and sign in as `admin` with the configured local demo password. Open **Feature Demos** in the sidebar.
2. Read the readiness panel. It identifies missing components and mock versus live configuration. A component initialization report is not a successful scenario test.
3. Browse categories: Identity/PII and Financial/Banking exercise privacy; Secrets tests credential refusal; Prompt Injection tests instruction/extraction prevention; RAG tests document permissions; Benign tests legitimate requests. Output and Human Review remain visible with explicit pending reasons. Historical custom checksum, entropy and normalization cards are disabled.
4. Search a title or stable `preset-...` ID. Card text shows its expected action and required stage evidence. All example data is synthetic.
5. Select the correct authenticated persona. Only a verified administrator can use the local demo switch. Switching creates a new server session, revokes the old token, and remounts the workspace so previous results and chat history cannot be reused. After switching to an employee, sign out and sign in again to choose a different identity; there is no employee-to-admin quick escalation.
6. Click **Run demonstration** for a retained scenario under its required persona. It requests an actual backend receipt even when model dependencies are unavailable; in that case the gateway returns NOT IMPLEMENTED/BLOCK without calling the LLM. Other execution/switch controls are locked while it runs. Out-of-scope/pending scenarios and wrong-persona execution remain disabled. Failures of the authenticated status endpoint appear as ERROR. Refresh readiness keeps existing receipts visible.
7. Interpret the receipt:

| Status | Meaning |
| --- | --- |
| PASS | The stated scenario assertions passed. ACL-only PASS explicitly does not verify the detector/model/output chain. |
| FAIL | Actual action, persona, invocation, privacy preview or other asserted behavior contradicted the scenario. An HTTP 200 alone cannot pass. |
| ERROR | Request/network failure, malformed response or execution failure; no successful security result is claimed. |
| NOT IMPLEMENTED | Required component, stage evidence, workflow or fixture is unavailable. No fabricated predictions. |

Receipts include actual identity, request ID, action, reason code, provider, stage evidence, findings, context count and latency when available. Safe response and sanitized preview are displayed only with fixture-value checks. The browser cannot independently inspect network payloads sent by the backend or audit storage; automated capture/privacy tests cover those boundaries with doubles.

8. Click **Open in Secure Chat** to prefill a supported scenario. Only its catalog ID is transferred through browser navigation state and a one-time session-storage fallback; prompt text is not stored there. Navigation state restores the selected synthetic preset after a Chat page reload. The signed-in persona stays active. Inspect/edit the prompt, then press Send explicitly. The normal approved chat path runs; missing checks fail closed. Out-of-scope scenarios cannot be loaded this way. Pending cards may be inspected in Chat, but this does not implement their claimed feature.
9. Use **Prev/Next** in the six-step Examiner Tour. Each step states its expected purpose and availability. Run this step executes the selected card under the current verified persona; it never silently impersonates someone. Full output protection remains an explicitly unavailable final step.

## A verified 3–5 minute jury sequence available now

This is an **integration/readiness demonstration**, not a complete live security showcase:

1. (45 s) Sign in as administrator, open Feature Demos, explain the actual readiness panel. State that the selected Laya interface is still a prerequisite; do not claim NeMo/Presidio ran.
2. (30 s) Show categories and disabled historical/pending cards. Explain why missing features cannot claim PASS.
3. (60 s) Switch from administrator to `bob`. Filter RAG or search `preset-rag-denied`. Run it. Observe **PASS, authorization-only**, `BLOCK`, `AUTHORIZATION_DENIED`, identity `bob`, context count `0`, model called `false`, provider `not_called`, and a request ID. This was verified in an actual browser against the actual local backend.
4. (45 s) Open a retained PII scenario in Secure Chat. Inspect the prefilled prompt; show that no send occurred automatically. If Send is pressed with missing components, observe NOT IMPLEMENTED/BLOCK, not a pretend masking success.
5. (45 s) Show the tour's unavailable detector and output steps and the automated test results. Explain that completing the model contract/configuration is necessary before demonstrating live PII masking, injection detection, authorized real-model retrieval or generated-output redaction to judges.

Only after those dependencies are installed and verified should the jury script include live detector/output examples. A complete 3–5 minute security presentation cannot honestly be supplied today for unavailable modules.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
npm.cmd run test:studio
npm.cmd run build
node --test scripts/hero-media.test.mjs
```

Browser integration uses Playwright with local test servers, a fresh temporary synthetic DB and the offline provider. If Playwright is already installed in an accessible location, point `PLAYWRIGHT_MODULE` to it. With an installed Edge browser:

```powershell
$env:PLAYWRIGHT_MODULE = 'C:\Users\goyal\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
$env:BROWSER_CHANNEL = 'msedge'
npm.cmd run test:e2e
```

The example path was verified on this laptop; another machine needs its own Playwright installation/path. The script creates and terminates only its own servers and removes only its own temporary test DB. Tests involving missing components and explicit doubles are labelled accordingly. See `STUDIO-AUDIT.md` and `docs/New_ones/memory.md` for measured counts and limitations.

AES-256-CCM is an independent tested primitive, not an encrypted-database migration. If recoverable storage is later connected, set `AEGIS_VAULT_KEY` to base64 encoding of 32 secure random bytes, keep it protected across restarts, and define the key ID/purpose/rotation lifecycle. Current request tokenization is request-local and nonrecoverable; no persistent vault or automatic restore is implied.
