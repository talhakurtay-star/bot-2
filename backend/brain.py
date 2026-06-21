"""Jarvis'in beyni - Ollama (yerel, ücretsiz LLM) ile tool-calling döngüsü."""
import os
import ollama

import tools
import memory

MODEL = os.environ.get("JARVIS_MODEL", "llama3.1")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

_client = ollama.Client(host=OLLAMA_HOST)

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
- Bir aracı kullandıktan sonra sonucu doğal bir cümleyle özetle."""


def _max_iterations() -> int:
    return 8


def chat(user_message: str, session_id: str = "default") -> str:
    """Kullanıcı mesajını işler, gerekirse araç çağırır, metin cevap döndürür."""
    memory.add_message(session_id, "user", user_message)

    facts = memory.get_facts()
    facts_text = ""
    if facts:
        facts_text = "\n\nKullanıcı hakkında bildiklerin:\n" + "\n".join(
            f"- {k}: {v}" for k, v in facts.items()
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT + facts_text}]
    messages += memory.get_history(session_id, limit=20)

    final_text = ""
    for _ in range(_max_iterations()):
        response = _client.chat(
            model=MODEL,
            messages=messages,
            tools=tools.TOOL_SCHEMAS,
        )
        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            final_text = msg.get("content", "").strip()
            break

        # Araçları çalıştır ve sonuçları geri besle
        for call in tool_calls:
            fn = call["function"]
            name = fn["name"]
            args = fn.get("arguments", {}) or {}
            result = tools.run_tool(name, args)
            messages.append({"role": "tool", "content": result, "name": name})
    else:
        final_text = "Üzgünüm efendim, isteği tamamlayamadım."

    if not final_text:
        final_text = "Anladım efendim."

    memory.add_message(session_id, "assistant", final_text)
    return final_text


def health() -> dict:
    """Ollama bağlantısını ve modelin yüklü olup olmadığını kontrol eder."""
    try:
        models = _client.list().get("models", [])
        names = [m.get("model", m.get("name", "")) for m in models]
        installed = any(MODEL in n for n in names)
        return {"ollama": "ok", "model": MODEL, "model_installed": installed, "models": names}
    except Exception as e:
        return {"ollama": "error", "error": str(e), "model": MODEL}
