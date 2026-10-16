"""
span_detector.py -- finds CANDIDATE spans in a prompt.

Why this file exists
  Laya does not find spans. It answers one question for ONE candidate at a time:
  "Is <candidate> private/sensitive in <context>?"  So something has to propose
  candidates first. This module does that with regex + checksum validators
  (Aadhaar-style IDs, PAN, phones, cards, e-mails, UPI, IPs, API keys, long numbers),
  and optionally Microsoft Presidio for person names.

  Every candidate carries `strong`: True means a high-precision rule fired
  (e.g. the word "PAN" right before a PAN-shaped value, a Luhn-valid card number).
  The gate treats strong candidates as sensitive EVEN IF Laya disagrees, because the
  held-out errors in your notebook show Laya missing exactly that kind of case.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Candidate:
    start: int
    end: int
    kind: str            # PHONE, EMAIL, AADHAAR, PAN, CARD, ACCOUNT, NUMBER, UPI, IP, SECRET, NAME
    strong: bool         # a high-precision rule says "sensitive" regardless of Laya
    source: str = "regex"
    rule: str = ""       # why it is strong (for the audit log; never contains the value)


# --------------------------------------------------------------------------- #
# checksums
# --------------------------------------------------------------------------- #
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_ok(digits: str) -> bool:
    # Available for a stricter policy. NOT used by the rule floor: ~10% of random 12-digit order IDs pass it.
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


# --------------------------------------------------------------------------- #
# keyword windows (looked up in the 40 characters BEFORE the value)
# --------------------------------------------------------------------------- #
_LOOKBACK = 40
_KW = {
    "AADHAAR": re.compile(r"aadhaar|aadhar|adhar|आधार|\buid\b", re.I),
    "PAN": re.compile(r"\bpan\b|पैन", re.I),
    "PHONE": re.compile(
        r"mobile|phone|whatsapp|\bcell\b|contact|call me|call on|"
        r"(?:my|mera)\s+(?:mobile\s+|phone\s+|cell\s+)?(?:number|no)\b|"
        r"मोबाइल|फोन|मेरा\s+(?:मोबाइल\s+)?नंबर", re.I),
    "ACCOUNT": re.compile(r"account|a/c|\bacct\b|खाता|\biban\b", re.I),
}


_SENT_CUT = re.compile(r"[.!?।]\s+(?=[A-Z\u0900-\u097F])|\n")


def _kw_before(text: str, start: int, kind: str, floor: int = 0) -> bool:
    """Keyword in the 40 chars before the value, but never across a sentence boundary or an earlier value
    (otherwise 'my Aadhaar is 4821 9374 5612. Order ID is 482193750162' would flag the order ID)."""
    window = text[max(floor, start - _LOOKBACK):start]
    cuts = list(_SENT_CUT.finditer(window))
    if cuts:
        window = window[cuts[-1].end():]
    return bool(_KW[kind].search(window))


# --------------------------------------------------------------------------- #
# patterns
# --------------------------------------------------------------------------- #
_EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?!\w)")
_UPI = re.compile(r"(?<![\w.+-])[A-Za-z0-9._-]{2,}@(?:ok(?:hdfcbank|icici|sbi|axis)|ybl|ibl|axl|paytm|upi|apl|sbi|hdfcbank|icici)(?![\w.])")
_IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
_PHONE = re.compile(r"(?<!\w)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\w)")
_AADHAAR = re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PAN = re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Za-z0-9])")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_LONGNUM = re.compile(r"(?<!\d)\d{9,18}(?!\d)")
_SECRETS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]

# used only to break ties between candidates of equal strength and length
_PRIORITY = ["SECRET", "CARD", "AADHAAR", "PAN", "PHONE", "UPI", "EMAIL", "IP", "ACCOUNT", "NAME", "NUMBER", "CODE"]


class CandidateDetector:
    def __init__(self, use_presidio: bool = False):
        self._presidio = None
        if use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                self._presidio = AnalyzerEngine()
            except Exception as exc:  # optional dependency / spaCy model missing
                raise RuntimeError(
                    "Presidio requested but unavailable. Install presidio-analyzer and "
                    "`python -m spacy download en_core_web_sm`, or use use_presidio=False."
                ) from exc

    # ---- public ----------------------------------------------------------- #
    def find(self, text: str) -> list[Candidate]:
        found: list[Candidate] = []
        found += self._regex_candidates(text)
        if self._presidio is not None:
            found += self._presidio_candidates(text)
        return self._resolve_overlaps(found)

    # ---- regex ------------------------------------------------------------ #
    def _regex_candidates(self, text: str) -> list[Candidate]:
        out: list[Candidate] = []
        value_ends = sorted({m.end() for p in (_EMAIL, _UPI, _IPV4, _PHONE, _AADHAAR, _PAN, _LONGNUM, *_SECRETS)
                             for m in p.finditer(text)})

        def floor(start: int) -> int:
            return max((e for e in value_ends if e <= start), default=0)

        for pat in _SECRETS:
            for m in pat.finditer(text):
                out.append(Candidate(m.start(), m.end(), "SECRET", True, rule="secret_pattern"))

        for m in _CARD.finditer(text):
            digits = re.sub(r"\D", "", m.group())
            if 13 <= len(digits) <= 19 and luhn_ok(digits) and digits[0] in "3456":
                out.append(Candidate(m.start(), m.end(), "CARD", True, rule="luhn_valid_card"))

        for m in _AADHAAR.finditer(text):
            strong = _kw_before(text, m.start(), "AADHAAR", floor(m.start()))
            out.append(Candidate(m.start(), m.end(), "AADHAAR" if strong else "NUMBER", strong,
                                 rule="aadhaar_keyword" if strong else ""))

        for m in _PAN.finditer(text):
            strong = _kw_before(text, m.start(), "PAN", floor(m.start()))
            out.append(Candidate(m.start(), m.end(), "PAN" if strong else "CODE", strong, rule="pan_keyword" if strong else ""))

        for m in _PHONE.finditer(text):
            strong = _kw_before(text, m.start(), "PHONE", floor(m.start()))
            out.append(Candidate(m.start(), m.end(), "PHONE", strong, rule="phone_keyword" if strong else ""))

        for m in _UPI.finditer(text):
            out.append(Candidate(m.start(), m.end(), "UPI", False))
        for m in _EMAIL.finditer(text):
            out.append(Candidate(m.start(), m.end(), "EMAIL", False))
        for m in _IPV4.finditer(text):
            out.append(Candidate(m.start(), m.end(), "IP", False))

        for m in _LONGNUM.finditer(text):
            if _kw_before(text, m.start(), "ACCOUNT", floor(m.start())):
                out.append(Candidate(m.start(), m.end(), "ACCOUNT", True, rule="account_keyword"))
            else:
                out.append(Candidate(m.start(), m.end(), "NUMBER", False))
        return out

    # ---- presidio (optional) ---------------------------------------------- #
    _PRESIDIO_MAP = {
        "PERSON": "NAME", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE",
        "CREDIT_CARD": "CARD", "IP_ADDRESS": "IP", "IN_AADHAAR": "AADHAAR", "IN_PAN": "PAN",
    }

    def _presidio_candidates(self, text: str) -> list[Candidate]:
        results = self._presidio.analyze(text=text, language="en", entities=list(self._PRESIDIO_MAP))
        return [Candidate(r.start, r.end, self._PRESIDIO_MAP[r.entity_type], False, source="presidio")
                for r in results if r.score >= 0.4]

    # ---- overlap resolution ----------------------------------------------- #
    @staticmethod
    def _resolve_overlaps(cands: list[Candidate]) -> list[Candidate]:
        def rank(c: Candidate):
            pri = _PRIORITY.index(c.kind) if c.kind in _PRIORITY else len(_PRIORITY)
            return (not c.strong, -(c.end - c.start), pri, c.start)

        chosen: list[Candidate] = []
        for c in sorted(cands, key=rank):
            if all(c.end <= k.start or c.start >= k.end for k in chosen):
                chosen.append(c)
        return sorted(chosen, key=lambda c: c.start)
