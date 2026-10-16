import os
import base64
import secrets
import hashlib
import hmac
import time
import uuid
import json
import asyncio
import calendar
from datetime import datetime, timezone, timedelta
from contextlib import suppress
from functools import lru_cache
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pathlib import Path
from collections import Counter
from sqlalchemy import or_
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from .database import init_db, Session, Event, Policy, Document, Approval, UserPreference, AdminAudit
from .gateway import run, permitted_documents, pending_requests
from .approved_pipeline import run_approved, status as pipeline_status, demo_enabled
from . import providers
from .secure_layers.ocr_layer import Attachment, OcrError, OcrLayer

app=FastAPI(title='AI Guard Security Gateway',version='1.0.0')
init_db()
cleanup_task = None
sessions={}; attempts={}
chat_attempts={}
accounts={'admin':{'id':'admin','name':'Alex Morgan','role':'admin'},'alice':{'id':'alice','name':'Alice Chen','role':'employee'},'bob':{'id':'bob','name':'Bob Wilson','role':'employee'}}
accounts['individual']={'id':'individual','name':'Personal Demo User','role':'individual'}

RETENTION_POLICIES = {'1_week': '1 week', '1_month': '1 month', '1_quarter': '1 quarter', '1_year': '1 year'}

def retention_deadline(start: datetime, policy: str) -> datetime:
    if policy == '1_week':
        return start + timedelta(days=7)
    months = {'1_month': 1, '1_quarter': 3, '1_year': 12}[policy]
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return start.replace(year=year, month=month, day=min(start.day, calendar.monthrange(year, month)[1]))

def cleanup_expired_documents(db):
    now = datetime.now(timezone.utc)
    expired = db.query(Document).filter(
        Document.delete_at.is_not(None),
        Document.delete_at <= now.isoformat(),
        or_(Document.deletion_status.is_(None), Document.deletion_status != 'deleted'),
    ).all()
    for document in expired:
        # The current storage provider is the database content column. Clear it
        # only after selecting the record for deletion and retain no sensitive data.
        document.content = None
        document.processing_status = 'deleted'
        document.deletion_status = 'deleted'
        document.deleted_at = now.isoformat()
    if expired:
        db.commit()
    return len(expired)

async def document_cleanup_loop():
    while True:
        try:
            with Session() as db:
                cleanup_expired_documents(db)
        except Exception:
            pass
        await asyncio.sleep(60)

@app.on_event('startup')
async def start_document_cleanup():
    global cleanup_task
    cleanup_task = asyncio.create_task(document_cleanup_loop())

@app.on_event('shutdown')
async def stop_document_cleanup():
    if cleanup_task:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

@app.middleware('http')
async def security_headers(request: Request,call_next):
    max_request_bytes = int(os.getenv('MAX_REQUEST_BYTES', str(16 * 1024 * 1024)))
    if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0')) > max_request_bytes:
        return JSONResponse({'detail':'Request too large'},status_code=413)
    if request.method in ('POST','PUT','PATCH'):
        size=0
        chunks=[]
        async for chunk in request.stream():
            size+=len(chunk)
            if size > max_request_bytes: return JSONResponse({'detail':'Request too large'},status_code=413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    try:
        response=await call_next(request)
    except Exception:
        response=JSONResponse({'detail':'Security processing failed closed'},status_code=503)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Cache-Control']='no-store';response.headers['X-Frame-Options']='DENY'
    return response

@app.exception_handler(RequestValidationError)
async def safe_validation_error(request:Request,exc:RequestValidationError):
    # Pydantic's default error includes the invalid input, which can be a secret.
    return JSONResponse({'detail':'Invalid request fields or size'},status_code=422)

def db_session():
    with Session() as db: yield db

def current_user(request:Request):
    token=request.headers.get('authorization','').removeprefix('Bearer ')
    session=sessions.get(token)
    if not session or session['expires']<time.time(): raise HTTPException(401,'Sign in to continue')
    return accounts[session['id']]

def admin(user=Depends(current_user)):
    if user['role']!='admin': raise HTTPException(403,'Administrator permission required')
    return user

class Login(BaseModel):
    username:str=Field(max_length=40)
    password:str=Field(max_length=200)

@lru_cache(maxsize=1)
def demo_password_hash(expected):
    return PasswordHasher().hash(expected)

@app.post('/api/auth/login')
def login(body:Login,request:Request):
    if not demo_enabled(): raise HTTPException(403,'Synthetic demo login is disabled. Production identity integration is not configured.')
    host=request.client.host if request.client else 'local'; now=time.time()
    attempts[host]=[t for t in attempts.get(host,[]) if now-t<60]
    if len(attempts[host])>=15: raise HTTPException(429,'Too many attempts; retry in a minute')
    attempts[host].append(now)
    expected=os.getenv('DEMO_PASSWORD','AegisDemo!2026')
    try:
        valid=PasswordHasher().verify(demo_password_hash(expected),body.password)
    except VerifyMismatchError:
        valid=False
    if body.username not in accounts or not valid: raise HTTPException(401,'Invalid credentials')
    token=secrets.token_urlsafe(32);sessions[token]={'id':body.username,'expires':now+3600}
    return {'token':token,'user':accounts[body.username]}

class DemoSwitch(BaseModel):
    username: str = Field(max_length=40)

@app.post('/api/auth/demo-switch')
def demo_switch(body:DemoSwitch,request:Request,user=Depends(admin)):
    if not demo_enabled(): raise HTTPException(403,'Demo switching is disabled')
    if body.username not in accounts: raise HTTPException(400,'Unknown demo identity')
    # Only a verified administrator can enter a lower-privilege synthetic session.
    # That session cannot escalate back: sign in again with demo credentials.
    sessions.pop(request.headers.get('authorization','').removeprefix('Bearer '),None)
    token=secrets.token_urlsafe(32)
    sessions[token]={'id':body.username,'expires':time.time()+3600}
    return {'token':token,'user':accounts[body.username]}

@app.post('/api/auth/logout')
def logout(request:Request,user=Depends(current_user)):
    sessions.pop(request.headers.get('authorization','').removeprefix('Bearer '),None)
    return {'ok':True}

@app.get('/api/auth/me')
def me(user=Depends(current_user)): return user

class Chat(BaseModel):
    prompt:str=Field(min_length=1,max_length=12000)
    document_id:str|None=Field(default=None,max_length=100)

def limit_chat(user):
    now=time.time()
    for key in list(chat_attempts):
        chat_attempts[key]=[t for t in chat_attempts[key] if now-t<60]
        if not chat_attempts[key]: del chat_attempts[key]
    history=chat_attempts.setdefault(user['id'],[])
    if len(history)>=30: raise HTTPException(429,'Too many requests; retry in a minute')
    history.append(now)

@app.post('/api/chat')
@app.post('/v1/chat')
async def chat(body:Chat,user=Depends(current_user),db=Depends(db_session)):
    limit_chat(user)
    if os.getenv('AEGIS_PIPELINE')=='legacy' and demo_enabled():
        if providers.provider.name!='mock': raise HTTPException(503,'Legacy regression mode cannot use an external provider')
        result=await run(db,user,body.prompt,body.document_id)
        return {**result,'execution_status':'LEGACY','stages':['legacy_regex_pipeline']}
    return await run_approved(db,user,body.prompt,body.document_id)

@app.get('/api/demo/status')
def demo_status(user=Depends(current_user)):
    return pipeline_status()

class DemoRun(Chat):
    preset_id: str = Field(min_length=1,max_length=100)

@app.post('/api/demos/run')
async def demo_run(body:DemoRun,user=Depends(current_user),db=Depends(db_session)):
    # Live studio execution always uses the approved path, even if a developer
    # explicitly enables the separate legacy regression pipeline for chat.
    limit_chat(user)
    return await run_approved(db,user,body.prompt,body.document_id)

def row(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

@app.get('/api/incidents')
def incidents(user=Depends(admin),db=Depends(db_session)):
    return [row(e) for e in db.query(Event).order_by(Event.timestamp.desc()).limit(500)]

def account_event_identity(account):
    return 'usr-'+hmac.new(os.getenv('AUDIT_HMAC_KEY','local-demo-only').encode(), account['id'].encode(), hashlib.sha256).hexdigest()[:10]

class MonitoringUpdate(BaseModel):
    level: str = Field(pattern='^(summary|security|full)$')

class ResourceAccessUpdate(BaseModel):
    allowed: bool

@app.get('/api/settings/access')
def settings_access(user=Depends(admin), db=Depends(db_session)):
    employees=[]
    for account in accounts.values():
        if account['role'] != 'employee':
            continue
        preference=db.get(UserPreference, account['id'])
        employees.append({
            'id': account['id'], 'name': account['name'],
            'email': account['id']+'@aegis.local', 'status': 'Active',
            'monitoring_level': preference.monitoring_level if preference and preference.monitoring_level else 'summary',
            'resource_count': len(permitted_documents(db, account)),
        })
    resources=[]
    for document in db.query(Document).filter(Document.deletion_status != 'deleted').order_by(Document.title).all():
        resources.append({
            'id': document.id, 'name': document.title, 'type': document.mime_type or document.classification or 'Document',
            'owner_id': document.owner_id, 'owner': accounts.get(document.owner_id, {}).get('name', document.owner_id),
            'public': document.classification == 'PUBLIC',
            'access': {account['id']: ('owner' if document.owner_id == account['id'] else 'shared' if account['id'] in (document.allowed_users or []) or account['role'] in (document.allowed_roles or []) else 'public' if document.classification == 'PUBLIC' else 'none') for account in accounts.values() if account['role'] == 'employee'},
        })
    return {'employees': employees, 'resources': resources, 'mandatory': [
        {'id':'AUTH-001','name':'Document authorization'},
        {'id':'OUT-001','name':'Output inspection'},
        {'id':'CTX-001','name':'Untrusted context protection'},
    ]}

@app.put('/api/settings/access/{employee_id}/monitoring')
def update_monitoring(employee_id: str, body: MonitoringUpdate, user=Depends(admin), db=Depends(db_session)):
    employee=accounts.get(employee_id)
    if not employee or employee['role'] != 'employee': raise HTTPException(404, 'Employee not found')
    preference=db.get(UserPreference, employee_id)
    if not preference: preference=UserPreference(user_id=employee_id)
    preference.monitoring_level=body.level
    db.add(preference)
    db.add(AdminAudit(id='AUD-'+uuid.uuid4().hex[:10].upper(), administrator_id=user['id'], action='monitoring.changed', target_id=employee_id, outcome='success'))
    db.commit()
    return {'employee_id': employee_id, 'monitoring_level': body.level}

@app.put('/api/settings/access/{employee_id}/resources/{document_id}')
def update_resource_access(employee_id: str, document_id: str, body: ResourceAccessUpdate, user=Depends(admin), db=Depends(db_session)):
    employee=accounts.get(employee_id)
    document=db.get(Document, document_id)
    if not employee or employee['role'] != 'employee': raise HTTPException(404, 'Employee not found')
    if not document or document.deletion_status == 'deleted': raise HTTPException(404, 'Resource not found')
    allowed=list(document.allowed_users or [])
    if body.allowed and employee_id not in allowed: allowed.append(employee_id)
    if not body.allowed: allowed=[item for item in allowed if item != employee_id]
    document.allowed_users=allowed
    db.add(AdminAudit(id='AUD-'+uuid.uuid4().hex[:10].upper(), administrator_id=user['id'], action='resource.access.'+('granted' if body.allowed else 'revoked'), target_id=document_id+':'+employee_id, outcome='success'))
    db.commit()
    return {'employee_id': employee_id, 'document_id': document_id, 'allowed': employee_id in allowed}

@app.get('/api/settings/activity')
def settings_activity(employee_id: str, days: int=Query(default=30, ge=1, le=90), scope: str='all', user=Depends(admin), db=Depends(db_session)):
    employee=accounts.get(employee_id)
    if not employee or employee['role'] != 'employee': raise HTTPException(404, 'Employee not found')
    if scope not in VALID_RESOURCE_SCOPES: raise HTTPException(422, 'Choose a valid resource scope')
    preference=db.get(UserPreference, employee_id)
    level=preference.monitoring_level if preference and preference.monitoring_level else 'summary'
    start=(datetime.now(timezone.utc)-timedelta(days=days-1)).date().isoformat()
    query=db.query(Event).filter(Event.user == account_event_identity(employee), Event.timestamp >= start)
    events=query.order_by(Event.timestamp.desc()).all()
    if scope == 'limited':
        allowed_ids={d.id for d in db.query(Document).all() if employee_id in (d.allowed_users or []) or employee['role'] in (d.allowed_roles or [])}
        events=[event for event in events if event.resource_id in allowed_ids]
    elif scope == 'mine':
        owned_ids={d.id for d in db.query(Document).filter(Document.owner_id == employee_id).all()}
        events=[event for event in events if event.resource_id in owned_ids]
    counts=compute_security_actions(events)
    result={'employee_id':employee_id,'monitoring_level':level,'total':len(events),'blocked':counts['BLOCK'],'masked':counts['MASK'],'hashed':counts['HASH'],'pending':counts['APPROVE / PENDING']}
    if level == 'summary':
        return result | {'events': [], 'resource_activity': []}
    result['events']=[{'id':e.id,'timestamp':e.timestamp,'action':e.action,'outcome':e.outcome,'severity':e.severity,'risk':e.risk,'provider':e.provider,'model_called':e.model_called,'resource_id':e.resource_id,'categories':e.categories or [],'policies':e.policies or [],'reason':e.reason or 'Recorded security event.','title':e.title,'latency':e.latency,'user':e.user} for e in events[:50]]
    result['resource_activity']=[{'resource_id':key,'count':sum(1 for event in events if event.resource_id == key)} for key in sorted({event.resource_id for event in events if event.resource_id})]
    return result

def classify_action(action: str | None, outcome: str | None = None) -> str | None:
    if not action:
        return 'APPROVE / PENDING' if outcome and outcome.lower() == 'pending' else None
    act = action.strip().upper()
    if act in ('BLOCK', 'BLOCKED', 'ACCESS DENY', 'ACCESS_DENY', 'DENY', 'DENIED'):
        return 'BLOCK'
    if act in ('MASK', 'MASKED', 'REDACT', 'REDACTED'):
        return 'MASK'
    if act in ('HASH', 'HASHED', 'ANONYMIZE', 'ANONYMIZED', 'PSEUDONYMIZE', 'PSEUDONYMIZED'):
        return 'HASH'
    if act in ('APPROVE / PENDING', 'REQUIRE APPROVAL', 'REQUIRE_APPROVAL', 'APPROVAL', 'APPROVE', 'APPROVED', 'ALLOW', 'ALLOWED', 'WARN', 'PENDING', 'PENDING_APPROVAL', 'PENDING APPROVAL') or (outcome and outcome.lower() == 'pending'):
        return 'APPROVE / PENDING'
    return None

def compute_security_actions(events):
    counts = {'BLOCK': 0, 'MASK': 0, 'HASH': 0, 'APPROVE / PENDING': 0}
    for e in events:
        cat = classify_action(getattr(e, 'action', None), getattr(e, 'outcome', None))
        if cat:
            counts[cat] += 1
    return counts

VALID_RESOURCE_SCOPES = {'all', 'limited', 'mine'}

def scoped_event_query(db, user, scope):
    if scope not in VALID_RESOURCE_SCOPES:
        raise HTTPException(422, 'Choose a valid resource scope')
    identity='usr-'+hmac.new(os.getenv('AUDIT_HMAC_KEY','local-demo-only').encode(),user['id'].encode(),hashlib.sha256).hexdigest()[:10]
    query=db.query(Event)
    if user['role'] == 'admin' and scope == 'all':
        return query
    documents=permitted_documents(db,user)
    if scope == 'all':
        resource_ids={d.id for d in documents}
        return query.filter(or_(Event.user == identity, Event.resource_id.in_(resource_ids))) if resource_ids else query.filter(Event.user == identity)
    if scope == 'mine':
        resource_ids={d.id for d in documents if d.owner_id == user['id']}
        # Older personal requests predate resource_id. They are still owned by
        # the authenticated user when they have no document/resource attached.
        return query.filter(or_(
            (Event.user == identity) & Event.resource_id.is_(None),
            Event.resource_id.in_(resource_ids),
        )) if resource_ids else query.filter((Event.user == identity) & Event.resource_id.is_(None))
    else:
        resource_ids={d.id for d in documents if d.owner_id != user['id'] and (user['id'] in (d.allowed_users or []) or user['role'] in (d.allowed_roles or []))}
    return query.filter(Event.resource_id.in_(resource_ids)) if resource_ids else query.filter(False)

@app.get('/api/analytics')
def analytics(days:int=Query(default=30, ge=1, le=90), user=Depends(admin),db=Depends(db_session)):
    if days not in (7,30,90):
        raise HTTPException(422, 'Choose 7, 30, or 90 days')
    end=datetime.now(timezone.utc).date()
    start=end-timedelta(days=days-1)
    events=db.query(Event).filter(
        Event.timestamp >= start.isoformat(),
        Event.timestamp < (end+timedelta(days=1)).isoformat(),
    ).all()
    actions=Counter(e.action for e in events);categories=Counter(c for e in events for c in e.categories);severities=Counter(e.severity for e in events)
    action_counts = compute_security_actions(events)
    timeline={(start+timedelta(days=i)).isoformat():{
        'date':(start+timedelta(days=i)).isoformat(),
        'requests':0,'allowed':0,'prevented':0,'sanitized':0,
    } for i in range(days)}
    for e in events:
        date=e.timestamp[:10]
        if date not in timeline:
            continue
        timeline[date]['requests']+=1
        category=classify_action(e.action, e.outcome)
        if category == 'BLOCK': timeline[date]['prevented']+=1
        elif category in ('MASK','HASH'): timeline[date]['sanitized']+=1
        else: timeline[date]['allowed']+=1
    return {'total':len(events),'blocked':action_counts['BLOCK'],'sanitized':action_counts['MASK'],'injections':categories['INJECTION'],'unauthorized':actions['ACCESS DENY'],'sensitive':sum(bool(e.categories) for e in events),'high_risk':sum(e.risk>=50 for e in events),'calls_prevented':sum(not e.model_called for e in events),'latency':round(sum(e.latency for e in events)/max(1,len(events)),2),'actions':[{'name':k,'value':v} for k,v in action_counts.items()],'raw_actions':[{'name':k,'value':v} for k,v in actions.items()],'categories':[{'name':k,'value':v} for k,v in categories.items()],'severity':[{'name':k,'value':v} for k,v in severities.items()],'timeline':list(timeline.values()),'policy_effectiveness':[{'name':p.name,'value':sum(p.id in e.policies for e in events)} for p in db.query(Policy)],'policy_count':db.query(Policy).filter_by(enabled=True).count()+3}

@app.get('/api/me/dashboard')
def personal_dashboard(days:int=30,scope:str='all',user=Depends(current_user),db=Depends(db_session)):
    from datetime import datetime, timezone, timedelta
    if days not in (7,30,90):
        raise HTTPException(422,'Choose 7, 30, or 90 days')
    event_query=scoped_event_query(db,user,scope)
    start=(datetime.now(timezone.utc)-timedelta(days=days-1)).date()
    event_query=event_query.filter(Event.timestamp>=start.isoformat())
    events=event_query.order_by(Event.timestamp.desc()).all()
    actions=Counter(e.action for e in events)
    action_counts = compute_security_actions(events)
    timeline={(start+timedelta(days=i)).isoformat():{'date':(start+timedelta(days=i)).isoformat(),'requests':0,'allowed':0,'prevented':0,'sanitized':0} for i in range(days)}
    for event in events:
        if event.timestamp[:10] in timeline:
            timeline[event.timestamp[:10]]['requests']+=1
            category=classify_action(event.action, event.outcome)
            if category == 'BLOCK': timeline[event.timestamp[:10]]['prevented']+=1
            elif category in ('MASK','HASH'): timeline[event.timestamp[:10]]['sanitized']+=1
            else: timeline[event.timestamp[:10]]['allowed']+=1
    categories=Counter(c for e in events for c in e.categories)
    severities=Counter(e.severity for e in events)
    return {'total':len(events),'blocked':action_counts['BLOCK'],
        'sanitized':action_counts['MASK'],
        'latency':round(sum(e.latency for e in events)/len(events),1) if events else None,
        'actions':[{'name':k,'value':v} for k,v in action_counts.items()],
        'raw_actions':[{'name':k,'value':v} for k,v in actions.items()],
        'timeline':list(timeline.values()),
        'categories':[{'name':k,'value':v} for k,v in categories.items()],
        'severity':[{'name':k,'value':v} for k,v in severities.items()],
        'events':[row(e) for e in events[:8]],
        'mock_events':sum(e.provider=='mock' for e in events)}

@app.get('/api/me/history')
def personal_history(limit:int=Query(default=7, ge=1, le=500),scope:str='all', user=Depends(current_user), db=Depends(db_session)):
    """Return privacy-safe, newest-first request history for the signed-in user."""
    query=scoped_event_query(db,user,scope).order_by(Event.timestamp.desc())
    return {'events':[row(e) for e in query.limit(limit).all()], 'total':query.count(), 'limit':limit}

@app.get('/api/policies')
def policies(user=Depends(admin),db=Depends(db_session)): return [row(p) for p in db.query(Policy)]

class PolicyUpdate(BaseModel):
    enabled:bool
    action:str
    threshold:int=Field(ge=0,le=100)
    scope:str=Field(default='all',max_length=40)

@app.put('/api/policies/{pid}')
def update_policy(pid:str,body:PolicyUpdate,user=Depends(admin),db=Depends(db_session)):
    if body.action not in ('WARN','MASK','BLOCK','REDACT','REQUIRE APPROVAL','HASH'): raise HTTPException(400,'Unsupported action')
    p=db.get(Policy,pid)
    if not p: raise HTTPException(404,'Policy not found')
    for k,v in body.model_dump().items(): setattr(p,k,v)
    db.commit();return row(p)

@app.get('/api/documents')
def documents(user=Depends(current_user),db=Depends(db_session)):
    cleanup_expired_documents(db)
    return [{k:v for k,v in row(d).items() if k!='content'} for d in permitted_documents(db,user)]

@app.get('/api/documents/vault')
def document_vault(user=Depends(current_user),db=Depends(db_session)):
    cleanup_expired_documents(db)
    records = db.query(Document).filter(
        Document.owner_id == user['id'],
        Document.source == 'secure chat upload',
        Document.deletion_status != 'deleted',
    ).order_by(Document.created_at.desc()).all()
    return [{k:v for k,v in row(d).items() if k not in ('content','allowed_users','allowed_roles')} | {'retention_label': RETENTION_POLICIES.get(d.retention_policy or '', d.retention_policy or 'Not set')} for d in records]

class RetentionInput(BaseModel):
    policy: str

@app.get('/api/me/document-retention')
def get_document_retention(user=Depends(current_user),db=Depends(db_session)):
    preference = db.get(UserPreference, user['id'])
    if not preference:
        preference = UserPreference(user_id=user['id'], document_retention='1_week')
        db.add(preference); db.commit()
    return {'policy': preference.document_retention, 'label': RETENTION_POLICIES.get(preference.document_retention, '1 week')}

@app.put('/api/me/document-retention')
def set_document_retention(body:RetentionInput,user=Depends(current_user),db=Depends(db_session)):
    if body.policy not in RETENTION_POLICIES: raise HTTPException(400, 'Invalid retention policy')
    preference = db.get(UserPreference, user['id'])
    if not preference: preference = UserPreference(user_id=user['id'])
    preference.document_retention = body.policy
    db.add(preference); db.commit()
    return {'policy': body.policy, 'label': RETENTION_POLICIES[body.policy]}

class SecureChatUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(default='application/octet-stream', max_length=160)
    size_bytes: int = Field(ge=0, le=50_000_000)
    content: str | None = Field(default=None, max_length=20_000)
    data_base64: str | None = Field(default=None, max_length=14_000_000)

@app.post('/api/documents/upload')
def upload_from_secure_chat(body:SecureChatUpload,user=Depends(current_user),db=Depends(db_session)):
    cleanup_expired_documents(db)
    preference = db.get(UserPreference, user['id'])
    policy = preference.document_retention if preference and preference.document_retention in RETENTION_POLICIES else '1_week'
    now = datetime.now(timezone.utc)
    extracted_content = body.content
    processing_status = 'ready' if body.content is not None else 'uploaded_unprocessed'
    if body.data_base64 is not None:
        try:
            raw = base64.b64decode(body.data_base64, validate=True)
            if len(raw) > 10_000_000:
                raise ValueError('too large')
            extracted = OcrLayer().extract(Attachment(raw, body.filename))
            extracted_content = extracted.text[:20_000] or None
            processing_status = 'ready' if extracted_content else 'uploaded_empty'
        except OcrError:
            # The file is retained as unavailable metadata only. It is never
            # sent to the provider when OCR cannot safely inspect it.
            extracted_content = None
            processing_status = 'uploaded_unprocessed'
        except Exception:
            extracted_content = None
            processing_status = 'uploaded_unprocessed'
    document = Document(
        id='DOC-'+uuid.uuid4().hex[:10], title=body.filename, content=extracted_content,
        owner_id=user['id'], allowed_users=[], allowed_roles=[], classification='INTERNAL',
        source='secure chat upload', created_at=now.isoformat(), filename=body.filename,
        mime_type=body.mime_type, size_bytes=body.size_bytes, retention_policy=policy,
        delete_at=retention_deadline(now, policy).isoformat(),
        processing_status=processing_status, deletion_status='active',
    )
    db.add(document); db.commit()
    return {k:v for k,v in row(document).items() if k != 'content'}

@app.delete('/api/documents/{did}')
def delete_document(did:str,user=Depends(current_user),db=Depends(db_session)):
    document = db.get(Document, did)
    if not document or document.owner_id != user['id']:
        raise HTTPException(404, 'Document unavailable')
    document.content = None
    document.processing_status = 'deleted'
    document.deletion_status = 'deleted'
    document.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {'deleted': True, 'id': did}

class DocumentInput(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    content:str=Field(min_length=1,max_length=20000)
    classification:str
    allowed_users:list[str]=Field(default_factory=list,max_length=20)
    allowed_roles:list[str]=Field(default_factory=list,max_length=10)

@app.post('/api/documents')
def upload(body:DocumentInput,user=Depends(current_user),db=Depends(db_session)):
    if body.classification not in ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED'): raise HTTPException(400,'Invalid classification')
    if any(u not in accounts for u in body.allowed_users) or any(r not in ('employee','admin') for r in body.allowed_roles): raise HTTPException(400,'Unknown user or role')
    d=Document(id='DOC-'+uuid.uuid4().hex[:10],title=body.title,content=body.content,classification=body.classification,owner_id=user['id'],allowed_users=body.allowed_users,allowed_roles=body.allowed_roles,source='user upload')
    db.add(d);db.commit();return {'id':d.id}

@app.put('/api/documents/{did}')
def edit_document(did:str,body:DocumentInput,user=Depends(current_user),db=Depends(db_session)):
    d=db.get(Document,did)
    if not d or (d.owner_id!=user['id'] and user['role']!='admin'): raise HTTPException(404,'Document unavailable')
    if body.classification not in ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED') or any(u not in accounts for u in body.allowed_users) or any(r not in ('employee','admin') for r in body.allowed_roles): raise HTTPException(400,'Invalid permissions')
    for k,v in body.model_dump().items(): setattr(d,k,v)
    db.commit();return {'id':d.id}

@app.get('/api/approvals')
def approvals(user=Depends(admin),db=Depends(db_session)): return [row(a) for a in db.query(Approval).all()]

class Review(BaseModel):
    status:str

@app.put('/api/approvals/{aid}')
def review(aid:str,body:Review,user=Depends(admin),db=Depends(db_session)):
    if body.status not in ('approved','rejected'): raise HTTPException(400,'Invalid review')
    a=db.get(Approval,aid)
    if not a: raise HTTPException(404,'Review not found')
    if a.status!='pending': raise HTTPException(409,'This request was already reviewed')
    a.status=body.status;a.reviewer=user['id']
    if body.status=='rejected': pending_requests.pop(aid,None)
    db.commit();return row(a)

@app.post('/api/approvals/{aid}/execute')
async def execute_approval(aid:str,user=Depends(admin),db=Depends(db_session)):
    if os.getenv('AEGIS_PIPELINE')!='legacy' or not demo_enabled() or providers.provider.name!='mock':
        raise HTTPException(501,'Legacy approval execution is unavailable in the approved pipeline')
    a=db.get(Approval,aid)
    if not a or a.status!='approved': raise HTTPException(409,'An approved request is required')
    pending=pending_requests.pop(aid,None)
    if not pending or pending['expires']<time.time(): raise HTTPException(410,'Pending content expired or server restarted. Submit a new request.')
    a.status='executed';db.commit()
    return await run(db,pending['user'],pending['prompt'],pending['document_id'],approval_granted=True)

@app.get('/api/evaluation')
def evaluation(user=Depends(admin)):
    path=Path(__file__).parent/'evaluation-report.json'
    return json.loads(path.read_text()) if path.exists() else {'available':False}

@app.get('/api/health')
@app.get('/health')
def health(): return {'status':'running','provider':providers.provider.name,'security_pipeline':'architecture-v2','demo_login_enabled':demo_enabled()}
