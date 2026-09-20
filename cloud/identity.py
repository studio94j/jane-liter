import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from .limits import Unavailable

COOKIE = 'jane_session'

def secret():
    key = os.getenv('SESSION_SECRET','')
    if len(key) < 32: raise Unavailable()
    return key.encode()

def digest(value):
    return hmac.new(secret(), value.encode(), hashlib.sha256).hexdigest()

def sign(session, tier='public', expires=None):
    payload = f'{session}.{tier}.{expires or int(time.time())+30*86400}'
    return payload+'.'+digest(payload)

def identity(request):
    value = request.cookies.get(COOKIE,'')
    parts = value.split('.')
    if len(parts) == 4:
        sid, tier, expiry, mac = parts
        if (re.fullmatch(r'[a-f0-9]{32}',sid) and tier in ('public','judge') and expiry.isdigit()
                and int(expiry) > time.time() and hmac.compare_digest(mac,digest('.'.join(parts[:3])))):
            # Preserve the existing session and its counters; retire privileged cookies.
            return sid,'public',value if tier=='public' else sign(sid,expires=int(expiry))
    sid = secrets.token_hex(16)
    return sid,'public',sign(sid)

def ip_hash(request):
    # Vercel sets this header itself. Never trust client X-Forwarded-For.
    raw = request.headers.get('x-vercel-forwarded-for','') if os.getenv('VERCEL') else request.client.host
    try:
        address = ipaddress.ip_address(raw.strip())
        # IPv6 temporary addresses share a /64 rate limit.
        normalized = str(ipaddress.ip_network(f'{address}/64',strict=False)) if address.version==6 else str(address)
    except ValueError:
        normalized = 'unknown'  # Fail to a shared bucket, never an unlimited random identity.
    return digest('ip:'+datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d')+':'+normalized)

def set_cookie(response,value):
    response.set_cookie(COOKIE,value,max_age=30*86400,httponly=True,
                        secure=bool(os.getenv('VERCEL')),samesite='strict',path='/')
