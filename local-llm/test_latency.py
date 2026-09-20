import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ai import retrieval as r
from ai import quotations as q
from ai import context as web
from ai.prompts import reply_policy

class LatencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):r.ensure_index()
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(q,'CACHE_PATH',Path(tmp.name)/'cache.sqlite3');patcher.start();self.addCleanup(patcher.stop)
    def test_dictionary_hit_skips_rewrite_and_miss_uses_one_rewrite(self):
        with patch.object(r,'urlopen',side_effect=AssertionError('unnecessary model call')):
            sources,meta=r.retrieve('austen','연인이 약속 시간을 바꿔서 서운해요.')
        self.assertTrue(sources);self.assertEqual(meta['query_mode'],'dictionary-first')
        answer={'message':{'content':json.dumps({'terms':['love','fear','uncertainty']})}}
        with patch.object(r,'urlopen',return_value=io.BytesIO(json.dumps(answer).encode())) as request:
            sources,meta=r.retrieve('austen','마음이 먹먹해요')
        self.assertEqual(request.call_count,1);self.assertEqual(meta['query_mode'],'local-rewrite');self.assertTrue(sources)
    def test_translation_reuse_keeps_current_provenance_and_version_isolation(self):
        quote=q.select_quote(r.search('austen',['love','trust']))
        response={'message':{'content':json.dumps({'korean':'사랑과 믿음에 관한 번역 시험 문장입니다.'})}}
        with patch.object(q,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as request:
            first=q.translate_quote(quote)
        self.assertEqual(request.call_count,1);self.assertEqual(first['translation_cache'],'miss')
        with patch.object(q,'urlopen',side_effect=AssertionError('cache must avoid model call')):
            second=q.translate_quote({**quote,'source_page':'current-provenance'})
        self.assertEqual(second['translation_cache'],'hit');self.assertEqual(second['source_page'],'current-provenance');self.assertEqual(second['english'],quote['english'])
        with patch.object(q,'TRANSLATION_VERSION','new-version'):self.assertIsNone(q.cached_translation(quote))
        self.assertIsNone(q.cached_translation({**quote,'english':quote['english']+'Changed.'}))
        self.assertIsNone(q.cached_translation({**quote,'translator':'Different edition'}))
    def test_failed_translation_is_not_cached(self):
        quote=q.select_quote(r.search('william',['love']))
        with patch.object(q,'urlopen',side_effect=OSError('unavailable')):
            self.assertEqual(q.translate_quote(quote)['translation_status'],'failed')
        self.assertIsNone(q.cached_translation(quote))
    def test_brief_turn_limits_preserve_direct_advice_and_safety(self):
        brief=[{'role':'user','content':'연인에게 서운해요.'},{'role':'assistant','content':'어떤 일이 있었나요?'},{'role':'user','content':'약속 시간을 바꿨어요.'}]
        for author in ('austen','william','chekhov'):
            with patch.object(web,'retrieve',return_value=([],{'status':'no-match'})):
                payload,meta=web.build_request({'author':author,'messages':brief})
            self.assertEqual(meta['reply_mode'],'brief');self.assertLessEqual(payload['options']['num_predict'],160)
            self.assertEqual(payload['messages'][-3:],brief)
            for text in ['질문은 그만하고 어떻게 말할지 구체적으로 알려줘','연인이 때려서 위험해요.']:
                self.assertEqual(reply_policy(author,[{'role':'user','content':text}])['mode'],'advice')

if __name__=='__main__':unittest.main()
