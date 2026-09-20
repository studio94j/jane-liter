# 화면 소스

현행 기준: 2026-09-20. 실행·배포는 [상위 README](../README.md), 기능은 [최종 스펙](../spec/product-spec-final.md)을 따른다.

하단 메뉴는 대화와 나의 기록이다. 설정은 상단 앱바에서 접근한다. 나의 기록에는 대화 기록·편지함·예언이 있다.

| 파일 | 수정 대상 |
|---|---|
| `screens/chat.js` | 대화·오프닝·메시지·대화 메뉴 |
| `screens/records.js` | 기록 탭·저장한 책과 조언 |
| `screens/letters.js` | 하루 한 통·100자 편지 작성과 보관 |
| `screens/settings.js` | 설정·작가 선택·작가 상세 바텀시트 |
| `app.js` | 공통 상태·라우팅·초기화·제안 스낵바 |
| `content.js`, `situations.js`, `situations.json` | 작가 소개·주제 칩·추천 시작 문구 |
| `local-chat.js`, `cloud-session.js` | 대화 API·스트리밍·공통 익명 세션 |
| `chat-archive.js`, `conversation-records.js`, `prophecy-archive.js` | 브라우저의 임시 기록 |
| `fortune.js` | 세 마녀의 예언 UI |
| `onboarding.js`, `onboarding.css` | 실제 UI 캡처 기반 4단계 안내 |
| `styles.css`, `fonts.css` | 흑백 UI·에스코어드림 강조·프리텐다드 본문 |
| `index.html` | 스크립트 순서·링크 공유 메타데이터 |

일반 script 방식이다. 화면 함수들을 로드한 뒤 `app.js`가 공통 상태를 초기화한다. `memory.js`는 별도 기억 저장을 비활성화한 호환 인터페이스다. 브라우저 기록과 모델의 장기 기억을 구분한다.

이 디렉터리를 수정하고 `jane/`에서 `python scripts/build_public.py`를 실행한다. `public/`은 빌드 결과이며 직접 수정하지 않는다. 이전 `v1/`, `v2/`, `qa*/`는 제거하고 [실험 요약](../history/experiment-summary.md)에 통합했다. `figma/` 작업 자료는 공개 빌드 대상이 아니다.

UI 변경 확인: 온보딩, 작가 선택·더보기·더블클릭·롱탭, 대화 버블·스트리밍, 조건부 스낵바, 날짜별 기록, 100자 편지, 예언 재요청, 모바일 바텀시트 스크롤. 공유 설명은 ‘문학으로 마음의 위로를 받아보아요...’이며 공유 이미지는 `assets/onboarding/share-v45.png`이다.
