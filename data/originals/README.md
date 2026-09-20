# Jane — 영어 원문·영문 번역판 자료

Project Gutenberg의 영어 텍스트 판본을 내려받아 **수정 없이** 보관합니다. 오스틴·셰익스피어는 영어 원문이며, 체호프는 러시아어 작품의 역사적 영문 번역판입니다. 체호프 러시아어 원문을 수집한 것은 아닙니다. 요약·모델 생성 텍스트를 작품 본문으로 사용하지 않습니다. 초판 스캔이나 학술 비평판을 의미하지 않으며, 판본별 편집·서문·주석이 포함될 수 있습니다.

| 작가 | 작품 | 파일 | 출처 |
|---|---|---|---|
| Jane Austen | Pride and Prejudice | `austen/pride-and-prejudice.txt` | https://www.gutenberg.org/ebooks/1342 |
| Jane Austen | Sense and Sensibility | `austen/sense-and-sensibility.txt` | https://www.gutenberg.org/ebooks/161 |
| Jane Austen | Emma | `austen/emma.txt` | https://www.gutenberg.org/ebooks/158 |
| Jane Austen | Mansfield Park | `austen/mansfield-park.txt` | https://www.gutenberg.org/ebooks/141 |
| Jane Austen | Persuasion | `austen/persuasion.txt` | https://www.gutenberg.org/ebooks/105 |
| Jane Austen | Northanger Abbey | `austen/northanger-abbey.txt` | https://www.gutenberg.org/ebooks/121 |
| Jane Austen | Lady Susan | `austen/lady-susan.txt` | https://www.gutenberg.org/ebooks/946 |
| William Shakespeare | The Complete Works of William Shakespeare | `shakespeare/complete-works.txt` | https://www.gutenberg.org/ebooks/100 |
| Anton Chekhov | The Sea-Gull | `chekhov/the-sea-gull.txt` | https://www.gutenberg.org/ebooks/1754 |
| Anton Chekhov | Uncle Vanya | `chekhov/uncle-vanya.txt` | https://www.gutenberg.org/ebooks/1756 |
| Anton Chekhov | Plays by Anton Chekhov, Second Series | `chekhov/plays-second-series.txt` | https://www.gutenberg.org/ebooks/7986 |
| Anton Chekhov | The Lady with the Dog and Other Stories | `chekhov/lady-with-the-dog-and-other-stories.txt` | https://www.gutenberg.org/ebooks/13415 |
| Anton Chekhov | The Darling and Other Stories | `chekhov/darling-and-other-stories.txt` | https://www.gutenberg.org/ebooks/13416 |

오스틴은 장편 6편과 Lady Susan을 수집했습니다. 오스틴의 편지·습작·미완성작 전체를 수집한 것은 아닙니다. 셰익스피어는 Gutenberg #100 전집 판본의 수록 범위입니다.

`manifest.json`에 다운로드 주소·수집 시각·파일 크기·줄 수·SHA-256을 기록했습니다. 파일의 Project Gutenberg 안내·라이선스도 보존했습니다. 출처 페이지는 미국 내 public domain으로 표시합니다.

RAG용 본문 추출·작품/장/막/장면 분할 색인은 `../../ai/index/`에 생성하고, 이 원문과 줄 번호·해시로 연결합니다. 원문 파일 자체를 덮어쓰지 않습니다. 이 자료를 저장했다고 모델이 학습된 것은 아닙니다.

재현: 프로젝트 루트 `jane/`에서 `python3 local-llm/scripts/download_originals.py` 실행. 이미 존재하는 파일은 다시 내려받지 않습니다.

체호프는 5개 영문 판본에 수록된 29편의 본문을 모두 검색합니다. 체호프 전 작품을 망라한 전집은 아닙니다. 수록작·번역·퍼블릭 도메인 출처: [chekhov/README.md](chekhov/README.md).

현재 검색·문맥 정책은 [RAG 문서](../../local-llm/RAG.md)를 따른다. 자료 목록 검토 기준일: 2026-09-20.
