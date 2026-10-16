"""Deterministic input rules registered with NeMo Guardrails as `aegis_inspect_input`.

The action returns reason codes and a risk level only. It never returns, logs or
stores the matched text (Rules.md section 3).

Risk levels:
  high   -> the input rail blocks (override, prompt disclosure, secret/cross-user extraction,
            instructions hidden in pasted content)
  medium -> not blocked here; reported so the policy engine can decide
  none   -> nothing found

Hinglish coverage is a small starter set and is UNVERIFIED against real usage.
"""

import re
import unicodedata

from nemoguardrails.actions import action

RULES_VERSION = "1"
# Defence in depth only. The gateway already caps prompts at 12,000 chars (backend/main.py) and
# uploaded documents at 20,000 chars; retrieved documents pass through this same rail, so the
# bound must be the larger of the two or valid documents would be blocked as CONTEXT_BLOCKED.
MAX_INPUT_CHARS = 20_000

_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")

_I = re.IGNORECASE
_IS = re.IGNORECASE | re.DOTALL

# (reason_code, risk, compiled pattern). Quantifiers are bounded to keep matching cheap.
_RULES = [
    # --- Direct override / jailbreak -------------------------------------------------
    ("INJ_OVERRIDE_INSTRUCTIONS", "high", re.compile(
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|of\s+|the\s+|your\s+|my\s+)*"
        r"(?:previous|prior|above|earlier|preceding|original|system|safety)\s+"
        r"(?:instructions?|prompts?|rules|directives|guidelines|restrictions|messages)\b", _I)),
    ("INJ_OVERRIDE_INSTRUCTIONS", "high", re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass)\s+(?:all\s+|any\s+)?your\s+(?:\w+\s+)?"
        r"(?:instructions?|rules|guidelines|restrictions|safeguards|programming)\b", _I)),
    ("INJ_OVERRIDE_INSTRUCTIONS", "high", re.compile(
        r"\bbypass\s+(?:the\s+|your\s+)?(?:safety|security|content)\s+"
        r"(?:filters?|guardrails?|restrictions?|checks?)\b", _I)),
    ("INJ_ROLE_OVERRIDE", "high", re.compile(
        r"\byou\s+are\s+now\s+(?:in\s+)?(?:dan\b|developer\s+mode|unrestricted|unfiltered|jailbroken)", _I)),
    ("INJ_ROLE_OVERRIDE", "high", re.compile(
        r"\b(?:enable|activate|enter|switch\s+to)\s+(?:developer|god|admin|debug|unrestricted)\s+mode\b", _I)),
    ("INJ_ROLE_OVERRIDE", "high", re.compile(r"\bdo\s+anything\s+now\b", _I)),
    ("INJ_ROLE_OVERRIDE", "high", re.compile(
        r"\bpretend\s+(?:that\s+)?(?:you|to)\b.{0,40}\b(?:no|without)\s+"
        r"(?:restrictions|rules|limits|filters|guidelines)\b", _IS)),
    ("INJ_ROLE_OVERRIDE", "high", re.compile(
        r"\bact\s+as\b.{0,30}\b(?:unrestricted|unfiltered|jailbroken)\b", _IS)),
    # --- System prompt disclosure ----------------------------------------------------
    ("INJ_REVEAL_SYSTEM_PROMPT", "high", re.compile(
        r"\b(?:reveal|show|print|display|output|repeat|leak|dump|expose|share|tell\s+me|give\s+me)\b"
        r"[^.\n]{0,40}\b(?:your|the|its|this)\s+(?:system|hidden|initial|original|secret|internal)\s+"
        r"(?:prompt|instructions?|message)\b", _I)),
    ("INJ_REVEAL_SYSTEM_PROMPT", "high", re.compile(
        r"\brepeat\s+(?:everything|all|the\s+text|the\s+words)\s+(?:above|before)\b", _I)),
    ("INJ_REVEAL_SYSTEM_PROMPT", "high", re.compile(
        r"\bwhat\s+(?:is|are|were)\s+your\s+(?:system\s+prompt|hidden\s+instructions|initial\s+instructions)\b", _I)),
    # --- Fake role / delimiter tokens ------------------------------------------------
    ("INJ_DELIMITER_TOKEN", "high", re.compile(
        r"<\|(?:im_start|im_end|system|endoftext)\|>|\[/?INST\]|<<\s*SYS\s*>>", _I)),
    ("INJ_DELIMITER_TOKEN", "high", re.compile(
        r"^\s*#{2,}\s*(?:system|instruction)s?\b|-{3,}\s*end\s+of\s+(?:system\s+)?(?:prompt|instructions?)", _I | re.MULTILINE)),
    # --- Extraction of secrets / other users' data -----------------------------------
    ("EXT_SECRETS", "high", re.compile(
        r"\b(?:reveal|show|list|print|dump|give\s+me|tell\s+me|leak|expose|share|send\s+me)\b"
        r"[^.\n]{0,30}\b(?:all|every|any)\b[^.\n]{0,20}"
        r"\b(?:secrets?|passwords?|api\s+keys?|credentials|tokens|private\s+keys?)\b"
        r"(?!\s+(?:polic|rotation|manager|requirement))", _I)),
    ("EXT_OTHER_USERS_DATA", "high", re.compile(
        r"\b(?:other|another|previous|all|every)\s+(?:users?|customers?|employees?|clients?)(?:'s|s')?\s+"
        r"(?:conversations?|chats?|messages?|history|queries|prompts?)\b", _I)),
    ("EXT_OTHER_USERS_DATA", "high", re.compile(
        r"\bwhat\s+did\s+the\s+(?:previous|last|other)\s+user\s+(?:ask|say|type|write)\b", _I)),
    ("EXT_BULK_LISTING", "medium", re.compile(
        r"\b(?:list|show|dump|export)\s+(?:me\s+)?(?:all|every)\s+(?:the\s+)?(?:customers?|users?|employees?|accounts?)\b", _I)),
    # --- Hinglish starter set (UNVERIFIED coverage) ----------------------------------
    ("INJ_OVERRIDE_INSTRUCTIONS", "high", re.compile(
        r"\bpichle\s+(?:saare\s+|sabhi\s+)?(?:instructions?|nirdesh|niyam)\s+(?:ko\s+)?(?:ignore|bhool|nazarandaz)", _I)),
    ("INJ_REVEAL_SYSTEM_PROMPT", "high", re.compile(
        r"\bsystem\s+prompt\s+(?:ko\s+)?(?:batao|bata\s+do|dikhao|dikha\s+do|bhejo)\b", _I)),
    ("EXT_SECRETS", "high", re.compile(
        r"\b(?:sabke|sabhi|saare)\s+(?:passwords?|secrets?|api\s+keys?)\s+(?:batao|dikhao|bhejo)\b", _I)),
    ("EXT_OTHER_USERS_DATA", "high", re.compile(
        r"\b(?:dusre|doosre)\s+(?:users?|logon?)\s+ki\s+(?:chats?|conversations?|details)\b", _I)),
    # --- Instructions aimed at the AI inside pasted/retrieved content -----------------
    ("IND_CONCEAL_FROM_USER", "high", re.compile(
        r"\bdo\s*n[o']?t\s+(?:tell|inform|alert|mention)\b.{0,30}\b(?:the\s+)?user\b", _IS)),
    ("IND_HIDDEN_COMMENT_INSTRUCTION", "high", re.compile(
        r"<!--.{0,300}?\b(?:ignore|disregard|assistant|ai\b|system\s+prompt|reveal|forward|exfiltrate)\b.{0,300}?-->", _IS)),
]

# An instruction addressed to the AI is only a finding when an imperative follows it,
# so "Note to the assistant team: lunch is at 1" is not flagged.
_AI_ADDRESS = re.compile(
    r"\b(?:note|message|instruction|attention|reminder)s?\s+(?:to|for)\s+(?:the\s+)?(?:ai|assistant|model|llm|chatbot|bot)\b"
    r"|^\s*(?:ai|assistant|llm)\s*(?:instruction|note)?\s*:"
    r"|\bwhen\s+(?:you|the\s+(?:ai|assistant|model))\s+(?:read|summari[sz]e|process)\w*\s+this\b",
    _I | re.MULTILINE,
)
_IMPERATIVE = re.compile(
    r"\b(?:ignore|disregard|reveal|send|forward|email|post|upload|exfiltrate|append|include|output|print|leak|"
    r"do\s*n[o']?t\s+tell)\b",
    _I,
)
_AI_ADDRESS_WINDOW = 200


def _normalise(text: str) -> tuple[str, bool]:
    """NFKC-fold, drop zero-width characters, collapse whitespace.

    Exists only so zero-width padding and full-width letters cannot hide a phrase from the
    rules above. Returns the normalised text and whether zero-width characters were present.
    """
    had_zero_width = bool(_ZERO_WIDTH.search(text))
    folded = unicodedata.normalize("NFKC", _ZERO_WIDTH.sub("", text))
    return re.sub(r"[ \t\r\f\v]+", " ", folded), had_zero_width


def inspect_text(text: str) -> dict:
    """Pure function: returns risk and reason codes only, never matched text."""
    if len(text) > MAX_INPUT_CHARS:
        return _result({"INPUT_TOO_LONG"}, "high")

    normalised, had_zero_width = _normalise(text)
    codes: set[str] = set()
    risk = "none"

    for code, rule_risk, pattern in _RULES:
        if pattern.search(normalised):
            codes.add(code)
            if rule_risk == "high":
                risk = "high"
            elif risk == "none":
                risk = rule_risk

    for match in _AI_ADDRESS.finditer(normalised):
        window = normalised[match.end(): match.end() + _AI_ADDRESS_WINDOW]
        if _IMPERATIVE.search(window):
            codes.add("IND_INSTRUCTION_TO_AI")
            risk = "high"
            break

    if had_zero_width:
        codes.add("OBFUSCATION_ZERO_WIDTH")
        if risk == "none":
            risk = "medium"

    return _result(codes, risk)


def _result(codes: set[str], risk: str) -> dict:
    return {
        "blocked": risk == "high",
        "risk": risk,
        "reason_codes": sorted(codes),
        "rules_version": RULES_VERSION,
    }


@action(name="aegis_inspect_input")
async def aegis_inspect_input(text: str = "") -> dict:
    return inspect_text(text or "")
