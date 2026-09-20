import tempfile
from pathlib import Path
from ai import quotations as cache_module
import io
import json
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch
from ai import retrieval as r
from ai import quotations as q
from ai.prompts import system_prompt, VOICE_STYLES

class QuotationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        patcher=patch.object(cache_module,'CACHE_PATH',Path(tmp.name)/'translations.sqlite3');patcher.start();self.addCleanup(patcher.stop)

    @classmethod
    def setUpClass(cls):r.ensure_index()

    def test_quotes_are_contiguous_original_text_for_every_work(self):
        with closing(sqlite3.connect(r.INDEX)) as db:
            db.row_factory=sqlite3.Row
            works=db.execute('SELECT * FROM works').fetchall()
            for work in works:
                passage=db.execute('SELECT text FROM passages WHERE work_id=? AND length(text)>300 LIMIT 1',(work['id'],)).fetchone()[0]
                sources=r.search(work['author'],r.terms_from(passage),work['title'])
                quote=q.select_quote(sources)
                self.assertIsNotNone(quote,work['title'])
                lines=(r.PROJECT/quote['path']).read_text(encoding='utf-8-sig').splitlines()
                self.assertIn(quote['english'],'\n'.join(lines[quote['start_line']-1:quote['end_line']]))
                self.assertTrue(any(quote['english'] in s['text'] for s in sources))
                self.assertLessEqual(len(quote['english'].split()),45)

    def test_no_sources_and_tampered_english(self):
        self.assertIsNone(q.select_quote([]))
        source=r.search('austen',['trust','friend'])[0]
        source['text']='This entirely fabricated passage must never become a verified quotation.'
        self.assertIsNone(q.select_quote([source]))

    def test_translation_cannot_change_english(self):
        quote=q.select_quote(r.search('chekhov',['work','rest']))
        response={'message':{'content':json.dumps({'english':'Fabricated words','korean':'이것은 번역 처리 흐름을 확인하는 시험 문장이다.'})}}
        with patch.object(q,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
            translated=q.translate_quote(quote)
        self.assertEqual(translated['english'],quote['english'])
        self.assertEqual(translated['start_line'],quote['start_line'])
        self.assertEqual(translated['translation_status'],'complete')

    def test_translation_failure_does_not_fabricate_korean(self):
        quote=q.select_quote(r.search('william',['work','rest']))
        for content in ['invalid JSON',json.dumps({'korean':'English only'}),json.dumps({'korean':'한국어 中国'}),json.dumps({'korean':[]})]:
            response={'message':{'content':content}}
            with patch.object(q,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
                translated=q.translate_quote(quote)
            self.assertEqual(translated['translation_status'],'failed')
            self.assertIsNone(translated['korean'])
            self.assertEqual(translated['english'],quote['english'])

    def test_generated_source_heading_removed(self):
        self.assertEqual(q.strip_model_footer('그럴 수도 있겠지.\n\n<출처>\nMr. Banya'), '그럴 수도 있겠지.')
        self.assertEqual(q.strip_model_footer('본문\nSources: made up'), '본문')
        self.assertEqual(q.strip_model_footer('본문\n<출'), '본문')
        for tag in ['<출처: 익명의 이야기, 7637-7658 줄>', '<출처：', '<출처:']:
            self.assertEqual(q.strip_model_footer('본문\n\n'+tag), '본문')
        self.assertEqual(q.strip_model_footer('그 말의 출처를 살펴보겠소.'), '그 말의 출처를 살펴보겠소.')

    def test_distinct_voices_and_separate_translation(self):
        for author in VOICE_STYLES:
            prompt=system_prompt(author,[{'text':'Source data'}])
            self.assertIn(VOICE_STYLES[author],prompt)
            self.assertNotIn('자연스러운 한국어 존댓말로 답한다',prompt)
            self.assertIn('서버가 검증된 영어 발췌',prompt)
        self.assertIn('하오체',system_prompt('william'))
        self.assertIn('리젠시',system_prompt('austen'))
        self.assertIn('반말 독백체',system_prompt('chekhov'))

if __name__=='__main__':unittest.main()
