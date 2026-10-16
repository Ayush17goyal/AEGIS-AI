"""
privacy_gate.py -- connects  detector -> Laya -> rule floor -> TokenVault.

    prompt
      |  CandidateDetector.find()           candidates (start, end, kind, strong)
      |  LayaScorer.score()                 P(sensitive) per candidate, using +-160 chars of context
      |  decision = (P >= threshold) OR strong_rule       <- fail-closed floor
      |  TokenVault.protect_text()          sensitive spans -> [KIND_n] + AES-256-GCM records
      v
    masked_text  (send to the LLM)   +   records (store in DB)   +   audit (log; no plaintext)

Rules baked in
  * If Laya crashes or returns garbage, EVERY candidate is masked (fail closed), and `degraded=True`.
  * Authorization is checked in restore(); a denied restore returns the masked text unchanged.
  * Nothing returned in `decisions` or `audit` contains a raw value, only an HMAC fingerprint.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from .encryption_layer import Span, TokenVault
from .laya_adapter import CONTEXT_CHARS, DEFAULT_THRESHOLD, Scorer
from .span_detector import Candidate, CandidateDetector


@dataclass
class Decision:
    start: int
    end: int
    kind: str
    p_sensitive: float | None   # None when Laya failed
    laya_flag: bool
    rule_flag: bool
    sensitive: bool
    reason: str                 # laya | rule | laya+rule | laya_error_fail_closed | below_threshold

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProtectResult:
    masked_text: str
    records: list[dict]                 # AES-GCM vault records -> store in DB
    decisions: list[Decision]
    audit: list[dict] = field(default_factory=list)   # safe to log: fingerprints only
    degraded: bool = False              # True if Laya failed and the gate fell back to masking everything

    @property
    def any_sensitive(self) -> bool:
        return any(d.sensitive for d in self.decisions)


class PrivacyGate:
    def __init__(self, vault: TokenVault, scorer: Scorer, detector: CandidateDetector | None = None,
                 threshold: float = DEFAULT_THRESHOLD, context_chars: int = CONTEXT_CHARS):
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be in (0, 1)")
        self.vault, self.scorer = vault, scorer
        self.detector = detector or CandidateDetector()
        self.threshold, self.context_chars = threshold, context_chars

    # ---- step 1: decide -------------------------------------------------- #
    def analyze(self, text: str) -> tuple[list[Candidate], list[Decision], bool]:
        cands = self.detector.find(text)
        if not cands:
            return cands, [], False

        pairs = [(text[max(0, c.start - self.context_chars):min(len(text), c.end + self.context_chars)],
                  text[c.start:c.end]) for c in cands]
        degraded, probs = False, []
        try:
            probs = self.scorer.score(pairs)
            if len(probs) != len(cands) or any(not isinstance(p, float) or math.isnan(p) for p in probs):
                raise ValueError("scorer returned malformed output")
        except Exception:        # never include the exception text: it may echo the prompt
            degraded, probs = True, [None] * len(cands)

        decisions = []
        for c, p in zip(cands, probs):
            if degraded:
                decisions.append(Decision(c.start, c.end, c.kind, None, False, c.strong, True,
                                          "laya_error_fail_closed"))
                continue
            laya_flag = p >= self.threshold
            sens = laya_flag or c.strong
            reason = ("laya+rule" if laya_flag and c.strong else "laya" if laya_flag
                      else "rule" if c.strong else "below_threshold")
            decisions.append(Decision(c.start, c.end, c.kind, round(p, 4), laya_flag, c.strong, sens, reason))
        return cands, decisions, degraded

    # ---- step 2: protect ------------------------------------------------- #
    def protect(self, text: str, *, user_id: str, request_id: str, label_prefix: str = "") -> ProtectResult:
        cands, decisions, degraded = self.analyze(text)
        spans = [Span(d.start, d.end, d.kind) for d in decisions if d.sensitive]
        masked, records = self.vault.protect_text(text, spans, user_id=user_id, request_id=request_id,
                                                   label_prefix=label_prefix)

        tokens = iter(r["token"] for r in records)
        audit = []
        for d in decisions:
            audit.append({
                "request_id": request_id, "kind": d.kind, "decision": "mask" if d.sensitive else "keep",
                "reason": d.reason, "p_sensitive": d.p_sensitive,
                "token": next(tokens) if d.sensitive else None,
                "fingerprint": self.vault.fp.fingerprint(text[d.start:d.end]),
            })
        return ProtectResult(masked, records, decisions, audit, degraded)

    # ---- step 3: restore (only after the policy engine approves) ---------- #
    def restore(self, masked_text: str, records: list[dict], *, user_id: str, request_id: str,
                authorized: bool) -> str:
        return self.vault.restore_text(masked_text, records, user_id=user_id, request_id=request_id,
                                       authorized=authorized)
