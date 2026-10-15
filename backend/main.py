import os
import secrets
import hashlib
import hmac
import time
import uuid
import json
from functools import lru_cache
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from .database import init_db, Session, Event, Policy, Document, Approval
from .gateway import run, permitted_documents, pending_requests
from .approved_pipeline import run_approved, status as pipeline_status, demo_enabled
from . import providers

app=FastAPI(title='AI Guard Security Gateway',version='1.0.0')
init_db()
sessions={}; attempts={}
chat_attempts={}
accounts={'admin':{'id':'admin','name':'Alex Morgan','role':'admin'},'alice':{'id':'alice','name':'Alice Chen','role':'employee'},'bob':{'id':'bob','name':'Bob Wilson','role':'employee'}}
accounts['individual']={'id':'individual','name':'Personal Demo User','role':'individual'}

@app.middleware('http')
async def security_headers(request: Request,call_next):
    if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0'))>65536:
        return JSONResponse({'detail':'Request too large'},status_code=413)
    if request.method in ('POST','PUT','PATCH'):
        size=0
        chunks=[]
        async for chunk in request.stream():
            size+=len(chunk)
            if size>65536: return JSONResponse({'detail':'Request too large'},status_code=413)
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

@app.get('/api/analytics')
def analytics(user=Depends(admin),db=Depends(db_session)):
    events=db.query(Event).all();actions=Counter(e.action for e in events);categories=Counter(c for e in events for c in e.categories);severities=Counter(e.severity for e in events)
    action_counts = compute_security_actions(events)
    days={}
    for e in events:
        date=e.timestamp[:10];days.setdefault(date,{'date':date,'allowed':0,'prevented':0,'sanitized':0})
        days[date]['prevented' if e.action in ('BLOCK','ACCESS DENY') else 'sanitized' if e.action in ('MASK','REDACT') else 'allowed']+=1
    return {'total':len(events),'blocked':action_counts['BLOCK'],'sanitized':action_counts['MASK'],'injections':categories['INJECTION'],'unauthorized':actions['ACCESS DENY'],'sensitive':sum(bool(e.categories) for e in events),'high_risk':sum(e.risk>=50 for e in events),'calls_prevented':sum(not e.model_called for e in events),'latency':round(sum(e.latency for e in events)/max(1,len(events)),2),'actions':[{'name':k,'value':v} for k,v in action_counts.items()],'raw_actions':[{'name':k,'value':v} for k,v in actions.items()],'categories':[{'name':k,'value':v} for k,v in categories.items()],'severity':[{'name':k,'value':v} for k,v in severities.items()],'timeline':list(sorted(days.values(),key=lambda x:x['date'])),'policy_effectiveness':[{'name':p.name,'value':sum(p.id in e.policies for e in events)} for p in db.query(Policy)],'policy_count':db.query(Policy).filter_by(enabled=True).count()+3}

@app.get('/api/me/dashboard')
def personal_dashboard(days:int=30,user=Depends(current_user),db=Depends(db_session)):
    from datetime import datetime, timezone, timedelta
    if days not in (7,30,90):
        raise HTTPException(422,'Choose 7, 30, or 90 days')
    identity='usr-'+hmac.new(os.getenv('AUDIT_HMAC_KEY','local-demo-only').encode(),user['id'].encode(),hashlib.sha256).hexdigest()[:10]
    start=(datetime.now(timezone.utc)-timedelta(days=days-1)).date()
    events=db.query(Event).filter(Event.user==identity,Event.timestamp>=start.isoformat()).order_by(Event.timestamp.desc()).all()
    actions=Counter(e.action for e in events)
    action_counts = compute_security_actions(events)
    timeline={(start+timedelta(days=i)).isoformat():{'date':(start+timedelta(days=i)).isoformat(),'requests':0} for i in range(days)}
    for event in events:
        if event.timestamp[:10] in timeline:
            timeline[event.timestamp[:10]]['requests']+=1
    return {'total':len(events),'blocked':action_counts['BLOCK'],
        'sanitized':action_counts['MASK'],
        'latency':round(sum(e.latency for e in events)/len(events),1) if events else None,
        'actions':[{'name':k,'value':v} for k,v in action_counts.items()],
        'raw_actions':[{'name':k,'value':v} for k,v in actions.items()],
        'timeline':list(timeline.values()),'events':[row(e) for e in events[:8]],
        'mock_events':sum(e.provider=='mock' for e in events)}

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
    return [{k:v for k,v in row(d).items() if k!='content'} for d in permitted_documents(db,user)]

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
