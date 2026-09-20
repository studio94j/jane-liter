#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! /usr/bin/curl --max-time 3 -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  mkdir -p logs || exit 1
  ./serve.sh > logs/server.log 2>&1 &
  jane_model_pid=$!
  trap 'kill "$jane_model_pid" 2>/dev/null' EXIT
  jane_attempt=0
  until /usr/bin/curl --max-time 2 -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; do
    jane_attempt=$((jane_attempt + 1))
    if [ "$jane_attempt" -ge 60 ]; then echo 'Ollama 실행 실패: logs/server.log 확인'; exit 1; fi
    sleep 1
  done
fi
if /usr/bin/curl --max-time 4 -fsS http://127.0.0.1:8317/api/health >/dev/null 2>&1; then
  open 'http://127.0.0.1:8317/?v=26#chat'
  exit 0
fi
python3 web_server.py
