import tempfile
from pathlib import Path
from ai import quotations as cache_module
import io
import json
import random
import sqlite3
import threading
import unittest
from contextlib import closing
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import prophecy as p
from ai import retrieval as r
import web_server as web

class ProphecyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(cache_module,'CACHE_PATH',Path(tmp.name)/'translations.sqlite3');patcher.start();self.addCleanup(patcher.stop)

    @classmethod
    def setUpClass(cls):r.ensure_index()

    def test_all_eighty_works_are_eligible_and_quotes_are_verbatim(self):
        with closing(sqlite3.connect(r.INDEX)) as db:
            db.row_factory=sqlite3.Row
            works=list(db.execute('SELECT id,author FROM works'))
        self.assertEqual(len(works),80)
        for work in works:
            class PreferWork:
                def shuffle(self,items):
                    if isinstance(items[0],str):items.sort(key=lambda a:a!=work['author'])
                    elif 'id' in items[0].keys():items.sort(key=lambda w:w['id']!=work['id'])
                    else:random.Random(7).shuffle(items)
            q=p.draw_quote(rng=PreferWork())
            self.assertEqual(q['author'],work['author'])
            with closing(sqlite3.connect(r.INDEX)) as db:
                title=db.execute('SELECT title FROM works WHERE id=?',(work['id'],)).fetchone()[0]
            self.assertEqual(q['original_title'],title)
            original=(r.PROJECT/q['path']).read_text(encoding='utf-8-sig').splitlines()
            self.assertIn(q['english'],'\n'.join(original[q['start_line']-1:q['end_line']]))

    def test_repeat_exclusion_and_three_author_coverage(self):
        seen=[];authors=set()
        for seed in range(12):
            q=p.draw_quote(seen,random.Random(seed));self.assertNotIn(q['id'],seen);seen.append(q['id']);authors.add(q['author'])
        self.assertEqual(authors,set(p.AUTHOR_NAMES))

    def test_model_cannot_replace_quote_or_source(self):
        q=p.draw_quote(rng=random.Random(1))
        output={'korean':'마음의 말을 천천히 들어 보세요.','lines':['그대 마음의 소리를 들어라.','모르는 마음을 정하지 말라.','그대의 선택을 남겨 두어라.'],'action':'오늘 어떤 마음을 전하고 싶나요?','english':'FAKE','title':'FAKE'}
        response={'message':{'content':json.dumps(output,ensure_ascii=False)}}
        with patch.object(p,'draw_quote',return_value=q),patch.object(p,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as upstream:
            card=p.generate_prophecy()
        self.assertEqual(card['quote']['english'],q['english']);self.assertEqual(card['quote']['title'],q['title']);self.assertEqual(card['baseLines'],output['lines'])
        self.assertEqual(upstream.call_count,1)
        cached_response={'message':{'content':json.dumps({'lines':output['lines'],'action':output['action']},ensure_ascii=False)}}
        with patch.object(p,'draw_quote',return_value=q),patch.object(p,'urlopen',return_value=io.BytesIO(json.dumps(cached_response).encode())) as second:
            cached=p.generate_prophecy()
        self.assertEqual(cached['quote']['translation_cache'],'hit')
        self.assertNotIn('korean',json.loads(second.call_args.args[0].data)['format']['required'])
        with patch.object(p,'draw_quote',return_value=q),patch.object(p,'urlopen',return_value=io.BytesIO(b'{"message":{"content":"{}"}}')):
            with self.assertRaises(RuntimeError):p.generate_prophecy()

    def test_endpoint_validates_only_exclusion_ids_and_shares_model_lock(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),web.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def call(data):return urlopen(Request(f'http://127.0.0.1:{server.server_port}/api/prophecy',data=json.dumps(data).encode(),headers={'Host':'127.0.0.1:8317','Content-Type':'application/json'}))
        try:
            with patch.object(web,'generate_prophecy',return_value={'id':'a'*24}) as generate:
                with call({'exclude':['b'*24]}) as res:self.assertEqual(json.load(res)['card']['id'],'a'*24)
                generate.assert_called_once_with(['b'*24])
                for invalid in [{'dob':'1995-05-17'}, {'exclude':['bad']}, {'exclude':['b'*24]*21}]:
                    with self.assertRaises(HTTPError) as error:call(invalid)
                    self.assertEqual(error.exception.code,400)
                web.GENERATION_LOCK.acquire()
                try:
                    with self.assertRaises(HTTPError) as error:call({'exclude':[]})
                    self.assertEqual(error.exception.code,409)
                finally:web.GENERATION_LOCK.release()
                self.assertEqual(generate.call_count,1)
                self.assertFalse(web.GENERATION_LOCK.locked())
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
