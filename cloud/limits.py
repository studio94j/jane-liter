"""Atomic Upstash reservations. No prompts or responses are stored in Redis."""
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

# One transaction checks all counters, budget and leases before mutating anything.
RESERVE = r'''
local cfg = cjson.decode(ARGV[1])
local now = tonumber(ARGV[2])
local lease = ARGV[3]
local reserve = tonumber(ARGV[4])
if redis.call('EXISTS', KEYS[1]) == 1 then return 'duplicate' end
for i,c in ipairs(cfg) do
 local key = KEYS[i+1]
 if c.kind == 'lease' then
  redis.call('ZREMRANGEBYSCORE',key,'-inf',now)
  if redis.call('ZCARD',key) >= c.limit then return 'busy' end
 else
  local current = tonumber(redis.call('GET',key) or '0')
  local amount = c.kind == 'budget' and reserve or 1
  if current + amount > c.limit then return c.kind end
 end
end
for i,c in ipairs(cfg) do
 local key = KEYS[i+1]
 if c.kind == 'lease' then redis.call('ZADD',key,now+180,lease)
 else redis.call('INCRBY',key,c.kind == 'budget' and reserve or 1) end
 redis.call('EXPIRE',key,c.ttl)
end
redis.call('SET',KEYS[1],'reserved','EX',86400)
return 'ok'
'''
SETTLE = r'''
if redis.call('GET',KEYS[1]) ~= 'reserved' then return 0 end
redis.call('SET',KEYS[1],'settled','KEEPTTL')
local refund = tonumber(ARGV[2])
for i=2,3 do
 if redis.call('EXISTS',KEYS[i]) == 1 then redis.call('DECRBY',KEYS[i],refund) end
end
for i=4,#KEYS do redis.call('ZREM',KEYS[i],ARGV[1]) end
return 1
'''
THROTTLE = r'''
local n=tonumber(redis.call('GET',KEYS[1]) or '0')
if n>=tonumber(ARGV[1]) then return 0 end
redis.call('INCR',KEYS[1]); if n==0 then redis.call('EXPIRE',KEYS[1],ARGV[2]) end
return 1
'''
class Unavailable(Exception):
    pass

class Limited(Exception):
    def __init__(self, reason):
        self.reason = reason

class Redis:
    async def command(self, *args):
        url, token = os.getenv('UPSTASH_REDIS_REST_URL',''), os.getenv('UPSTASH_REDIS_REST_TOKEN','')
        if not url.startswith('https://') or not token:
            raise Unavailable()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(url, headers={'Authorization': 'Bearer '+token}, json=list(args))
                r.raise_for_status()
                body = r.json()
                if 'error' in body: raise Unavailable()
                return body['result']
        except (httpx.HTTPError, ValueError, KeyError) as e:
            raise Unavailable() from e

class Limiter:
    def __init__(self, redis=None):
        self.redis = redis or Redis()
        self.prefix = os.getenv('REDIS_NAMESPACE', 'jane-v1')+':'

    async def throttle(self, key, limit, seconds=60):
        if not await self.redis.command('EVAL', THROTTLE, 1, self.prefix+key, limit, seconds):
            raise Limited('rate')

    async def reserve(self, session, ip, tier, request_id, amount):
        import json
        now = time.time()
        date = datetime.fromtimestamp(now, ZoneInfo('Asia/Seoul'))
        day, month = date.strftime('%Y-%m-%d'), date.strftime('%Y-%m')
        minute = str(int(now // 60))
        # One shared quota pool, including callers holding legacy judge sessions.
        tier = 'public'
        upper = 'PUBLIC'
        entries = [
            (f's:{session}:d:{day}', 'day', 20, 172800),
            (f's:{session}:m:{minute}', 'rate', 3, 120),
            (f'{tier}:ip:{ip}:d:{day}', 'day', 100, 172800),
            (f'{tier}:ip:{ip}:m:{minute}', 'rate', 15, 120),
            (f'{tier}:d:{day}', 'day', int(os.getenv(upper+'_DAILY_REQUESTS',300)), 172800),
            (f'{tier}:budget:d:{day}', 'budget', int(os.getenv(upper+'_DAILY_BUDGET_MICRO_USD',300000)), 172800),
            (f'{tier}:budget:m:{month}', 'budget', int(os.getenv(upper+'_MONTHLY_BUDGET_MICRO_USD',9000000)), 5356800),
            (f's:{session}:active', 'lease', 1, 240),
            (f'{tier}:active', 'lease', 4, 240),
        ]
        marker = self.prefix+f'request:{session}:{request_id}'
        keys = [self.prefix+x[0] for x in entries]
        config = [{'kind':kind,'limit':limit,'ttl':ttl} for _,kind,limit,ttl in entries]
        result = await self.redis.command('EVAL',RESERVE,1+len(keys),marker,*keys,
                                          json.dumps(config),now,request_id,amount)
        if result != 'ok': raise Limited(result)
        return {'marker':marker, 'budget':keys[5:7], 'leases':keys[7:], 'id':request_id, 'amount':amount}

    async def settle(self, reservation, cost=None):
        # Uncertain provider failures / disconnects retain the entire reservation.
        refund = max(0, reservation['amount'] - (reservation['amount'] if cost is None else cost))
        # If provider reports unexpectedly greater usage, record the overage too.
        if cost is not None and cost > reservation['amount']: refund = reservation['amount'] - cost
        keys = [reservation['marker'],*reservation['budget'],*reservation['leases']]
        await self.redis.command('EVAL',SETTLE,len(keys),*keys,reservation['id'],refund)
