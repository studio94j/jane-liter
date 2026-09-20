# Jane · Vercel + Gemini + Upstash

공개 주소: https://literary-consult.vercel.app · 2026-09-20 배포 및 외부 API 검증 완료.
Vercel Hobby / Upstash Free를 사용하는 공모전 운영 구성입니다. 플랜과 제공사 무료 할당량은 각 콘솔에서 확인합니다. 이 문서의 금액은 코드에 설정된 모델 예산이며 제공사 최신 요금표를 보증하지 않습니다.

현재 HTML과 80개 작품 원문 검색을 유지한 로그인 없는 공모전용 배포 구성입니다.
Vercel은 화면과 Python API, Gemini는 답변, Upstash는 익명 사용량·예산·중복 요청을 담당합니다.

## 실행

```sh
cd jane
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
# .env.example을 참고해 .env.local에 서버 전용 키 입력
.venv/bin/python scripts/build_public.py
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8318 --no-access-log
```

기존 `local-llm/web_server.py`는 Ollama용으로 유지됩니다. 공개 배포는 `app.py`를 사용합니다.
`.env.local`은 브라우저나 업로드 파일에 포함하지 않습니다. 값은 Vercel 환경 변수로 등록합니다.
Upstash 연결이 없으면 대화 API는 503으로 중단하며 무제한 무료 우회 모드는 없습니다.

## 필요한 환경 변수

- `GEMINI_API_KEY`: Google 서버 호출용 키.
- `GEMINI_MODEL`: `gemini-3.1-flash-lite` 기본값. 모델을 바꾸면 가격과 thinking 설정도 검토합니다.
- `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`: Upstash Redis REST 값.
- `SESSION_SECRET`: 32자 이상 난수. 모든 Vercel 인스턴스에서 동일해야 합니다.
- `APP_ORIGINS`: 쉼표로 구분한 허용 웹 출처. Vercel 기본·프로덕션 주소도 자동 허용합니다.
- `REDIS_NAMESPACE`: 운영/미리보기별 분리. 변경하면 기존 카운터가 새로 시작하므로 운영 중 임의 변경하지 않습니다.
- `AI_ENABLED=false`: 신규 대화 호출 중단 스위치. 환경 변수 변경 후 재배포해야 합니다.

## 기본 한도

| 범위 | 모든 사용자 |
|---|---:|
| 익명 세션 하루 / 1분 | 10회 / 3회 |
| IP 하루 / 1분 | 50회 / 15회 |
| 전체 하루 | 300회 |
| 세션 / 전체 동시 답변 | 1개 / 4개 |
| 하루 / 달력 월 모델 예산 | $0.30 / $9 |

하루/월은 서울 시간 기준입니다. 월 한도는 달력 월로 구현했습니다.
Google 자체 프로젝트 한도는 별도로 적용되며 위보다 낮으면 먼저 제한될 수 있습니다.
쿠키를 지우거나 IP를 바꾸면 개인 제한을 우회할 수 있지만 전체 횟수·예산은 유지됩니다.
같은 와이파이 사용자는 IP 한도를 공유합니다. IP 원문은 저장하지 않고 날짜별 HMAC으로 변환합니다.

## 비용 통제

- Redis Lua 한 트랜잭션에서 모든 한도 확인과 예약을 처리합니다.
- 입력 UTF-8 바이트 수와 역할 여유분을 보수적인 입력 토큰 상한으로 삼고, 최대 출력 토큰 비용까지 먼저 확보합니다.
- 기존 문맥은 추정 3,200토큰으로 자르고 추가로 16,000바이트 기반 토큰 상한을 적용합니다. 출력은 턴에 따라 128~400, 절대 최대 500토큰입니다.
- 정상 종료 시 Gemini 실제 사용량(생각 토큰 포함)으로 정산합니다. 중단·타임아웃·정산 실패 시 예약 비용을 유지합니다.
- 알 수 없는 상태를 자동 재시도하지 않습니다. 같은 세션/요청 ID는 24시간 중복 차단합니다.
- Redis 장애 시 새 모델 호출을 중단합니다. 프롬프트/응답 원문은 Redis에 넣지 않습니다.
- 금액은 설정된 Gemini 단가 기준 앱 내부 계산이며 Google 결제 계정의 지출 한도가 아닙니다. 호스팅·Redis 비용은 포함하지 않습니다.
- Gemini 무료 프로젝트는 별도 요금 청구 없이 제공사 무료 할당량을 따릅니다. 서비스가 민감한 사연을 다루므로 무료/유료 데이터 이용 조건은 공개 전에 확인해야 합니다.

## 원문과 예언

- 빌드 때 SQLite FTS5를 확인하고 배포합니다. 요청 중에는 원문 인덱스를 읽기 전용으로 엽니다.
- 오스틴 7, 셰익스피어 44, 체호프 29작품 전체에서 선택한 작가의 관련 구절을 검색합니다.
- 조언 턴에서 원문 검증과 기존 번역 캐시가 모두 있는 경우 인용을 붙입니다. 번역 캐시가 없으면 추가 API 호출 없이 인용을 생략합니다.
- 예언은 우선 원문 검증한 편집 카드 9개(작가별 3개)를 무작위로 제공합니다. 모든 원문에서 즉석 생성하던 로컬 버전과 달리 준비된 카드 풀에서 추첨합니다. 풀 확대는 `scripts/prepare_prophecies.py`에서 관리합니다.
- 예언 API는 Gemini를 호출하지 않습니다. 최근 카드를 피하고, 전체 풀이 소진되면 마지막 카드만 제외합니다.
- 생년월일·지역은 예언 API로 전송하지 않습니다.

## 단일 공개 링크

심사위원과 일반 사용자는 https://literary-consult.vercel.app/ 하나를 사용합니다. 별도 초대 API·좌석·우대 한도는 제거했습니다. 기존 심사 쿠키는 같은 세션 ID를 유지한 일반 쿠키로 전환하고 모든 요청은 기존 PUBLIC 예산을 공유합니다. 기존 초대 북마크는 토큰을 제거하고 대화 화면으로 이동합니다. 기존 도메인 별칭도 같은 서비스를 제공합니다.

`JUDGE_*` 환경 변수는 사용하지 않습니다. Redis namespace와 PUBLIC 카운터를 유지하므로 통합하면서 기존 일반 사용량을 초기화하지 않습니다.

## 배포

```sh
npx vercel login
npx vercel link --project literary-consult
# jane를 루트로, FastAPI 프레임워크, python scripts/build_public.py 빌드 사용
# Vercel 프로젝트 환경 변수에 .env.example 항목 설정
npx vercel --prod
```

공개 디렉터리는 `public/`으로 한정합니다. spec·QA·Figma 백업·원문 SQLite·서버 코드가 정적 경로로 노출되지 않습니다.
처음에는 프리뷰로 API 연결·모바일 화면·한도 테스트를 확인한 후 운영 주소를 공개합니다.

## 검증

```sh
.venv/bin/python -m pytest tests local-llm/test_*.py -q
.venv/bin/python scripts/build_public.py
```

동일 세션 병렬 요청 20개 중 1개 허용, 이중 정산 방지, 예산 초과 차단, 이전 심사 세션의 일반 한도 전환, 일일 10회 한도,
서명 쿠키 변조, 출처 검증, 중복 요청, 비공개 파일 404, Redis 장애 시 모델 미호출을 검증합니다.
실제 Gemini 3.1 Flash-Lite의 스트리밍과 기존 오스틴 RAG 프롬프트도 별도로 연결 확인했습니다.

공식 문서: [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi),
[Gemini 3.1 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite),
[Upstash REST](https://upstash.com/docs/redis/features/restapi).


## 공용 AI 코드 위치

프롬프트·문맥 구성·RAG·인용은 `ai/` 패키지에 있습니다. 원문 색인과 번역 캐시는 `ai/index/`를 사용합니다. 공개 서버는 `local-llm/web_server.py`를 가져오지 않습니다. `local-llm/`은 Qwen 실행과 로컬 테스트를 위한 어댑터입니다. 전체 구조는 [README.md](README.md)를 참고하세요.

## API와 운영 확인

| 경로 | 역할 |
|---|---|
| GET `/api/health` | 모델명·필수 설정 준비 여부. 실제 Gemini/Redis 접속 성공을 보증하는 검사는 아님 |
| GET `/api/session` | 서명된 익명 세션과 공통 한도 확인 |
| POST `/api/chat` | 입력·출처·중복·한도 검증 후 Gemini 답변 스트리밍 |
| POST `/api/prophecy` | 최근 카드 제외 목록으로 준비된 예언 카드 추첨 |

브라우저는 Gemini SSE를 직접 받지 않고 서버가 변환한 줄 단위 JSON 이벤트를 받습니다. API 응답은 캐시하지 않습니다. 클라이언트가 보낸 `memory`는 공개 서버에서 비웁니다. 별도 대화 DB나 계정 로그인은 없습니다.

운영 변경 순서: 코드·환경 변수 변경 → 테스트 및 공개 빌드 → 필요 시 프리뷰 검증 → 프로덕션 배포 → 공개 URL·세션·대화·예언 확인. 프리뷰는 별도의 Redis namespace와 허용 출처를 사용합니다. 모델 변경 시 `cloud/gemini.py`의 thinking 설정 호환성과 입력·출력 계산 단가를 함께 검토합니다.

장애 시에는 오류 메시지와 Vercel·Upstash 콘솔을 확인하되 키·사연을 로그에 추가하지 않습니다. 긴급 중단은 `AI_ENABLED=false` 설정 후 재배포합니다. 배포 복구는 검증된 이전 코드로 다시 배포하는 방식으로 수행하고 운영 Redis namespace를 무심코 바꾸지 않습니다.

공개 주소는 `https://literary-consult.vercel.app/`, 기존 별칭은 `https://jane-contest.vercel.app/`입니다. 원문 자료는 서버의 RAG 입력이고 정적 공개 파일이 아닙니다. 문서만 수정한 경우 새 프로덕션 배포는 필요하지 않습니다.

세션 사용량 조회(`/api/session`)는 공용 IP당 60초에 120회까지 허용합니다. 채팅 횟수에는 포함하지 않습니다. 프런트는 진행 중 조회를 공유하고 일반 조회는 10초간 재사용하며, 실패 시 60초 대기합니다. 대화 전송 후에는 최신 사용량을 다시 조회합니다. 봇 인증은 사용하지 않습니다.
