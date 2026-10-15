# AI Guard frontend demo

Runtime: 03:35. Captioned walkthrough of the running frontend; no voiceover.

## Chapters

- 00:00 — Welcome to AI Guard: Choose personal protection or an organization workspace.
- 00:04 — Company roles: Administrator, limited employee, and normal employee map to verified demo identities.
- 00:09 — Administrator sign-in: The role filters the account list. Backend credentials determine actual permissions.
- 00:13 — Security overview: Live dashboard: monitored requests, prevention outcomes, risk, and recent events.
- 00:18 — Secure AI chat: Choose a prompt or a synthetic security scenario, then send it through the gateway.
- 00:25 — Safe requests are allowed: The offline demo model receives the inspected request and returns a protected response.
- 00:30 — Personal data protection: Load synthetic personal data to demonstrate masking before the model is called.
- 00:38 — Explainable gateway evidence: Masked identifiers, detector confidence, and policy IDs explain the decision.
- 00:43 — Prompt injection defense: Instruction overrides are blocked before reaching the model.
- 01:00 — Untrusted document defense: Document-borne instructions are inspected before model context is accepted.
- 01:10 — Confidential review workflow: Sensitive business requests can be held for administrator review before model execution.
- 01:19 — Live security monitor: Review content-free audit events, filter outcomes, and inspect individual incidents.
- 01:33 — Security analytics: Review measured enforcement outcomes, category breakdowns, and policy effectiveness.
- 01:42 — Policy management: Inspect policy actions, thresholds, and scope. Mandatory controls remain enforced.
- 01:50 — Human review queue: Confidential requests appear as metadata-only review records; this demo rejects the held request.
- 01:58 — Document security: Administrators inspect classification, ownership, and explicit document permissions.
- 02:03 — Document creation form: Classification, content, and allowed users or roles can be configured before saving.
- 02:18 — Authorized document retrieval: Test retrieval checks the signed-in identity before passing approved context to the model.
- 02:27 — Evaluation and benchmarking: Measured results from synthetic fixtures, including precision, recall, and enforcement checks.
- 02:36 — Normal employee access: Alice has assigned document permissions and no organization-wide administration.
- 02:44 — Authorized employee retrieval: Alice can retrieve the synthetic Orion budget because her backend identity is permitted.
- 02:54 — Limited employee boundaries: Bob can use the assistant, but restricted company content remains inaccessible.
- 03:09 — Individual login: Personal accounts skip company role selection and enter their own restricted workspace.
- 03:14 — Password visibility and validation: Show or hide the password; incorrect credentials return a clear sign-in error.
- 03:21 — Personal workspace: The individual identity has secure chat and permitted documents, with no admin navigation.
- 03:30 — Secure sign-out: Sign out ends the session and returns to the public AI Guard experience.

## Recording notes

- Uses the existing deterministic offline model; no hosted model was configured.
- Evaluation metrics shown are from the existing 46-case synthetic report, not real-world accuracy claims.
- The document creation form was demonstrated by saving a public synthetic checklist: Video demo - Safe AI checklist (DOC-56eff00241).
- Demo chat requests created normal audit events. The synthetic confidential request was rejected in the review queue.
- Existing policy values were saved without modification. No application source code was changed for this recording.
- Editing access and uploading a text file are visible in the document form; they were not executed in this walkthrough.
- Approval execution is available in the product; the recorded review demonstrates rejection instead.
