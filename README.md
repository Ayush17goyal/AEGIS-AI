# AI Guard

> **2026-10-15 Studio audit:** The finalized backend is Architecture v2 (NeMo + Laya input; Python policy/privacy/ACL; real LLM; Regex + Presidio output). Older prototype descriptions below are historical. Default chat and Studio execution now fail closed when required components are missing; the offline regex/mock evaluation is not a live-model result. Start with [Studio operation guide](docs/STUDIO-GUIDE.md) and [per-card audit](docs/STUDIO-AUDIT.md). Laya's repository/interface, NeMo rails, Presidio local model and real-provider configuration remain unresolved; a complete live security demonstration is not yet available.

A prevention-first AI data leakage gateway for CyberCup 6.0. The design follows the supplied recording: cinematic visor portrait, amber lighting, oversized type, and glass panels. The authenticated application exposes real database-backed security events, policies, documents, and measured evaluation results.

## Run locally

Requirements: Node 22+, Python 3.12+.

```powershell
npm install
python -m pip install -r backend/requirements.txt
# Optional full ZIP-delivered layers (OCR, NeMo, Presidio, Laya runtime)
python -m pip install -r backend/requirements-pipeline.txt
python -m pip install -r backend/requirements-guardrails.txt
python -m backend.evaluate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm run dev
```

Open http://127.0.0.1:5173. After installing dependencies, Windows users can also run `./start.ps1` to launch both servers in hidden background processes. The script does not open a browser or automatically terminate previous servers.

Sign in with `admin`, `alice`, or `bob`; the local demo password is `AegisDemo!2026`. Admin sees all management screens. Alice is permitted to retrieve the synthetic restricted budget; Bob is denied. The backend assigns identity and role. Supplied role fields cannot change permission.

The sign-in flow starts with Individual or Company. Company choices filter the existing demo accounts: Owner / Administrator → `admin`, Limited Employee → `bob`, Normal Employee → `alice`. Individual uses the `individual` demo identity with the same demo password, public documents only, and no administrative access. Employee management and role assignment are not implemented in this demo. Selecting a login option never changes backend permissions.

## Test and evaluate

```powershell
python -m pytest backend/tests -q
python -m backend.evaluate
npm run build
```

The generated `backend/evaluation-report.json` contains actual results for 46 legitimate and adversarial fixtures. Its positive class is a request requiring protection. The runner uses default policies, a fresh in-memory database, and a deterministic mock provider, leaving live audit history unchanged. It records findings, actions, invariants, confusion matrix, precision, recall, F1, acceptance, latency, and per-category outcomes. Fixture accuracy does not establish real-world generalization.

## Architecture

React + Vite + TypeScript + Tailwind CSS, Lucide icons, Recharts, React Router → FastAPI → authenticated server identity → layered input detection → configurable policy enforcement → permission-filtered local retrieval → context inspection → mock/hosted provider → mandatory output inspection → privacy-aware SQLAlchemy audit → safe response.

- `backend/detectors.py`: regex/context/entropy rules; PAN format, contextual Aadhaar-like identifiers with Verhoeff checksum, Luhn-valid cards, IFSC, emails, mobile numbers, contextual bank accounts, credential formats, and direct/indirect injection indicators.
- `backend/gateway.py`: authorization, risk, enforcement, context and output inspection, audit decisions. Block, denied access, and pending approval stop before provider invocation.
- `backend/database.py`: SQLAlchemy schema, initialization, default policies, synthetic documents. SQLite by default. `DATABASE_URL` is the abstraction boundary; PostgreSQL requires an appropriate driver and migrations.
- `backend/providers.py`: bounded hosted adapter and deterministic mock. Mock stores the last sanitized input/permitted context only in process memory for tests, never audit records.
- `backend/main.py`: authenticated API, policy and document management, aggregate analytics, metadata-only review records.
- `src/main.tsx`, `src/styles.css`: responsive landing and security workspace.

The local retrieval alternative uses lexical relevance ranking after permission filtering instead of ChromaDB. It is sufficient for the small synthetic corpus but does not implement vector embeddings, semantic search, or chunk-level indexing. The ZIP-delivered OCR, AES-GCM vault, Laya scorer adapter, and output guard now live under `backend/secure_layers`; their heavyweight dependencies remain optional and the gateway fails closed when they are not configured. Python 3.14 is installed on the development laptop, so the base install avoids model downloads. No paid API is needed for the offline demo.

## Enforcement

Policies have enabled state, category, confidence threshold, scope (role/user/all), and WARN/MASK/BLOCK/REDACT/REQUIRE APPROVAL actions. Decision precedence is block → approval → sanitize → warn → allow. Thresholds match detector confidence; they do not weaken document authorization. Authorization, unsafe context handling, and output protection are mandatory. Numeric risk is an explanatory heuristic, using confidence, category severity, and multiple category signals; 0–24 low, 25–49 medium, 50–74 high, 75–100 critical.

Approval requests are held in bounded server memory for 15 minutes and have metadata-only database records. An administrator reviews and explicitly executes an approved request once; execution rechecks permissions and all other controls using the original identity. Restart or expiration discards pending content. Approval does not override output security or authorization. A production approval service needs encrypted persistence, individual identities, and a safe reviewer evidence workflow.

All model outputs receive mandatory scanning. Structured values are redacted. Credential/injection/classification findings are withheld. Restricted document sentence matches are withheld regardless of input policies. This similarity check is heuristic and cannot reliably prevent paraphrased or encoded leakage from a hostile model. Unauthorized context is never sent by the retrieval path.

## API

Interactive schema: http://127.0.0.1:8000/docs. Login returns a session bearer token, held in browser session storage. Tokens expire after one hour and are invalidated on logout; backend restart invalidates all sessions.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/logout` | Login / authenticated |
| GET | `/api/auth/me`, `/api/health` | Authenticated / public |
| POST | `/api/chat`, `/api/demos/run` | Authenticated; approved gateway chat and feature-demo execution |
| GET | `/api/documents`, `/api/documents/vault` | Authenticated; server-filtered document listing |
| POST, PUT, DELETE | `/api/documents`, `/api/documents/upload`, `/api/documents/{id}` | Authenticated; owner/admin rules apply; unverified binary uploads remain unavailable for retrieval |
| GET, PUT | `/api/me/document-retention` | Authenticated; retention preference for secure-chat uploads |
| GET | `/api/incidents`, `/api/analytics`, `/api/evaluation` | Administrator |
| GET, PUT | `/api/policies`, `/api/policies/{id}` | Administrator |
| GET, PUT | `/api/settings/access`, `/api/settings/access/{employee}/monitoring`, `/api/settings/access/{employee}/resources/{document}` | Administrator; access and privacy-safe monitoring metadata |
| GET | `/api/settings/activity`, `/api/me/dashboard`, `/api/me/history` | Authenticated; scope-filtered privacy-safe aggregates/history |
| GET, PUT | `/api/approvals`, `/api/approvals/{id}` | Administrator |
| POST | `/api/approvals/{id}/execute` | Administrator; approved request only |

## Configuration and hosted LLM

See `.env.example`. Local Python does not automatically load `.env`; set environment variables in the shell before starting it. Docker Compose loads project `.env` automatically. Never put keys in Vite variables or frontend source. Set `LLM_PROVIDER=hosted`, `LLM_API_KEY`, optional `LLM_BASE_URL`, and `LLM_MODEL` for an OpenAI-compatible chat completions endpoint. The adapter has a 25-second timeout and no unsafe fallback. Hosted execution was not tested without an API key. Mock output is explicitly labeled and does not offer general-purpose model reasoning.

NeMo Guardrails, Laya, and Presidio are not silently emulated: the approved pipeline reports them as unavailable and withholds execution until their verified package/model contracts are configured. When OCR dependencies are installed, binary uploads are decoded by magic bytes and processed through the ZIP OCR layer; unreadable or unsupported files remain `uploaded_unprocessed` and are never forwarded as provider context. Set `LAYA_MODEL_DIR` plus `AEGIS_VAULT_KEY` (or `LEAK_GW_KEYS`) to activate the ZIP Laya/privacy-vault path. Do not present the local mock or deterministic detector suite as proof of a live external model deployment.

## Docker

```powershell
docker compose up --build
```

Open http://127.0.0.1:8080. Nginx serves the frontend and proxies same-origin API calls to the private backend. A named volume persists SQLite. Docker definitions are provided but were not executed on this laptop. For external hosting, use TLS at a reverse proxy and complete `docs/THREAT-MODEL.md` production checks first. The Vite development server is for local use.

## Privacy

Ordinary audit events store UTC timestamp, incident ID, keyed pseudonymous identity, category, risk, matched policies, action/outcome, provider, call status, and latency. They never contain raw prompts, full responses, detected secret values, or document titles. Retention defaults to 30 days and expired records are removed on the next gateway request. Audit persistence errors fail closed. Raw pending requests and mock last-call evidence exist only in process memory. Documents are intentionally retained in SQLite for retrieval and are not encrypted at rest in this demo. Browser session-only sanitized evidence is not persisted. Change `AUDIT_HMAC_KEY` and `DEMO_PASSWORD` before shared deployment. Seed content and fixtures are synthetic; illustrative PAN identifiers are not verified identities.

## Troubleshooting

- Keep both backend and frontend running. Vite forwards `/api` to port 8000; HTTP 502 means the backend is unavailable.
- If a port is already occupied, stop the previous owned server; do not start duplicate instances.
- Sessions expire on restart; sign in again.
- An expired approved request returns HTTP 410; submit it again for fresh review.
- Empty charts mean no live gateway requests yet. Run the chat scenarios. Evaluation cases use a separate database and do not inflate live counters.
- Policy changes affect subsequent requests only. Use default actions from the seed configuration to reproduce evaluation cases.
- Document editing requires replacement content; originals are not returned through a raw-content API.

See `docs/DEMO.md` for judge instructions and `docs/THREAT-MODEL.md` for implemented boundaries and remaining limitations.
