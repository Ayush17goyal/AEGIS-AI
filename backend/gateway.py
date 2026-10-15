import uuid
import time
import hashlib
import hmac
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete
from .database import Event, Document, Policy, Approval
from .detectors import inspect, sanitize
from . import providers

def authorized(doc,user):
    return user['role']=='admin' or doc.owner_id==user['id'] or user['id'] in doc.allowed_users or user['role'] in doc.allowed_roles or doc.classification=='PUBLIC'

def permitted_documents(db,user,document_id=None):
    # Permission filter is applied before ranking, chunking, or exposing metadata.
    from sqlalchemy import or_, exists, select, func, cast
    query = db.query(Document)
    if document_id:
        query = query.filter(Document.id == document_id)
    if user['role'] != 'admin':
        if db.bind.dialect.name == 'sqlite':
            users = func.json_each(Document.allowed_users).table_valued('value').alias('acl_users')
            roles = func.json_each(Document.allowed_roles).table_valued('value').alias('acl_roles')
            member = exists(select(1).select_from(users).where(users.c.value == user['id']))
            role = exists(select(1).select_from(roles).where(roles.c.value == user['role']))
        else:
            from sqlalchemy.dialects.postgresql import JSONB
            member = cast(Document.allowed_users, JSONB).contains([user['id']])
            role = cast(Document.allowed_roles, JSONB).contains([user['role']])
        query = query.filter(or_(Document.owner_id == user['id'], Document.classification == 'PUBLIC', member, role))
    return query.all()

def severity(score): return 'Critical' if score>=75 else 'High' if score>=50 else 'Medium' if score>=25 else 'Low'

pending_requests={}

async def run(db,user,prompt,document_id=None,approval_granted=False):
    start=time.perf_counter(); findings=inspect(prompt); policies=[]; called=False; context=[]; sanitized=None
    active=db.query(Policy).filter_by(enabled=True).all()
    matches=[p for p in active if p.scope in ('all',user['role'],user['id']) and any(f.category==p.category and f.confidence>=p.threshold for f in findings)]
    policies=[p.id for p in matches]
    rank={'WARN':1,'MASK':2,'REDACT':2,'REQUIRE APPROVAL':3,'BLOCK':4}
    action=max((p.action for p in matches if not (approval_granted and p.action=='REQUIRE APPROVAL')),key=lambda a:rank[a],default='ALLOW')
    reason='Security inspection passed.'
    score=min(100,max((f.confidence*(1 if f.category in ('SECRET','INJECTION') else .7) for f in findings),default=0)+max(0,len(set(f.category for f in findings))-1)*10)
    if document_id:
        doc=db.get(Document,document_id)
        if doc is None or not authorized(doc,user):
            action='ACCESS DENY';score=100;reason='Document access was refused before retrieval.';policies.append('AUTH-001')
            findings=[] # Do not expose requested document metadata.
        else:
            context=[doc.content]
    elif action not in ('BLOCK','REQUIRE APPROVAL'):
        words={w.strip('.,?!:') for w in prompt.lower().split() if len(w)>3}-{'what','this','that','about','summarize','synthetic','document','please'}
        candidates=permitted_documents(db,user)
        context=[d.content for d in sorted(candidates,key=lambda d:len(words & set(d.title.lower().split())),reverse=True) if words & set(d.title.lower().split())][:3]
    if action not in ('ACCESS DENY','BLOCK','REQUIRE APPROVAL'):
        for text in context:
            extra=inspect(text)
            if any(f.category=='INJECTION' for f in extra):
                action='BLOCK';score=100;reason='Untrusted document instructions were blocked.';findings+=extra;policies.append('CTX-001');break
        context=[sanitize(c,[f for f in inspect(c) if f.category in ('PII','SECRET','FINANCIAL')]) for c in context]
    if action=='ACCESS DENY': response='Access denied. No document content was retrieved or sent to the model.'
    elif action=='BLOCK': response='This request was blocked by the security gateway. No model call was made.';reason=reason if reason!='Security inspection passed.' else 'A prevention policy blocked high-risk content.'
    elif action=='REQUIRE APPROVAL': response='This request requires administrator review. An authorized reviewer can approve and execute it within 15 minutes.';reason='Confidential content held for human review; prompt stored only in expiring server memory.'
    else:
        sanitized=sanitize(prompt,[f for f in findings if any(p.category==f.category and p.action in ('MASK','REDACT') for p in matches)])
        called=True
        try:
            output=await providers.provider.generate(sanitized,context)
            output_findings=inspect(output)
            # Output controls are mandatory regardless of configurable input policies.
            restricted=[d for d in db.query(Document).all() if not authorized(d,user)]
            leaked=any(d.content in output or any(s.strip() in output for s in d.content.split('.') if len(s.strip())>35) for d in restricted)
            if leaked:
                response='The model response was withheld because it contained unauthorized information.';action='BLOCK';score=100;reason='Restricted output was withheld.';policies.append('OUT-002')
            elif any(f.category in ('SECRET','INJECTION','CONFIDENTIAL') for f in output_findings):
                response='The model response was withheld by mandatory output security inspection.';action='BLOCK';score=max(score,95);reason='Unsafe model output withheld.';policies.append('OUT-001');findings+=output_findings
            else:
                response=sanitize(output,output_findings)
                if output_findings: action='REDACT';findings+=output_findings;policies.append('OUT-001')
                reason='Sensitive values were replaced before model invocation.' if action in ('MASK','REDACT') else 'Request passed input, access, and output inspection.'
        except Exception:
            response='The model provider is unavailable. Your request was not sent to an alternate provider.';action='ERROR';reason='Provider request failed safely.'
    event_id='INC-'+uuid.uuid4().hex[:8].upper()
    latency=round((time.perf_counter()-start)*1000,2)
    # Keyed pseudonyms, content-free audit events, bounded retention.
    pseudonym=hmac.new(os.getenv('AUDIT_HMAC_KEY','local-demo-only').encode(),user['id'].encode(),hashlib.sha256).hexdigest()[:10]
    cutoff=(datetime.now(timezone.utc)-timedelta(days=int(os.getenv('AUDIT_RETENTION_DAYS','30')))).isoformat()
    db.execute(delete(Event).where(Event.timestamp<cutoff))
    db.add(Event(id=event_id,timestamp=datetime.now(timezone.utc).isoformat(),user='usr-'+pseudonym,categories=sorted(set(f.category for f in findings)) if action!='ACCESS DENY' else ['AUTHORIZATION'],risk=round(score),severity=severity(score),policies=list(set(policies)),action=action,outcome='prevented' if action in ('BLOCK','ACCESS DENY') else 'pending' if action=='REQUIRE APPROVAL' else 'error' if action=='ERROR' else 'protected' if action in ('MASK','REDACT') else 'allowed',model_called=called,provider=providers.provider.name,latency=latency,reason=reason))
    if action=='REQUIRE APPROVAL':
        aid=uuid.uuid4().hex
        db.add(Approval(id=aid,event_id=event_id))
        for key in list(pending_requests):
            if pending_requests[key]['expires']<time.time(): pending_requests.pop(key,None)
        if len(pending_requests)<100:
            pending_requests[aid]={'user':dict(user),'prompt':prompt,'document_id':document_id,'expires':time.time()+900}
    db.commit() # Fail closed if audit persistence fails; never return an unlogged answer.
    return {'id':event_id,'response':response,'risk':round(score),'severity':severity(score),'action':action,'reason':reason,'findings':[f.safe() for f in findings] if action!='ACCESS DENY' else [],'policies':list(set(policies)),'model_called':called,'provider':providers.provider.name,'latency':latency,'sanitized_prompt':sanitize(sanitized,inspect(sanitized)) if sanitized and action in ('MASK','REDACT') else None,'context_count':len(context) if called else 0}
