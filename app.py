"""Jane public demo: Vercel + Gemini + atomic Upstash quotas."""
import asyncio
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.parse import urlparse
import anyio
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if not os.getenv('VERCEL'):
    load_dotenv(ROOT / '.env.local', override=False)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from ai.context import build_request, validate_request
from ai.quotations import select_quote, cached_translation, strip_model_footer
from ai.retrieval import stats
from cloud import gemini
from cloud.identity import identity, ip_hash, set_cookie, digest
from cloud.limits import Limiter, Limited, Unavailable

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
limiter = Limiter()
CARDS = json.loads((ROOT / 'cloud/prophecies.json').read_text()) if (ROOT / 'cloud/prophecies.json').exists() else []

MESSAGES = {
    'busy':'아직 답변을 작성 중이에요. 잠시 뒤 다시 보내 주세요.',
    'duplicate':'이미 처리한 요청이에요. 대화 내용을 확인해 주세요.',
    'rate':'조금 천천히 이야기해 주세요. 1분 뒤 다시 보낼 수 있어요.',
    'day':'오늘의 대화 횟수를 모두 사용했어요. 내일 다시 만나요.',
    'budget':'오늘은 잠시 쉬어갑니다. 대화 이용 한도가 다시 열리면 만나요.',
}

def error(message, status=400):
    return JSONResponse({'error':message},status_code=status,headers={'Cache-Control':'no-store'})

def ready():
    return (os.getenv('AI_ENABLED','true')=='true' and len(os.getenv('SESSION_SECRET',''))>=32
            and all(os.getenv(k) for k in ('GEMINI_API_KEY','UPSTASH_REDIS_REST_URL','UPSTASH_REDIS_REST_TOKEN')))

def same_origin(request):
    allowed = {x.strip().rstrip('/') for x in os.getenv('APP_ORIGINS','').split(',') if x.strip()}
    for key in ('VERCEL_URL','VERCEL_PROJECT_PRODUCTION_URL'):
        if os.getenv(key): allowed.add('https://'+os.environ[key])
    origin = request.headers.get('origin','')
    if not os.getenv('VERCEL'):
        allowed |= {'http://'+request.headers.get('host','')} if request.url.hostname in ('localhost','127.0.0.1') else set()
    return origin in allowed and request.headers.get('sec-fetch-site','same-origin') in ('same-origin','none')

async def read_json(request, max_bytes=100000):
    if request.headers.get('content-type','').split(';')[0] != 'application/json': raise ValueError('JSON 형식으로 보내 주세요.')
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>max_bytes: raise ValueError('대화 내용이 너무 길어요.')
    data = json.loads(raw)
    if not isinstance(data,dict): raise ValueError('요청 형식을 확인해 주세요.')
    return data

@app.middleware('http')
async def secure_api(request,call_next):
    if request.url.path.startswith('/api/'):
        if request.method=='POST' and not same_origin(request):
            return error('이 서비스 화면에서 다시 요청해 주세요.',403)
        try:
            response = await call_next(request)
        except Unavailable:
            response = error('사용량을 확인할 수 없어 대화를 잠시 쉬고 있어요. 잠시 뒤 다시 시도해 주세요.',503)
        except Limited as e:
            response = JSONResponse({'error':MESSAGES.get(e.reason,MESSAGES['rate']), 'code':'limit_'+e.reason},status_code=429)
            response.headers['Retry-After']='60'
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    return await call_next(request)

@app.get('/api/health')
async def health():
    # Readiness of configuration, not an expensive provider call on every page view.
    return {'ready':ready(),'provider':'gemini','model':gemini.MODEL,'label':'Gemini · 작품 기반 대화'}

@app.get('/api/session')
async def session(request: Request):
    sid,tier,cookie = identity(request)
    try:
        usage = await limiter.daily_usage(sid)
    except Unavailable:
        usage = None
    response = JSONResponse({'tier':tier,'dailyLimit':10,'provider':'gemini','usage':usage})
    set_cookie(response,cookie)
    return response

@app.post('/api/prophecy')
async def prophecy(request: Request):
    sid,_,cookie = identity(request)
    await limiter.throttle('prophecy:'+ip_hash(request),20,60)
    try:
        data = await read_json(request,4096)
        exclude = data.get('exclude',[])
        if set(data)-{'exclude'} or not isinstance(exclude,list) or len(exclude)>20 or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{24}',x) for x in exclude): raise ValueError()
    except (ValueError,UnicodeError): return error('예언 요청 형식을 확인해 주세요.')
    if not CARDS: return error('예언을 준비 중이에요.',503)
    eligible = [c for c in CARDS if c['id'] not in exclude]
    # When the small curated deck is exhausted, avoid only the latest card.
    if not eligible: eligible = [c for c in CARDS if not exclude or c['id']!=exclude[-1]] or CARDS
    authors = sorted({c['quote']['author'] for c in eligible})
    author = secrets.choice(authors)
    response = JSONResponse({'card':secrets.choice([c for c in eligible if c['quote']['author']==author])})
    set_cookie(response,cookie)
    return response

@app.post('/api/chat')
async def chat_endpoint(request: Request):
    if not ready(): return error('대화 연결을 준비 중이에요. 잠시 뒤 다시 찾아 주세요.',503)
    sid,tier,cookie = identity(request)
    request_id = request.headers.get('idempotency-key','')
    if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}',request_id): return error('대화 요청 번호를 확인해 주세요.')
    await limiter.throttle('ingress:'+ip_hash(request),30,60)
    try:
        data = await read_json(request)
        # Separate memory is disabled, including requests from older clients.
        data['memory'] = []
        validate_request(data)
        payload,meta = await run_in_threadpool(build_request,data)
        body = gemini.body_for(payload)
        bound = gemini.input_bound(body)
        if bound>16000: return error('대화가 길어졌어요. 조금 짧게 나누어 주세요.')
    except (ValueError,TypeError,UnicodeError): return error('대화 내용을 확인해 주세요. 한 번에 2,000자까지 보낼 수 있어요.')
    reservation = await limiter.reserve(sid,ip_hash(request),tier,request_id,
                                        gemini.cost_micro(bound,body['generationConfig']['maxOutputTokens']))
    meta['model']=gemini.MODEL
    meta['provider']='gemini'
    # Internal filesystem paths and line locations are not UI data.
    public_meta = {**meta,'sources':[{k:v for k,v in s.items() if k not in ('path','start_line','end_line','sha256','score')} for s in meta['sources']]}
    def event(obj): return json.dumps(obj,ensure_ascii=False)+'\n'
    async def generate():
        usage = None
        completed = False
        started = time.monotonic()
        raw = visible = ''
        finish = None
        try:
            yield event(public_meta)
            async with asyncio.timeout(75):
                async for chunk in gemini.stream(body):
                    if chunk.get('usageMetadata'): usage = chunk['usageMetadata']
                    candidates = chunk.get('candidates',[])
                    if candidates:
                        candidate = candidates[0]
                        for part in candidate.get('content',{}).get('parts',[]):
                            if part.get('thought'): continue
                            raw += part.get('text','')
                        clean = strip_model_footer(raw)
                        if clean.startswith(visible):
                            if clean[len(visible):]: yield event({'type':'delta','content':clean[len(visible):]})
                        elif clean!=visible: yield event({'type':'replace','content':clean})
                        visible = clean
                        finish = candidate.get('finishReason') or finish
            if finish not in ('STOP','MAX_TOKENS') or not visible.strip():
                raise gemini.ProviderError('답변을 마치지 못했어요. 내용을 조금 바꾸어 다시 보내 주세요.')
            completed = True
            if meta['reply_mode']=='advice' and meta['sources'] and meta['retrieval'].get('status')!='safety-priority':
                quote = await run_in_threadpool(select_quote,meta['sources'],meta['retrieval']['terms'])
                translated = await run_in_threadpool(cached_translation,quote) if quote else None
                # No second LLM call on cache misses: keep the reply fast and cost bounded.
                if quote and translated:
                    quote.update(korean=translated,translation_status='complete',translation_cache='hit')
                    quote = {k:v for k,v in quote.items() if k not in ('path','start_line','end_line')}
                    yield event({'type':'quote','quote':quote})
            yield event({'type':'done','reason':'length' if finish=='MAX_TOKENS' else 'stop',
                         'output_tokens':(usage or {}).get('candidatesTokenCount'),
                         'timings':{'total_seconds':round(time.monotonic()-started,2)}})
        except gemini.ProviderError as exc:
            yield event({'type':'error','message':str(exc)})
        except asyncio.CancelledError:
            raise
        except Exception:
            yield event({'type':'error','message':'답변 연결이 중단되었어요. 잠시 뒤 다시 시도해 주세요.'})
        finally:
            cost = None
            if completed and usage and 'promptTokenCount' in usage and 'totalTokenCount' in usage:
                cost = gemini.cost_micro(usage['promptTokenCount'],max(0,usage['totalTokenCount']-usage['promptTokenCount']))
            with anyio.CancelScope(shield=True):
                try: await limiter.settle(reservation,cost)
                except Unavailable: pass  # Reservation remains charged; leases expire.
    response = StreamingResponse(generate(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
    set_cookie(response,cookie)
    return response

# Vercel serves public/ on its CDN. Only local development mounts it here.
if not os.getenv('VERCEL') and (ROOT / 'public').exists():
    app.mount('/',StaticFiles(directory=ROOT / 'public',html=True),name='public')
