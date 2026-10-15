"""Request-local transformations; no recovery mapping is persisted or exported."""
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    category: str
    kind: str
    start: int
    end: int
    confidence: int = 100

    def safe(self):
        return {"category": self.category, "kind": self.kind, "confidence": self.confidence}


def transform(text, findings, tokenize=False):
    spans = sorted((f.start, f.end) for f in findings)
    merged = []
    for start, end in spans:
        if not 0 <= start < end <= len(text):
            raise ValueError("Invalid sensitive span")
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    mapping = {}
    for start, end in reversed(merged):
        value = text[start:end]
        replacement = "[PROTECTED]"
        if tokenize:
            if value not in mapping:
                mapping[value] = "[PROTECTED_" + secrets.token_hex(8) + "]"
            replacement = mapping[value]
        text = text[:start] + replacement + text[end:]
    return text
