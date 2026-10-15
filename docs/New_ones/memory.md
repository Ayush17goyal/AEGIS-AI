# AEGIS AI — Project Memory (`memory.md`)

> **This file is the project's persistent memory.** AI agents forget everything between sessions; this file is how the project remembers.
> **Version:** 1.0 · **Created:** 2026-10-15 · **Last updated:** 2026-10-15

> ### 🧠 AI AGENT INSTRUCTION — MANDATORY, EVERY SESSION
> **START of session:** read this whole file. Continue from **§1 Current status → Next step**.
> **DURING:** update this file whenever you make a decision, finish or block a task, create/change/delete a file, measure a metric, find a bug, or verify an `[UNVERIFIED]` item.
> **END of session (before saying "done"):** update **§1 Current status**, **§2 Done this session** (append to §9), **§4 Decisions** (if any), **§6 Measured results** (if any), **§7 Open issues**, **§1 Next step**, and **§10 Change log**. A session that changes the project without updating this file is incomplete.
> **Rules for entries:** factual, dated `YYYY-MM-DD`, specific (paths, commands, numbers, git SHA). Observed facts only, never aspirations. No real personal data, no real credentials, no raw sensitive values — ever. Never delete another entry; mark `SUPERSEDED by <id>`. Full rules: `Rules.md` §1.

---

## 1. Current status

| Field | Value |
|---|---|
| **Project** | AEGIS AI — CC6-AI03 "Detection and Prevention of Data Leakage through AI Models" (CyberCup 6.0) |
| **Owner** | Pratham (handle: v8god) |
| **Current phase** | Architecture v2 Studio audit/repair; frontend and fail-closed foundations repaired, full live security pipeline incomplete |
| **Phase board** | Historical P0–P9 completion describes regex/mock prototype only; v2 input/output/model integration remains blocked |
| **Scenarios live** | Bob ACL-only denial verified through actual HTTP/browser. Model-dependent scenarios NOT IMPLEMENTED until required components exist. |
| **Last session date** | 2026-10-15 |
| **Repo state** | Existing React/FastAPI preserved. Default protected endpoints use approved fail-closed pipeline. Legacy regex/mock path requires explicit offline regression flag. Temporary browser test servers/DB were isolated and cleaned up. |
| **Tests run / result** | 2026-10-15: 96 backend tests passed (1 Starlette deprecation warning), 41 frontend verification/render tests passed, 11 media tests passed, 16 actual Edge browser assertions passed, TypeScript/Vite build succeeded. Model tests use explicit doubles; no live NeMo/Laya/Presidio/provider inference established. |
| **Blockers** | Exact Laya model repository/interface/weights/training unspecified; NeMo/Presidio/config/local model absent; real provider configuration/connectivity unverified; approval semantics and generated-output demo fixture unresolved. |
| **▶ NEXT STEP** | Obtain the selected Laya repository/model ID or local implementation path and verify its task, input/output contract, labels and span support before implementing inference. |

---

## 2. Project snapshot (stable facts)

**AD-13 correction, 2026-10-15:** Snapshot bullets, requirement checkmarks and earlier session claims below describe the historical regex/mock prototype. They are preserved for history, not certification of finalized Architecture v2. The latest user explicitly selects v2 over conflicting older PRD/phase/memory statements. The UI now supports both dark/light themes and enlarged typography; old dark-only statements are superseded.

**Done this session:** audited all 20 actual cards; repaired result assertions/provenance, OUTPUT filter, six-step tour, persona session isolation, ID-only prefill, error/loading states, and mobile overflow; added approved fail-closed orchestrator, missing-component reporting, deterministic policy/privacy and SQL ACL filtering/recheck; guarded demo auth and legacy approval execution; added AES-256-CCM primitive, captured transport/output/privacy/failure tests, safe validation errors and bounded chat/body handling. Full implementation inventory is in `../STUDIO-AUDIT.md`; operating and limited jury guides are in `../STUDIO-GUIDE.md`.

- **Product:** a security gateway between users and an LLM. Three pillars: **Input inspection**, **Authorized retrieval**, **Output protection**. Cross-cutting: configurable actions, privacy-aware audit log, dashboard.
- **Core flow (README & Live Gateway):** Authenticate Identity → Inspect Prompt (Verhoeff/Luhn checksums, regex, context cues, entropy, injection patterns) → Apply Prevention Policies (`ALLOW`, `WARN`, `MASK`, `REDACT`, `BLOCK`, `REQUIRE APPROVAL`) → Authorize Document Context (server-side pre-filtering + `CTX-001` untrusted context scan) → Provider Call (Mock or Hosted OpenAI-compatible with timeout) → Mandatory Output Inspection (`OUT-001`, `OUT-002` restricted sentence withholding) → Privacy-safe Audit Event (keyed HMAC pseudonyms, rolling 30-day purge).
- **Stack (live):** Python 3.12+ (tested on Python 3.14) + FastAPI + SQLAlchemy + SQLite (`aegis.db`) · React 19 + TypeScript + Vite 6 + Tailwind CSS v4 + React Router 7 + Lucide React + Recharts · Adaptive HeroVideo Engine (WebM VP9 / MP4 H.264 loop, Save-Data, reduced-motion compliance) · Docker Compose.
- **Brief requirements → PRD IDs:** R1 prompt inspection `FR-PI`, R2 response inspection `FR-RI`, R3 injection `FR-INJ`, R4 access-controlled RAG `FR-RAG`, R5 configurable actions `FR-POL`, R6 audit `FR-AUD`, R7 dashboard `FR-DASH`; plus `FR-DEC`, `FR-SAN`, `FR-API`.
- **Deliverables:** working gateway; 4 live scenarios in web app (accidental disclosure, injection extraction, unauthorised retrieval, human approval queue); live preventive controls; measured evaluation on 46 synthetic prompts.
- **Design reference:** user's image — amber-visor cinematic hero, headline "INTELLIGENCE. WITHOUT EXPOSURE.", HUD readouts, three pillars. Implemented with seamless forward/reverse hero video loop and dark glassmorphic UI.
- **Data rule:** synthetic data only; footer says "Synthetic data demonstration".

---

## 3. Requirement and phase tracker

Status: ☐ not started · ◐ in progress · ✔ done and tested · ✖ dropped (reason)

| Group | IDs | Status | Phase | Notes |
|---|---|---|---|---|
| Prompt inspection | FR-PI-01 … 07 | ✔ | 1 | Implemented in `backend/detectors.py` (Aadhaar Verhoeff, Luhn cards, PAN, phone, IFSC, bank account, credentials, entropy, injection, composite SMS) |
| Decision model & scoring | FR-DEC-01 … 05 | ✔ | 4 | Implemented in `backend/gateway.py` (0–100 risk scoring, 4 severity tiers, policy floor clamping, fail-closed handling; LLaMA serving extensible) |
| Sanitization | FR-SAN-01 … 07 | ✔ | 2–3 | Implemented in `backend/detectors.py` & `backend/gateway.py` (MASK, REDACT, span merging, Safe Preview in chat UI) |
| Response inspection | FR-RI-01 … 06 | ✔ | 5–6 | Implemented in `backend/gateway.py` (`OUT-001` output detector scan + `OUT-002` restricted sentence leak withholding) |
| Injection detection | FR-INJ-01 … 06 | ✔ | 5 | Implemented in `backend/detectors.py` (direct override, system prompt extraction, educational exceptions) and `backend/gateway.py` (`CTX-001` indirect context injection defense) |
| Access-controlled RAG | FR-RAG-01 … 07 | ✔ | 6 | Implemented in `backend/gateway.py` & `src/main.tsx` (server-side pre-filtering, document ACLs, Alice/Bob role separation, Document Security manager) |
| Policy actions & approvals | FR-POL-01 … 09 | ✔ | 2, 7, 8 | Implemented in `backend/gateway.py`, `backend/database.py`, `src/main.tsx` (real-time policy card toggles, threshold sliders, scope selectors, human review queue with 15-min TTL) |
| Audit log | FR-AUD-01 … 06 | ✔ | 7 | Implemented in `backend/database.py` & `backend/gateway.py` (privacy-safe `events` table, keyed HMAC-SHA256 user pseudonyms, rolling 30-day retention cleanup, zero raw secrets) |
| Dashboard & monitor | FR-DASH-01 … 08 | ✔ | 7–8 | Implemented in `src/main.tsx` (Overview KPI strip + charts, Live Security Monitor with 10s auto-refresh and compound filters, Analytics with 5 charts, Evaluation dashboard) |
| API / client / demo | FR-API-01 … 08 | ✔ | 3, 8 | Implemented in `backend/main.py` & `src/main.tsx` (`/api/*` endpoints, HeroVideo engine, tiered demo login, interactive chat with Gateway Evidence drawer, 4 scenario cards) |
| Evaluation | PRD §9, `EVALUATION.md` | ✔ | 9 | Implemented in `backend/evaluate.py` (46 synthetic cases, 100% P/R/F1, 0% FPR/FNR, 0.70ms latency, rendered in `/app/evaluation`) |


(When an ID is finished, split its row or add a line here: `FR-PI-01 ✔ 2026-xx-xx, tests: <path>, coverage %`.)

---

## 4. Decisions (append-only)

| ID | Date | Decision | Reason | Consequence / status |
|---|---|---|---|---|
| D-01 | 2026-10-15 | Product name **AEGIS AI**, tagline "Intelligence. Protected."; code CC6-AI03 | Taken from the user's design reference and brief | Used across docs and UI copy |
| AD-13 | 2026-10-15 | User-selected finalized Architecture v2 overrides historical expanded PRD/LLaMA/regex implementation claims | Explicit Studio audit request and Architecture v2 §§15–16 | NeMo + Laya input, deterministic Python authority, privacy/ACL, real model, Regex + Presidio output; missing dependencies fail closed; no invented Laya inference. |
| AD-14 | 2026-10-15 | Studio has 15 retained, 3 excluded, 2 pending scenarios; ACL-only PASS is explicitly separate | Catalog source contained 20, not 19, cards; original two-boolean verifier was insufficient | Retained does not mean available; custom invalid checksum/entropy/normalizer disabled, approval/output fixtures pending. |
| AD-15 | 2026-10-15 | Synthetic switch requires a verified admin, revokes old session, cannot escalate employee back | Original frontend embedded shared login password | Production disables demo login; production identity integration remains missing. |
| AD-16 | 2026-10-15 | AES-256-CCM primitive uses env-only 32-byte key, random 13-byte nonce, 16-byte tag, AAD key ID/purpose | Approved recoverable encryption requirement | Independent primitive only: no existing DB encryption, vault schema or automatic restore added. cryptography==49.0.0 and argon2-cffi==25.1.0 pinned for crypto/demo password hashing. |
| D-02 | 2026-10-15 | Scope = full original brief (R1–R7), not only the README's input-side scope; build order P0 → P1 → P2 | README says input-side only but the brief requires response inspection, injection, RAG, dashboard | PRD §12 |
| AD-01 | 2026-10-15 | Policy **floor + clamp**: model output can never lower the policy floor | Model errors must not cause leaks | Architecture §6.4 |
| AD-02 | 2026-10-15 | `decision_mode`: `ambiguous_only` (default), `always` (demo) | 1B/3B inference cannot meet a 50 ms budget; keeps "LLaMA decides" while honest on latency | Two latency budgets in PRD §8; revisit after Phase 4 bake-off |
| AD-03 | 2026-10-15 | Keyed HMAC-SHA256, never unkeyed SHA-256, for hashing identifiers | 10–12 digit identifiers are brute-forceable | Rules §3.8 |
| AD-04 | 2026-10-15 | Decision model sees masked context windows, never raw values | Keep the model outside the sensitive-data boundary | Architecture §6.2 |
| AD-05 | 2026-10-15 | ACL pre-filter inside the vector query + fingerprint check on output | Post-filtering lets restricted text enter the context | Architecture §4.3 |
| AD-06 | 2026-10-15 | Hash-chained audit log, no raw content | Tamper evidence without sensitive data | Architecture §10 |
| AD-07 | 2026-10-15 | Buffered (non-streaming) response inspection in v1 | Correctness first | Streaming is P2 |
| AD-08 | 2026-10-15 | Heuristic, algorithmic & checksum detector suite in pure Python | Sub-millisecond deterministic evaluation, no external model download dependencies | Implemented in `backend/detectors.py` |
| AD-09 | 2026-10-15 | Server-side permission filtering before lexical context ranking | Prevents unauthorized documents from entering context or relevance scoring | Implemented in `backend/gateway.py` |
| AD-10 | 2026-10-15 | Multi-tier demo authentication (Individual vs Company with 3 personas) | Illustrates organizational vs individual data boundary enforcement | Implemented in `src/main.tsx` + `backend/main.py` |
| AD-11 | 2026-10-15 | Adaptive HeroVideo media engine (WebM/MP4, Save-Data, reduced-motion) | Cinematic visual fidelity with strict accessibility and performance fallbacks | Implemented in `src/components/HeroVideo.tsx` |
| AD-12 | 2026-10-15 | Human Review Queue with 15-minute expiring memory and atomic re-check | Prevents stale approval execution and enforces full security re-evaluation | Implemented in `backend/gateway.py` & `src/main.tsx` |
| DD-01 | 2026-10-15 | UI is **dark-only**; Inter Tight + JetBrains Mono; amber accent `#F5A524`; tokens in `design.md` §6 | Matches reference; contrast ratios computed | Implemented in `src/styles.css` |
| DD-02 | 2026-10-15 | Motion: CSS + Motion first; GSAP ScrollTrigger only for the pinned pipeline section if needed | Fewer dependencies; GSAP terms not confirmed | `design.md` §12.6 |
| DD-03 | 2026-10-15 | Hero HUD values are labelled "Illustrative" | Honesty rule (`Rules.md` §5) | `design.md` A4 |
| DD-04 | 2026-10-15 | Multi-step sign-in modal with password reveal toggle | Seamless demo switching between admin, employee, and individual accounts | Implemented in `src/main.tsx` |
| DD-05 | 2026-10-15 | Chat Safe Preview with collapsible Gateway Evidence drawer | Eliminates raw prompt retention in DOM while providing complete transparency | Implemented in `src/main.tsx` |

---

## 5. Assumptions and verification ledger

`[UNVERIFIED]` items must be checked against installed versions / current docs before use. Update the status when verified.

| Item | Status | Date | Source / note |
|---|---|---|---|
| Python version (3.12+ requirement, 3.14 on dev machine) | `[VERIFIED]` | 2026-10-15 | Active development runtime |
| FastAPI version and async route handling | `[VERIFIED]` | 2026-10-15 | `backend/main.py` |
| React 19 + TypeScript 5.7 + Vite 6 | `[VERIFIED]` | 2026-10-15 | `package.json` |
| Tailwind CSS v4 + @tailwindcss/vite | `[VERIFIED]` | 2026-10-15 | `package.json` |
| Lucide React (v0.468+) + Recharts (v2.15+) | `[VERIFIED]` | 2026-10-15 | `package.json` |
| React Router v7 | `[VERIFIED]` | 2026-10-15 | `package.json` |
| Hero video adaptive WebM/MP4 format negotiation & fallback | `[VERIFIED]` | 2026-10-15 | `src/components/HeroVideo.tsx`, `scripts/hero-media.test.mjs` (11 tests passed) |
| Motion install `npm install motion`, import `motion/react` | `[VERIFIED]` | 2026-10-15 | motion.dev/docs/react-quick-start |
| Motion reduced-motion API (`useReducedMotion`, config option) | `[PARTIAL]` | 2026-10-15 | Hook listed in docs sidebar; behaviour not confirmed |
| GSAP `registerPlugin(ScrollTrigger)`, `start`/`end`/`scrub`/`pin` | `[VERIFIED]` | 2026-10-15 | gsap.com/docs/v3/Plugins/ScrollTrigger/ |
| LLaMA serving tool structured-output (JSON schema) option | `[UNVERIFIED]` | — | Extensible target for local 1B/3B integration |
| Vector store choice (Chroma / FAISS) vs Lexical filtering | `[VERIFIED]` | 2026-10-15 | Implemented server-side pre-filtered lexical retrieval in `backend/gateway.py` |
| Statistical claim: ~600 positives for FNR < 0.5%; ~300 negatives for FPR < 1% | Reasoned | 2026-10-15 | PRD §9 |

---

## 6. Measured results (append; never overwrite)

Format: `date · what · dataset (n) · value (95 % CI) · command · git SHA`.

| Date | Metric | Dataset (n) | Value | Command | SHA |
|---|---|---|---|---|---|
| 2026-10-15 | Synthetic evaluation suite | 46 cases (25 pos, 21 neg) | Precision: 100%, Recall: 100%, F1: 100%, Acceptance: 100%, Prevented calls: 16, Mean latency: 0.70ms | `python -m backend.evaluate` | local run |
| 2026-10-15 | Backend repair tests | 96 tests: 18 legacy, 43 approved-path, 28 crypto, 7 adapter/transport | 96 passed, 1 deprecation warning, 2.60 s | `python -m pytest backend/tests -q` outside Windows sandbox | no Git repository in checkout |
| 2026-10-15 | Frontend contract/render tests | 41 explicit scenario tests | 41 passed, no failures/skips | `npm.cmd run test:studio` | no Git repository |
| 2026-10-15 | Media regression tests | 11 tests | 11 passed | `node --test scripts/hero-media.test.mjs` | no Git repository |
| 2026-10-15 | Real browser integration | Edge, isolated HTTP servers + synthetic DB + offline mock configuration | 16 assertions passed, including ACL-only refusal, prefill/no send, filters/tour/mobile/error | `npm.cmd run test:e2e` with bundled PLAYWRIGHT_MODULE and BROWSER_CHANNEL=msedge | no live-model accuracy measurement |
| 2026-10-15 | Production build | existing frontend | TypeScript + Vite passed; 2214 modules transformed | `npm.cmd run build` | no Git repository |

Targets (not results): deterministic path p95 ≤ 50 ms (≤ 2,000 chars) · FNR < 0.5 % · FPR < 1.0 % · decision-model p95 target ≤ 1 s (to be measured).

Planned datasets: hand-curated hard set (≥ 100) · seeded generated corpus (≥ 600 positives, ≥ 300 negatives, frozen hold-out) · red-team injection set (≥ 40).

---

## 7. Open issues, risks and questions

**Status of questions:**
1. Final demo target: Laptop-ready with `./start.ps1` and `docker-compose.yml` (`[RESOLVED]`).
2. Primary external LLM: Default mock provider for deterministic offline evaluations + hosted OpenAI-compatible adapter (`[RESOLVED]`).
3. Submission / demo date for CyberCup 6.0: Pending user schedule confirmation.
4. Hero portrait: Integrated cinematic character footage with 11.8s loop and static WebP fallbacks (`[RESOLVED]`).
5. Tailwind or plain CSS: Tailwind CSS v4 + tokens in `styles.css` / `landing.css` (`[RESOLVED]`).
6. Dark-only UI: Implemented cinematic dark theme (`[RESOLVED]`).

**Risks:** see `PRD.md` §14 and `docs/THREAT-MODEL.md`.


*Rule: append new issues as `I-nn · date · description · status`; close by marking `RESOLVED <date> — how`.*

| ID | Date | Issue | Status |
|---|---|---|---|
| — | — | (none) | |
| I-01 | 2026-10-15 | Full v2 live pipeline cannot execute: exact selected Laya identity, interface, weights/training unspecified; NeMo and Presidio packages/config/models missing | OPEN; user asked for Laya reference while independent repairs continued |
| I-02 | 2026-10-15 | Real provider not verified; mock is not a live inference result | OPEN; configure backend key/model/HTTPS base only after input/output prerequisites verified |
| I-03 | 2026-10-15 | Approval lifecycle and controlled generated-output demo are unresolved v2 prerequisites | OPEN; cards NOT IMPLEMENTED, legacy execute guarded to explicit offline regression |
| I-04 | 2026-10-15 | Historical all-requirements-complete/19-cards statements overclaim implementation | SUPERSEDED by AD-13/14 and current audit; historical entries retained |
| I-05 | 2026-10-15 | Windows sandbox hangs in asyncio socketpair creation; bundled Chromium revision absent | RESOLVED for verification by running tests outside sandbox and using installed Edge; no application workaround |
| I-06 | 2026-10-15 | SQLite document content remains plaintext; no production IdP/PostgreSQL/live-model integration certification | OPEN; primitive encryption alone is not a storage migration |

---

## 8. File registry

| Path | Purpose | Status |
|---|---|---|
| `docs/New_ones/PRD.md` | Requirements, personas, scenarios, metrics, baseline | v1.1, updated 2026-10-15 |
| `docs/New_ones/Architecture.md` | System context, components, active API, data models, failure modes | v1.1, updated 2026-10-15 |
| `docs/New_ones/Rules.md` | Project rules, memory protocol, security invariants, definition of done | v1.1, updated 2026-10-15 |
| `docs/New_ones/phases.md` | Status board, completed phases (0–9), hardening roadmap | v1.1, updated 2026-10-15 |
| `docs/New_ones/memory.md` | Persistent project memory, status, decisions, measured results | v1.1, updated 2026-10-15 |
| `src/main.tsx` | React 19 single-page app: router, 7 modules, modals, live charts | active, live on port 5173 |
| `src/presets.ts` | 19 feature presets, PRD mappings, examiner tour steps, talking points | active |
| `src/components/FeatureDemos.tsx` | Feature Demonstration Studio view, tour runner, verification drawer | active |
| `src/landing.css`, `src/styles.css` | Cinematic visor theme, design tokens, HUD styles | active |
| `src/components/HeroVideo.tsx` | Adaptive hero video loop player (forward/reverse, WebM/MP4) | active |
| `src/components/heroMedia.ts` | Video asset discovery, connection & reduced-motion filtering | active |
| `backend/main.py` | FastAPI server, auth routes, security headers, rate limits | active, live on port 8000 |
| `backend/gateway.py` | Core pipeline orchestrator, context & output rails, audit logger | active |
| `backend/detectors.py` | Explainable regex, Verhoeff, Luhn, entropy, and injection detectors | active |
| `backend/database.py` | SQLAlchemy SQLite models (`policies`, `documents`, `events`, `approvals`) | active |
| `backend/providers.py` | Mock and hosted OpenAI-compatible LLM provider adapters | active |
| `backend/evaluate.py` | 46-case synthetic benchmark runner | active |
| `backend/evaluation-report.json` | Generated evaluation metrics and per-case results | active |
| `docs/DEMO.md` | Step-by-step judge demonstration guide for CyberCup 6.0 | active |
| `docs/EVALUATION.md` | Benchmark metrics report (100% precision, recall, F1, 0.70ms) | active |
| `docs/HERO-VIDEO.md` | Cinematic hero video integration documentation | active |
| `docs/THREAT-MODEL.md` | Implemented invariants, threat model, and production checklist | active |
| `start.ps1`, `docker-compose.yml` | Deployment scripts and container definitions | active |

---

## 9. Session log (newest first)

### 2026-10-15 — Demo Run/Open buttons and refresh behavior

- Screenshot Run button was disabled by client-side readiness gating, so clicking could never produce a missing-component receipt. Retained scenarios now call the actual approved endpoint under the correct persona even if modules are missing. Backend still fails closed and returns NOT IMPLEMENTED; no legacy or mocked pass is substituted. Unsupported/pending execution and incorrect-persona runs remain disabled.
- `src/components/FeatureDemos.tsx` now uses separate execution permission vs capability checks, shows readiness refresh progress, preserves run receipts on readiness refresh, and navigates to Chat with only a preset ID. `src/demoVerification.ts` adds the execution gate and validated ID-only navigation-state lookup. `src/main.tsx` restores Chat's selected synthetic preset from navigation state after reload without automatically sending.
- Updated `scripts/demo-verification.test.mjs`, `scripts/studio-e2e.mjs` and `docs/STUDIO-GUIDE.md`. Verification: 49 frontend tests passed, 21 actual Edge/HTTP browser assertions passed (including both buttons, unavailable receipt, refresh persistence, Chat reload and no auto-send). TypeScript/Vite production build passed (7.78 s Vite build). Missing model integration prerequisites remain unchanged.
- Current status: button/refresh issue repaired; next user action is refresh the site and use Run demonstration or Open in Secure Chat. Overall integration next step remains verifying the selected Laya model contract.

### 2026-10-15 — Running-backend readiness 404 repair

- Screenshot readiness ERROR traced to stale FastAPI on port 8000: actual listener PID 12208 started before Studio changes; `/api/health` returned old healthy/mock schema, OpenAPI had no `/api/demo/status`, endpoint returned 404. This was not a Laya inference error.
- Restarted only the verified port-8000 owner using this workspace's `backend.main:app`, with backend source reload and hidden window. Existing in-memory sessions require sign-in again. Verified new health `architecture-v2`, OpenAPI endpoint present, authenticated readiness HTTP 200 through a temporary synthetic Bob session; logged that test session out. Components honestly report missing NeMo, Presidio, Laya and real LLM.
- Changed `src/main.tsx` to retain HTTP status on errors, `src/demoVerification.ts` to map 401/403/404/502–504/network failures to actionable messages, and `src/components/FeatureDemos.tsx` to distinguish loading/connection failure from known component unavailability. Updated `start.ps1` to reuse listeners, reject outdated backends clearly, and enable backend source reload for new local starts.
- Tests: `npm.cmd run test:studio` 46/46 passed (five new readiness error tests); `npm.cmd run build` TypeScript/Vite passed, 2214 modules transformed, 11.35 s Vite build. No live detector inference claim. Existing v2 dependency blockers remain open.
- Current next step for screenshot issue: refresh browser and sign in again. Next integration step remains the exact Laya implementation/contract from the user.

### 2026-10-15 — Architecture v2 Studio audit, repair and honest readiness

- Read Rules, PRD, Architecture, phases, memory and design reference. Finalized Architecture is v2; earlier docs still describe LLaMA/custom regex prototype. Applied latest user-selected scope, added explicit supersession notes without deleting history.
- Parallel frontend and backend/crypto audits found 20 actual cards; mismatched Aadhaar claim/fixture, mock live claims, input-only output demo, neutral mismatches, failed-switch tour continuation, unfiltered SQL retrieval, raw validation errors and shared frontend password switching.
- Repaired frontend execution against `/api/demos/run`, strict verdicts, stage/persona/provenance checks, safe evidence, six-step tour including unavailable output, category/search, ID-only handoff and remounted identity state. Kept existing brand/card classes; fixed 30px mobile overflow found by browser.
- Added approved pipeline and adapter boundaries. Missing NeMo/Laya/Presidio/real LLM returns NOT IMPLEMENTED/BLOCK with no provider fallback; authorization denial can complete independently. No Laya interface/outputs invented. Document SQL ACL filtering/recheck; Python ALLOW/MASK/BLOCK/APPROVAL; request-local transform; regex/Presidio output boundary; privacy-safe reason-code audit. Legacy chat/approvals restricted to explicit demo+mock regression.
- Added env-key AES-256-CCM primitive (not storage migration), Argon2id demo-password verification, bounded request bodies/chat requests, safe validation/failure responses, admin-only session switches. Pinned observed base dependencies; no untested model package installation claimed.
- Synthetic test isolation no longer copies live uploaded documents. Historical evaluator no longer counts ERROR as protected detection. Historical evaluation report was not regenerated or relabelled as live evidence.
- Verification: 96 backend, 41 Studio, 11 media tests passed; build passed; 16 real Edge assertions passed. One deprecation warning; no live detector/model execution. Initial browser mobile check failed and was repaired; final browser suite passed. All passing counts refer to explicit tests, not accuracy statistics.
- Source/config/docs inventory: `../STUDIO-AUDIT.md`. User/manual/jury commands: `../STUDIO-GUIDE.md`. Laya clarification is pending. Overall live-model goal remains incomplete.
- Next step: obtain exact selected Laya implementation and inference contract, then configure/verify NeMo, Presidio and real provider with labelled input/output datasets.

### 2026-10-15 — Feature Demonstration Studio & Presets Hub
- **Done:** Created the comprehensive **Feature Demonstration Studio (`/app/demos`)** with 19 interactive feature presets covering all PRD functional requirements, an 8-step Examiner Guided Tour, a real-time persona quick-switcher, and automatic invariant verification.
- **Components & files created/updated:**
  1. `src/presets.ts`: Definitive catalog of 19 feature presets with PRD codes (`FR-PI-01..09`, `FR-INJ-01..05`, `FR-RAG-01..02`, `FR-POL-06`, `FR-RI-01`), invigilator talking points, exact payloads, expected outcomes, and 8-step guided presentation sequence.
  2. `src/components/FeatureDemos.tsx`: Interactive demo studio with 1-click execution against live `/api/chat`, inline verification status drawer (`INVARIANT VERIFIED`), metric meters, detected findings breakdown, sanitized preview, and persona recommendation checks.
  3. `src/main.tsx`: Added `/app/demos` route and sidebar navigation across all roles; added header quick-link and persona indicator; updated `SecureChat` to allow one-click preset loading from full preset catalog.
  4. `src/styles.css`: Glassmorphic styling for demo tour banner, persona switch pills, category filters, and preset result cards matching the amber-visor theme.
- **Verification:** Verified via Vite production build (`npm run build`, 0 errors), TypeScript compiler (`tsc --noEmit`, 0 errors), backend API testing, and browser subagent end-to-end execution of live presets and persona switching.
- **Next step:** Ready for live examination and invigilator presentation using the step-by-step tour.

### 2026-10-15 — Alignment & Feature Synchronization Session
- **Done:** Updated all 5 foundational documents in `docs/New_ones/` (`Architecture.md`, `PRD.md`, `phases.md`, `Rules.md`, `memory.md`) to incorporate all features added to the live website and backend, while strictly preserving the base requirements and architectural floor.
- **Features synchronized:**
  1. **Cinematic Hero Video Engine:** 11.8-second seamless forward/reverse loop, multi-format negotiation (WebM VP9, MP4 H.264), mobile vs desktop asset resolution, Save-Data and slow connection detection, manual Play/Pause button, and WCAG reduced-motion compliance.
  2. **Multi-tier Demo Authentication:** 3-step sign-in modal with Individual User tier vs Company tier (Owner/Admin `admin` Alex Morgan, Limited Employee `bob` Bob Wilson, Normal Employee `alice` Alice Chen), password reveal toggle, bearer session tokens, IP rate limiting (15 attempts/min), and security headers middleware.
  3. **Seven Live Workspace Views:** Overview (KPI strip, activity area chart, category donut, recent events), Secure Chat (context selector, Safe Preview, Gateway Evidence drawer, 4 synthetic scenario cards, Enforcement Path checklist), Live Security Monitor (10s auto-refresh, query/severity/action/date compound filters, sanitized modal), Analytics (5 charts), Policies (real-time card toggles, threshold sliders 0–100, scope selectors, and 15-min expiring Human Review Queue), Document Security (server-filtered catalog, `.txt`/`.md` upload, classification tags, in-place retrieval testing), Evaluation (interactive report dashboard).
  4. **Active Gateway Invariants:** Mandatory server rules `AUTH-001`, `OUT-001`, `OUT-002`, `CTX-001` that cannot be weakened by user-level policy toggles.
  5. **Measured Benchmarks:** 46-case synthetic suite reporting 100% precision, 100% recall, 100% F1, 100% legitimate acceptance, 0.70 ms latency, and 16 model calls prevented.
- **Base principles preserved:** Fail-closed design, deterministic floor above model advice, zero raw secrets in logs/audit/memory, server-enforced JWT identity, and synthetic-only data rules.
- **Next step:** Maintain live server stability, verify containerized Docker build, and practice judge presentation flow (`docs/DEMO.md`).

### 2026-10-15 — Specification session
- **Done:** wrote `PRD.md`, `Architecture.md`, `Rules.md`, `phases.md`, `design.md`, `memory.md` from the user's README, the CC6-AI03 brief, the idea-discussion transcript and the reference image.
- **Verified this session:** Motion install/import path; GSAP ScrollTrigger API semantics; computed WCAG contrast ratios for the full palette (values in `design.md` §6).
- **Could not verify:** Google Fonts repo pages (blocked by robots) → fonts remain `[UNVERIFIED]`.
- **Decisions:** D-01, D-02, AD-01…AD-07, DD-01…DD-03 (§4).
- **Key judgement calls to review:** (a) widened scope from the README's input-side focus to the full brief; (b) two latency budgets and `decision_mode` because a 1B/3B model can't be expected to run inside 50 ms; (c) honest-reporting rule — a 30-prompt test set cannot support a 0.5 % FNR claim; (d) landing sections 02–04 are extensions beyond the reference.
- **No code or tests were run.**
- **Next step:** Phase 0 (§1).

*(Once this log exceeds ~20 entries, roll older ones into a short "History digest" below, in a batch; never delete decisions.)*

---

## 10. Change log (docs and architecture)

2026-10-15 — Demo action repair: separated permission gating from missing-component readiness, enabled truthful backend receipts, preserved receipts on refresh, and persisted only synthetic preset IDs in navigation state for Chat reload. Manual guide and session test evidence updated.

2026-10-15 — Readiness repair: fixed actual stale local backend and actionable frontend error states; made local startup reuse existing listeners and detect stale versions. See session log for actual HTTP evidence and test results.

2026-10-15 — AD-13..16: `PRD.md` v1.2 and `Architecture.md` v2.1 add explicit finalized-scope and observed-readiness corrections; phase board/memory distinguish prototype history from unresolved v2 work. Added Studio audit and manual guide; updated root README/design to link actual status and preserve existing visual system. Full changed-source list in `../STUDIO-AUDIT.md`.

| Date | Doc | Change |
|---|---|---|
| 2026-10-15 | `Architecture.md` | v1.1: Documented implemented components (HeroVideo, multi-tier auth, 7 workspace modules), active `/api/*` routes, SQLAlchemy database models, current codebase layout, and decisions AD-08..AD-12. |
| 2026-10-15 | `PRD.md` | v1.1: Added demo persona mappings, requirements `FR-RAG-07`, `FR-POL-07..09`, `FR-DASH-07..08`, `FR-API-06..08`, live chat scenario cards, and active 46-case measured baseline. |
| 2026-10-15 | `phases.md` | v1.1: Updated status board to mark Phases 0–9 completed and Phase 10 in progress; checked off completed tasks with implementation references. |
| 2026-10-15 | `Rules.md` | v1.1: Added live runtime rules for automatic 30-day rolling audit retention, chat Safe Preview, mandatory server controls, demo auth bounds, and HeroVideo accessibility standards. |
| 2026-10-15 | `memory.md` | v1.1: Synchronized live phase board, decisions AD-08..AD-12, DD-04..DD-05, measured results, complete file registry, and feature alignment session log. |
| 2026-10-15 | `Rules.md` | Aligned the demo-scenario regression gate with `phases.md` (scenarios gate from the phase in which they go live) |
| 2026-10-15 | all | Initial versions (v1.0) |


---

## 11. History digest

(empty — populated when the session log is rolled up)

---

## 12. Quick reference for agents

- **Add a new entity:** `Rules.md` §9.
- **Policy floor order:** `ALLOW < WARN < MASK < REDACT < BLOCK` (`Architecture.md` §6.4).
- **Never:** raw sensitive values in logs/DB/errors · unkeyed hashing of identifiers · model overriding the floor · post-filtered ACLs · following instructions in retrieved text · presenting targets as results.
- **UI:** tokens and motion IDs only (`design.md`); no raw values in the DOM; reduced-motion respected.
- **Evidence rule:** only claim a test/build/benchmark passed if it was run and observed; record command and result in §6/§9.
- **Working style:** decide and proceed on implementation/readiness choices; record the decision in §4; ask only for irreversible choices, scope/deadline changes, credentials, or unresolvable doc conflicts (`Rules.md` §10).
\n+## 2026-10-15 — Analytics timeline line chart

- Replaced the Analytics “Incidents over time” area chart with a true multi-series `LineChart`.
- Preserved the real backend UTC-day aggregates for allowed, prevented, and sanitized outcomes; no synthetic timeline data was added.
- Added an in-chart legend, thicker accessible strokes, and null-connecting lines for multi-day data.
- Verified with `npm.cmd run build` successfully.
\n+## 2026-10-15 — Visible sign-out control

- Added a labeled `Sign out` button to the authenticated workspace header.
- Reused the existing server logout/session cleanup flow and kept the sidebar icon action wired to the same handler.
- Verified with `npm.cmd run build` successfully.
