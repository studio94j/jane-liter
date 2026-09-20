"""Bounded situation hints; no classifier model calls or permanent user labels."""
import json,re
from pathlib import Path
PROJECT=Path(__file__).resolve().parent.parent
CASE_PATH=PROJECT/'cloud/situations.json' if (PROJECT/'cloud/situations.json').exists() else PROJECT/'proto/situations.json'
CASES=json.loads(CASE_PATH.read_text())
BY_ID={x['id']:x for x in CASES}
def select_situation(value,latest):
    if value is not None and (not isinstance(value,str) or value not in BY_ID):
        raise ValueError('고민 주제를 다시 선택해 주세요.')
    if value:return BY_ID[value], 'selected'
    matches=[x for x in CASES if not x.get('legacy') and re.search(x['pattern'],latest)]
    return (matches[-1], 'tentative') if matches else (None,'none')
def situation_instruction(item,origin,author):
    if not item:return ''
    lens={'austen':'행동과 합의한 기대를 확인한다.','william':'욕망과 두려움을 탐색하되 숨은 동기를 지어내지 않는다.','chekhov':'사용자가 말한 사소한 장면의 모순을 짧게 짚는다.'}[author]
    return '\n상황 단서('+origin+'): '+item['label']+'. 최신 발언이 우선이며 분류를 사실로 단정하지 않는다. '+item['guidance']+' '+lens
