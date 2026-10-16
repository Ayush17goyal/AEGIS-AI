"""
laya_adapter.py -- the ONLY place that knows how to talk to the trained Laya model.

What the model is (from your notebook, cells 10 / 17 / 21)
  * A fine-tuned multilingual encoder (jhu-clsp/mmBERT-base + a Laya head), one question: is_sensitive, type "noul".
  * INPUT  : one (context, candidate) pair, formatted EXACTLY as in training:
                 state = {"body": "Context: <text around the value>\\nCandidate: <the value>"}
  * OUTPUT : one float per pair, P(candidate is sensitive in this context), already calibrated
             by the temperature saved in the checkpoint (rl_agent_config.json).
  * It does NOT return labels like PHONE/EMAIL and it does NOT return spans.
  * Operating threshold chosen on validation in your notebook: 0.78 (F2-optimal with FPR <= 10%).

Requires (only where the real model is used): pip install laya "transformers<5" torch
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Protocol, Sequence

# Must equal the training text character for character (notebook cell 21 says so too).
QUESTIONS = {
    "is_sensitive": {
        "type": "noul",
        "instructions": "Is the candidate private or sensitive information in this context?",
    }
}
DEFAULT_THRESHOLD = 0.78      # your validation-chosen operating point
CONTEXT_CHARS = 160           # the training contexts were text[start-160 : end+160]


def build_state(context: str, candidate: str) -> dict:
    return {"body": f"Context: {context}\nCandidate: {candidate}"}


class Scorer(Protocol):
    def score(self, pairs: Sequence[tuple[str, str]]) -> list[float]: ...


class LayaScorer:
    """Wraps the exported folder (laya-pii-v3/). Returns P(sensitive) for each (context, candidate)."""

    def __init__(self, model_dir: str | os.PathLike, device: str | None = None, batch_size: int = 16):
        import laya  # imported lazily so the rest of the backend works without torch installed

        model_dir = Path(model_dir)
        qfile = model_dir / "questions.json"
        if qfile.exists():  # guard against the classic silent bug: question text drifting from training
            saved = json.loads(qfile.read_text(encoding="utf-8"))
            if saved != QUESTIONS:
                raise RuntimeError("questions.json in the model folder differs from QUESTIONS in laya_adapter.py")
        if device is None:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        self.agent = laya.load(str(model_dir), device=device)
        self.batch_size = batch_size

    def score(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        states = [build_state(c, k) for c, k in pairs]
        out: list[float] = []
        for i in range(0, len(states), self.batch_size):
            chunk = states[i:i + self.batch_size]
            for o in self.agent.predict_batch(chunk, QUESTIONS, batch_size=self.batch_size):
                out.append(float((o.get("answers", o))["is_sensitive"]["noul"]))
        return out


# --------------------------------------------------------------------------- #
# NOT a model. A keyword stand-in so the pipeline and the encryption tests run on a
# laptop / CI without torch or the 640 MB weights. Never use it for real decisions.
# --------------------------------------------------------------------------- #
class KeywordStubScorer:
    _PRIVATE = re.compile(
        r"\bmy\b|\bmine\b|\bmera\b|\bmeri\b|मेरा|मेरी|personal|call me|whatsapp|applicant|"
        r"customer|salary|aadhaar|आधार|\bpan\b|account|mobile|phone|card|password|ssn|passport|"
        r"lives|address", re.I)

    def score(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        out = []
        for ctx, cand in pairs:
            before = ctx.split(cand, 1)[0][-60:]
            out.append(0.95 if self._PRIVATE.search(before) else 0.05)
        return out
