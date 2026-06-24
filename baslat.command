#!/usr/bin/env bash
# Jarvis - cift tikla baslat (macOS / Linux) - SIFIR KURULUM (pip gerekmez)
cd "$(dirname "$0")"

open_url() { command -v open >/dev/null 2>&1 && open "$1" || (command -v xdg-open >/dev/null 2>&1 && xdg-open "$1"); }

# 1) Python kontrolu
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 bulunamadi. Indirme sayfasi aciliyor..."
  open_url "https://www.python.org/downloads/"
  read -p "Python'u kurduktan sonra Enter..." _
  exit 1
fi

# 2) Ilk acilis sihirbazi (.env yoksa)
if [ ! -f .env ]; then
  python3 backend/wizard.py
fi

# 3) .env ayarlarini yukle
set -a
[ -f .env ] && . .env
set +a

# 4) Ollama modu ise model hazirla (ollama kuruluysa)
if [ -n "${JARVIS_MODEL:-}" ]; then
  if command -v ollama >/dev/null 2>&1; then
    echo "Ollama modeli hazirlaniyor (${JARVIS_MODEL})..."
    ollama pull "${JARVIS_MODEL}" 2>/dev/null || true
  elif [ "${JARVIS_PROVIDER:-ollama}" = "ollama" ]; then
    echo "NOT: Ollama kurulu degil. Ucretsiz mod icin: https://ollama.com"
    open_url "https://ollama.com"
  fi
fi

# 5) Sunucuyu baslat (paket KURULUMU YOK)
echo ""
python3 backend/server.py
