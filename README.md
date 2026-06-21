# Jarvis — Web Tabanlı Sesli Yapay Zeka Asistanı

Iron Man'deki Jarvis'ten esinlenen, **tamamen ücretsiz ve yerel** çalışan bir sesli asistan.
Tarayıcıda konuşursun, beyin senin bilgisayarında çalışır — buluta veri gitmez, API ücreti yok.

## Özellikler

- 🎤 **Sesli konuşma** — Tarayıcının yerleşik ses tanıma (STT) ve seslendirme (TTS) motoru ile, Türkçe.
- 🗣️ **Wake word** — "Jarvis" diyerek elini sürmeden çağır.
- 🧠 **Yerel beyin** — [Ollama](https://ollama.com) ile açık kaynak LLM (varsayılan: `llama3.1`). Ücretsiz.
- 🌐 **Web arama** — Güncel bilgi, haber, hava durumu için DuckDuckGo (API anahtarı gerekmez).
- 💻 **Sistem kontrolü** — Uygulama açma, web sitesi açma, ses seviyesi ayarı (Windows/macOS/Linux).
- 💾 **Hafıza** — Konuşma geçmişi ve kişisel bilgiler SQLite'ta kalıcı saklanır.

## Mimari

```
Tarayıcı (frontend)            Yerel sunucu (backend)
┌──────────────────┐          ┌────────────────────────┐
│ Ses tanıma (STT) │          │ FastAPI                │
│ Seslendirme (TTS)│ ──HTTP─► │  ├─ brain.py (Ollama)  │ ──► Ollama (yerel LLM)
│ Wake word        │          │  ├─ tools.py (araçlar) │ ──► DuckDuckGo / sistem
│ Sohbet arayüzü   │ ◄──────  │  └─ memory.py (SQLite) │
└──────────────────┘          └────────────────────────┘
```

Backend yerel makinede çalıştığı için tarayıcının yapamadığı sistem işlemlerini (uygulama açma vb.) yapabilir.

## Kurulum

### 1. Ollama'yı kur ve modeli indir
[ollama.com](https://ollama.com/download) adresinden Ollama'yı kur, sonra:

```bash
ollama pull llama3.1
```

> İpucu: Tool-calling destekleyen modeller önerilir (`llama3.1`, `qwen2.5`, `mistral-nemo`).
> Daha hafif makine için: `ollama pull qwen2.5:3b` ve `JARVIS_MODEL=qwen2.5:3b`.

### 2. Python bağımlılıkları

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Çalıştır

```bash
# backend klasöründeyken:
python main.py
```

Ardından tarayıcıda **http://127.0.0.1:8000** adresini aç.

> Mikrofon erişimi için Chrome/Edge önerilir. Mikrofon `localhost` üzerinde otomatik izinlidir.

## Kullanım

- **Yazarak:** Alta yaz, Enter'a bas.
- **Tek seferlik konuşma:** 🎤 düğmesine bas, konuş.
- **Eller serbest:** "Jarvis'i dinle" düğmesini aç, sonra "Jarvis, hava bugün nasıl?" de.

Örnek komutlar:
- "Jarvis, saat kaç?"
- "Hesap makinesini aç."
- "İstanbul'da hava nasıl?" (web arama)
- "Benim adım Talha, bunu hatırla." (hafıza)
- "Sesi yüzde 30 yap."

## Ayarlar (ortam değişkenleri)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `JARVIS_MODEL` | `llama3.1` | Kullanılacak Ollama modeli |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama sunucu adresi |

## Klasör Yapısı

```
backend/
  main.py        # FastAPI sunucu + frontend servisi
  brain.py       # Ollama tool-calling döngüsü
  tools.py       # Araçlar: web arama, sistem kontrolü, hafıza
  memory.py      # SQLite hafıza
  requirements.txt
frontend/
  index.html     # Arayüz
  app.js         # STT/TTS/wake word + sohbet
  style.css
```

## Notlar & Güvenlik

- Uygulama açma yalnızca bilinen uygulamalarla sınırlandırılmıştır; keyfi komut çalıştırmaz.
- Windows'ta ses kontrolü için ek paket (`pycaw`/`nircmd`) gerekebilir.
- Her şey yerel çalışır; veriler `backend/jarvis_memory.db` dosyasında kalır.
