#!/usr/bin/env bash
# Jarvis tek tık kurulum (Linux / macOS)
set -e
cd "$(dirname "$0")"

echo "🤖 Jarvis kuruluyor..."

# .env yoksa örnekten oluştur
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📝 .env oluşturuldu (gerekirse düzenleyin)."
fi

cd backend
if [ ! -d .venv ]; then
  echo "📦 Sanal ortam oluşturuluyor..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "📦 Bağımlılıklar yükleniyor..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# .env'i yükle
set -a
[ -f ../.env ] && . ../.env
set +a

echo "✅ Kurulum tamam. Sunucu başlatılıyor: http://127.0.0.1:8000"
python main.py
