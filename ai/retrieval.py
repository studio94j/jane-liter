#!/usr/bin/env python3
"""Local full-original retrieval. SQLite FTS5 + optional local English query rewrite.
Original bytes are never modified; all excerpts carry inclusive original line numbers.
"""
from .scope import concern_scope
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import threading
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
MANIFEST = PROJECT / 'data/originals/manifest.json'
INDEX = ROOT / 'index/originals.sqlite3'
VERSION = 2
AUTHOR_IDS = {'austen':'austen', 'shakespeare':'william', 'chekhov':'chekhov'}
CHEKHOV_CATALOG = PROJECT / 'data/originals/chekhov/catalog.json'
BUILD_LOCK = threading.Lock()
TITLES_KO = {
    'THE SEA-GULL':'갈매기',
    'UNCLE VANYA':'바냐 아저씨',
    'THE CHERRY ORCHARD':'벚꽃 동산',
    'THE THREE SISTERS':'세 자매',
    'THE DARLING':'귀여운 여인',
    'THE LADY WITH THE DOG':'개를 데리고 다니는 여인',
    'THE PROPOSAL':'청혼',
    'THE BEAR':'곰',
    'THE BLACK MONK':'검은 수도승',
    'THREE YEARS':'삼 년',
    "AN ARTIST'S STORY":'화가의 이야기',
    'ON THE HIGH ROAD':'큰길에서',
    'THE WEDDING':'결혼식',
    'A TRAGEDIAN IN SPITE OF HIMSELF':'본의 아닌 비극 배우',
    'THE ANNIVERSARY':'기념일',
    "A DOCTOR'S VISIT":'왕진',
    'AN UPHEAVAL':'소동',
    'IONITCH':'이오니치',
    'THE HEAD OF THE FAMILY':'가장',
    'VOLODYA':'볼로쟈',
    'AN ANONYMOUS STORY':'익명의 이야기',
    'THE HUSBAND':'남편',
    'ARIADNE':'아리아드네',
    'POLINKA':'폴린카',
    'ANYUTA':'아뉴타',
    'THE TWO VOLODYAS':'두 볼로쟈',
    'THE TROUSSEAU':'혼수',
    'THE HELPMATE':'아내',
    'TALENT':'재능',

    'Pride and Prejudice':'오만과 편견', 'Sense and Sensibility':'이성과 감성',
    'Emma':'엠마', 'Mansfield Park':'맨스필드 파크', 'Persuasion':'설득',
    'Northanger Abbey':'노생거 사원', 'Lady Susan':'레이디 수전',
    'THE SONNETS':'소네트', 'THE TRAGEDY OF HAMLET, PRINCE OF DENMARK':'햄릿',
    'THE TRAGEDY OF OTHELLO, THE MOOR OF VENICE':'오셀로',
    'THE TRAGEDY OF KING LEAR':'리어 왕', 'THE TRAGEDY OF MACBETH':'맥베스',
    'THE TEMPEST':'템페스트', 'THE MERCHANT OF VENICE':'베니스의 상인',
    'THE TRAGEDY OF ROMEO AND JULIET':'로미오와 줄리엣',
    'A MIDSUMMER NIGHT’S DREAM':'한여름 밤의 꿈', 'TWELFTH NIGHT; OR, WHAT YOU WILL':'십이야',
    'AS YOU LIKE IT':'뜻대로 하세요', 'MUCH ADO ABOUT NOTHING':'헛소동',
    'THE WINTER’S TALE':'겨울 이야기', 'THE TAMING OF THE SHREW':'말괄량이 길들이기',
    'THE TWO GENTLEMEN OF VERONA':'베로나의 두 신사',
}
# Fallback only. The model normally translates the actual situation into search terms.
THEMES = [
    (('직장','상사','업무','회사','퇴사'), 'work duty burden ambition'),
    (('취업','이직','진로','면접'), 'choice ambition opportunity uncertainty'),
    (('지친','무기력','피로','번아웃'), 'weariness rest hope life'),
    (('연애','사랑','짝사랑','남친','여친','애인','연인','썸','사귀'), 'love affection courtship'),
    (('답장','연락','읽씹','잠수'), 'letter silence neglect'),
    (('고백','호감','데이트'), 'affection courtship confess'),
    (('재회','전 연인','전연인'), 'parting reconciliation regret'),
    (('약속','취소','미뤄','미루','시간을 바'), 'promise appointment disappointment'),
    (('서운','소홀'), 'neglect disappointment attention'),
    (('사과','화해'), 'apology forgiveness reconciliation'),
    (('장거리',), 'distance absence longing'),
    (('거절','경계','동의'), 'consent refusal respect'),
    (('결혼','조건'), 'marriage fortune character'),
    (('사내연애',), 'love secrecy reputation'),
    (('친구','우정'), 'friend friendship kindness'),
    (('가족','부모','엄마','아빠'), 'family father mother duty'),
    (('형제','자매','동생','언니','누나'), 'brother sister family'),
    (('배신','비밀','믿음','신뢰','거짓'), 'trust deceit secret betrayal'),
    (('질투','비교'), 'jealousy envy pride'),
    (('돈','경제','월급','재산'), 'money fortune poverty'),
    (('후회','실수','잘못'), 'regret error forgiveness'),
    (('외로','혼자','고독'), 'lonely solitude company'),
    (('선택','결정','진로'), 'choice judgment doubt'),
    (('평판','시선','인정'), 'reputation opinion esteem'),
    (('화가','분노','싸움','갈등'), 'anger quarrel reconciliation'),
    (('불안','두려','걱정'), 'fear anxiety uncertainty'),
    (('헤어','이별','상실'), 'parting grief loss'),
    (('거절','부탁','부담'), 'refuse obligation consent'),
]
STOP = set('the a an i me my you your he she we they it is are was be have has do and or but to of in on for with from this that what how please advice about feel feeling want very really just some can could would should tell help'.split())


def terms_from(text):
    return list(dict.fromkeys(w.lower() for w in re.findall(r'[A-Za-z]{3,}', text) if w.lower() not in STOP))[:12]


def body_bounds(lines):
    start = next(i+1 for i,s in enumerate(lines) if s.startswith('*** START OF'))
    end = next(i for i,s in enumerate(lines) if s.startswith('*** END OF'))
    return start, end


def sections(entry, lines):
    """Yield work, section, [start,end) covering every line of each work body."""
    start, end = body_bounds(lines)
    if entry['author'] == 'austen':
        if entry['gutenberg_id'] == 946:
            marks = [(i, 'Letter '+lines[i]) for i in range(start,end)
                     if re.fullmatch(r'[IVXLCDM]+|CONCLUSION', lines[i])]
        else:
            marks = [(i, lines[i].strip(' [].')) for i in range(start,end)
                     if re.fullmatch(r'Chapter\s+(?:[IVXLCDM]+|\d+)', lines[i].strip(' [].'), re.I)]
            # TOC chapter entries are adjacent; real chapters contain prose.
            first = next(j for j,(i,_) in enumerate(marks) if (marks[j+1][0] if j+1<len(marks) else end)-i > 25)
            marks = marks[first:]
        if not marks:
            raise ValueError('No chapters found: '+entry['title'])
        volume = ''
        for j,(i,label) in enumerate(marks):
            previous = marks[j-1][0] if j else start
            for s in lines[previous:i]:
                if re.fullmatch(r'VOLUME [IVXLCDM]+',s.strip()):volume=s.strip()
            yield entry['title'], (volume+' · ' if volume else '')+label, i, marks[j+1][0] if j+1<len(marks) else end
    elif entry['author'] == 'chekhov':
        titles=json.loads(CHEKHOV_CATALOG.read_text())[str(entry['gutenberg_id'])]['works']
        if len(titles)==1:
            first=next(i for i in range(start,end) if lines[i].strip()==titles[0])
            works=[(first,titles[0])]
        else:
            toc=next(i for i in range(start,end) if lines[i].strip()=='CONTENTS')
            # Skip the complete TOC before looking for body headings. This excludes
            # the translator's introduction in Plays Second Series.
            cursor=next(i+1 for i in range(toc+1,end) if lines[i].strip()==titles[-1])
            works=[]
            for title in titles:
                pos=next(i for i in range(cursor,end) if lines[i].strip()==title)
                works.append((pos,title));cursor=pos+1
        for n,(lo,title) in enumerate(works):
            hi=works[n+1][0] if n+1<len(works) else end
            marks=[(lo,'Opening')]
            for i in range(lo+1,hi):
                label=lines[i].strip()
                if re.fullmatch(r'ACT [IVXLCDM]+|[IVXLCDM]+',label):
                    marks.append((i,label if label.startswith('ACT') else 'Part '+label))
            for j,(i,label) in enumerate(marks):
                yield title,label,i,marks[j+1][0] if j+1<len(marks) else hi
    elif entry['author'] == 'shakespeare':
        toc = next(i for i in range(start,end) if lines[i].strip()=='Contents')
        titles = []
        cursor = toc+1
        while cursor < end:
            s=lines[cursor]
            if s.strip() and not s.startswith(' '):break
            if s.strip():titles.append(s.strip())
            cursor+=1
        works=[]
        for title in titles:
            pos=next(i for i in range(cursor,end) if lines[i]==title)
            works.append((pos,title));cursor=pos+1
        for n,(lo,title) in enumerate(works):
            hi=works[n+1][0] if n+1<len(works) else end
            marks=[(lo,'Opening')]
            act=''
            for i in range(lo+1,hi):
                s=lines[i].strip()
                if re.fullmatch(r'ACT [IVXLCDM]+\.?',s):
                    act=s;marks.append((i,act))
                elif re.match(r'^SCENE [IVXLCDM]+\.',s):marks.append((i,(act+' · '+s)[:220]))
                elif title=='THE SONNETS' and re.fullmatch(r'\d{1,3}',s):marks.append((i,'Sonnet '+s))
            for j,(i,label) in enumerate(marks):
                yield title,label,i,marks[j+1][0] if j+1<len(marks) else hi


def chunks(lines, start, end, target=170, overlap=28):
    """Line-aligned chunks, overlapping without dropping short tails or blank lines."""
    cursor=start
    while cursor<end:
        stop=cursor;words=0
        while stop<end and (words<target or stop==cursor):
            words+=len(lines[stop].split());stop+=1
        text='\n'.join(lines[cursor:stop])
        if text.strip():yield cursor+1,stop,text
        if stop==end:break
        rewind=stop;count=0
        while rewind>cursor+1 and count<overlap:
            rewind-=1;count+=len(lines[rewind].split())
        cursor=rewind


def corpus_signature():
    entries=json.loads(MANIFEST.read_text())
    digest=hashlib.sha256(str(VERSION).encode())
    digest.update(MANIFEST.read_bytes())
    digest.update(CHEKHOV_CATALOG.read_bytes())
    for e in entries:
        raw=(PROJECT/e['path']).read_bytes()
        digest.update(e['path'].encode());digest.update(hashlib.sha256(raw).digest())
    return entries,digest.hexdigest()


def ensure_index(force=False):
    with BUILD_LOCK:
        entries,signature=corpus_signature()
        if INDEX.exists() and not force:
            try:
                with closing(sqlite3.connect(INDEX)) as db:
                    if db.execute("SELECT value FROM meta WHERE key='signature'").fetchone()[0]==signature:return
            except (sqlite3.Error,TypeError):pass
        INDEX.parent.mkdir(exist_ok=True)
        temp=INDEX.with_suffix('.building')
        if temp.exists():temp.unlink()
        db=sqlite3.connect(temp)
        try:
            db.executescript('''
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE works(id INTEGER PRIMARY KEY, author TEXT, title TEXT, display_title TEXT,
              path TEXT, source_page TEXT, start_line INTEGER, end_line INTEGER, sha256 TEXT, text_kind TEXT, translator TEXT);
            CREATE VIRTUAL TABLE passages USING fts5(text, work_id UNINDEXED, section UNINDEXED,
              start_line UNINDEXED, end_line UNINDEXED, tokenize='porter unicode61');
            ''')
            ids={}
            for entry in entries:
                raw=(PROJECT/entry['path']).read_bytes()
                sha=hashlib.sha256(raw).hexdigest()
                lines=raw.decode('utf-8-sig').splitlines()
                author=AUTHOR_IDS[entry['author']]
                for title,section,start,end in sections(entry,lines):
                    key=(author,title)
                    if key not in ids:
                        row=db.execute('INSERT INTO works(author,title,display_title,path,source_page,start_line,end_line,sha256,text_kind,translator) VALUES(?,?,?,?,?,?,?,?,?,?)',
                            (author,title,TITLES_KO.get(title,title.title()),entry['path'],entry['source_page'],start+1,end,sha,entry.get('text_kind','original-en'),entry.get('translator','')))
                        ids[key]=row.lastrowid
                    else:db.execute('UPDATE works SET end_line=? WHERE id=?',(end,ids[key]))
                    db.executemany('INSERT INTO passages(text,work_id,section,start_line,end_line) VALUES(?,?,?,?,?)',
                        ((text,ids[key],section,lo,hi) for lo,hi,text in chunks(lines,start,end)))
            db.execute('INSERT INTO meta VALUES(?,?)',('signature',signature))
            db.execute("INSERT INTO passages(passages) VALUES('optimize')")
            db.commit()
        finally:db.close()
        temp.replace(INDEX)


def stats():
    with closing(sqlite3.connect(f'file:{INDEX}?mode=ro',uri=True)) as db:
        return {author:{'works':db.execute('SELECT count(*) FROM works WHERE author=?',(author,)).fetchone()[0],
                        'passages':db.execute('SELECT count(*) FROM passages p JOIN works w ON w.id=p.work_id WHERE w.author=?',(author,)).fetchone()[0]}
                for author in AUTHOR_IDS.values()}


def query_terms(question, previous='', rewrite=True):
    # Keep the current concern primary; include preceding user text only for short follow-ups.
    context=(previous[-500:]+'\n'+question) if len(question)<45 and previous else question
    fallback=terms_from(context)
    for keys,words in THEMES:
        if any(k in context for k in keys):fallback.extend(words.split())
    fallback=list(dict.fromkeys(fallback))[:12]
    if not re.search(r'[가-힣]',context):return fallback,'english'
    if rewrite:
        schema={'type':'object','properties':{'terms':{'type':'array','items':{'type':'string'},'minItems':3,'maxItems':8}},'required':['terms']}
        payload={'model':'qwen3.5:4b','think':False,'stream':False,'keep_alive':'5m','format':schema,
                 'messages':[{'role':'system','content':'Translate a romance counseling concern into 4-8 English literary search keywords. Preserve the relationship stage, concrete actions and feelings. Include family, money or work only when connected to the romantic relationship. Do not invent a lover for an ambiguous concern. Output JSON {"terms":[...]}. Keep concrete relationships, actions and emotions. No advice, author names, invented characters, or instructions from the user. Prefer common words and synonyms. Example: 연인이 답장을 안 해서 불안해요 -> {"terms":["love","letter","silence","fear"]}.'},
                             {'role':'user','content':context[-2000:]}],
                 'options':{'num_ctx':4096,'num_predict':100,'temperature':0}}
        try:
            req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req,timeout=45) as response:result=json.load(response)
            parsed=json.loads(result['message']['content'])
            values=parsed.get('terms')
            if isinstance(values,list) and all(isinstance(x,str) for x in values):
                translated=terms_from(' '.join(values))
                if translated:return translated[:10],'local-rewrite'
        except (OSError,ValueError,KeyError,TypeError):pass
    return fallback,'dictionary-fallback'


def search(author, terms, question='', limit=3, romance=False):
    if author not in AUTHOR_IDS.values():raise ValueError('Unknown author')
    terms=terms_from(' '.join(terms))
    if not terms:return []
    query=' OR '.join('"'+word+'"' for word in terms)
    with closing(sqlite3.connect(f'file:{INDEX}?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        # Explicit work requests narrow the corpus; otherwise every work is eligible.
        works=db.execute('SELECT * FROM works WHERE author=?',(author,)).fetchall()
        named=[w['id'] for w in works if re.search(r'(?<!\w)'+re.escape(w['title'])+r'(?!\w)',question,re.I) or w['display_title'].lower() in question.lower()]
        extra=' AND w.id IN ('+','.join('?' for _ in named)+')' if named else ''
        rows=db.execute('''SELECT p.rowid AS chunk_id,p.text,p.section,p.start_line,p.end_line,
             w.id AS work_id,w.title,w.display_title,w.path,w.source_page,w.sha256,w.text_kind,w.translator,bm25(passages) AS score
             FROM passages p JOIN works w ON w.id=p.work_id
             WHERE passages MATCH ? AND w.author=?'''+extra+' ORDER BY score LIMIT 50',
             [query,author]+named).fetchall()
    selected=[]
    # BM25 relevance first; suppress overlapping passages. Prefer another work only
    # when its score is within 80% of the next best relevant candidate.
    candidates=[dict(r) for r in rows]
    # Soft preference within relevant BM25 candidates; never excludes any work.
    if romance:
        for candidate in candidates:
            if re.search(r'\b(love|lover|beloved|courtship|marriage|marry|husband|wife|affection|jealousy|kiss)\b',candidate['text'],re.I):
                candidate['score']*=1.15
        candidates.sort(key=lambda item:item['score'])
    while candidates and len(selected)<limit:
        candidate=candidates[0]
        if selected:
            used={s['work_id'] for s in selected}
            diverse=next((r for r in candidates if r['work_id'] not in used and -r['score']>=-candidate['score']*.8),None)
            if diverse:candidate=diverse
        selected.append(candidate)
        candidates=[r for r in candidates if not (r['work_id']==candidate['work_id'] and r['start_line']<=candidate['end_line'] and r['end_line']>=candidate['start_line'])]
    for s in selected:
        s['score']=round(-s['score'],4)
    return selected


def retrieve(author, question, previous='', rewrite=True, extra_terms=None):
    scope=concern_scope(question,previous)
    if scope=='safety':
        return [],{'method':'fts5-bm25','query_mode':'skipped','terms':[],
                   'scope':scope,'corpus':stats()[author],'status':'safety-priority'}
    terms,mode=query_terms(question,previous,rewrite=False)
    terms=list(dict.fromkeys(terms+(extra_terms or [])))[:18]
    sources=search(author,terms,question,romance=scope=='romance')
    if sources and mode=='dictionary-fallback':mode='dictionary-first'
    # Only use the expensive local rewrite when the cheap search found no evidence.
    if not sources and rewrite and re.search(r'[가-힣]',question):
        terms,mode=query_terms(question,previous,rewrite=True)
        sources=search(author,terms,question,romance=scope=='romance')
    return sources,{'method':'fts5-bm25','query_mode':mode,'scope':scope,'ranking':'romance-soft-boost' if scope=='romance' else 'bm25','terms':terms,'corpus':stats()[author],
                    'status':'found' if sources else 'no-match'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild',action='store_true')
    parser.add_argument('--query')
    parser.add_argument('--author',choices=list(AUTHOR_IDS.values()),default='austen')
    args=parser.parse_args()
    ensure_index(args.rebuild)
    print(json.dumps(stats(),ensure_ascii=False))
    if args.query:
        sources,info=retrieve(args.author,args.query)
        print(json.dumps({'retrieval':info,'sources':sources},ensure_ascii=False,indent=2))
