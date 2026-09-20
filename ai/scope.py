"""General concern routing with optional romance relevance and safety priority.
These lexical hints are not a semantic classifier or a complete safety detector.
"""
import re

ROMANCE = re.compile(r'연애|연인|애인|남친|여친|남자\s*친구|여자\s*친구|짝사랑|썸|데이트|사내연애|결혼|약혼|배우자|남편|아내|이별|재회|전\s*연인|헤어[졌지질]|사귀|좋아하는\s*사람|\b(?:romance|romantic|boyfriend|girlfriend|lover|dating|marriage|marry|spouse|husband|wife|breakup|crush)\b',re.I)
OUTSIDE = re.compile(r'직장|회사|상사|업무|퇴사|취업|이직|면접|진로|주식|투자|코딩|파이썬|날씨|시험|성적|친구|우정|부모|가족|엄마|아빠|\b(?:career|boss|job|workplace|stocks|coding|weather|exam|friendship|parents)\b',re.I)
SAFETY = re.compile(r'자해|자살|죽고\s*싶|죽을|죽여|극단적|목숨|위협|폭력|폭행|때렸|때려|협박|스토킹|위치\s*추적|감시|거절.*(계속|연락)|차단.*(계정|연락)|강압|강요|성폭|위험|\b(?:suicid\w*|self.harm|violence|abuse|stalking|threat\w*)\b',re.I)


def concern_scope(question, previous=''):
    if SAFETY.search(question):return 'safety'
    if OUTSIDE.search(question) and not ROMANCE.search(question):return 'general'
    if re.search(r'연애.{0,6}(말고|무관)|연애\s*(상담)?\s*(아니|아닌)',question):return 'general'
    if ROMANCE.search(question):return 'romance'
    if ROMANCE.search(previous):return 'romance'
    return 'general'
