# 로컬 Qwen 실행

공용 프롬프트·RAG·문맥 로직은 `../ai/`로 이동했습니다.

- `chat.py`: Qwen 명령행 대화
- `web_server.py`: 8317 포트의 로컬 화면·Ollama API 어댑터
- `prophecy.py`: 로컬 예언 생성
- `serve.sh`, `run-*.command`: macOS 실행 보조 스크립트
- `test_*.py`: 공용 AI와 로컬 서버 회귀 테스트

공개 Gemini 서비스 실행, 환경 변수, 테스트 및 배포는 [상위 README](../README.md)를 참고하세요. [RAG](RAG.md), [말투·인용](VOICES-AND-QUOTES.md), [작가 관점](AUTHOR-COUNSELING-V10.md)은 현재 구현 문서입니다. 과거 결과와 고정 발췌 실험은 제거하고 [실험 요약](../history/experiment-summary.md)에 통합했습니다. 실행 보조 스크립트의 로그는 `logs/`에 생성됩니다. 현재 검색 DB와 번역 캐시는 `../ai/index/`에 있습니다.
