@echo off
REM Jarvis - cift tikla baslat (Windows)
cd /d "%~dp0"

REM 1) Python kontrolu
where python >nul 2>&1
if errorlevel 1 (
  echo Python bulunamadi. Indirme sayfasi aciliyor...
  start "" https://www.python.org/downloads/
  echo Python'u kurarken "Add Python to PATH" kutusunu isaretle, sonra bu dosyaya tekrar cift tikla.
  pause
  exit /b 1
)

REM 2) Ilk acilis sihirbazi (.env yoksa)
if not exist .env (
  python backend\wizard.py
)

REM 3) Kurulum (sanal ortam yoksa)
if not exist backend\.venv (
  echo Bagimliliklar yukleniyor, lutfen bekleyin (ilk seferde biraz surer)...
  python -m venv backend\.venv
  backend\.venv\Scripts\python -m pip install --upgrade pip -q
  backend\.venv\Scripts\pip install -r backend\requirements.txt -q
)

REM 4) .env ayarlarini yukle
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  echo %%a | findstr /b "#" >nul || if not "%%a"=="" set "%%a=%%b"
)

REM 5) Ollama modu ise modeli indir (ollama kuruluysa)
if not "%JARVIS_MODEL%"=="" (
  where ollama >nul 2>&1
  if errorlevel 1 (
    echo NOT: Ollama kurulu degil. Ucretsiz mod icin: https://ollama.com
    start "" https://ollama.com
  ) else (
    echo Ollama modeli hazirlaniyor (%JARVIS_MODEL%)...
    ollama pull %JARVIS_MODEL%
  )
)

REM 6) Tarayiciyi ac + sunucuyu baslat
start "" http://127.0.0.1:8000
echo Jarvis calisiyor -^> http://127.0.0.1:8000  (kapatmak icin bu pencereyi kapatin)
cd backend
.venv\Scripts\python main.py
