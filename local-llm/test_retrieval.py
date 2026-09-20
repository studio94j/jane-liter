"""Meaningful corpus/provenance/context regression checks; no network or model required."""
from contextlib import closing
import hashlib
import json
import sqlite3
import time
import unittest
from unittest.mock import patch
from ai import retrieval as r
from ai import context as web

class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):r.ensure_index()

    def test_all_works_and_original_line_coverage(self):
        self.assertEqual({a:s['works'] for a,s in r.stats().items()},{'austen':7,'william':44,'chekhov':29})
        with closing(sqlite3.connect(r.INDEX)) as db:
            db.row_factory=sqlite3.Row
            files={}
            for work in db.execute('SELECT * FROM works'):
                path=r.PROJECT/work['path']
                if str(path) not in files:files[str(path)]=path.read_bytes().decode('utf-8-sig').splitlines()
                lines=files[str(path)]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),work['sha256'])
                covered=set()
                for p in db.execute('SELECT * FROM passages WHERE work_id=?',(work['id'],)):
                    self.assertEqual(p['text'],'\n'.join(lines[p['start_line']-1:p['end_line']]))
                    self.assertNotIn('*** END OF',p['text'])
                    self.assertGreaterEqual(p['start_line'],work['start_line'])
                    self.assertLessEqual(p['end_line'],work['end_line'])
                    covered.update(range(p['start_line'],p['end_line']+1))
                missing=[i for i in range(work['start_line'],work['end_line']+1) if lines[i-1].strip() and i not in covered]
                self.assertEqual(missing,[],work['title'])

    def test_every_work_can_be_retrieved(self):
        # Take a substantive middle passage from EACH work, not hand-picked fixed samples.
        with closing(sqlite3.connect(r.INDEX)) as db:
            db.row_factory=sqlite3.Row
            for work in db.execute('SELECT * FROM works'):
                passages=db.execute('SELECT text FROM passages WHERE work_id=? AND length(text)>300',(work['id'],)).fetchall()
                passage=passages[len(passages)//2]['text']
                terms=r.terms_from(passage)
                results=r.search(work['author'],terms,work['title'])
                self.assertTrue(results,work['title'])
                self.assertTrue(all(x['work_id']==work['id'] for x in results))

    def test_author_isolation_no_match_and_syntax(self):
        for author in ('austen','william','chekhov'):
            hits=r.search(author,['love','secret','trust'])
            self.assertTrue(hits)
            self.assertTrue(all(('/'+{'austen':'austen','william':'shakespeare','chekhov':'chekhov'}[author]+'/') in x['path'] for x in hits))
        self.assertEqual(r.search('austen',['xyznonexistentword']),[])
        r.search('austen',['" OR *); DROP TABLE works;--'])
        self.assertEqual(r.stats()['austen']['works'],7)

    def test_fallback_and_followup(self):
        terms,mode=r.query_terms('친구가 비밀을 말했어요',rewrite=False)
        self.assertIn('friend',terms);self.assertIn('secret',terms)
        terms,_=r.query_terms('어떻게 말할까요?',previous='가족과 돈 때문에 갈등이 있어요',rewrite=False)
        self.assertIn('money',terms)

    def test_chekhov_edition_and_prompt(self):
        self.assertEqual(set(web.PERSPECTIVES),set(r.AUTHOR_IDS.values()))
        with closing(sqlite3.connect(r.INDEX)) as db:
            works=db.execute("SELECT title,start_line FROM works WHERE author='chekhov'").fetchall()
        expected={t for e in json.loads(r.CHEKHOV_CATALOG.read_text()).values() for t in e['works']}
        self.assertEqual({w[0] for w in works},expected)
        sources=r.search('chekhov',['work','rest','tired'],'바냐 아저씨')
        self.assertTrue(sources)
        self.assertTrue(all(s['title']=='UNCLE VANYA' and s['text_kind']=='translation-en' for s in sources))
        self.assertIn('체호프',web.system_prompt('chekhov'))
        self.assertNotIn('오스틴',web.system_prompt('chekhov'))
        # Translator introduction in the play collection is preserved on disk, excluded from RAG.
        with closing(sqlite3.connect(r.INDEX)) as db:
            first=db.execute("SELECT start_line FROM works WHERE author='chekhov' AND title='ON THE HIGH ROAD'").fetchone()[0]
        self.assertGreater(first,200)

    def test_payload_and_metadata_match(self):
        def offline(author,question,previous='',**kwargs):return r.retrieve(author,question,previous,rewrite=False,extra_terms=kwargs.get('extra_terms'))
        for author in ('austen','william','chekhov'):
            history=[{'role':'user','content':'연인이 비밀을 알려서 신뢰가 깨졌어요.'}]
            with patch.object(web,'retrieve',side_effect=offline):payload,meta=web.build_request({'author':author,'messages':history})
            self.assertTrue(meta['sources'])
            for source in meta['sources']:
                self.assertIn(json.dumps(source['text'],ensure_ascii=False)[1:-1],payload['messages'][0]['content'])
            self.assertLessEqual(sum(web.estimate_tokens(m['content']) for m in payload['messages']),3200)
        history=[]
        for i in range(10):history.extend([{'role':'user','content':'회사에서 받은 부당한 대우 때문에 고민이 있어요. '*10},{'role':'assistant','content':'말씀하신 상황을 조금 더 구체적으로 설명해 주실 수 있나요? '*10}])
        history.append({'role':'user','content':'그래서 거절하려고 해요.'})
        with patch.object(web,'retrieve',side_effect=offline):payload,meta=web.build_request({'author':'austen','messages':history})
        self.assertTrue(meta['trimmed'])
        self.assertEqual(payload['messages'][-1],history[-1])
        self.assertLessEqual(sum(web.estimate_tokens(m['content']) for m in payload['messages']),3200)
        with patch.object(web,'retrieve',side_effect=offline):payload,meta=web.build_request({'author':'william','messages':[{'role':'user','content':'xyznonexistentword'}]})
        self.assertEqual(meta['sources'],[])
        self.assertEqual(meta['retrieval']['status'],'no-match')
        self.assertIn('관련 원문이 제공되지 않았다',payload['messages'][0]['content'])

    def test_author_followup_preserves_detail_and_correction_within_budget(self):
        history=[]
        for _ in range(8):
            history.extend([{'role':'user','content':'이전 직장 이야기. '*40},
                            {'role':'assistant','content':'그때는 그런 생각이 들었겠네. '*25}])
        recent=[{'role':'user','content':'책상 서랍에 사직서를 넣어 두었어.'},
                {'role':'assistant','content':'떠나는 일이 두려운 걸 수도 있겠네.'},
                {'role':'user','content':'두려운 건 아니야. 사실은 동료가 붙잡아 줬으면 좋겠어.'}]
        history.extend(recent)
        def offline(author,question,previous='',**kwargs):
            return r.retrieve(author,question,previous,rewrite=False,extra_terms=kwargs.get('extra_terms'))
        for author in ('austen','william','chekhov'):
            with self.subTest(author=author):
                with patch.object(web,'retrieve',side_effect=offline):
                    payload,meta=web.build_request({'author':author,'messages':history})
                    fresh,_=web.build_request({'author':author,'messages':[{'role':'user','content':'오늘은 친구 이야기야.'}]})
                # Preserve literal user facts and the latest correction as distinct turns,
                # without turning an assistant's speculation into a stored user memory.
                self.assertEqual(payload['messages'][-3:],recent)
                self.assertTrue(meta['trimmed'])
                self.assertTrue(meta['sources'])
                self.assertLessEqual(sum(web.estimate_tokens(m['content']) for m in payload['messages']),3200)
                self.assertNotIn('사직서',str(fresh['messages']))

    def test_austen_direct_advice_overrides_exploration_without_cross_author_leak(self):
        user={'role':'user','content':'질문은 그만하고 다음에 어떻게 말할지 알려주세요.'}
        # A direct request has the same priority on the first or a later turn.
        first=web.dialogue_focus('austen',[user])
        later=web.dialogue_focus('austen',[{'role':'user','content':'친구 때문에 지쳐요.'},
            {'role':'assistant','content':'최근에 어떤 일이 있었나요?'},user])
        self.assertEqual(first,later)
        self.assertNotEqual(first,web.dialogue_focus('austen',[{'role':'user','content':'친구 때문에 지쳐요.'}]))
        self.assertEqual(web.dialogue_focus('william',[user]),'')
        self.assertEqual(web.dialogue_focus('chekhov',[user]),'')

    def test_austen_context_limit_includes_dialogue_guidance(self):
        # Near the accepted input boundary, never silently exceed the final budget.
        size=int((2940-web.estimate_tokens(web.system_prompt('austen')))/1.6)
        data={'author':'austen','messages':[{'role':'user','content':'가'*size}]}
        web.validate_request(data)
        with patch.object(web,'retrieve',return_value=([],{'status':'no-match'})):
            try:
                payload,_=web.build_request(data)
            except ValueError as error:
                self.assertIn('문맥 한도',str(error))
            else:
                self.assertLessEqual(sum(web.estimate_tokens(m['content']) for m in payload['messages']),3200)

if __name__=='__main__':unittest.main()
