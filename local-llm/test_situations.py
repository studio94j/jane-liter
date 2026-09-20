import unittest
from unittest.mock import patch
from ai import context as web
import web_server as local_web
from ai.situations import select_situation,BY_ID
class SituationTests(unittest.TestCase):
    def test_cases_and_uncertain_evidence(self):
        self.assertEqual(len([x for x in BY_ID.values() if not x.get('legacy')]),7)
        for text,expected in [('가족의 기대가 부담스러워요','family'),('상사 때문에 고민이에요','work')]:
            item,origin=select_situation(None,text);self.assertEqual(item['id'],expected);self.assertEqual(origin,'tentative')
        with self.assertRaises(ValueError):select_situation('invented','hello')
    def test_situation_reaches_prompt_and_search_without_model_rewrite(self):
        for case in ['betrayal','temptation']:
            with patch.object(web,'retrieve',return_value=([],{'status':'no-match'})) as retrieve:
                payload,meta=web.build_request({'author':'austen','messages':[{'role':'user','content':'연인과의 관계를 어떻게 해야 할까요?'}],'situation':case})
            self.assertIn(BY_ID[case]['guidance'],payload['messages'][0]['content'])
            self.assertFalse(retrieve.call_args.kwargs['rewrite']);self.assertEqual(retrieve.call_args.kwargs['extra_terms'],BY_ID[case]['terms'].split())
    def test_only_advice_translates_and_emits_quote(self):
        base={'sources':[{}],'retrieval':{'terms':[],'status':'found'}}
        with patch.object(local_web,'select_quote',return_value={'english':'original'}),patch.object(local_web,'translate_quote',return_value={'korean':'번역'}) as translate:
            for mode,sources,status in [('brief',[{}],'found'),('advice',[],'no-match'),('advice',[{}],'safety-priority')]:
                events=[];local_web.emit_advice_quote({**base,'reply_mode':mode,'sources':sources,'retrieval':{'terms':[],'status':status}},events.append);self.assertEqual(events,[])
            translate.assert_not_called()
            events=[];local_web.emit_advice_quote({**base,'reply_mode':'advice'},events.append);translate.assert_called_once();self.assertEqual([x['type'] for x in events],['status','quote'])
if __name__=='__main__':unittest.main()
