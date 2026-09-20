"""Romance domain routing, genuine source retrieval and API bypass regressions."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen
from ai import retrieval
from ai import context as web
from ai.scope import concern_scope

class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):retrieval.ensure_index()

    def test_context_and_topic_switch(self):
        cases=[('회사 동료와 사내연애 중인데 들킬까 걱정돼요.','','romance'),
               ('부모님이 결혼을 반대해요.','','romance'),
               ('연인이 바빠서 연락을 안 해요.','','romance'),
               ('My girlfriend does not trust me.','','romance'),
               ('그럼 어떻게 말할까?','연인과 다퉜어요.','romance'),
               ('부모님이 반대하세요.','연인과 결혼하고 싶어요.','general'),
               ('다른 고민인데 친구와 싸웠어.','연인이 연락을 안 해요.','general'),
               ('상사가 업무를 떠넘겨요.','연인과 다퉜어요.','general'),
               ('파이썬 코딩을 알려줘.','','general'),
               ('연애 말고 취업 상담 해줘.','','general'),
               ('그 사람이 마음에 걸려요.','','general'),
               ('오늘은 힘들어요.','','general'),
               ('직장에서 괴롭힘을 받아 죽고 싶어요.','','safety'),
               ('연인이 때려요.','','safety'),
               ('거절했는데 계속 연락하고 싶어.','','safety')]
        for q,p,expected in cases:
            with self.subTest(q=q):self.assertEqual(concern_scope(q,p),expected)

    def test_no_literary_retrieval_for_outside_or_safety(self):
        with patch.object(retrieval,'query_terms',side_effect=AssertionError('must skip rewrite')):
            for q in ['회사에서 죽고 싶다는 생각이 들어요']:
                sources,meta=retrieval.retrieve('william',q)
                self.assertEqual(sources,[])
                self.assertEqual(meta['terms'],[])

    def test_romantic_situations_retrieve_actual_author_sources(self):
        for author in ('austen','william','chekhov'):
            for q in ['연인이 답장을 안 해서 불안해요.','결혼을 부모님이 반대해요.','전 연인과 재회하고 싶어요.']:
                with self.subTest(author=author,q=q):
                    sources,meta=retrieval.retrieve(author,q,rewrite=False)
                    self.assertEqual(meta['scope'],'romance')
                    self.assertTrue(sources)
                    for source in sources:
                        lines=(retrieval.PROJECT/source['path']).read_text(encoding='utf-8-sig').splitlines()
                        self.assertEqual(source['text'],'\n'.join(lines[source['start_line']-1:source['end_line']]))
                    with patch.object(web,'retrieve',return_value=(sources,meta)):
                        payload,result=web.build_request({'author':author,'messages':[{'role':'user','content':q}]})
                    self.assertTrue(result['sources'])
                    self.assertLessEqual(sum(web.estimate_tokens(m['content']) for m in payload['messages']),3200)

    def test_general_concerns_use_model_path_and_sources(self):
        for author in ('austen','william','chekhov'):
            for question in ['상사가 업무를 떠넘겨요.','가족의 기대가 부담스러워요.','친구와 다퉜어요.']:
                sources,meta=retrieval.retrieve(author,question,rewrite=False)
                self.assertEqual(meta['scope'],'general')
                self.assertTrue(sources)
                payload,result=web.build_request({'author':author,'messages':[{'role':'user','content':question}]})
                self.assertIn('직장·진로',payload['messages'][0]['content'])
                self.assertNotIn('연애 관계만 다룬다',payload['messages'][0]['content'])

if __name__=='__main__':unittest.main()
