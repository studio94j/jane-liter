# 안톤 체호프 — 로컬 작품 자료

기존 영어 RAG와 같은 경로로 검색할 수 있도록 Project Gutenberg의 **퍼블릭 도메인 영문 번역판** 5개 파일을 내려받았다. 러시아어 원작을 영문으로 번역한 판본이며, 원어 러시아어 자료 또는 현대 한국어 번역본이 아니다. 선택한 판본의 본문은 생략하지 않고 검색하지만 체호프의 모든 작품을 수집한 것은 아니다.

각 출처 페이지에서 `Public domain in the USA` 표시를 확인했다. 원본 파일의 안내·라이선스는 보존한다. 내려받은 바이트를 변경하지 않으며 URL·수집 시각·SHA-256은 상위 `manifest.json`에 기록한다. 번역자가 명시되지 않은 두 파일은 임의로 번역자를 추정하지 않는다.

| 파일 | 번역자(판본 표기) | 수록작 | 출처 |
|---|---|---|---|
| [the-sea-gull.txt](the-sea-gull.txt) | 다운로드 판본에 미기재 | 갈매기 | [PG #1754](https://www.gutenberg.org/ebooks/1754) |
| [uncle-vanya.txt](uncle-vanya.txt) | 다운로드 판본에 미기재 | 바냐 아저씨 | [PG #1756](https://www.gutenberg.org/ebooks/1756) |
| [plays-second-series.txt](plays-second-series.txt) | Julius West | 큰길에서 · 청혼 · 결혼식 · 곰 · 본의 아닌 비극 배우 · 기념일 · 세 자매 · 벚꽃 동산 | [PG #7986](https://www.gutenberg.org/ebooks/7986) |
| [lady-with-the-dog-and-other-stories.txt](lady-with-the-dog-and-other-stories.txt) | Constance Garnett | 개를 데리고 다니는 여인 · 왕진 · 소동 · 이오니치 · 가장 · 검은 수도승 · 볼로쟈 · 익명의 이야기 · 남편 | [PG #13415](https://www.gutenberg.org/ebooks/13415) |
| [darling-and-other-stories.txt](darling-and-other-stories.txt) | Constance Garnett | 귀여운 여인 · 아리아드네 · 폴린카 · 아뉴타 · 두 볼로쟈 · 혼수 · 아내 · 재능 · 화가의 이야기 · 삼 년 | [PG #13416](https://www.gutenberg.org/ebooks/13416) |

총 29편 / 1,766개 검색 구간. 희곡은 막, 단편은 내부 절을 구분하고 원본 파일의 행 번호를 붙인다. 희곡집의 번역자 서문은 보관하되 체호프 작품 본문 검색에서는 제외한다. 검색 결과에 영문 번역판임을 표시하고 명시된 번역자는 함께 표시한다.

서비스 관점은 **말하지 못한 마음을 살피는 관찰자**로 설정했다. 일상의 피로, 바라는 삶과 현실의 간극, 작은 변화에 주목하는 서비스 해석이며, 작가의 실제 발언이나 모든 인물의 신념이 아니다. 실제 응답에는 체호프의 검색 구절만 전달하며 다른 두 작가의 본문을 섞지 않는다.

현재 작가 UI는 `proto/assets/hamsters/chekhov-figma.png`의 사용자 제공 햄스터 캐릭터를 사용한다. 과거 초상화의 출처는 [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Anton_Chekhov_with_bow-tie_sepia_image.jpg)이며 `proto/assets/chekhov.jpg`는 이전 자료다.

검색 색인은 `ai/index/originals.sqlite3`에 있다. 행 번호는 내부 검증용이며 현재 사용자 화면에 표시하지 않는다. 현재 상담 관점은 [작가별 지침](../../../local-llm/AUTHOR-COUNSELING-V10.md)을 따른다. 문서 검토 기준일: 2026-09-20.
