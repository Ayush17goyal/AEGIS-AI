"""Approved component boundaries. Missing modules never fall back to legacy input regex."""
import asyncio
import importlib.util
import os
import re
from pathlib import Path
from functools import lru_cache
from .privacy import Signal


class ComponentUnavailable(RuntimeError):
    pass


class LayaAdapter:
    # No guessed package/API contract: the selected model is not identified in
    # Architecture v2. Implement only after its repository and labels are verified.
    async def inspect(self, text):
        raise ComponentUnavailable("Laya model identity and inference contract are unresolved")


@lru_cache(maxsize=1)
def nemo_engine():
    config_path = os.getenv("NEMO_CONFIG_PATH", "")
    if not config_path or not Path(config_path).is_dir():
        raise ComponentUnavailable("NeMo input-rail configuration is missing")
    from nemoguardrails import LLMRails, RailsConfig
    config = RailsConfig.from_path(config_path)
    if not config.rails.input.flows:
        raise ComponentUnavailable("NeMo has no configured input rails")
    return LLMRails(config, verbose=False)


class NemoAdapter:
    async def inspect(self, text):
        from nemoguardrails.rails.llm.options import RailStatus, RailType
        result = await asyncio.wait_for(nemo_engine().check_async(
            [{"role": "user", "content": text}], rail_types=[RailType.INPUT]
        ), timeout=15)
        if result.status == RailStatus.BLOCKED:
            return {"action": "BLOCK", "findings": []}
        # Unknown/error statuses must never become ALLOW.
        if result.status != RailStatus.PASSED:
            raise ComponentUnavailable("NeMo inspection did not confirm allow")
        return {"action": "ALLOW", "findings": []}


@lru_cache(maxsize=1)
def presidio_engine():
    # Do not trigger implicit model downloads while serving a user request.
    model = os.getenv("PRESIDIO_SPACY_MODEL", "en_core_web_sm")
    if importlib.util.find_spec(model) is None:
        raise ComponentUnavailable("Presidio local NLP model is missing")
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    engine = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": model}]}).create_engine()
    return AnalyzerEngine(nlp_engine=engine, supported_languages=["en"])


OUTPUT_PATTERNS = (
    ("PII", "EMAIL_ADDRESS", r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    ("PII", "IN_PAN", r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b"),
    ("PII", "PHONE_NUMBER", r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)"),
    ("SECRET", "CREDENTIAL", r"(?i)\b(?:password|api[_ -]?key|secret)\s*[:=]\s*\S+"),
    ("SECRET", "PROVIDER_KEY", r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20,})\b"),
)


def output_regex(text):
    return [Signal(category, kind, match.start(), match.end())
            for category, kind, pattern in OUTPUT_PATTERNS for match in re.finditer(pattern, text)]


class OutputInspector:
    def inspect(self, text):
        findings = output_regex(text)
        for result in presidio_engine().analyze(text=text, language="en"):
            findings.append(Signal("PII", result.entity_type, result.start, result.end, round(result.score * 100)))
        return findings


def component_status():
    components = []
    for name, factory in (("NeMo Guardrails", nemo_engine), ("Microsoft Presidio", presidio_engine)):
        try:
            factory()
            components.append({"name": name, "status": "configured", "detail": "Initialized locally; request-time failures still fail closed"})
        except Exception:
            components.append({"name": name, "status": "missing", "detail": "Package, local model, or input-rail configuration unavailable"})
    components.append({"name": "Laya", "status": "missing", "detail": "Selected model repository and inference contract have not been provided"})
    from .providers import provider
    live = provider.name == "hosted" and bool(os.getenv("LLM_API_KEY"))
    components.append({"name": "Real LLM", "status": "configured" if live else "missing", "detail": "Hosted configuration present; connectivity unverified" if live else "Offline mock is not a live model"})
    return components
