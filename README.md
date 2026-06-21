# Jarvis — Web Tabanlı Sesli Yapay Zeka Asistanı

Iron Man'deki Jarvis'ten esinlenen, **tamamen ücretsiz ve yerel** çalışan bir sesli asistan.
Tarayıcıda konuşursun, beyin senin bilgisayarında çalışır — buluta veri gitmez, API ücreti yok.

## Özellikler

- 🎤 **Sesli konuşma** — Tarayıcının yerleşik ses tanıma (STT) ve seslendirme (TTS) motoru ile, Türkçe.
- 🗣️ **Wake word** — "Jarvis" diyerek elini sürmeden çağır.
- 🧠 **Yerel beyin** — [Ollama](https://ollama.com) ile açık kaynak LLM (varsayılan: `llama3.1`). Ücretsiz.
- 🌐 **Web arama** — Güncel bilgi, haber, hava durumu için DuckDuckGo (API anahtarı gerekmez).
- 💻 **Sistem kontrolü** — Uygulama açma, web sitesi açma, ses seviyesi ayarı (Windows/macOS/Linux).
- 👨‍💻 **Kod yazma & çalıştırma** — Dosya oluşturma/okuma/listeleme ve komut çalıştırma (güvenli bir çalışma klasörü içinde).
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
| `JARVIS_PROVIDER` | `ollama` | Yapay zeka beyni: `ollama` (yerel/ücretsiz) veya `claude` (Claude API, pro) |
| `JARVIS_MODEL` | `llama3.1` | Kullanılacak Ollama modeli (kod için `qwen2.5-coder` önerilir) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama sunucu adresi |
| `JARVIS_CLAUDE_MODEL` | `claude-opus-4-8` | Claude modu için kullanılacak model |
| `JARVIS_CLAUDE_MAX_TOKENS` | `2048` | Claude modu yanıt uzunluğu sınırı |
| `ANTHROPIC_API_KEY` | — | Claude modu için API anahtarı (zorunlu) |
| `JARVIS_WORKSPACE` | `~/jarvis_workspace` | Dosya/komut işlemlerinin yapıldığı klasör |
| `JARVIS_ALLOW_COMMANDS` | `1` | Komut çalıştırmayı kapatmak için `0` yap |

### İki beyin modu

**Ücretsiz/yerel (varsayılan)** — Ollama ile, internet/ödeme gerekmez:
```bash
python main.py
```

**Profesyonel (Claude Opus 4.8)** — gerçekten Claude'un kendisi, çok daha yetenekli (ücretli):
```bash
export JARVIS_PROVIDER=claude
export ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com adresinden alınır
python main.py
```
Claude modunda Ollama kurulumuna gerek yoktur; tüm araçlar (web arama, sistem kontrolü, kod yazma) aynen çalışır.

### Kod yazma örneği

- "Jarvis, Python'da bir asal sayı bulucu yaz ve çalıştır."
- Jarvis `write_file` ile dosyayı `~/jarvis_workspace` içine kaydeder, `run_command` ile çalıştırır, hata olursa düzeltir.

> ⚠️ **Güvenlik:** Dosya işlemleri yalnızca çalışma klasörü içinde yapılır (dışarı çıkılamaz).
> Komut çalıştırmada tehlikeli kalıplar (`rm -rf /`, `shutdown`, indirme + çalıştırma vb.) engellenir ve 60 sn zaman aşımı vardır.
> Kod için en iyi sonuç: `ollama pull qwen2.5-coder` ve `JARVIS_MODEL=qwen2.5-coder`.

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
