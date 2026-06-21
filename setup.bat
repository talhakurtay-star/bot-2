@echo off
REM Jarvis tek tık kurulum (Windows)
cd /d "%~dp0"

echo Jarvis kuruluyor...

if not exist .env (
  copy .env.example .env >nul
  echo .env olusturuldu ^(gerekirse duzenleyin^).
)

cd backend
if not exist .venv (
  echo Sanal ortam olusturuluyor...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Bagimliliklar yukleniyor...
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

REM .env degiskenlerini yukle
for /f "usebackq tokens=1,* delims==" %%a in ("..\.env") do (
  echo %%a | findstr /b "#" >nul || if not "%%a"=="" set "%%a=%%b"
)

echo.
echo Kurulum tamam. Sunucu baslatiliyor: http://127.0.0.1:8000
python main.py
