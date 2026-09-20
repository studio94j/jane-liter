"""Build an editorial starter deck and quote cache, checking every English excerpt."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ai.quotations import cache_translation
# Korean text and witch lines are editorial translations/creative interpretations.
ROWS=[
('austen','Till this moment, I never knew myself.','이 순간까지, 나는 나 자신을 모르고 있었다.',
 ['낯익은 마음에도 아직 읽지 못한 방이 있구나.','처음 내린 판단이 마지막 답일 필요는 없으리라.','오늘은 남의 평가보다 그대의 마음을 다시 펼쳐 보아라.'],'최근 생각이 달라진 일은 무엇인가요?'),
('austen','time will explain.','시간이 설명해 줄 것이다.',
 ['아직 이름 붙이지 못한 징조가 있구나.','기다림은 답을 드러낼 수도, 질문을 바꿀 수도 있으리라.','서둘러 결론 내리기 전에 오늘 확인할 사실 하나를 보아라.'],'지금 아는 사실과 기다려야 알 수 있는 일은 무엇인가요?'),
('austen','There is no charm equal to tenderness of heart,','다정한 마음에 견줄 매력은 없다.',
 ['큰 말보다 작은 다정함이 눈에 들어올 날이로다.','빛나는 모습과 마음의 온기는 다를 수 있으리라.','그대 자신에게도 다정한 선택을 남겨 두어라.'],'오늘 나에게 다정하게 할 수 있는 일은 무엇인가요?'),
('william','Give sorrow words.','슬픔에 말을 주어라.',
 ['말하지 못한 마음이 문턱에 서 있구나.','침묵이 지켜 주던 것이 때로는 무거운 짐이 되리라.','모든 것을 말할 필요는 없으니 한 문장부터 골라 보아라.'],'마음에 남은 일을 한 문장으로 적는다면요?'),
('william','Wisely and slow; they stumble that run fast.','신중하게, 천천히. 서둘러 달리는 이들은 넘어진다.',
 ['발걸음보다 마음이 먼저 달려가고 있구나.','빠른 길이 늘 원하는 곳으로 이어지지는 않으리라.','한 번 숨을 고르면 다음 발 디딜 곳이 보일 수도 있으리라.'],'오늘 서두르지 않아도 되는 일 하나는 무엇인가요?'),
('william','Our doubts are traitors,\nAnd make us lose the good we oft might win\nBy fearing to attempt.','의심은 배신자다. 시도하기를 두려워하게 해, 얻을 수도 있었을 좋은 것을 잃게 한다.',
 ['문 앞에는 가능성과 두려움이 함께 서 있구나.','망설임이 그대를 지킬 때도, 길을 가릴 때도 있으리라.','무모한 도약 대신 되돌릴 수 있는 작은 시도를 택해 보아라.'],'부담 없이 시험해 볼 수 있는 작은 선택은 무엇인가요?'),
('chekhov','Suppose we could use\none life, already ended, as a sort of rough draft for another?','이미 끝난 한 삶을 다른 삶을 위한 일종의 초안으로 삼을 수 있다면?',
 ['지나온 날들이 고쳐 쓸 수 없는 초안처럼 놓였구나.','같은 장면을 떠올려도 오늘의 눈은 어제와 다르리라.','새 삶을 기다리기 전에 작은 반복 하나를 바꾸어 보아라.'],'다시 반복하고 싶지 않은 작은 습관은 무엇인가요?'),
('chekhov','If only we could know, if only we could know!','알 수만 있다면, 알 수만 있다면!',
 ['답을 바라는 목소리가 오늘도 들리는구나.','모른다는 사실만 또렷해지는 날도 있으리라.','답이 오기 전에도 그대의 하루를 돌볼 수는 있으리라.'],'답을 기다리는 동안 나를 돌볼 방법은 무엇인가요?'),
('chekhov','We shall rest.','우리는 쉬게 될 것이다.',
 ['지친 손끝에 쉬고 싶은 마음이 머물러 있구나.','견디는 일과 쉬는 일이 반드시 적일 필요는 없으리라.','먼 훗날의 쉼을 기다리기 전에 오늘의 틈 하나를 찾아라.'],'오늘 잠깐 내려놓아도 괜찮은 일은 무엇인가요?')]
NAMES={'austen':'제인 오스틴','william':'윌리엄 셰익스피어','chekhov':'안톤 체호프'}
def main():
 cards=[]
 with sqlite3.connect(ROOT/'ai/index/originals.sqlite3') as db:
  db.row_factory=sqlite3.Row
  for author,english,korean,lines,action in ROWS:
   r=db.execute('SELECT p.text,p.start_line,p.section,w.* FROM passages p JOIN works w ON w.id=p.work_id WHERE w.author=? AND p.text LIKE ? LIMIT 1',(author,'%'+english+'%')).fetchone()
   if not r: raise ValueError('Unverified quotation: '+english)
   original=(ROOT/r['path']).read_text(encoding='utf-8-sig')
   assert english in original
   quote={'english':english,'korean':korean,'path':r['path'],'original_title':r['title'],'title':r['display_title'],
          'section':r['section'],'translator':r['translator'],'text_kind':r['text_kind'],'source_page':r['source_page'],
          'author':author,'author_name':NAMES[author],'translation_status':'complete'}
   quote['id']=hashlib.sha256((quote['path']+'\n'+english).encode()).hexdigest()[:24]
   cache_translation(quote,korean)
   public={k:v for k,v in quote.items() if k!='path'}
   cards.append({'id':quote['id'],'title':NAMES[author]+'에게서 온 징조','lines':lines,'baseLines':lines,'action':action,'quote':public})
 (ROOT/'cloud/prophecies.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2))
 print('Verified editorial prophecy cards:',len(cards))
if __name__=='__main__':main()
