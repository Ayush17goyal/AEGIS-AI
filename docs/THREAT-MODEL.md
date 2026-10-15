# Threat model and production readiness

Assets: retained document text, provider keys, session tokens, pending request content, audit metadata. Trust boundaries: browser/API; authenticated identity/document permissions; untrusted context/model; generated response/user; database/admin.

Implemented invariants:
- Authentication identity is server-owned. Unauthenticated API requests are rejected.
- Authorization precedes relevance ranking and context use. Unauthorized metadata is excluded from lists, and absent or forbidden IDs receive the same safe denial.
- Authorization is independent of numeric scoring and policy toggles.
- Blocked, denied, or unapproved requests do not invoke the provider.
- Retrieved injection instructions are inspected as data.
- Outputs are rescanned independently of configurable input policy states.
- Audit records contain structured content-free metadata and keyed pseudonyms.
- Login is rate limited, inputs are bounded, provider calls have deadlines, and errors never echo provider exception content.

Limitations:
- Rules do not cover every language, obfuscation, encoding, semantic attack, name, or address. Educational wording can suppress injection signals; a motivated attacker may exploit this. Defense relies on independent authorization and output controls too.
- Output restricted-content comparison is literal sentence matching, not a complete semantic disclosure detector. Malicious/paraphrased outputs may evade it.
- The hosted provider's compliance with instructions is not a security guarantee.
- Demo credentials are shared by default. Roles are fixed fixtures; sessions and rate limits are process-local. No SSO, MFA, durable user store, password reset, or account administration.
- Documents are plaintext in SQLite and loaded server-side for permission filtering. This is not a hardened multi-tenant document platform. No malware scanning or binary/PDF document parser; ingestion accepts text only.
- Approval payloads are expiring RAM only. Reviewers see metadata rather than raw confidential evidence. Restarts invalidate pending content; expired records may remain as metadata. No requester notification system.
- Retrieval uses lexical ranking, not embeddings. No semantic quality benchmark or large-corpus performance validation.
- Latency displayed for live requests includes model and audit time. Evaluation uses the mock, so its timing does not predict hosted latency. Security-stage-only telemetry is not yet implemented.
- Tests cover the key demo invariants, not every route, denial-of-service condition, browser attack, or adversarial input distribution.

Production checklist (remaining):
- Replace demo accounts with SSO/OIDC, MFA, individually managed roles, password hashing and rotating sessions.
- Use HTTPS, CSP, secure cookie sessions/CSRF controls, stricter origins, authenticated rate limits, request body streaming limits, and tenant isolation.
- Encrypt documents and approval content, manage keys, restrict DB credentials, and define deletion/backup retention policy.
- Implement reviewed database migrations, PostgreSQL/vector indexes, database-side authorization filters, atomic approval execution and durable queue.
- Add comprehensive policy-change audit records, immutable remote event sink, retention jobs, and alerting.
- Benchmark security-only/model timing separately; add worker-wide session/rate-limit stores.
- Expand multilingual/adversarial tests, test against hosted models, measure semantic leakage and false positives using independently labeled examples.
- Validate Docker builds, operational failover, restore workflows, proxy configuration, and threat-model review before internet exposure.

Generated visual asset: `public/aegis-hero.png`, produced with the built-in imagegen tool. Prompt: cinematic landscape premium website background; upward-looking female android profile, glossy black visor with amber rim, silver hair and teal skin light, centered right with dark negative space on the left, bronze atmospheric glow; no text, logos, or panels. The exact request is also retained in `docs/image-prompt.txt`.
