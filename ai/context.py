"""Provider-independent validation, RAG selection and context budgeting."""
import json
import math
from .prompts import PERSPECTIVES, system_prompt, dialogue_focus, reply_policy
from .retrieval import retrieve
from .situations import select_situation, situation_instruction

def estimate_tokens(text):
    # Conservative heuristic for this Korean/English prototype, not a tokenizer.
    return math.ceil(sum(1.6 if ord(c)>127 else 0.35 for c in text))

def validate_request(data):
    if not isinstance(data, dict) or data.get('author') not in PERSPECTIVES:
        raise ValueError('함께할 작가를 다시 선택해 주세요.')
    author=data['author']
    history=data.get('messages')
    if not isinstance(history,list) or not 1<=len(history)<=41 or len(history)%2!=1:
        raise ValueError('대화 형식을 확인할 수 없어요. 새 대화를 시작해 주세요.')
    for i,m in enumerate(history):
        role='user' if i%2==0 else 'assistant'
        if not isinstance(m,dict) or m.get('role')!=role or not isinstance(m.get('content'),str) or not m['content'].strip() or len(m['content'])>6000:
            raise ValueError('대화 내용이 올바르지 않아요.')
    if len(history[-1]['content'])>2000:
        raise ValueError('한 번에 2,000자까지 이야기할 수 있어요.')
    if estimate_tokens(system_prompt(author))+estimate_tokens(history[-1]['content'])>2950:
        raise ValueError('지금 입력이 모델의 문맥 한도를 넘었어요. 조금 짧게 나누어 주세요.')
    select_situation(data.get('situation'),history[-1]['content'])
    validate_memory(data)
    return author,history

def validate_memory(data):
    memory=data.get('memory',[])
    if not isinstance(memory,list) or len(memory)>8 or any(not isinstance(x,str) or not x.strip() or len(x)>160 for x in memory):
        raise ValueError('기억은 최대 8개, 항목당 160자까지 전달할 수 있어요.')
    return memory

def build_request(data):
    author,history=validate_request(data)
    latest=history[-1]['content']
    policy=reply_policy(author,history)
    situation,origin=select_situation(data.get('situation'),latest)
    focus=dialogue_focus(author,history)+situation_instruction(situation,origin,author)
    extra=policy['instruction']
    requested_memory=validate_memory(data)
    kept_memory=[]
    def memory_text():
        # Escape delimiters: client memory is data, never a new prompt section.
        return json.dumps(kept_memory,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e') if kept_memory else None
    for item in reversed(requested_memory):
        kept_memory.insert(0,item)
        if estimate_tokens(memory_text())>360:
            kept_memory.pop(0)
    base=system_prompt(author,memory=memory_text())+focus+extra
    while kept_memory and estimate_tokens(base)+estimate_tokens(latest)>2900:
        kept_memory.pop(0)
        base=system_prompt(author,memory=memory_text())+focus+extra
    sources,retrieval=retrieve(author,latest,history[-3]['content'] if len(history)>2 else '',rewrite=False,extra_terms=situation['terms'].split() if situation else [])
    selected=[{'role':'user','content':latest}]
    pairs=[history[i:i+2] for i in range(0,len(history)-1,2)][-6:]
    # Reserve room for evidence while retaining the most recent complete exchange.
    remaining=3200-estimate_tokens(base)-estimate_tokens(latest)-180
    kept=0
    if pairs:
        cost=sum(estimate_tokens(m['content']) for m in pairs[-1])
        if cost<=min(1100,remaining*.5):
            selected=[dict(m) for m in pairs[-1]]+selected
            remaining-=cost;kept=1
    passed=[]
    def make_instruction(items):
        evidence=[{'title':x['display_title'],'section':x['section'],
                   'lines':[x['start_line'],x['end_line']],'text':x['text'],
                   'edition':'English translation from Russian' if x.get('text_kind')=='translation-en' else 'English original'} for x in items]
        result=system_prompt(author,evidence,memory_text())
        if evidence:
            result+='\n작가별 말투를 유지하고 중국어는 쓰지 않는다.'
        else:
            result+='\n이번 답변에는 관련 원문이 제공되지 않았다. 특정 작품이나 장면을 근거로 제시하거나 원문을 참조했다고 말하지 않는다. 일반적인 작가 관점을 바탕으로 대화를 이어간다.'
        return result+'\n'+focus+'\n'+extra
    if estimate_tokens(make_instruction([]))+estimate_tokens(latest)>3200:
        raise ValueError('지금 입력이 모델의 문맥 한도를 넘었어요. 조금 짧게 나누어 주세요.')
    selected_cost=sum(estimate_tokens(m['content']) for m in selected)
    # Preserve more conversation context for Austen's follow-up questions. Search
    # still covers every work; only the amount of evidence passed is reduced.
    evidence_candidates=sources[:1] if author=='austen' else sources
    for source in evidence_candidates:
        if estimate_tokens(make_instruction(passed+[source]))+selected_cost<=3200:
            passed.append(source)
    instruction=make_instruction(passed)
    budget=3200-estimate_tokens(instruction)-selected_cost
    for pair in reversed(pairs[:len(pairs)-kept]):
        cost=sum(estimate_tokens(m['content']) for m in pair)
        if cost>budget:break
        selected=[dict(m) for m in pair]+selected;budget-=cost
    if not passed and sources:retrieval['status']='context-limit'
    retrieval['passed']=len(passed)
    payload={'messages':[{'role':'system','content':instruction}]+selected,
             'stream':True,'think':False,'keep_alive':'5m',
             'options':{'num_ctx':4096,'num_predict':policy['max_tokens'],'temperature':0.5}}
    meta={'type':'meta','sources':passed,'retrieval':retrieval,'trimmed':len(selected)<len(history),'reply_mode':policy['mode'],'memory_count':len(kept_memory),'memory_trimmed':len(kept_memory)<len(requested_memory)}
    return payload,meta
