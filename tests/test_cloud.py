import asyncio
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
import fakeredis.aioredis
import httpx
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.update(SESSION_SECRET='test-secret-'*5,UPSTASH_REDIS_REST_URL='https://example.invalid',UPSTASH_REDIS_REST_TOKEN='test-only',GEMINI_API_KEY='test-only',REDIS_NAMESPACE='test')
import app as server
from cloud.limits import Limiter, Limited, Unavailable
from cloud.identity import identity, sign

class FakeRedis:
 def __init__(self): self.db=fakeredis.aioredis.FakeRedis(decode_responses=True)
 async def command(self,*args): return await self.db.execute_command(*args)

def test_atomic_parallel_reservations_and_double_settlement():
 async def run():
  fake=FakeRedis();lim=Limiter(fake)
  async def attempt(i):
   try:return await lim.reserve('same-session','ip','public',str(i),100)
   except Limited as e:return e.reason
  results=await asyncio.gather(*(attempt(i) for i in range(20)))
  accepted=[r for r in results if isinstance(r,dict)]
  assert len(accepted)==1
  r=accepted[0]
  assert await fake.command('GET',r['budget'][0])=='100'
  await asyncio.gather(lim.settle(r,25),lim.settle(r,25))
  assert await fake.command('GET',r['budget'][0])=='25'
  assert await fake.command('ZCARD',r['leases'][0])==0
  with pytest.raises(Limited) as e:await lim.reserve('same-session','ip','public',r['id'],100)
  assert e.value.reason=='duplicate'
 asyncio.run(run())

def test_legacy_tier_uses_shared_budget_and_unknown_failure_charge():
 async def run():
  lim=Limiter(FakeRedis())
  with patch.dict(os.environ,{'PUBLIC_DAILY_BUDGET_MICRO_USD':'150'}):
   r=await lim.reserve('one','ip','public','request1',100)
   await lim.settle(r,None)
   with pytest.raises(Limited) as e:await lim.reserve('two','ip','public','request2',100)
   assert e.value.reason=='budget'
   with pytest.raises(Limited) as e:await lim.reserve('judge','ip','judge','request3',100)
   assert e.value.reason=='budget'
   assert await lim.redis.command('GET',r['budget'][0])=='100'
 asyncio.run(run())

def test_session_daily_quota():
 async def run():
  lim=Limiter(FakeRedis())
  for n in range(10):
   # Reset only minute quota to exercise daily cap without waiting.
   for key in await lim.redis.db.keys('*:m:*'): 
    if ':budget:' not in key:await lim.redis.db.delete(key)
   r=await lim.reserve('same','ip','public',str(n),1);await lim.settle(r,1)
  with pytest.raises(Limited) as e:await lim.reserve('same','ip','public','11',1)
  assert e.value.reason=='day'
 asyncio.run(run())

def test_http_stream_private_routes_origin_validation_and_fail_closed():
 async def run():
  fake=FakeRedis();lim=Limiter(fake)
  calls=[]
  async def stream(body):
   calls.append(body)
   yield {'candidates':[{'content':{'parts':[{'text':'그때 어떤 말을 들으셨나요?'}]}}]}
   yield {'candidates':[{'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':1000,'candidatesTokenCount':20,'totalTokenCount':1020}}
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://127.0.0.1:8318',headers={'Origin':'http://127.0.0.1:8318'}) as client:
   with patch.object(server,'limiter',lim),patch.object(server.gemini,'stream',stream):
    session=await client.get('/api/session');assert session.status_code==200
    assert 'HttpOnly' in session.headers['set-cookie']
    payload={'author':'austen','messages':[{'role':'user','content':'친구가 제 의견을 무시해서 속상해요.'}],'memory':[]}
    headers={'Idempotency-Key':'request-1234567890'}
    r=await client.post('/api/chat',json=payload,headers=headers)
    assert r.status_code==200,r.text
    events=[json.loads(x) for x in r.text.splitlines()]
    assert [e['type'] for e in events]==['meta','delta','done']
    assert events[0]['model']=='gemini-3.1-flash-lite'
    assert all('path' not in s for s in events[0]['sources'])
    assert len(calls)==1
    r=await client.post('/api/chat',json=payload,headers=headers);assert r.status_code==429
    r=await client.post('/api/chat',json=payload,headers={**headers,'Origin':'https://evil.invalid'});assert r.status_code==403
    r=await client.post('/api/chat',json={'author':'bad'},headers=headers);assert r.status_code==400
    r=await client.post('/api/prophecy',json={'exclude':[]});assert r.status_code==200
    assert len(calls)==1 # prophecy makes no model call
    for private in ['/.env.local','/cloud/limits.py','/local-llm/index/originals.sqlite3','/ai/index/originals.sqlite3','/ai/prompts.py','/spec/deployment-plan-contest-min-cost.md']:
     r=await client.get(private);assert r.status_code==404
   class Broken:
    async def command(self,*args):raise Unavailable()
   with patch.object(server,'limiter',Limiter(Broken())),patch.object(server.gemini,'stream',stream):
    r=await client.post('/api/chat',json=payload,headers={'Idempotency-Key':'request-2345678901'})
    assert r.status_code==503 and len(calls)==1
 asyncio.run(run())

def test_tampered_cookie_is_not_judge():
 from starlette.requests import Request
 signed=sign('a'*32,'public')
 req=Request({'type':'http','headers':[(b'cookie',('jane_session='+signed.replace('.public.','.judge.')).encode())]})
 assert identity(req)[1]=='public'

def test_request_input_bound_and_quote_deck():
 from cloud.gemini import input_bound,body_for
 body=body_for({'messages':[{'role':'system','content':'시스템'},{'role':'user','content':'고민'}],'options':{'num_predict':100000}})
 assert body['generationConfig']['maxOutputTokens']==500
 assert input_bound(body)>=len('시스템고민'.encode())
 assert len(server.CARDS)==9 and len({c['quote']['author'] for c in server.CARDS})==3
 for c in server.CARDS:
  assert len(c['lines'])==3 and 'path' not in c['quote']

def test_legacy_judge_cookie_migrates_without_resetting_session():
 from starlette.requests import Request
 sid='b'*32
 expiry=int(time.time())+3600
 old=sign(sid,'judge',expiry)
 req=Request({'type':'http','headers':[(b'cookie',('jane_session='+old).encode())]})
 actual,tier,cookie=identity(req)
 assert actual==sid and tier=='public'
 assert cookie==sign(sid,'public',expiry)
 async def run():
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://127.0.0.1:8318',headers={'Origin':'http://127.0.0.1:8318','Cookie':'jane_session='+old}) as c:
   r=await c.get('/api/session')
   assert r.json()['tier']=='public' and r.json()['dailyLimit']==10
   assert '.public.' in r.headers['set-cookie']
   r=await c.post('/api/judge',json={'token':'retired'})
   assert r.status_code in (404,405)
 asyncio.run(run())

def test_limit_error_codes_for_contact_notice():
 async def run():
  class Blocked:
   def __init__(self, reason): self.reason=reason
   async def throttle(self,*args): raise Limited(self.reason)
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://127.0.0.1:8318',headers={'Origin':'http://127.0.0.1:8318'}) as c:
   for reason in ('day','budget','rate','busy','duplicate'):
    with patch.object(server,'limiter',Blocked(reason)):
     r=await c.post('/api/chat',json={'author':'austen','messages':[{'role':'user','content':'고민이에요'}]},headers={'Idempotency-Key':'limit-test-123456789'})
     assert r.status_code==429
     assert r.json()['code']=='limit_'+reason
 asyncio.run(run())

def test_ip_daily_quota_shared_across_browsers():
 async def run():
  lim=Limiter(FakeRedis())
  for n in range(50):
   for key in await lim.redis.db.keys('*:m:*'):
    if ':budget:' not in key:await lim.redis.db.delete(key)
   r=await lim.reserve('browser-'+str(n),'shared-ip','public',str(n),1)
   await lim.settle(r,1)
  with pytest.raises(Limited) as e:await lim.reserve('new-browser','shared-ip','public','51',1)
  assert e.value.reason=='day'
  r=await lim.reserve('another-browser','other-ip','public','other',1)
  assert r
 asyncio.run(run())

def test_daily_usage_tracks_reservations_and_resets_by_seoul_date():
 from datetime import datetime,timedelta
 from zoneinfo import ZoneInfo
 async def run():
  lim=Limiter(FakeRedis())
  assert (await lim.daily_usage('reader'))['used']==0
  r=await lim.reserve('reader','ip','public','usage-1',1)
  await lim.settle(r,None)
  assert (await lim.daily_usage('reader'))['used']==1
  assert (await lim.daily_usage('other'))['used']==0
  with patch('cloud.limits.datetime') as clock:
   clock.now.return_value=datetime.now(ZoneInfo('Asia/Seoul'))+timedelta(days=1)
   assert (await lim.daily_usage('reader'))['used']==0
 asyncio.run(run())
