@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title 카리스 주보제작 · 윈도우 실행판 만들기

echo ────────────────────────────────────────────────
echo   카리스 주보제작 · 윈도우 실행판 만들기
echo ────────────────────────────────────────────────
echo.
echo 몇 분 걸립니다. 창을 닫지 마시고 기다려 주세요.
echo.

if exist .venv\Scripts\python.exe goto ready
echo · 준비 중입니다 (처음 한 번만 오래 걸립니다)
py -3 -m venv .venv
if errorlevel 1 (
  echo.
  echo [!] Python 이 설치되어 있지 않습니다.
  echo.
  echo     https://www.python.org/downloads/windows/ 에서 설치한 뒤
  echo     이 파일을 다시 두 번 클릭해 주세요.
  echo     설치 첫 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요.
  echo.
  pause
  exit /b 1
)

:ready
echo · 필요한 것들을 내려받는 중
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo.
  echo [!] 인터넷 연결을 확인해 주세요.
  pause
  exit /b 1
)

echo · 실행판을 만드는 중
echo.
.venv\Scripts\python.exe build-native.py
if errorlevel 1 goto failed

echo.
echo ────────────────────────────────────────────────
echo   다 되었습니다.
echo ────────────────────────────────────────────────
echo.
echo   이 폴더 안에 아래 두 가지가 생겼습니다.
echo.
echo     · dist\KarisBulletin  폴더   ^<- 실제 프로그램
echo     · KarisBulletin-2.0-Windows.zip  ^<- 전달용 압축파일
echo.
echo   다른 교회에 주실 때는 ZIP 파일을 그대로 보내시면 됩니다.
echo   보내기 전에 dist 폴더 안의 프로그램을 한 번 실행해 보세요.
echo.
explorer dist
pause
exit /b 0

:failed
echo.
echo ────────────────────────────────────────────────
echo   만들지 못했습니다.
echo ────────────────────────────────────────────────
echo.
echo   위에 나온 오류 내용을 그대로 복사해서 문의해 주세요.
echo.
pause
exit /b 1
