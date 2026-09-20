#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! /usr/bin/curl --max-time 3 -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  mkdir -p logs || exit 1
  ./serve.sh > logs/server.log 2>&1 &
  jane_server_pid=$!
  trap 'kill "$jane_server_pid" 2>/dev/null' EXIT
  jane_attempt=0
  until /usr/bin/curl --max-time 2 -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; do
    jane_attempt=$((jane_attempt + 1))
    if [ "$jane_attempt" -ge 60 ]; then
      echo 'Ollama 실행 실패: logs/server.log를 확인하세요.'
      exit 1
    fi
    sleep 1
  done
fi
exec_python=$(command -v python3) || exit 1
"$exec_python" chat.py --source --author "${1:-austen}"
