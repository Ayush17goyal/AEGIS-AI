# AEGIS AI — Phases and Build Plan

> **Version:** 1.1 · **Date:** 2026-10-15 · Companion to `PRD.md` (requirements), `Architecture.md` (design), `Rules.md` (conduct).
> Effort sizes are **rough estimates for one focused builder** (S ≈ ½–1 day, M ≈ 1–2 days, L ≈ 2–4 days) — not commitments. The submission date is unknown (PRD open question 3); adjust after you decide it.

> ### 🧠 AI AGENT INSTRUCTION — READ FIRST, EVERY SESSION
> 1. Read `memory.md` → find the **Current phase** and **Next step**.
> 2. Work only on the active phase unless blocked; tick checkboxes here **and** log them in `memory.md`.
> 3. **Before ending the session, update `memory.md`** (Rules §1.3). A phase is not complete until its exit criteria are met and recorded there.

---

## 0. How to read this plan

**2026-10-15 correction:** The completed board below describes the historical regex/mock prototype. It does not certify finalized Architecture v2. The user's selected NeMo + Laya pipeline takes precedence over historical LLaMA/custom-detector plans. Active work is the Studio audit/repair: UI, contracts, ACL, privacy/crypto and failure tests repaired; real input/output components and model execution still blocked by unresolved prerequisites. See `../STUDIO-AUDIT.md` and `memory.md`.

Current v2 exit checklist:

- [x] Discover and audit all 20 actual cards and frontend controls.
- [x] Stop false passes; distinguish unavailable modules, mock runs and ACL-only verification.
- [x] Repair persona boundary, safe ID-only Chat prefill, categories and tour navigation.
- [x] SQL ACL filtering, deterministic policy, request privacy, encryption primitive and fail-closed integration tests.
- [x] Actual local browser integration, frontend verification tests and production build.
- [ ] Identify and verify selected Laya model/interface/weights/training.
- [ ] Install/configure and execute vetted NeMo input rails and Presidio local NLP.
- [ ] Verify real hosted provider and full input-to-output labelled evaluation.
- [ ] Resolve generated-output fixture and approval semantics before enabling their cards.

The overall v2 feature is not complete while these dependencies remain unresolved.

- **Order = P0 → P1 → P2.** P0 (Phases 0–4) delivers the headline: *sensitive data never reaches the external LLM*. P1 (Phases 5–9) completes the original brief. P2 is polish.
- Every phase has **Goal · Tasks · Requirements covered · Exit criteria · Evidence to record**.
- **Regression gate:** from Phase 3 onward, every demo scenario that already exists must still pass at the end of each phase (Scenario 1 from Phase 3, Scenario 2 from Phase 5, Scenario 3 from Phase 6).
- **Parallel track — UI:** after Phase 3 the frontend can proceed against the real API plus fixtures, in parallel with backend phases (see Track B at the end).

### Status board

| Phase | Name | Priority | Size | Status | Notes |
|---|---|---|---|---|---|
| 0 | Foundations | P0 | S | ✔ completed | FastAPI backend, Vite + React 19 frontend, SQLite, Dockerfile, scripts |
| 1 | Detection core | P0 | L | ✔ completed | Verhoeff, Luhn, PAN, phone, IFSC, bank account, credentials, entropy, injection |
| 2 | Policy, sanitization, vault | P0 | M | ✔ completed | Declarative policy schema, floor enforcement, MASK/REDACT sanitization |
| 3 | Gateway API, provider connector → **Scenario 1 live** | P0 | L | ✔ completed | `/api/chat`, mock & hosted providers, protection evidence drawer, Scenario 1 live |
| 4 | Decision layer & scoring | P0 | M | ✔ completed | Algorithmic risk scoring (0–100), severity levels, configurable thresholds (LLaMA extensible) |
| 5 | Injection detection + response inspection → **Scenario 2 live** | P1 | L | ✔ completed | Direct injection, `CTX-001` indirect context injection, `OUT-001`/`OUT-002` mandatory output controls |
| 6 | Access-controlled RAG → **Scenario 3 live** | P1 | L | ✔ completed | Server-side pre-filtering, document ACLs, Alice/Bob role separation, Scenario 3 live |
| 7 | Audit log, approvals, metrics API | P1 | M | ✔ completed | Keyed HMAC pseudonyms, 30-day auto-retention, human review queue with 15-min TTL, `/api/analytics` |
| 8 | Web app: workspace, Scenario Lab, dashboard, policy UI | P1 | L | ✔ completed | 7 workspace views, cinematic HeroVideo, multi-tier demo auth modal, live monitor |
| 9 | Evaluation: dataset, metrics, latency | P1 | M | ✔ completed | 46-case synthetic runner (`backend/evaluate.py`), 100% P/R/F1, `evaluation-report.json` |
| 10 | Hardening, deployment, demo and submission | P1/P2 | M | ◐ in progress | `start.ps1`, Docker files, judge demo script (`docs/DEMO.md`), threat model docs |


(Keep this table current; mirror it in `memory.md` → "Current status".)

---

## Phase 0 — Foundations (P0 · S)

**Goal:** a runnable skeleton with quality gates and synthetic-data tooling, so nothing later is built on sand.

**Tasks**
- [x] Create repo layout with backend, src, public, docs, scripts.
- [x] Backend scaffold: FastAPI app (`backend/main.py`), Pydantic models, security headers (`X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, `X-Frame-Options: DENY`, 64KB body limit).
- [x] Frontend scaffold: Vite + React 19 + TS, tokens and styles (`src/styles.css`, `src/landing.css`, `src/theme.css`).
- [x] Pre-commit, `.env.example`, `docker-compose.yml`, `start.ps1`.
- [x] Seeded synthetic data generator and default documents (`DOC-PUBLIC`, `DOC-RESTRICTED`, `DOC-INJECTION`).
- [x] Verify and record installed versions: Python 3.12+, FastAPI, React 19, Vite 6, Tailwind v4, Lucide React, Recharts.
- [x] Create `memory.md` entries: stack versions, decisions, structure.

**Requirements:** foundation for all. **Exit:** test suite green; app starts; security headers and rate-limits active; versions logged.
**Evidence:** command outputs + versions in `memory.md`.

---

## Phase 1 — Detection core (P0 · L)

**Goal:** fast, validated detection of the README's sensitive-data list, robust to obfuscation.

**Tasks**
- [x] `validators/`: Verhoeff checksum algorithm for Aadhaar, Luhn algorithm for payment cards, PAN holder-type validation, IFSC pattern.
- [x] `normalize/`: Unicode NFKC, zero-width character stripping (`\u200b-\u200f\ufeff`), lower-casing, separator handling.
- [x] Detectors: Aadhaar (Verhoeff-validated + lookalike filtering), PAN, mobile (IN), bank account (cue-based), IFSC, card (Luhn), credentials, API keys/tokens (`sk-`, `AKIA`, `ghp_`), private keys (PEM), database connection strings, entropy (>4.3), email, confidential markers.
- [x] Composite rules (`BANK_SMS`) & prompt injection intent detectors with educational exemptions.
- [x] `Finding` dataclass (category, kind, start, end, confidence, `safe()`) — no raw sensitive value field.
- [x] Span merge/overlap resolution.
- [x] Fast pre-screen and compiled regex patterns.

**Requirements:** FR-PI-01..07. **Exit:** all detector tests green; lookalike 12-digit non-Aadhaar numbers not flagged; sub-millisecond deterministic path benchmark recorded.
**Evidence:** 46-case synthetic evaluation report in `backend/evaluation-report.json`, p50/p95 detection time.

---

## Phase 2 — Policy, sanitization, vault (P0 · M)

**Goal:** turn findings into safe text, driven by declarative policy.

**Tasks**
- [x] Policy schema & database model (`backend/database.py`), default policies (`POL-001`..`POL-005`).
- [x] Action severity order: `BLOCK` > `REQUIRE APPROVAL` > `MASK` / `REDACT` > `WARN` > `ALLOW`.
- [x] Sanitizer: `MASK`, `REDACT`, span merging (`[CATEGORY_REDACTED]`).
- [x] Strategy selection by category and configurable policy actions.
- [x] Bounded in-memory session protection with zero raw values in database or audit log.
- [ ] Local token vault database encryption (stretch: separate encrypted SQLite DB with Fernet).

**Requirements:** FR-POL-01..03, FR-SAN-01..06. **Exit:** property tests green; Scenario 1's SMS sanitized correctly in live run and evaluation.
**Evidence:** sanitized before/after examples logged in `memory.md` and visible in chat evidence drawer.

---

## Phase 3 — Gateway API, provider connector → Scenario 1 live (P0 · L)

**Goal:** end-to-end protected chat. The first demo.

**Tasks**
- [x] LLM connector interface (`backend/providers.py`); `mock` provider and `hosted` OpenAI-compatible provider with 25s timeout and fail-closed error handling.
- [x] Pipeline orchestrator (`backend/gateway.py`) with per-stage timing and latency measurement.
- [x] Protected chat endpoint `/api/chat`, `/api/health`, session auth with demo accounts, rate limiting, request size bounds.
- [x] Protection receipt in the response with risk, severity, findings, policies, and sanitized prompt preview.
- [x] Outbound-payload integration test with the mock LLM proving sensitive values never leave process memory.
- [x] Scenario 1 live in app (`Try the security boundary` card 01) and evaluation suite.
- [x] Safe preview (original text not retained in conversation history).

**Requirements:** FR-API-01/02, FR-SAN-07, FR-PI-* (integrated), FR-POL (integrated). **Exit:** **Scenario 1 passes live**; mock-LLM test proves no raw value left the gateway; sub-millisecond latency recorded.
**Evidence:** screenshot/log of "You typed / LLM received", latency breakdown.

---

## Phase 4 — Decision layer & scoring (P0 · M)

**Goal:** model-assisted & algorithmic decision layer, safe by construction.

**Tasks**
- [x] Algorithmic risk scoring (0–100) combining confidence, category weights (secret/injection 1.0x vs 0.7x), and multi-category penalties (+10 per additional category).
- [x] Four severity bands: Low (0–24), Medium (25–49), High (50–74), Critical (75–100).
- [x] Clamping to policy floors; fail-closed behavior on provider errors.
- [x] Configurable confidence thresholds matching detector confidence levels.
- [ ] Local LLaMA 1B/3B structured JSON inference serving (extensible target for Phase 4 bake-off).

**Requirements:** FR-DEC-01..05. **Exit:** property test "never below floor" green; fault-injection green; Scenario 1 works in live app.
**Evidence:** bake-off table, JSON-validity %, latency distribution.

---

## Phase 5 — Injection detection + response inspection → Scenario 2 live (P1 · L)

**Goal:** stop extraction attempts and catch leaks on the way out.

**Tasks**
- [x] Heuristic prompt injection patterns (direct override, system prompt reveal, developer mode impersonation, educational exception filtering).
- [x] Indirect injection scan for retrieved chunks (`CTX-001` untrusted document context defense).
- [x] Output inspection (`OUT-001`): mandatory rescan of model output for secrets, injection, and confidential markers.
- [x] Restricted document sentence match leak withholding (`OUT-002`).
- [x] Spotlighting: retrieved context delimited and scanned before provider call.
- [x] Red-team injection test cases in the 46-case synthetic evaluation suite.
- [x] Scenario 2 live in app (`Try the security boundary` card 02 & card 04).

**Requirements:** FR-INJ-01..06, FR-RI-01..03, FR-RI-05/06, FR-RAG-06. **Exit:** **Scenario 2 passes live** (direct + indirect); canary/leak always blocked; injection metrics reported.
**Evidence:** injection recall/FPR on evaluation suite (100% detection on injection fixtures).

---

## Phase 6 — Access-controlled RAG → Scenario 3 live (P1 · L)

**Goal:** the assistant only reads what the asking user may read.

**Tasks**
- [x] Document model with ACL and classifications (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`).
- [x] Server-side **pre-filtered** retrieval keyed on authenticated session identity (`permitted_documents`).
- [x] Lexical keyword relevance ranking over permitted document subsets.
- [x] Unauthorized retrieval denial (`ACCESS DENY`) with zero metadata leakage.
- [x] Output inspection against restricted document sentences (`OUT-002`).
- [x] Scenario 3 live in app (`Try the security boundary` card 03: Alice permitted for `DOC-RESTRICTED`, Bob denied).

**Requirements:** FR-RAG-01..05, FR-RI-04. **Exit:** **Scenario 3 passes live** with two users; ACL tests green; no confirmation of restricted-doc existence.
**Evidence:** transcript of Alice vs Bob; context capture from the mock LLM.

---

## Phase 7 — Audit log, approvals, metrics API (P1 · M)

**Goal:** privacy-preserving accountability and the data behind the dashboard.

**Tasks**
- [x] Audit writer: privacy-safe `Event` records with keyed HMAC-SHA256 user pseudonyms (`usr-<hmac>`).
- [x] Automatic rolling retention cleanup: purging events older than 30 days (`AUDIT_RETENTION_DAYS`) on each request.
- [x] Human review queue (`REQUIRE APPROVAL`): bounded server memory with 15-minute TTL, admin approve/reject, and atomic one-time execution re-evaluating all gateway security invariants.
- [x] Metrics endpoints: `/api/analytics` (aggregations, timeline, category/action/severity breakdowns, policy effectiveness) and `/api/incidents`.
- [x] Audit database contains zero raw sensitive values.
- [ ] Hash chain verify endpoint (stretch: offline chain audit tool).

**Requirements:** FR-AUD-01..06, FR-POL-04..06, FR-DASH data. **Exit:** audit scan test green; zero raw values in events table; review queue functional.
**Evidence:** verify output, scan test output.

---

## Phase 8 — Web app (P1 · L)

**Goal:** the product experience defined in `design.md`.

**Tasks**
- [x] Design tokens, typography, layout, and cinematic dark theme.
- [x] **Landing page**: Hero section with adaptive `HeroVideo` (WebM VP9 / MP4 H.264, mobile/desktop renditions, Play/Pause control, reduced-motion compliance), 3 pillars, trust strip, feature grid, and footer.
- [x] **Multi-tier Demo Auth**: Individual vs Company tier, persona selector, password visibility toggle.
- [x] **Overview**: KPI cards, operational banner, activity area chart, category donut chart, recent events table.
- [x] **Secure Chat**: Chat UI with automatic/explicit context selector, Safe Preview bubble, response bubble with action badges, collapsible Gateway Evidence drawer, 4 one-click scenario cards, and enforcement path checklist.
- [x] **Live Security Monitor**: Real-time 10-second polling feed with query/severity/action/date filters and sanitized incident modal.
- [x] **Analytics**: 5 comprehensive analytical charts.
- [x] **Policies**: Real-time policy cards with threshold sliders, scope selectors, and human review queue.
- [x] **Document Security**: Server-filtered catalog, `.txt`/`.md` upload (max 20KB), classification badges, and retrieval testing.
- [x] **Evaluation**: Interactive benchmark dashboard displaying `evaluation-report.json`.
- [x] Accessibility pass (keyboard, focus, contrast, reduced motion) and responsive pass.

**Requirements:** FR-API-03/04, FR-DASH-01..06, FR-POL-06. **Exit:** all 7 workspace pages live; responsive mobile & desktop; reduced-motion verified.
**Evidence:** screenshots, live running application at `http://localhost:5173`.

---

## Phase 9 — Evaluation (P1 · M)

**Goal:** honest, reproducible metrics.

**Tasks**
- [x] 46-case synthetic evaluation suite (`backend/evaluate.py`).
- [x] Generation of `backend/evaluation-report.json`.
- [x] 100% precision, 100% recall, 100% F1, 100% legitimate acceptance, 0.70 ms latency, 16 model calls prevented.
- [x] Live display on Evaluation page (`/app/evaluation`).
- [x] Documentation in `docs/EVALUATION.md` and `PRD.md` §9.

**Requirements:** PRD §9, success criteria. **Exit:** report committed; numbers displayed in UI; no target presented as a result.
**Evidence:** `backend/evaluation-report.json` and `docs/EVALUATION.md`.

---

## Phase 10 — Hardening, deployment, demo, submission (P1/P2 · M)

**Tasks**
- [x] `start.ps1`, `docker-compose.yml`, Dockerfiles, `nginx.conf`.
- [x] CyberCup 6.0 judge demo guide (`docs/DEMO.md`).
- [x] Evaluation report documentation (`docs/EVALUATION.md`).
- [x] Video integration guide (`docs/HERO-VIDEO.md`).
- [x] Threat model and production readiness (`docs/THREAT-MODEL.md`).
- [ ] Clean machine containerized end-to-end rehearsal.

**Exit:** all demo scenarios pass live; metrics report current; limitations documented.

### P2 stretch (only after Phase 10 exit)
- Chunk-buffered **streaming** response inspection.
- Browser extension / paste-guard client.
- Additional languages; additional entity packs (passport, driving licence, GSTIN — with validators).
- Policy simulation against historical (sanitized) audit data.
- Role-aware restoration UX; per-department policy overrides.

---

## Track B — UI in parallel (starts after Phase 3)

| Step | Depends on | Output |
|---|---|---|
| B1 tokens + layout + landing page (static, motion specs) | Phase 0 | Landing page matching the reference direction |
| B2 workspace chat + receipts | Phase 3 API | Working protected chat UI |
| B3 Scenario Lab | Phases 3, 5, 6 as they land | Scripted demos |
| B4 dashboard & tables | Phase 7 API (fixtures before) | Incidents UI |
| B5 admin pages | Phases 6–7 | Policies, documents, approvals, audit |
| B6 QA pass | all | `design.md` §18 checklist |

---

## Minimum "winning demo" cut-line (if time runs short)

Keep, in this order: **Phases 0 → 1 → 2 → 3 → 4** (headline), then **Phase 6** (Scenario 3), **Phase 5 (direct injection + canary only)**, a **minimal dashboard** from Phase 7/8, and the **Phase 9 report on whatever set size exists** — stated honestly. Drop first: streaming, approvals UI polish, extra entities, indirect-injection variants beyond the poisoned-document demo, admin pages other than policy dry-run.

---

## Risk checkpoints

| Checkpoint | Question | If "no" |
|---|---|---|
| End of Phase 1 | Is the deterministic path near 50 ms p95? | Optimise patterns/pre-screen before building on it |
| End of Phase 3 | Does NeMo Guardrails fit the latency budget? | Use fallback in Architecture §5 and record AD |
| End of Phase 4 | Is the 1B/3B decision model valid ≥ 99 % of the time and fast enough? | Keep `ambiguous_only`, tighten ambiguity rules, or use deterministic-only with model as audit-time reviewer |
| End of Phase 6 | Does any unauthorised chunk reach the mock LLM? | Stop; fix ACL pre-filter before anything else |
| End of Phase 9 | Do the sample sizes support the claims? | Rewrite claims; expand the generated corpus |
