@echo off
REM Jarvis - cift tikla baslat (Windows)
cd /d "%~dp0"

REM 1) Python kontrolu (py launcher veya python)
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo.
  echo [HATA] Python bulunamadi.
  echo Indirme sayfasi aciliyor. Kurarken ALT TARAFTAKI
  echo "Add python.exe to PATH" kutusunu MUTLAKA isaretle.
  echo Kurduktan sonra bu dosyaya tekrar cift tikla.
  echo.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Python bulundu: %PY%

REM 2) Ilk acilis sihirbazi (.env yoksa)
if not exist .env (
  %PY% backend\wizard.py
  if errorlevel 1 ( echo [HATA] Sihirbaz calismadi. & pause & exit /b 1 )
)

REM 3) Kurulum: sanal ortam + paketler (her acilista dogrulanir, yarim kalmis kurulum kendini onarir)
if not exist backend\.venv (
  echo Sanal ortam olusturuluyor...
  %PY% -m venv backend\.venv
  if errorlevel 1 ( echo [HATA] Sanal ortam olusturulamadi. & pause & exit /b 1 )
)
backend\.venv\Scripts\python -c "import fastapi, uvicorn, anthropic" >nul 2>&1
if errorlevel 1 (
  echo Bagimliliklar yukleniyor, lutfen bekleyin (ilk seferde birkac dakika surebilir)...
  backend\.venv\Scripts\python -m pip install --upgrade pip -q
  backend\.venv\Scripts\pip install -r backend\requirements.txt
  if errorlevel 1 ( echo [HATA] Paketler yuklenemedi. Yukaridaki hatayi kopyalayip gonder. & pause & exit /b 1 )
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
echo.
echo Jarvis calisiyor -^> http://127.0.0.1:8000
echo (Kapatmak icin bu pencereyi kapat)
echo.
backend\.venv\Scripts\python backend\main.py

echo.
echo === Sunucu durdu. Yukarida hata varsa okuyabilirsin. ===
pause
