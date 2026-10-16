"""
backend_adapters.py -- plugs Laya + encryption into the backend's adapter slots.

The patch you uploaded shows the slot contract the backend uses (tests/test_nemo_guardrails.py):

    adapters = (NemoAdapter(), <laya adapter>, <output inspector>, <provider>)
    class AllowLaya:  async def inspect(self, text): return {"action": "ALLOW", "findings": []}

LayaPrivacyAdapter implements that same `async inspect(text)` signature.
ASSUMPTION (not verifiable from the files I have): the backend accepts an action string other than ALLOW/BLOCK
for "sensitive, mask it" and reads `findings` as a list of dicts. Both are configurable below. If your
approved_pipeline.py expects different names, change ONLY the constants / `_finding()` here.

Findings never contain the raw value: only kind, offsets, reason, probability and an HMAC fingerprint.
"""
from __future__ import annotations

import asyncio

from .privacy_gate import PrivacyGate


class LayaPrivacyAdapter:
    ACTION_ALLOW = "ALLOW"
    ACTION_MASK = "MASK"          # <- rename if approved_pipeline.py uses another word (e.g. "REDACT")

    def __init__(self, gate: PrivacyGate):
        self.gate = gate

    @staticmethod
    def _finding(d, fingerprint: str) -> dict:
        return {"kind": d.kind, "start": d.start, "end": d.end, "reason": d.reason,
                "p_sensitive": d.p_sensitive, "fingerprint": fingerprint}

    async def inspect(self, text: str) -> dict:
        # Laya inference is blocking (torch): keep it off the event loop.
        _cands, decisions, degraded = await asyncio.to_thread(self.gate.analyze, text)
        findings = [self._finding(d, self.gate.vault.fp.fingerprint(text[d.start:d.end]))
                    for d in decisions if d.sensitive]
        return {"action": self.ACTION_MASK if findings else self.ACTION_ALLOW,
                "findings": findings, "degraded": degraded}


class NemoRulesAdapter:
    """Same contract as the backend's NemoAdapter, but calls guardrails/actions.py directly (no NeMo runtime).
    Use it for tests or as a fallback; in the real backend keep NemoAdapter (it runs the actual NeMo rail)."""

    async def inspect(self, text: str) -> dict:
        from guardrails.actions import inspect_text
        r = inspect_text(text or "")
        return {"action": "BLOCK" if r["blocked"] else "ALLOW",
                "findings": [{"reason_code": c} for c in r["reason_codes"]], "risk": r["risk"]}
