#!/usr/bin/env python3
"""Local-only Jane chat with full-original retrieval; no fine-tuning."""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parent
MODEL = 'qwen3.5:4b'
ENDPOINT = 'http://127.0.0.1:11434/api/chat'
from ai.prompts import PERSPECTIVES, VOICE_STYLES, system_prompt, response_form, dialogue_focus, reply_policy

def generate(messages, max_tokens=450, emit=False):
    payload = {'model': MODEL, 'messages': messages, 'think': False, 'stream': True,
               'keep_alive': '5m', 'options': {'num_ctx': 4096, 'num_predict': max_tokens, 'temperature': 0.7, 'seed': 42}}
    request = Request(ENDPOINT, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    start = time.monotonic()
    first = None
    pieces = []
    last = {}
    with urlopen(request, timeout=300) as response:
        for line in response:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get('error'):
                raise RuntimeError(event['error'])
            part = event.get('message', {}).get('content', '')
            if part:
                if first is None:
                    first = time.monotonic()-start
                pieces.append(part)
                if emit:
                    print(part, end='', flush=True)
            if event.get('done'):
                last = event
    if not last:
        raise RuntimeError('Stream ended without completion metadata')
    answer = ''.join(pieces)
    seconds = last.get('eval_duration', 0)/1e9
    metrics = {'wall_seconds': round(time.monotonic()-start, 2), 'first_token_seconds': round(first,2) if first is not None else None,
               'prompt_tokens': last.get('prompt_eval_count'), 'output_tokens': last.get('eval_count'),
               'tokens_per_second': round(last.get('eval_count',0)/seconds,2) if seconds else None,
               'load_seconds': round(last.get('load_duration',0)/1e9,2), 'done_reason': last.get('done_reason')}
    if emit:
        print('\n')
    return answer, metrics

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--author', choices=PERSPECTIVES, default='austen')
    parser.add_argument('--message', help='One-shot prompt; omit for interactive chat')
    parser.add_argument('--source', action='store_true', help='Compatibility flag: full-original retrieval is now on by default')
    parser.add_argument('--no-rag', action='store_true', help='Baseline test using only the author perspective')
    parser.add_argument('--memory-file', type=Path, help='Explicitly supply a UTF-8 memory file')
    args = parser.parse_args()
    from ai.retrieval import ensure_index
    from ai.context import build_request, estimate_tokens
    from ai.quotations import select_quote, translate_quote, format_quote, strip_model_footer
    from ai.scope import concern_scope, scope_reply
    if not args.no_rag:ensure_index()
    source = None
    memory = args.memory_file.read_text(encoding='utf-8') if args.memory_file else None
    system = {'role':'system','content':system_prompt(args.author,source,memory)}
    messages = [system]
    print(f'Jane local · {MODEL} · {args.author} · /exit 종료 · /reset 대화 초기화')
    print('이 도구는 대화를 파일에 자동 저장하지 않습니다. 긴 대화는 /reset 후 새로 시작하세요.')
    while True:
        try:
            question = args.message if args.message else input('나 > ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question == '/exit':
            break
        if question == '/reset':
            messages = [system]
            continue
        if not question:
            continue
        # Keep local test input modest; production context/memory management is separate.
        if len(question)>2000 or sum(len(m['content']) for m in messages)+len(question)>6500:
            print('테스트 컨텍스트 한도입니다. 입력을 줄이거나 /reset 해 주세요.')
            if args.message:
                break
            continue
        previous=next((m['content'] for m in reversed(messages) if m['role']=='user'),'')
        if concern_scope(question,previous)=='outside':
            answer=scope_reply(args.author)
            print(answer)
            messages += [{'role':'user','content':question},{'role':'assistant','content':answer}]
            if args.message:break
            continue
        pending = messages + [{'role':'user','content':question}]
        try:
            if not args.no_rag:
                request,meta=build_request({'author':args.author,'messages':pending[1:][-41:]})
                pending=request['messages']
                if memory:
                    pending[0]['content']+='\n<user_memory>\n'+memory+'\n</user_memory>'
                    if sum(estimate_tokens(m['content']) for m in pending)>3200:
                        raise ValueError('기억 파일과 대화가 문맥 예산을 넘었습니다. 기억 파일을 줄여 주세요.')
                print('원문 검색: '+', '.join(x['display_title']+' · '+x['section'] for x in meta['sources']) if meta['sources'] else '관련 원문 없음')
            answer, metrics = generate(pending, max_tokens=request['options']['num_predict'] if not args.no_rag else reply_policy(args.author,pending[1:])['max_tokens'], emit=False)
            answer=strip_model_footer(answer)
            print(answer)
            if not args.no_rag:
                quotation=translate_quote(select_quote(meta['sources'],meta['retrieval']['terms']))
                print(format_quote(quotation))
        except Exception as error:
            print(f'실행 실패: {error}. serve.sh와 ollama list를 확인해 주세요.')
            if args.message:
                raise SystemExit(1)
            continue
        messages = pending + [{'role':'assistant','content':answer}]
        print(json.dumps(metrics, ensure_ascii=False))
        if args.message:
            break

if __name__ == '__main__':
    main()
