@echo off
REM Jarvis - cift tikla baslat (Windows) - SIFIR KURULUM (pip gerekmez)
cd /d "%~dp0"

REM 1) Python bul
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo.
  echo [HATA] Python bulunamadi. Indirme sayfasi aciliyor.
  echo Kurarken "Add python.exe to PATH" kutusunu isaretle, sonra tekrar cift tikla.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Python bulundu: %PY%

REM 2) Ilk acilis sihirbazi (.env yoksa beyin secimi)
if not exist .env (
  %PY% backend\wizard.py
)

REM 3) .env ayarlarini yukle
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  echo %%a | findstr /b "#" >nul || if not "%%a"=="" set "%%a=%%b"
)

REM 4) Ollama modu ise model hazirla (ollama kuruluysa)
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

REM 5) Sunucuyu baslat (paket KURULUMU YOK - sadece Python standart kutuphanesi)
echo.
%PY% backend\server.py

echo.
echo === Sunucu durdu. Hata varsa yukarida gorunur. ===
pause
