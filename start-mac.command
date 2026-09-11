#!/bin/zsh
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo 'Python 3.10 이상을 python.org에서 설치해 주세요.'
  read '?Enter를 누르면 종료합니다.'
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python launch.py
