#!/usr/bin/env bash
# Jarvis - cift tikla baslat (macOS / Linux)
cd "$(dirname "$0")"

open_url() { command -v open >/dev/null 2>&1 && open "$1" || (command -v xdg-open >/dev/null 2>&1 && xdg-open "$1"); }

# 1) Python kontrolu
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 bulunamadi. Indirme sayfasi aciliyor..."
  open_url "https://www.python.org/downloads/"
  echo "Python'u kurduktan sonra bu dosyaya tekrar cift tikla."
  read -p "Cikmak icin Enter..." _
  exit 1
fi

# 2) Ilk acilis sihirbazi (.env yoksa beyin secimi sorar)
if [ ! -f .env ]; then
  python3 backend/wizard.py
fi

# 3) Kurulum (sanal ortam yoksa)
if [ ! -d backend/.venv ]; then
  echo "Bagimliliklar yukleniyor, lutfen bekleyin (ilk seferde biraz surer)..."
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip -q
  backend/.venv/bin/pip install -r backend/requirements.txt -q
fi

# 4) .env ayarlarini yukle
set -a
[ -f .env ] && . .env
set +a

# 5) Ollama modu ise modeli indir (ollama kuruluysa)
if [ -n "${JARVIS_MODEL:-}" ]; then
  if command -v ollama >/dev/null 2>&1; then
    echo "Ollama modeli hazirlaniyor (${JARVIS_MODEL})..."
    ollama pull "${JARVIS_MODEL}" 2>/dev/null || true
  elif [ "${JARVIS_PROVIDER:-ollama}" = "ollama" ]; then
    echo "NOT: Ollama kurulu degil. Ucretsiz mod icin: https://ollama.com"
    open_url "https://ollama.com"
  fi
fi

# 6) Tarayiciyi otomatik ac + sunucuyu baslat
( sleep 3; open_url "http://127.0.0.1:8000" ) &
echo "Jarvis calisiyor -> http://127.0.0.1:8000  (kapatmak icin bu pencereyi kapatin)"
cd backend
exec .venv/bin/python main.py
