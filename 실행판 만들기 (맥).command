#!/bin/zsh
# 맥에서 이 파일을 더블클릭하면 Python 없이 도는 실행판이 만들어집니다.
# 터미널 창이 뜨지만 아무것도 입력하지 않으셔도 됩니다. 끝나면 안내가 나옵니다.

cd "$(dirname "$0")" || exit 1

print_line() { echo "────────────────────────────────────────────────"; }

clear
print_line
echo "  카리스 주보제작 · 맥 실행판 만들기"
print_line
echo
echo "몇 분 걸립니다. 창을 닫지 마시고 기다려 주세요."
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "⚠  Python 이 설치되어 있지 않습니다."
  echo
  echo "   https://www.python.org/downloads/ 에서 내려받아 설치한 뒤"
  echo "   이 파일을 다시 더블클릭해 주세요."
  echo
  read "?Enter 를 누르면 닫힙니다."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "· 준비 중입니다 (처음 한 번만 오래 걸립니다)"
  python3 -m venv .venv || { echo "준비에 실패했습니다."; read "?Enter"; exit 1; }
fi

echo "· 필요한 것들을 내려받는 중"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt || {
  echo; echo "⚠  인터넷 연결을 확인해 주세요."; read "?Enter"; exit 1; }

echo "· 실행판을 만드는 중"
echo
.venv/bin/python build-native.py
STATUS=$?

echo
print_line
if [ $STATUS -eq 0 ]; then
  echo "  다 되었습니다."
  print_line
  echo
  echo "  이 폴더 안에 아래 두 가지가 생겼습니다."
  echo
  echo "    · dist/KarisBulletin  폴더   ← 실제 프로그램"
  echo "    · KarisBulletin-2.0-Mac-....zip  ← 전달용 압축파일"
  echo
  echo "  다른 교회에 주실 때는 ZIP 파일을 그대로 보내시면 됩니다."
  echo "  보내기 전에 dist 폴더 안의 프로그램을 한 번 실행해 보세요."
  echo
  open dist 2>/dev/null
else
  echo "  만들지 못했습니다."
  print_line
  echo
  echo "  위에 빨간 글씨로 나온 내용을 그대로 복사해서 문의해 주세요."
fi
echo
read "?Enter 를 누르면 이 창이 닫힙니다."
