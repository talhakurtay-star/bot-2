#!/usr/bin/env bash
# Jarvis - cift tikla baslat (macOS / Linux)
# Masaustune kisayol icin: bu dosyaya cift tikla (gerekirse: chmod +x baslat.command)
cd "$(dirname "$0")"

# Ilk acilista otomatik kurulum
if [ ! -d backend/.venv ]; then
  echo "Ilk kurulum yapiliyor, lutfen bekleyin..."
  [ -f .env ] || cp .env.example .env
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip -q
  backend/.venv/bin/pip install -r backend/requirements.txt -q
  echo "Kurulum tamam."
fi

# .env ayarlarini yukle
set -a
[ -f .env ] && . .env
set +a

# Sunucu acildiktan ~3 sn sonra tarayiciyi otomatik ac
(
  sleep 3
  if command -v open >/dev/null 2>&1; then open http://127.0.0.1:8000
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://127.0.0.1:8000
  fi
) &

echo "Jarvis baslatiliyor -> http://127.0.0.1:8000  (kapatmak icin bu pencereyi kapatin)"
cd backend
exec .venv/bin/python main.py
