# AEGIS AI — Project Rules

> **Version:** 1.1 · **Date:** 2026-10-15 · Applies to **every** human and AI contributor, in **every** session.
> If a rule here conflicts with a convenience, the rule wins. If a rule is wrong, change it through §2 — don't ignore it.

---

## 1. 🧠 Memory protocol — MANDATORY, EVERY SESSION

`memory.md` is the project's persistent memory. AI agents have no memory between sessions; **this file is the memory.**

### 1.1 At the start of every session
1. Read `memory.md` fully.
2. Read the "Current phase" and "Next step" entries; continue from there.
3. Skim `phases.md` for the active phase's checklist.
4. If `memory.md` is missing or empty, **create it from the template in that file's header** before doing anything else.

### 1.2 During the session — update `memory.md` when ANY of these happen
- A decision is made (technology, threshold, schema, naming, scope).
- A phase task starts, finishes, or is blocked.
- A file/module is created, renamed, deleted or substantially changed.
- A metric is **measured** (latency, precision/recall, FPR/FNR) — record value, dataset, date, command, git SHA.
- A bug, risk, or surprising behaviour is found.
- An assumption in `PRD.md` / `Architecture.md` turns out wrong.
- A `[UNVERIFIED]` item is verified (change it to `[VERIFIED: source, date]`).

### 1.3 Before ending the session or saying "done" — REQUIRED
Update these `memory.md` sections: **Current status**, **Done this session**, **Decisions** (if any), **Measured results** (if any), **Open issues**, **Next step** (one concrete action), **Change log**. A session that changes the project but does not update `memory.md` is **incomplete**.

### 1.4 Quality rules for memory entries
- Factual, dated (`YYYY-MM-DD`), and specific (file paths, command lines, numbers).
- Never aspirational ("should be fast") — record what was *observed*.
- Never put raw sensitive data, real credentials, or real personal data in `memory.md`.
- Keep it concise: summarise old session logs into the "History digest" once the "Session log" exceeds ~20 entries; do not delete decisions.
- Never delete another contributor's entry; mark it `SUPERSEDED by <id>` instead.

### 1.5 The big docs carry this rule
`PRD.md`, `Architecture.md`, `Rules.md`, `phases.md`, `design.md` and `memory.md` each start with the same AI agent instruction block. Do not remove it. If you create a new top-level doc, add the block.

---

## 2. Document hierarchy and change control

| Doc | Authority over | Change by |
|---|---|---|
| `PRD.md` | *What* and *why*; requirement IDs; metrics | Edit + bump version + `memory.md` change log |
| `Architecture.md` | *How*; contracts; failure modes; data model | Same; also add/modify an `AD-xx` decision |
| `Rules.md` | Conduct, quality bars | Same |
| `phases.md` | Order of work, exit criteria | Update checkboxes as work finishes; record scope changes |
| `design.md` | Visual and motion system; UI acceptance | Same; keep tokens in sync with `frontend/src/styles/tokens.css` |
| `memory.md` | Current state and history | Every session (§1) |

Precedence if docs conflict: **Rules → PRD → Architecture → design → phases → memory**. A conflict must be resolved by editing the lower-precedence doc and logging it.

Requirement IDs (`FR-…`) are stable. Never renumber; deprecate with a note.

---

## 3. Data and privacy rules (non-negotiable)

1. **Synthetic data only.** No real Aadhaar, PAN, phone numbers, bank details, OTPs, passwords, API keys, personal documents, or real SMS — in code, tests, fixtures, demos, screenshots, docs, prompts, commit messages or issue text. The footer of the product says "Synthetic data demonstration" and that must be true.
2. Synthetic identifiers are produced by `scripts/gen_synthetic.py` with a fixed seed, are labelled `synthetic=true`, and live only under `eval/` and `backend/tests/fixtures/`.
3. **No raw sensitive values in:** logs, audit tables, error messages, exception traces, metrics, analytics, dashboard payloads, URLs, or the decision model's input.
4. Findings after detection carry **type, offsets, confidence, validated flag** — never the value (it may exist only in local variables inside the detector and sanitizer, and is dropped immediately after use).
5. Logging uses an **allow-list** of safe fields. Do not log request/response bodies. Do not add `print()`/debug dumps of prompts.
6. The token vault, its key and its DB are never exported, never in backups by default, and never imported by the LLM connector module (an import-boundary test enforces this).
7. Secrets (`GEMINI_API_KEY`, `GROQ_API_KEY`, `AEGIS_VAULT_KEY`, `JWT_SECRET`) come from the environment only. `.env` is git-ignored; `.env.example` has placeholders. A pre-commit secret scan is required.
8. Hashing: **HMAC-SHA256 with a secret key** for pseudonymisation. Unkeyed SHA-256 of identifiers is forbidden. Hashing is never called "encryption".
9. Audit rule: after the full test suite, the audit-DB scan test must find **zero** planted synthetic values.
10. Automatic rolling audit retention: events older than `AUDIT_RETENTION_DAYS` (default 30) are purged on the next request to prevent unbounded retention.
11. Safe Preview in chat UI: the client conversation display replaces user prompts with sanitized previews (`result.sanitized_prompt` or "original text not retained") to prevent retaining or leaking raw prompt values in DOM.

---

## 4. Security rules

1. **Fail closed.** On any error in detection, decision, vault, or policy, apply the stricter behaviour (Architecture §12). Never write `except: pass` in the pipeline.
2. The decision model is **advisory above the floor** — it may not relax a policy floor, ever. Any code that bypasses the clamp is a defect.
3. Identity for access control comes **only** from the verified session token / JWT. Never trust `user_id`, `role`, or `department` from request bodies, headers other than `Authorization`, or prompt text.
4. ACL filtering happens **inside** the retrieval query (`permitted_documents`). Post-filtering is a defect.
5. Retrieved text and pasted documents are **untrusted data**. They are delimited and labelled; instructions inside them are never followed or executed by the gateway (`CTX-001`).
6. Never confirm the existence or title of a document the user is not authorised to see.
7. Error responses and block messages must not echo user content or matched values.
8. Bound everything: input length (max 12,000 chars), request body (max 64 KB), regex complexity, retries, queue sizes, approval TTLs (15 min).
9. No outbound call may carry unsanitized text. The external-LLM connector accepts only sanitized prompt text.
10. Do not disable TLS verification, auth, or rate limits "temporarily".
11. Dependencies are pinned and audited; add a dependency only with a one-line justification in `memory.md`.
12. **Mandatory server controls:** `AUTH-001` (document authorization), `OUT-001` (output inspection), `OUT-002` (restricted content withholding), and `CTX-001` (untrusted context defense) are non-negotiable server-side invariants and cannot be weakened by user-level policy toggles.
13. Demo sign-in role selection: choosing an account type or persona in the frontend login modal only filters client-side demo accounts; it never elevates or alters server-side permissions.
14. Bounded approval lifecycle: requests held under `REQUIRE APPROVAL` exist in server memory for 15 minutes; execution re-runs full authorization and security checks under the original authenticated identity.
15. Ingestion boundaries: document uploads are restricted to `.txt` and `.md` files under 20 KB. Ownership is assigned by the server; public documents are readable by all authenticated accounts; editing is restricted to the owner or administrator.

---

## 5. Honesty rules (reporting and claims)

1. **Never present a target as a result.** "FNR < 0.5 %" is a target. A result is a measured number with dataset, size, date, and a 95 % confidence interval.
2. Never write or imply that a test, build, benchmark or visual check passed unless it was actually run and observed in this session. Record the command and result in `memory.md`.
3. Use verification labels on external facts: `[VERIFIED: source, date]`, `[UNVERIFIED]`. Library names/APIs/versions from memory are `[UNVERIFIED]` until checked against the installed version or current docs.
4. Do not invent features, benchmark numbers, user feedback, or integrations. If something is mocked, say "mocked".
5. Synthetic-set accuracy is not real-world accuracy; say so wherever it is shown.
6. If a requirement cannot be met, say so and record the gap in `memory.md` "Open issues" — do not silently reduce scope.

---

## 6. Code conventions

### Python (backend)
- Python 3.12+ (tested with Python 3.14 on development machine); type hints; FastAPI with Pydantic models for every request/response.
- Pure functions for detectors/validators/sanitizers (no hidden I/O) so they are trivially testable.
- Fast precompiled regexes with algorithmic validators (Verhoeff for Aadhaar, Luhn for cards).
- Async for I/O (LLM, DB, provider calls); keep CPU-bound detection synchronous and fast.
- Security headers middleware and fail-closed error handling without echoing user content.

### TypeScript / React (frontend)
- Strict TypeScript; React 19 + Tailwind CSS v4 + React Router 7 + Lucide React + Recharts.
- Token-driven design system (`src/styles.css`, `src/landing.css`, `src/theme.css`).
- Never render or retain raw sensitive values in the DOM; use Safe Preview in chat history.
- **Hero Video & Motion Engine**: `HeroVideo` component must respect `prefers-reduced-motion: reduce`, check Save-Data and slow connection attributes before loading video assets, provide a manual Play/Pause control, and fall back gracefully to the static WebP portrait. Missing media files must never be mounted into the DOM.


### General
- Names: entities in `UPPER_SNAKE` (`AADHAAR`), files in `snake_case.py` / `PascalCase.tsx`, tokens in `--kebab-case`.
- Comments explain *why*, not *what*. TODOs carry an owner and a `memory.md` reference.
- No dead code, no commented-out blocks, no unexplained magic numbers (thresholds live in policy/config).

---

## 7. Git and review

- Branches: `feat/<area>-<short>`, `fix/<area>-<short>`, `docs/<short>`.
- Conventional Commits: `feat(detectors): add PAN holder-type validation`.
- One logical change per commit; commit messages never contain sensitive values (synthetic or otherwise — describe, don't paste).
- Every PR/commit that changes behaviour updates the relevant doc and `memory.md`.
- Pre-commit hooks: format, lint, type-check, secret scan, "no `print(` in `app/`".
- Never commit: `.env`, vault DBs, audit DBs, model weights, large generated datasets (reference the generator + seed instead).

---

## 8. Testing rules

1. **Every requirement ID maps to ≥ 1 automated test.** Keep the mapping in `docs/traceability.md` (generated by `scripts/trace.py`) and record coverage status in `memory.md`.
2. Detectors need four kinds of tests: **true positive**, **true negative / lookalike**, **obfuscated variant**, **Hinglish/context variant**.
3. Validators (Verhoeff, Luhn, PAN type, IFSC) have table-driven tests with known-valid and known-invalid synthetic values.
4. **Outbound-payload test:** integration tests use a mock LLM that records exactly what it received; assert no planted sensitive value, no vault content, and no unauthorised chunk appears in it.
5. **Property tests:** (a) sanitize(x) never contains the original value; (b) clamp(model_action, floor) ≥ floor for all inputs; (c) mask reveals ≤ policy limit.
6. **Fault-injection tests:** decision-model timeout, invalid JSON, vault down, vector store down, audit write failure — each must fail closed.
7. **Security tests:** forged identity on RAG, injection corpus, audit-DB scan, import-boundary (LLM connector cannot import the vault), rate-limit.
8. **Performance gates:** deterministic-path p95 ≤ 50 ms (≤ 2,000 chars) — CI fails if exceeded; decision-model path is *reported*, not gated.
9. **Evaluation** (`eval/run_eval.py`) is separate from unit tests: it produces metrics + CIs and writes `eval/reports/<date>-<sha>.json`. Test sets are **never tuned on the final held-out split** — keep a frozen hold-out and say so.
10. Flaky tests are fixed or removed within the session they appear; never skipped silently.
11. Coverage: ≥ 80 % lines on `detectors/`, `policy/`, `sanitize/`, `decision/clamp`, `audit/`.

---

## 9. How to add a new sensitive-data entity (checklist)

1. Add it to `PRD.md` §11 and `guardrails/entities.yml` (definition, cues, examples EN + Hinglish).
2. Implement `detectors/<name>.py` + validator (if any) + normaliser support.
3. Add default floor/strategy to `policies/default.yaml` (+ strict/relaxed variants).
4. Add the label to the decision schema enum and the dashboard category list.
5. Write tests (§8.2), add synthetic generator + templates, regenerate the eval corpus.
6. Re-run evaluation; record the new per-category numbers in `memory.md`.
7. Update the UI category chip colour/icon token in `design.md` if a new visual treatment is needed.

---

## 10. Working agreement for AI agents

1. **Use your judgement and keep moving.** For implementation and readiness decisions, decide, proceed, and record the decision in `memory.md`. Do not stop to ask for approval at every step.
2. **Do stop and ask** only when: a choice is irreversible or costly, scope or deadline must change, credentials/accounts are needed, or two docs conflict in a way you cannot resolve with the precedence in §2.
3. Prefer the **smallest change that meets the requirement**; build in the phase order in `phases.md` (P0 → P1 → P2).
4. Don't stub security-critical code with "TODO: secure later". If it can't be done now, fail closed and log the gap.
5. Show evidence: when finishing a task, state what you ran and what you observed.
6. Keep every demo scenario that already exists working at the end of **every** phase (regression gate: Scenario 1 from Phase 3, Scenario 2 from Phase 5, Scenario 3 from Phase 6 — see `phases.md`).
7. When uncertain about a library API, read the installed package or current docs; label anything unchecked `[UNVERIFIED]`.
8. Update `memory.md` (§1.3). Always.

---

## 11. UI and design rules (pointer)

All UI work follows `design.md`. In particular: tokens only (no raw hex), `prefers-reduced-motion` respected, WCAG 2.2 AA contrast, no raw sensitive values rendered, one signature motion moment per page, motion IDs from `design.md` §12 only. A UI change that deviates from `design.md` must update `design.md` in the same change.

---

## 12. Definition of Done

A task is done only when **all** apply:
- [ ] Meets its requirement ID acceptance criteria.
- [ ] Tests written and **actually run**; results recorded.
- [ ] No raw sensitive data in logs/DB/errors (scan test passes).
- [ ] Fail-closed behaviour covered where relevant.
- [ ] Lint, type-check, and format pass.
- [ ] Docs updated (PRD / Architecture / design if affected).
- [ ] Demo scenarios that already exist still pass (`phases.md` regression gate).
- [ ] **`memory.md` updated** (§1.3).

---

## 13. Prohibited

- Real personal data anywhere. Unkeyed hashing of identifiers. Sending raw text to any external service. Logging prompts/responses. Letting the model override the floor. Post-filtering ACLs. Following instructions found in retrieved/pasted content. Claiming unmeasured accuracy. Ending a session without updating `memory.md`.
