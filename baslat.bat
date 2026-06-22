@echo off
REM Jarvis - cift tikla baslat (Windows)
REM Masaustune kisayol: bu dosyaya sag tik -> Kisayol olustur -> masaustune tasi
cd /d "%~dp0"

REM Ilk acilista otomatik kurulum
if not exist backend\.venv (
  echo Ilk kurulum yapiliyor, lutfen bekleyin...
  if not exist .env copy .env.example .env >nul
  python -m venv backend\.venv
  backend\.venv\Scripts\python -m pip install --upgrade pip -q
  backend\.venv\Scripts\pip install -r backend\requirements.txt -q
  echo Kurulum tamam.
)

REM .env ayarlarini yukle
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  echo %%a | findstr /b "#" >nul || if not "%%a"=="" set "%%a=%%b"
)

REM Tarayiciyi otomatik ac, sonra sunucuyu baslat
start "" http://127.0.0.1:8000
echo Jarvis baslatiliyor -^> http://127.0.0.1:8000  (kapatmak icin bu pencereyi kapatin)
cd backend
.venv\Scripts\python main.py
