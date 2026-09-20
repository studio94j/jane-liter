# Jane · 작품에서 빌린 시선

오스틴·셰익스피어·체호프의 작품과 관점을 바탕으로 고민을 나누는 원티드 AI 공모전용 웹 서비스입니다. 실제 작가를 재현하거나 전문 상담을 제공하는 서비스는 아닙니다.

- 공개 서비스: https://literary-consult.vercel.app/
- 화면: 작가와 대화 / 나의 기록 / 상단 설정
- 부가 기능: 세 마녀의 예언, 하루 한 통·100자의 부치지 않을 편지, 온보딩

문서 현행화 기준일: 2026-09-20. 기능 설명은 현재 공개 서버 구현을 기준으로 하며 로컬 모델 실험은 별도로 표시합니다.

## 기술 구성

HTML·CSS·순수 JavaScript + Python FastAPI + Gemini + Upstash Redis, Vercel 배포. 별도의 React/Next.js 빌드나 회원가입은 없습니다.

```text
jane/
├── proto/                   화면 소스 (수정 대상)
│   ├── index.html           진입점·공유 메타데이터·스크립트 순서
│   ├── app.js               공통 상태·라우팅·앱 초기화·이벤트
│   ├── screens/             chat / records / letters / settings 화면
│   ├── local-chat.js        공용 /api/chat 클라이언트 (기존 파일명 유지)
│   ├── chat-archive.js      브라우저 대화 보관
│   ├── conversation-records.js  날짜별 기록 조회
│   ├── fortune.js           예언 화면과 요청
│   ├── prophecy-archive.js  예언 보관
│   ├── onboarding.*         첫 방문 안내
│   ├── styles.css, fonts.css
│   └── assets/              이미지·폰트·실제 UI 캡처
├── ai/                      공개/로컬에서 공유하는 AI 처리
│   ├── prompts.py           작가 관점·말투·답변 정책
│   ├── context.py           입력 검증·최근 대화·RAG 문맥 예산
│   ├── retrieval.py         원문 색인·FTS5/BM25 검색
│   ├── quotations.py        검증된 인용·번역 캐시
│   ├── scope.py             고민 범위·안전 단서
│   ├── situations.py        상황별 검색어·상담 지침
│   └── index/               원문 검색 DB·번역 캐시
├── app.py                   공개 FastAPI 진입점
├── cloud/                   Gemini 통신·익명 세션·Redis 비용 제한
├── local-llm/               Qwen/Ollama 실행·로컬 HTTP 서버·회귀 테스트
├── data/originals/          원문과 출처 목록
├── scripts/                 공개 파일 빌드·예언 카드 준비
├── tests/                   공개 서버·비용 제한 테스트
├── public/                  빌드 결과 (직접 수정하지 않음)
├── spec/product-spec-final.md  현재 구현 기준 최종 스펙 (배포 제외)
└── vercel.json              배포 설정
```

화면 파일은 기존 일반 script 방식과 공용 상태를 유지합니다. ES module 전환은 하지 않았습니다. `screens/`는 화면 함수와 관련 이벤트를 정의하고 마지막에 로드되는 `app.js`가 상태를 초기화한 뒤 첫 화면을 그립니다. 스크립트 순서를 바꾸면 초기화가 깨질 수 있습니다.

## AI 요청 흐름

1. 브라우저가 선택한 작가·최근 대화·고민 주제를 `/api/chat`으로 전송합니다.
2. `ai/context.py`가 입력을 검증하고 `prompts.py`의 작가 지침을 구성합니다.
3. `retrieval.py`가 선택한 작가의 원문 전체 색인에서 관련 구간을 검색합니다.
4. 최근 대화와 원문을 추정 3,200토큰 예산 안에 구성합니다.
5. `cloud/limits.py`가 Redis에서 횟수·동시 요청·비용 예산을 예약합니다.
6. `cloud/gemini.py`가 Gemini를 한 번 호출하고 답변을 스트리밍합니다.
7. 조언 턴에서 검증된 인용과 번역 캐시가 있으면 별도로 붙입니다.
8. 실제 사용량으로 비용을 정산하고 브라우저가 대화를 임시 보관합니다.

### 현재 구현 범위

- 기본 공개 모델: `gemini-3.1-flash-lite` (환경 변수로 변경 가능).
- 파인튜닝 없음. 작가별 프롬프트 + 원문 검색 RAG 사용.
- 원문 검색: SQLite FTS5/BM25. 임베딩·벡터 DB 미사용.
- 수집 범위: 오스틴 7, 셰익스피어 44, 체호프 29작품. 체호프는 영어 번역판.
- 관련 구간 최대 3개 검색, 오스틴은 대화 문맥 확보를 위해 최대 1개 전달. 전 작품을 매번 입력하거나 균일하게 인용하지 않음.
- 공개 대화에서는 검색어 생성·번역 캐시 미스 때문에 추가 모델 호출을 하지 않음.
- 장기 기억은 비활성화. 최근 대화만 문맥 예산 안에서 전달하며, 자동 요약 기억은 없음.
- 대화·편지·예언은 브라우저 임시 보관. 계정 동기화·영구 보관·복구 보장 없음.
- 공개 예언은 준비된 9개 카드에서 추첨. 생년월일·지역으로 계산한 운세가 아니며 해당 입력은 API로 전송하지 않음.
- Redis에는 익명 사용량과 비용 제한 정보를 관리하며 대화 본문은 넣지 않음.

## 로컬 실행: 공개 서버 방식

프로젝트 루트 `jane/`에서 실행합니다. Python 3.12 이상과 SQLite FTS5가 필요합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env.local
# .env.local에 Gemini, Upstash, SESSION_SECRET을 설정
python scripts/build_public.py
uvicorn app:app --host 127.0.0.1 --port 8318
```

http://127.0.0.1:8318 에 접속합니다. API까지 시험하려면 테스트용 Redis namespace를 사용하세요. 키를 화면 소스나 Git에 넣지 마세요.

## 로컬 실행: Qwen 실험 방식

Ollama와 `qwen3.5:4b` 모델이 준비된 환경에서 실행합니다.

```sh
ollama serve
# 별도 터미널
ollama pull qwen3.5:4b
python local-llm/web_server.py
```

http://127.0.0.1:8317 에서 `proto/`를 제공합니다. 명령행 대화는 `python local-llm/chat.py --author austen`입니다. 공개 서비스와 프롬프트·검색·문맥 구성은 공유하지만 모델 통신과 예언 생성 방식은 다릅니다.

## 검증

```sh
python -m pytest tests local-llm/test_*.py -q
python scripts/build_public.py
node --check proto/app.js
node --check proto/local-chat.js
for file in proto/screens/*.js; do node --check "$file"; done
```

서버 회귀 테스트는 실제 Gemini 호출 없이 비용 제한·서명 쿠키·스트리밍·원문 검색·인용·문맥 예산 등을 검증합니다. 화면 변경 후에는 온보딩, 작가 선택·상세, 대화 전송, 날짜별 기록, 편지 작성, 예언을 브라우저에서 확인하세요.

## 배포

```sh
npx vercel --prod
```

Vercel 환경 변수는 `.env.example` 항목을 참고하세요. `scripts/build_public.py`가 공개할 화면 파일만 `public/`으로 복사합니다. 원문과 색인은 서버 검색 자원이며 정적 웹 경로로 공개하지 않습니다. 배포 운영과 한도 설정은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

## Git 작업 방식

최종 제출 소스를 최초 커밋 하나로 정리하고 공개 저장소 [studio94j/jane-liter](https://github.com/studio94j/jane-liter)에 연결했습니다. 이전 개발 커밋 이력은 포함하지 않습니다.

```sh
git status
git diff
git log --oneline
```

`.env.local`, `.vercel/`, 가상환경, 개인 실험 결과와 QA 캡처는 제외합니다. `public/`은 재생성하므로 추적하지 않습니다. 과거 실험 파일은 제거하고 [실험 요약](history/experiment-summary.md) 하나로 통합했습니다.

새 기능은 별도 브랜치에서 수정 → 테스트 → 커밋 → 배포 순서로 진행하세요. GitHub 저장소는 제출·공유·원격 백업에 사용하며, Vercel 배포는 CLI로 별도 실행합니다.

제품·메뉴·AI·운영의 최종 명세는 [최종 스펙](spec/product-spec-final.md)을 참고하세요.

## 문서 안내

| 문서 | 내용 |
|---|---|
| [최종 스펙](spec/product-spec-final.md) | 제품 범위·메뉴·저장 정책·디자인·구현 한계 |
| [배포 운영](DEPLOYMENT.md) | 환경 변수·비용 한도·공통 익명 세션·운영 확인 |
| [화면 소스](proto/README.md) | 화면별 파일과 디자인 수정 위치 |
| [세 마녀의 예언](proto/FORTUNE-DESIGN.md) | 스낵바 진입·준비 카드·보관 |
| [로컬 Qwen](local-llm/README.md) | 공개 서버와 로컬 실험의 구분 |
| [RAG](local-llm/RAG.md) | 원문 범위·검색·문맥 예산 |
| [작가 상담 관점](local-llm/AUTHOR-COUNSELING-V10.md) | 작가별 진행과 작품 해석 |
| [말투와 인용](local-llm/VOICES-AND-QUOTES.md) | 짧은 답변·조언 턴·검증·번역 캐시 |
| [원문 자료](data/originals/README.md) | 판본·출처·수집 재현 |

`spec/`에는 최종본 한 개, `history/`에는 [과거 실험 요약](history/experiment-summary.md) 한 개를 유지합니다. 상세 과거 결과·캡처·초기 코드는 제거했습니다. 현재 로컬 실행 로그는 `local-llm/logs/`에 생성하며 추적하지 않습니다.
