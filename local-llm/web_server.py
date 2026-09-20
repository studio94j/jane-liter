#!/usr/bin/env python3
"""Loopback-only static prototype + bounded Ollama streaming proxy (no chat storage)."""
import json
import math
import time
import re
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chat import MODEL, ROOT
from ai.context import build_request as shared_request, validate_request
def build_request(data):
    payload, meta = shared_request(data)
    payload["model"] = MODEL
    meta["model"] = MODEL
    return payload, meta
from ai.retrieval import ensure_index, retrieve, stats
from ai.scope import concern_scope
from prophecy import generate_prophecy
from ai.situations import select_situation, situation_instruction
from ai.quotations import select_quote, translate_quote, strip_model_footer

PROTO = ROOT.parent / 'proto'
ORIGIN_HOSTS = {'127.0.0.1:8317', 'localhost:8317'}
GENERATION_LOCK = threading.Lock()

def emit_advice_quote(meta,emit):
    if meta['reply_mode']!='advice' or not meta['sources'] or meta['retrieval'].get('status')=='safety-priority':
        return
    emit({'type':'status','stage':'quotation'})
    quote=translate_quote(select_quote(meta['sources'],meta['retrieval']['terms']))
    emit({'type':'quote','quote':quote})

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(PROTO),**kwargs)

    def log_message(self,format,*args):
        # Never log prompts, responses or query strings.
        pass

    def allowed(self):
        host=self.headers.get('Host','')
        origin=self.headers.get('Origin')
        return host in ORIGIN_HOSTS and (not origin or origin in {'http://'+x for x in ORIGIN_HOSTS})

    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

    def json_response(self,code,data):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed():
            self.json_response(403,{'error':'로컬 주소에서 열어 주세요.'});return
        path=urlparse(self.path).path
        if path=='/api/health':
            try:
                with urlopen('http://127.0.0.1:11434/api/tags',timeout=3) as response:
                    models=json.load(response).get('models',[])
                ready=any(m.get('name')==MODEL for m in models)
                self.json_response(200,{'ready':ready,'model':MODEL,'busy':GENERATION_LOCK.locked(),'corpus':stats()})
            except (OSError,URLError,ValueError):
                self.json_response(503,{'ready':False,'model':MODEL})
            return
        if path.startswith('/api/'):
            self.json_response(404,{'error':'없는 API 주소입니다.'});return
        candidate=Path(self.translate_path(self.path)).resolve()
        if not candidate.is_relative_to(PROTO.resolve()):
            self.send_error(403);return
        super().do_GET()

    def serve_prophecy(self):
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.json_response(415,{'error':'JSON 요청만 지원합니다.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError('요청 크기를 확인해 주세요.')
            self.connection.settimeout(15)
            data=json.loads(self.rfile.read(size))
            exclude=data.get('exclude',[]) if isinstance(data,dict) else None
            if not isinstance(data,dict) or set(data)-{'exclude'} or not isinstance(exclude,list) or len(exclude)>20 or any(not isinstance(x,str) or not re.fullmatch(r'[a-f0-9]{24}',x) for x in exclude):
                raise ValueError('예언 요청 형식을 확인해 주세요.')
        except (ValueError,TypeError,UnicodeError,OSError):
            self.json_response(400,{'error':'예언 요청 형식을 확인해 주세요.'});return
        if not GENERATION_LOCK.acquire(blocking=False):
            self.json_response(409,{'error':'작가가 다른 답변을 쓰고 있어요. 답변이 끝난 뒤 예언을 다시 받아 주세요.'});return
        try:
            card=generate_prophecy(exclude)
            self.json_response(200,{'card':card})
        except RuntimeError as error:
            self.json_response(503,{'error':str(error)})
        except (BrokenPipeError,ConnectionResetError):
            pass
        finally:GENERATION_LOCK.release()

    def do_POST(self):
        if not self.allowed():
            self.json_response(403,{'error':'로컬 페이지에서 요청해 주세요.'});return
        if self.path=='/api/prophecy':
            self.serve_prophecy();return
        if self.path!='/api/chat':
            self.json_response(404,{'error':'없는 API 주소입니다.'});return
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.json_response(415,{'error':'JSON 요청만 지원합니다.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=100000:
                self.json_response(413,{'error':'대화 내용이 너무 길어요.'});return
            self.connection.settimeout(15)
            data=json.loads(self.rfile.read(size))
            validate_request(data)
        except (ValueError,TypeError,UnicodeError) as error:
            self.json_response(400,{'error':str(error) if isinstance(error,ValueError) and not isinstance(error,json.JSONDecodeError) else '요청을 읽을 수 없어요.'});return
        except OSError:
            self.json_response(408,{'error':'입력 전송 시간이 초과됐어요.'});return
        if not GENERATION_LOCK.acquire(blocking=False):
            self.json_response(409,{'error':'다른 대화의 답변을 생성 중이에요. 잠시 뒤 다시 보내 주세요.'});return
        started=False
        upstream=None
        def emit(event):
            self.wfile.write((json.dumps(event,ensure_ascii=False)+'\n').encode())
            self.wfile.flush()
        try:
            started_at=time.monotonic()
            payload,meta=build_request(data)
            retrieved_at=time.monotonic()
            first_token=None
            request=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            upstream=urlopen(request,timeout=180)
            self.connection.settimeout(30)
            self.send_response(200)
            self.send_header('Content-Type','application/x-ndjson; charset=utf-8')
            self.send_header('Connection','close')
            self.end_headers();started=True
            emit(meta)
            done=False
            raw_body='';visible_body=''
            for line in upstream:
                event=json.loads(line)
                if event.get('error'):
                    raise RuntimeError('모델이 응답을 완료하지 못했어요.')
                content=event.get('message',{}).get('content','')
                if content:
                    if first_token is None:first_token=time.monotonic()-started_at
                    raw_body+=content
                    clean=strip_model_footer(raw_body)
                    if clean.startswith(visible_body):
                        delta=clean[len(visible_body):]
                        if delta:emit({'type':'delta','content':delta})
                    elif clean!=visible_body:
                        emit({'type':'replace','content':clean})
                    visible_body=clean
                if event.get('done'):
                    completion={'type':'done','reason':event.get('done_reason'),'output_tokens':event.get('eval_count')}
                    done=True;break
            if not done:
                raise RuntimeError('응답 연결이 중간에 끊겼어요.')
            upstream.close();upstream=None
            reply_at=time.monotonic()
            emit_advice_quote(meta,emit)
            completion['timings']={'retrieval_seconds':round(retrieved_at-started_at,3),'first_token_seconds':round(first_token,3) if first_token is not None else None,'reply_seconds':round(reply_at-retrieved_at,3),'translation_seconds':round(time.monotonic()-reply_at,3),'total_seconds':round(time.monotonic()-started_at,3)}
            emit(completion)
        except (BrokenPipeError,ConnectionResetError):
            pass
        except (OSError,URLError,ValueError,RuntimeError) as error:
            message='로컬 모델에 연결할 수 없어요. Ollama 서버 실행을 확인한 뒤 다시 시도해 주세요.'
            if isinstance(error,(TimeoutError,socket.timeout)):
                message='답변 대기 시간이 초과됐어요. 잠시 뒤 다시 시도해 주세요.'
            elif isinstance(error,RuntimeError):
                message=str(error)
            try:
                if started:emit({'type':'error','message':message})
                else:self.json_response(503,{'error':message})
            except OSError:pass
        finally:
            if upstream:upstream.close()
            GENERATION_LOCK.release()
            self.close_connection=True

if __name__=='__main__':
    ensure_index()
    print('Original-text search: '+json.dumps(stats()),flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',8317),Handler)
    print('Jane + Qwen: http://127.0.0.1:8317/?v=26#chat',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
