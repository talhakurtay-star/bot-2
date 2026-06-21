# 🤖 Jarvis — Proje Özeti & Devir Notu

**Ne:** Iron Man'deki Jarvis'ten esinlenen, **web tabanlı, tamamen ücretsiz/yerel** çalışan sesli yapay zeka asistanı. Buluta veri gitmez, API ücreti yok.

- **Repo:** `talhakurtay-star/bot-2`
- **Dal (branch):** `claude/wonderful-lovelace-j8dzdz`
- **Durum:** Kod yazıldı ve push edildi. ✅ Henüz **çalıştırılıp test edilmedi** — sıradaki iş bu.

## Mimari

Tarayıcı arayüzü (ücretsiz ses tanıma/seslendirme) + yerel Python sunucusu. Sunucu yerelde çalıştığı için sistem kontrolü mümkün.

```
Tarayıcı (STT/TTS, wake word) ──HTTP──► FastAPI ──► Ollama (yerel LLM)
                                          ├─► DuckDuckGo (web arama)
                                          ├─► sistem kontrolü (uygulama/ses)
                                          └─► SQLite (hafıza)
```

## Özellikler

- 🎤 Sesli konuşma (tarayıcı STT/TTS, Türkçe)
- 🗣️ Wake word: "Jarvis"
- 🧠 Yerel beyin: Ollama + tool-calling (varsayılan model `llama3.1`)
- 🌐 Web arama (DuckDuckGo, anahtar gerekmez)
- 💻 Sistem kontrolü: uygulama açma, web sitesi açma, ses ayarı
- 💾 Kalıcı hafıza (SQLite): konuşma geçmişi + kişisel bilgiler

## Klasör Yapısı

```
backend/
  main.py        # FastAPI sunucu + frontend servisi
  brain.py       # Ollama tool-calling döngüsü
  tools.py       # Araçlar: web arama, sistem kontrolü, zaman, hafıza
  memory.py      # SQLite hafıza
  requirements.txt
frontend/
  index.html, app.js, style.css   # Arayüz + STT/TTS/wake word
README.md
```

## Çalıştırma (yapılacak)

```bash
# 1) Ollama kur (ollama.com) ve modeli indir
ollama pull llama3.1

# 2) Bağımlılıklar
cd backend && python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) Başlat → tarayıcıda http://127.0.0.1:8000
python main.py
```

## Sıradaki İşler (öneri)

1. Yerelde çalıştır, sesli test et (mikrofon + wake word).
2. Windows'ta tam ses kontrolü (`pycaw`).
3. Ek araçlar: hatırlatıcı/takvim, müzik, dosya arama.
4. Tek tık kurulum scripti (`.bat`/`.sh`).

## Notlar

- Ortam değişkenleri — `JARVIS_MODEL` (model değiştirmek için), `OLLAMA_HOST`. Detaylar `README.md`'de.
- Mikrofon için Chrome/Edge önerilir; `localhost` üzerinde mikrofon otomatik izinlidir.
- Sistem kontrolü ve sesli test ancak **yerel makinede** (örn. Claude Code ile) anlam kazanır; bulut/web oturumunda mikrofon ve sistem erişimi yoktur.
