"""Jarvis'in beyni - SIFIR HARİCİ PAKET (sadece Python standart kütüphanesi).

İki sağlayıcı (urllib ile, SDK gerekmez):
- "ollama"  : yerel, ücretsiz LLM (http://localhost:11434)
- "claude"  : Claude API (ANTHROPIC_API_KEY ile)

JARVIS_PROVIDER ortam değişkeni ile seçilir.
"""
import os
import re
import json
import urllib.request
import urllib.error

import tools
import memory

PROVIDER = os.environ.get("JARVIS_PROVIDER", "ollama").lower()

# --- Ollama ---
MODEL = os.environ.get("JARVIS_MODEL", "llama3.1")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# --- Claude ---
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "claude-haiku-4-5")
CLAUDE_MAX_TOKENS = int(os.environ.get("JARVIS_CLAUDE_MAX_TOKENS", "2048"))
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sen Jarvis adında, Türkçe konuşan yardımcı bir yapay zeka asistanısın.
Iron Man filmindeki Jarvis gibi kibar, kısa ve net cevaplar verirsin.
Kullanıcıya "efendim" diye hitap edebilirsin ama abartma.

Kuralların:
- Cevapların KISA ve sohbet dilinde olsun çünkü cevabın sesli okunacak.
- Madde işareti, markdown veya uzun paragraf KULLANMA. Düz, konuşma dilinde yaz.
- Güncel bilgi (hava, haber, tarih, fiyat) gerektiğinde web_search/get_weather kullan.
- Uygulama açma, ses ayarı gibi sistem işlemleri için ilgili araçları kullan.
- Kullanıcı kişisel bir bilgi paylaşırsa (ismi, tercihi) remember aracıyla kaydet.
- Kod yazarken cevabında kodu ```dil ... ``` bloğu içinde ver.
- Müzik için play_music; hava durumu için get_weather; ışıklar için hue_lights.
- "Bana ... hatırlat" -> set_reminder; not -> add_note; takvim -> add_event (tarihi ISO 8601'e çevir).
- Bir aracı kullandıktan sonra sonucu doğal bir cümleyle özetle."""

MAX_ITERATIONS = 8


def _post_json(url, payload, headers=None, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _build_system_text(facts: dict) -> str:
    if not facts:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + "\n\nKullanıcı hakkında bildiklerin:\n" + "\n".join(
        f"- {k}: {v}" for k, v in facts.items()
    )


def _auto_capture(user_message: str):
    patterns = {
        "isim": r"(?:benim\s+)?(?:ad[ıi]m|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)",
        "şehir": r"(?:ben\s+)?([A-Za-zÇĞİÖŞÜçğıöşü]+)\s*['’]?d[ae]\s+(?:yaşıyorum|oturuyorum)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, user_message, re.IGNORECASE)
        if m:
            memory.remember_fact(key, m.group(1).strip().capitalize())


# ---------------------------------------------------------------------------
# Ollama (urllib)
# ---------------------------------------------------------------------------
def _chat_ollama(system: str, history: list) -> str:
    messages = [{"role": "system", "content": system}] + history
    final_text = ""
    for _ in range(MAX_ITERATIONS):
        resp = _post_json(f"{OLLAMA_HOST}/api/chat", {
            "model": MODEL,
            "messages": messages,
            "tools": tools.TOOL_SCHEMAS,
            "stream": False,
        })
        msg = resp.get("message", {})
        messages.append(msg)
        calls = msg.get("tool_calls")
        if not calls:
            final_text = (msg.get("content") or "").strip()
            break
        for call in calls:
            fn = call["function"]
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            result = tools.run_tool(fn["name"], args)
            messages.append({"role": "tool", "content": result, "name": fn["name"]})
    else:
        final_text = "Üzgünüm efendim, isteği tamamlayamadım."
    return final_text or "Anladım efendim."


# ---------------------------------------------------------------------------
# Claude (urllib)
# ---------------------------------------------------------------------------
def _claude_tools():
    out = []
    for t in tools.TOOL_SCHEMAS:
        fn = t["function"]
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


def _chat_claude(facts: dict, history: list) -> str:
    if not ANTHROPIC_KEY:
        return "Claude için ANTHROPIC_API_KEY gerekli efendim (.env dosyasına ekleyin)."
    system_blocks = [{"type": "text", "text": SYSTEM_PROMPT,
                      "cache_control": {"type": "ephemeral"}}]
    if facts:
        ft = "Kullanıcı hakkında bildiklerin:\n" + "\n".join(f"- {k}: {v}" for k, v in facts.items())
        system_blocks.append({"type": "text", "text": ft})

    messages = [{"role": m["role"], "content": m["content"]}
                for m in history if m.get("role") in ("user", "assistant") and m.get("content")]
    anthropic_tools = _claude_tools()
    headers = {"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"}

    final_text = ""
    for _ in range(MAX_ITERATIONS):
        resp = _post_json("https://api.anthropic.com/v1/messages", {
            "model": CLAUDE_MODEL,
            "max_tokens": CLAUDE_MAX_TOKENS,
            "system": system_blocks,
            "tools": anthropic_tools,
            "messages": messages,
        }, headers=headers)

        content = resp.get("content", [])
        messages.append({"role": "assistant", "content": content})

        if resp.get("stop_reason") != "tool_use":
            final_text = "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            break

        tool_results = []
        for b in content:
            if b.get("type") == "tool_use":
                result = tools.run_tool(b["name"], b.get("input") or {})
                tool_results.append({"type": "tool_result", "tool_use_id": b["id"], "content": result})
        messages.append({"role": "user", "content": tool_results})
    else:
        final_text = "Üzgünüm efendim, isteği tamamlayamadım."
    return final_text or "Anladım efendim."


# ---------------------------------------------------------------------------
# Genel giriş noktası
# ---------------------------------------------------------------------------
def chat(user_message: str, session_id: str = "default") -> str:
    memory.add_message(session_id, "user", user_message)
    _auto_capture(user_message)
    facts = memory.get_facts()
    history = memory.get_history(session_id, limit=20)
    try:
        if PROVIDER == "claude":
            final_text = _chat_claude(facts, history)
        else:
            final_text = _chat_ollama(_build_system_text(facts), history)
    except urllib.error.URLError as e:
        if PROVIDER == "claude":
            final_text = f"Claude'a bağlanılamadı: {e}"
        else:
            final_text = ("Ollama'ya bağlanılamadım efendim. Ollama kurulu ve açık mı? "
                          "(https://ollama.com)")
    except Exception as e:
        final_text = f"Bir hata oluştu efendim: {e}"
    memory.add_message(session_id, "assistant", final_text)
    return final_text


def health() -> dict:
    if PROVIDER == "claude":
        return {"provider": "claude", "model": CLAUDE_MODEL,
                "api_key_set": bool(ANTHROPIC_KEY),
                "status": "ok" if ANTHROPIC_KEY else "ANTHROPIC_API_KEY eksik"}
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        names = [m.get("model", m.get("name", "")) for m in data.get("models", [])]
        return {"provider": "ollama", "model": MODEL,
                "model_installed": any(MODEL in n for n in names),
                "models": names, "status": "ok"}
    except Exception as e:
        return {"provider": "ollama", "model": MODEL, "status": "error", "error": str(e)}
