"""
output_guard.py -- last gate on the MODEL'S reply, before restore and before the user sees anything.

Three independent checks, results merged:
  1. Regex   : span_detector (secrets, cards, Aadhaar/PAN with keyword, phones, e-mail, UPI ...)
  2. Presidio: Microsoft Presidio AnalyzerEngine (English NLP + its own recognizers)
  3. Vault   : vault ciphertext / nonces / envelope JSON appearing in the reply (encrypted data must never leave)
Anything found is replaced with [REDACTED_<KIND>]. If a check itself fails, the reply is WITHHELD (fail closed).

It runs BEFORE restore on purpose: the reply still contains tokens like [PHONE_1], which are safe. An authorized
user's own values are re-inserted afterwards and are deliberately not re-scanned.

Presidio notes: English only (Hindi/Hinglish rely on the regex checks); PERSON is OFF by default because it
redacts every name the model mentions, turn it on with include_person=True.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .span_detector import CandidateDetector

# regex candidates of these kinds are redacted even without a "strong" keyword rule (no Laya context exists on output)
DEFAULT_ALWAYS_KINDS = frozenset({"SECRET", "CARD", "UPI", "EMAIL", "PHONE", "AADHAAR", "PAN"})
PRESIDIO_WANTED = ["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IP_ADDRESS", "IBAN_CODE", "CRYPTO",
                   "US_SSN", "IN_AADHAAR", "IN_PAN", "IN_PASSPORT"]
_PRESIDIO_KIND = {"EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "CREDIT_CARD": "CARD", "IP_ADDRESS": "IP",
                  "IBAN_CODE": "ACCOUNT", "CRYPTO": "SECRET", "US_SSN": "ID", "IN_AADHAAR": "AADHAAR",
                  "IN_PAN": "PAN", "IN_PASSPORT": "ID", "PERSON": "NAME"}
_ENVELOPE_MARKER = re.compile(r"[\"']alg[\"']\s*:\s*[\"']AES-256-GCM[\"']|[\"']kid[\"']\s*:\s*[\"']k\w+[\"']", re.I)


@dataclass
class OutputGuardResult:
    text: str                                   # redacted reply ("" when withheld)
    findings: list[dict] = field(default_factory=list)   # {kind, source, start, end}; never the value
    withheld: bool = False
    reason: str = "OK"                          # OK | REDACTED | OUTPUT_CHECK_FAILED


class OutputGuard:
    def __init__(self, detector: CandidateDetector | None = None, presidio=None, *, require_presidio: bool = True,
                 include_person: bool = False, min_score: float = 0.5, always_kinds=DEFAULT_ALWAYS_KINDS):
        self.detector = detector or CandidateDetector()
        self.min_score, self.always_kinds = min_score, frozenset(always_kinds)
        self.presidio, self._entities = presidio, []
        if self.presidio is None and require_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                self.presidio = AnalyzerEngine()
            except Exception as exc:
                raise RuntimeError("Presidio is required for the output layer but unavailable. "
                                   "pip install presidio-analyzer && python -m spacy download en_core_web_lg "
                                   "(or pass require_presidio=False to run regex-only, which weakens the guard).") from exc
        if self.presidio is not None:
            wanted = PRESIDIO_WANTED + (["PERSON"] if include_person else [])
            supported = set(self.presidio.get_supported_entities(language="en"))
            self._entities = [e for e in wanted if e in supported]      # don't ask for recognizers this install lacks

    # ---- checks ------------------------------------------------------------ #
    def _regex(self, text):
        return [(c.start, c.end, c.kind, "regex") for c in self.detector.find(text)
                if c.strong or c.kind in self.always_kinds]

    def _presidio(self, text):
        if self.presidio is None:
            return []
        res = self.presidio.analyze(text=text, language="en", entities=self._entities)
        return [(r.start, r.end, _PRESIDIO_KIND.get(r.entity_type, "PII"), "presidio")
                for r in res if r.score >= self.min_score]

    @staticmethod
    def _vault(text, records):
        out = []
        for m in _ENVELOPE_MARKER.finditer(text):
            out.append((m.start(), m.end(), "CIPHERTEXT", "vault"))
        for r in records or []:
            for v in (r.get("envelope", {}).get("ct"), r.get("envelope", {}).get("nonce")):
                if v and len(v) >= 12:
                    for m in re.finditer(re.escape(v), text):
                        out.append((m.start(), m.end(), "CIPHERTEXT", "vault"))
        return out

    # ---- public ------------------------------------------------------------ #
    def check(self, text: str, records: list[dict] | None = None) -> OutputGuardResult:
        try:
            hits = self._regex(text) + self._presidio(text) + self._vault(text, records)
        except Exception:                                   # exception text may echo the reply: drop it
            return OutputGuardResult("", [], True, "OUTPUT_CHECK_FAILED")
        if not hits:
            return OutputGuardResult(text)
        merged: list[list] = []
        for s, e, k, src in sorted(hits):                   # union overlapping spans
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e); merged[-1][4].add(src)
            else:
                merged.append([s, e, k, src, {src}])
        out, cur = [], 0
        for s, e, k, _src, srcs in merged:
            out += [text[cur:s], f"[REDACTED_{k}]"]; cur = e
        out.append(text[cur:])
        findings = [{"kind": k, "source": "+".join(sorted(srcs)), "start": s, "end": e} for s, e, k, _s, srcs in merged]
        return OutputGuardResult("".join(out), findings, False, "REDACTED")
