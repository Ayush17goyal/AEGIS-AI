"""Explainable heuristic detectors. Findings never include detected values."""
import re
import math
from collections import Counter
from dataclasses import dataclass

@dataclass
class Finding:
    category: str
    kind: str
    start: int
    end: int
    confidence: int
    def safe(self):
        return {'category': self.category, 'kind': self.kind, 'confidence': self.confidence}

def luhn(number):
    digits = [int(c) for c in re.sub(r'\D', '', number)]
    if len(digits) not in (13,14,15,16,17,18,19) or len(set(digits)) == 1:
        return False
    return sum((d*2-9 if d*2>9 else d*2) if i%2 else d for i,d in enumerate(reversed(digits))) % 10 == 0

def verhoeff(value):
    d=[[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]]
    p=[[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]
    c=0
    for i,n in enumerate(reversed(value)): c=d[c][p[i%8][int(n)]]
    return c==0

def inspect(text):
    findings=[]
    patterns=[
        ('PII','Email address',r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b',95),
        ('PII','PAN-format identifier',r'\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b',90),
        ('PII','Indian mobile number',r'(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)',85),
        ('FINANCIAL','IFSC code',r'\b[A-Z]{4}0[A-Z0-9]{6}\b',95),
        ('FINANCIAL','Bank account',r'(?i)\b(?:bank account|account number|a/c)\s*[:=]?\s*\d{9,18}\b',90),
        ('SECRET','Credential assignment',r'(?i)\b(?:password|passwd|api[_ -]?key|access[_ -]?token|secret[_ -]?key)\s*[:=]\s*[\x22\x27]?[^\s\x22\x27,;]{5,}',98),
        ('SECRET','Bearer token',r'(?i)\bBearer\s+[A-Za-z0-9._-]{12,}',98),
        ('SECRET','Provider key',r'\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20,})\b',98),
        ('SECRET','Private key',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END [^-]+-----|$)',100),
        ('SECRET','Database credential',r'\b(?:postgres(?:ql)?|mysql|mongodb)://[^\s:]+:[^\s@]+@[^\s]+',98),
        ('CONFIDENTIAL','Classification label',r'(?i)\b(?:CONFIDENTIAL|RESTRICTED)\s*[:\n]\s*[\s\S]+',85)]
    for category,kind,pattern,confidence in patterns:
        for m in re.finditer(pattern,text): findings.append(Finding(category,kind,m.start(),m.end(),confidence))
    for m in re.finditer(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)',text):
        if luhn(m.group()): findings.append(Finding('FINANCIAL','Luhn-valid payment card',m.start(),m.end(),98))
    for m in re.finditer(r'\b[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}\b',text):
        if re.search(r'(?i)aadhaar|aadhar|identity number',text[max(0,m.start()-40):m.end()+20]):
            valid=verhoeff(re.sub(r'\D','',m.group()))
            findings.append(Finding('PII','Aadhaar-like identifier (checksum '+('valid' if valid else 'unverified')+')',m.start(),m.end(),90 if valid else 60))
    for m in re.finditer(r'\b[A-Za-z0-9_+/=-]{24,}\b',text):
        counts=Counter(m.group()); entropy=-sum(n/len(m.group())*math.log2(n/len(m.group())) for n in counts.values())
        if entropy>4.3 and re.search(r'(?i)token|credential|secret|key',text[max(0,m.start()-35):m.start()]):
            findings.append(Finding('SECRET','High-entropy potential secret',m.start(),m.end(),80))
    normalized=re.sub(r'[\u200b-\u200f\ufeff]','',text).lower()
    educational=bool(re.search(r'\b(explain|detect|prevent|definition|what is|how to defend|example of)\b',normalized))
    override=bool(re.search(r'(ignore|disregard|forget|override|bypass).{0,45}(instructions|rules|policy|restrictions|access|guardrails)',normalized))
    extraction=bool(re.search(r'(reveal|dump|print|expose|show|return|give|disclose).{0,60}(system prompt|hidden instructions|all secrets|api keys|credentials|another user|other users)',normalized))
    impersonation=bool(re.search(r'(you are now|act as|developer mode|system override|\[system\])',normalized))
    if (override or extraction or (impersonation and re.search('unrestricted|unfiltered',normalized))) and not educational:
        findings.append(Finding('INJECTION','Instruction override / extraction intent',0,len(text),min(100,70+15*int(override and extraction)+10*int(impersonation))))
    return findings

def sanitize(text, findings):
    # Merge overlapping ranges so no part of a sensitive span survives.
    ranges=[]
    for f in sorted(findings,key=lambda f:f.start):
        if ranges and f.start<=ranges[-1][1]: ranges[-1]=(ranges[-1][0],max(f.end,ranges[-1][1]),ranges[-1][2])
        else: ranges.append((f.start,f.end,f.category))
    for start,end,category in reversed(ranges): text=text[:start]+'['+category+'_REDACTED]'+text[end:]
    return text
