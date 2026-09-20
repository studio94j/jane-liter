"""REST streaming adapter, explicit model, no automatic retries or tools."""
import json
import math
import os
import httpx

MODEL = os.getenv('GEMINI_MODEL','gemini-3.1-flash-lite')
MAX_OUTPUT = 500

class ProviderError(Exception):
    pass

def body_for(payload):
    turns = payload['messages']
    return {
        'systemInstruction': {'parts':[{'text':turns[0]['content']}]},
        'contents':[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in turns[1:]],
        'generationConfig':{'temperature':0.5,'maxOutputTokens':min(MAX_OUTPUT,payload['options']['num_predict']),
                            'thinkingConfig':{'thinkingLevel':'minimal'}},
    }

def input_bound(body):
    # Upper bound in UTF-8 bytes rather than a guessed Korean token count.
    # Add headroom for role/system wrappers. Actual usage settles the reservation.
    texts = [p['text'] for p in body['systemInstruction']['parts']]
    texts += [p['text'] for c in body['contents'] for p in c['parts']]
    return sum(len(t.encode('utf-8')) for t in texts) + 512 + len(body['contents'])*32

def cost_micro(input_tokens, output_tokens):
    ip = int(os.getenv('INPUT_MICRO_USD_PER_MILLION','250000'))
    op = int(os.getenv('OUTPUT_MICRO_USD_PER_MILLION','1500000'))
    if min(ip,op)<=0: raise ValueError('Invalid model prices')
    return math.ceil((input_tokens*ip+output_tokens*op)/1_000_000)

async def stream(body):
    key = os.getenv('GEMINI_API_KEY','')
    if not key: raise ProviderError('대화 연결을 준비 중이에요. 잠시 뒤 다시 찾아 주세요.')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:streamGenerateContent?alt=sse'
    async with httpx.AsyncClient(timeout=httpx.Timeout(45,connect=10)) as client:
        async with client.stream('POST',url,headers={'x-goog-api-key':key},json=body) as response:
            if response.status_code==429:
                raise ProviderError('AI 제공사의 사용 한도에 도달했어요. 잠시 뒤 다시 시도해 주세요.')
            if response.status_code!=200:
                raise ProviderError('대화 연결이 잠시 원활하지 않아요. 잠시 뒤 다시 시도해 주세요.')
            async for line in response.aiter_lines():
                if not line.startswith('data:'): continue
                data = json.loads(line[5:])
                if data.get('error'): raise ProviderError('답변을 마치지 못했어요. 잠시 뒤 다시 시도해 주세요.')
                yield data
