"""
secure_pipeline.py -- all layers in one request path.

  text / image / PDF / DOCX
    0. (prompt only) NeMo rail on the typed prompt first: cheap, so a blocked prompt never triggers OCR work
    1. OCR layer        attachments -> text (magic-byte sniffing, size caps, unreadable => BLOCK)
    2. NeMo input rail  every document / OCR text                 -> BLOCK = CONTEXT_BLOCKED
    3. Laya + rule floor -> sensitive spans become [PHONE_1] / [D1_PHONE_1]
    4. Encryption       TokenVault, AES-256-GCM records (one request_id, tokens namespaced per segment)
    5. LLM provider     sees masked TEXT only. Raw images/files are never forwarded.
    6. Output guard     Regex + Presidio + vault-ciphertext check, redact or withhold
    7. Restore          only if authorized_to_restore (policy engine's decision); default = masked reply

Any unexpected exception -> BLOCK / PIPELINE_ERROR. Exception text is never returned or logged.
ACL (access_control.py) must run BEFORE this, as in run_approved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Sequence

from .ocr_layer import Attachment, OcrError, OcrLayer
from .output_guard import OutputGuard
from .privacy_gate import PrivacyGate

Provider = Callable[[str, list[str]], Awaitable[str]]     # (masked_prompt, masked_documents) -> reply


@dataclass
class PipelineResult:
    action: str                       # ALLOW | BLOCK
    reason_code: str                  # OK | INPUT_BLOCK | CONTEXT_BLOCKED | ATTACHMENT_UNREADABLE | OUTPUT_CHECK_FAILED | PIPELINE_ERROR
    reply: str                        # text for the user ("" when blocked)
    stages: list[str] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)       # fingerprints only
    degraded: bool = False            # Laya failed -> everything detected was masked
    masked_prompt: str = ""           # safe to log
    detail: str = ""                  # e.g. the OCR error code, TOO_LARGE
    ocr: list[dict] = field(default_factory=list)         # per attachment: kind/pages/confidence/chars (no text)
    output_findings: list[dict] = field(default_factory=list)   # kind/source/offsets (no values)


class SecurePipeline:
    def __init__(self, nemo, gate: PrivacyGate, provider: Provider, ocr: OcrLayer, output_guard: OutputGuard,
                 min_ocr_confidence: float | None = 50.0):
        self.nemo, self.gate, self.provider = nemo, gate, provider
        self.ocr, self.output_guard, self.min_ocr_confidence = ocr, output_guard, min_ocr_confidence

    async def handle(self, *, user_id: str, request_id: str, prompt: str,
                     documents: Sequence[str] = (), attachments: Sequence[Attachment] = (),
                     authorized_to_restore: bool = False) -> PipelineResult:
        stages: list[str] = []
        try:
            # 0. typed prompt
            stages.append("nemo_input")
            if (await self.nemo.inspect(prompt)).get("action") == "BLOCK":
                return PipelineResult("BLOCK", "INPUT_BLOCK", "", stages)

            # 1. OCR
            texts, ocr_info = list(documents), []
            if attachments:
                stages.append("ocr")
            for att in attachments:
                try:
                    r = self.ocr.extract(att)
                except OcrError as e:
                    return PipelineResult("BLOCK", "ATTACHMENT_UNREADABLE", "", stages, detail=e.code, ocr=ocr_info)
                ocr_info.append({"kind": r.kind, "pages": r.pages, "confidence": r.confidence,
                                 "used_ocr": r.used_ocr, "chars": len(r.text), "warnings": r.warnings})
                if self.min_ocr_confidence is not None and r.confidence is not None \
                        and r.confidence < self.min_ocr_confidence:
                    return PipelineResult("BLOCK", "ATTACHMENT_UNREADABLE", "", stages,
                                          detail="LOW_OCR_CONFIDENCE", ocr=ocr_info)
                if r.text.strip():
                    texts.append(r.text)

            # 2. NeMo on every document / OCR text
            if texts:
                stages.append("nemo_context")
            for t in texts:
                if (await self.nemo.inspect(t)).get("action") == "BLOCK":
                    return PipelineResult("BLOCK", "CONTEXT_BLOCKED", "", stages, ocr=ocr_info)

            # 3-4. Laya + rule floor + vault
            stages.append("laya_encrypt")
            p = self.gate.protect(prompt, user_id=user_id, request_id=request_id)
            records, audit, degraded = list(p.records), list(p.audit), p.degraded
            masked_docs = []
            for i, t in enumerate(texts, 1):
                d = self.gate.protect(t, user_id=user_id, request_id=request_id, label_prefix=f"D{i}_")
                masked_docs.append(d.masked_text)
                records += d.records; audit += d.audit; degraded = degraded or d.degraded

            # 5. LLM: masked text only
            stages.append("provider")
            reply = await self.provider(p.masked_text, masked_docs)

            # 6. Output guard (before restore)
            stages.append("output_guard")
            g = self.output_guard.check(reply, records)
            if g.withheld:
                return PipelineResult("BLOCK", "OUTPUT_CHECK_FAILED", "", stages, audit, degraded,
                                      p.masked_text, ocr=ocr_info)
            reply = g.text

            # 7. Restore
            stages.append("restore" if authorized_to_restore else "no_restore")
            reply = self.gate.restore(reply, records, user_id=user_id, request_id=request_id,
                                      authorized=authorized_to_restore)
            return PipelineResult("ALLOW", "OK", reply, stages, audit, degraded, p.masked_text,
                                  ocr=ocr_info, output_findings=g.findings)
        except Exception:                      # fail closed; never surface exception text
            return PipelineResult("BLOCK", "PIPELINE_ERROR", "", stages + ["error"])
