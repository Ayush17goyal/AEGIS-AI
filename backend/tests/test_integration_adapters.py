"""Adapter contract tests with explicit doubles; no NeMo/Presidio/live-model claim."""
import asyncio
import json
import sys
from enum import Enum
from types import ModuleType, SimpleNamespace
import httpx
import pytest
from backend import integrations, providers
from backend.approved_pipeline import run_approved
from backend.evaluate import isolated_session
from backend.main import accounts
from backend.privacy import Signal


@pytest.mark.parametrize('state,expected', [('passed','ALLOW'),('blocked','BLOCK'),('modified',None),('error',None)])
def test_nemo_validation_contract(monkeypatch,state,expected):
    class RailStatus(str,Enum):
        PASSED='passed'; BLOCKED='blocked'; MODIFIED='modified'
    options=ModuleType('nemoguardrails.rails.llm.options')
    options.RailStatus=RailStatus
    options.RailType=SimpleNamespace(INPUT='input')
    monkeypatch.setitem(sys.modules,'nemoguardrails.rails.llm.options',options)
    class RailsDouble:
        async def check_async(self,messages,rail_types):
            assert messages==[{'role':'user','content':'Synthetic prompt'}]
            assert rail_types==['input']
            return SimpleNamespace(status=state)
    monkeypatch.setattr(integrations,'nemo_engine',lambda:RailsDouble())
    if expected:
        assert asyncio.run(integrations.NemoAdapter().inspect('Synthetic prompt'))['action']==expected
    else:
        with pytest.raises(integrations.ComponentUnavailable): asyncio.run(integrations.NemoAdapter().inspect('Synthetic prompt'))


def test_presidio_span_mapping_and_regex_are_both_used(monkeypatch):
    class AnalyzerDouble:
        def analyze(self,text,language):
            assert language=='en'
            return [SimpleNamespace(entity_type='PERSON',start=0,end=4,score=.9)]
    monkeypatch.setattr(integrations,'presidio_engine',lambda:AnalyzerDouble())
    findings=integrations.OutputInspector().inspect('Demo contact@synthetic.test')
    assert {f.kind for f in findings}=={'PERSON','EMAIL_ADDRESS'}
    assert all('value' not in f.safe() for f in findings)


def test_hosted_transport_receives_only_sanitized_approved_input(monkeypatch):
    captured=[]
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'Contact output@synthetic.test'}}]})
    client=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(handle),**kwargs))
    monkeypatch.setenv('LLM_API_KEY','synthetic-test-key')
    monkeypatch.setenv('LLM_BASE_URL','https://synthetic.invalid/v1')
    class InputDouble:
        async def inspect(self,text):
            return {'action':'MASK','findings':[Signal('PII','EMAIL_ADDRESS',6,len(text))]}
    class OutputDouble:
        def inspect(self,text): return integrations.output_regex(text)
    db=isolated_session()
    try:
        result=asyncio.run(run_approved(db,accounts['bob'],'Email input@synthetic.test',adapters=(InputDouble(),InputDouble(),OutputDouble(),providers.HostedProvider())))
        assert len(captured)==1
        assert 'input@synthetic.test' not in json.dumps(captured)
        assert '[PROTECTED]' in json.dumps(captured)
        assert '4.2 million' not in json.dumps(captured)
        assert 'output@synthetic.test' not in json.dumps(result)
        assert result['reason_code']=='OUTPUT_MASKED'
    finally: db.close()


def test_hosted_connector_rejects_plain_http(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY','synthetic-test-key')
    monkeypatch.setenv('LLM_BASE_URL','http://synthetic.invalid')
    with pytest.raises(RuntimeError,match='HTTPS'): asyncio.run(providers.HostedProvider().generate('hello',[]))
