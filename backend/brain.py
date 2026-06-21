"""Jarvis'in beyni - iki sağlayıcı destekler:

- "ollama"  : yerel, ücretsiz LLM (varsayılan)
- "claude"  : Claude API (Opus 4.8) - profesyonel kalite, ücretli

JARVIS_PROVIDER ortam değişkeni ile seçilir.
"""
import os
import re

import tools
import memory

PROVIDER = os.environ.get("JARVIS_PROVIDER", "ollama").lower()

# --- Ollama ayarları ---
MODEL = os.environ.get("JARVIS_MODEL", "llama3.1")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# --- Claude ayarları ---
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_MAX_TOKENS = int(os.environ.get("JARVIS_CLAUDE_MAX_TOKENS", "2048"))

SYSTEM_PROMPT = """Sen Jarvis adında, Türkçe konuşan yardımcı bir yapay zeka asistanısın.
Iron Man filmindeki Jarvis gibi kibar, kısa ve net cevaplar verirsin.
Kullanıcıya "efendim" diye hitap edebilirsin ama abartma.

Kuralların:
- Cevapların KISA ve sohbet dilinde olsun çünkü cevabın sesli okunacak.
- Madde işareti, markdown veya uzun paragraf KULLANMA. Düz, konuşma dilinde yaz.
- Güncel bilgi (hava, haber, tarih, fiyat) gerektiğinde web_search aracını kullan.
- Uygulama açma, ses ayarı gibi sistem işlemleri için ilgili araçları kullan.
- Kullanıcı kişisel bir bilgi paylaşırsa (ismi, tercihi) remember aracıyla kaydet.
- Kullanıcı kod yazmanı isterse: kodu write_file ile bir dosyaya kaydet, gerekirse run_command ile çalıştırıp test et. Hata çıkarsa düzelt ve tekrar dene.
- Dosya işlemleri çalışma klasörü içinde yapılır; var olanı görmek için list_files / read_file kullan.
- Bir web sayfasını okuman/özetlemen istenirse web_fetch kullan; matematik için calculate.
- "Bana ... hatırlat" denirse set_reminder kullan; not tutma için add_note / list_notes.
- Bilgisayar durumu (pil, RAM, disk) sorulursa system_info kullan.
- Müzik için play_music; çalanı duraklat/geç için media_control kullan.
- E-posta göndermek için send_email; takvim için add_event / list_events (tarihi ISO 8601'e çevir).
- Kod yazarken cevabında kodu ```dil ... ``` bloğu içinde ver ki ekranda düzgün gösterilsin.
- Hava durumu için get_weather; ışıkları açıp kapatmak için hue_lights kullan.
- Bir aracı kullandıktan sonra sonucu doğal bir cümleyle özetle."""

MAX_ITERATIONS = 8


def _build_system(facts: dict) -> str:
    if not facts:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + "\n\nKullanıcı hakkında bildiklerin:\n" + "\n".join(
        f"- {k}: {v}" for k, v in facts.items()
    )


# ---------------------------------------------------------------------------
# Ollama (yerel, ücretsiz)
# ---------------------------------------------------------------------------
_ollama_client = None


def _get_ollama():
    global _ollama_client
    if _ollama_client is None:
        import ollama
        _ollama_client = ollama.Client(host=OLLAMA_HOST)
    return _ollama_client


def _chat_ollama(user_message: str, system: str, history: list) -> str:
    client = _get_ollama()
    messages = [{"role": "system", "content": system}] + history

    final_text = ""
    for _ in range(MAX_ITERATIONS):
        response = client.chat(model=MODEL, messages=messages, tools=tools.TOOL_SCHEMAS)
        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            final_text = msg.get("content", "").strip()
            break

        for call in tool_calls:
            fn = call["function"]
            result = tools.run_tool(fn["name"], fn.get("arguments", {}) or {})
            messages.append({"role": "tool", "content": result, "name": fn["name"]})
    else:
        final_text = "Üzgünüm efendim, isteği tamamlayamadım."

    return final_text or "Anladım efendim."


# ---------------------------------------------------------------------------
# Claude API (Opus 4.8) - profesyonel kalite
# ---------------------------------------------------------------------------
_claude_client = None


def _get_claude():
    global _claude_client
    if _claude_client is None:
        import anthropic
        _claude_client = anthropic.Anthropic()  # ANTHROPIC_API_KEY ortamdan okunur
    return _claude_client


def _claude_tools() -> list:
    """Ollama/OpenAI tarzı şemaları Anthropic biçimine çevirir."""
    out = []
    for t in tools.TOOL_SCHEMAS:
        fn = t["function"]
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


def _chat_claude(user_message: str, system: str, history: list) -> str:
    client = _get_claude()
    anthropic_tools = _claude_tools()

    # Geçmişi Anthropic biçimine çevir (yalnızca metin user/assistant mesajları)
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]

    final_text = ""
    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=system,
            tools=anthropic_tools,
            messages=messages,
        )

        # Asistan yanıtını (tüm bloklarıyla) geçmişe ekle
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            final_text = "".join(
                b.text for b in response.content if b.type == "text"
            ).strip()
            break

        # Araçları çalıştır, sonuçları tek bir user mesajında geri besle
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = tools.run_tool(block.name, block.input or {})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})
    else:
        final_text = "Üzgünüm efendim, isteği tamamlayamadım."

    return final_text or "Anladım efendim."


# ---------------------------------------------------------------------------
# Genel giriş noktası
# ---------------------------------------------------------------------------
def _auto_capture(user_message: str):
    """Mesajdan basit kalıplarla kişisel bilgi yakalayıp otomatik kaydeder."""
    patterns = {
        "isim": r"(?:benim\s+)?(?:ad[ıi]m|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)",
        "şehir": r"(?:ben\s+)?([A-Za-zÇĞİÖŞÜçğıöşü]+)\s*['’]?d[ae]\s+(?:yaşıyorum|oturuyorum)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, user_message, re.IGNORECASE)
        if m:
            memory.remember_fact(key, m.group(1).strip().capitalize())


def chat(user_message: str, session_id: str = "default") -> str:
    """Kullanıcı mesajını işler, gerekirse araç çağırır, metin cevap döndürür."""
    memory.add_message(session_id, "user", user_message)
    _auto_capture(user_message)
    system = _build_system(memory.get_facts())
    history = memory.get_history(session_id, limit=20)

    try:
        if PROVIDER == "claude":
            final_text = _chat_claude(user_message, system, history)
        else:
            final_text = _chat_ollama(user_message, system, history)
    except Exception as e:
        final_text = f"Bir hata oluştu efendim: {e}"

    memory.add_message(session_id, "assistant", final_text)
    return final_text


def health() -> dict:
    """Seçili sağlayıcının durumunu kontrol eder."""
    if PROVIDER == "claude":
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        return {
            "provider": "claude",
            "model": CLAUDE_MODEL,
            "api_key_set": has_key,
            "status": "ok" if has_key else "ANTHROPIC_API_KEY eksik",
        }
    try:
        client = _get_ollama()
        models = client.list().get("models", [])
        names = [m.get("model", m.get("name", "")) for m in models]
        return {
            "provider": "ollama",
            "model": MODEL,
            "model_installed": any(MODEL in n for n in names),
            "models": names,
            "status": "ok",
        }
    except Exception as e:
        return {"provider": "ollama", "model": MODEL, "status": "error", "error": str(e)}
