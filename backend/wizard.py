"""Jarvis ilk açılış sihirbazı - .env dosyasını etkileşimli oluşturur.

Sadece standart kütüphane kullanır; sanal ortam kurulmadan önce çalışabilir.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def main():
    print("\n" + "=" * 48)
    print("   🤖  J.A.R.V.I.S  ilk kurulum sihirbazı")
    print("=" * 48)
    print("\nHangi beyni kullanmak istersin?\n")
    print("  1) Ollama   - tamamen ÜCRETSİZ, yerel (model indirilir)")
    print("  2) Claude   - PRO, çok daha akıllı (API anahtarı gerekir)")
    print("  3) İkisi de - ikisini de kur, sonra değiştirebilirsin\n")

    choice = ask("Seçim (1/2/3)", "1")

    lines = ["# Jarvis ayarları (sihirbaz tarafından oluşturuldu)\n"]
    use_ollama = choice in ("1", "3")
    use_claude = choice in ("2", "3")

    provider = "ollama"
    if use_claude:
        print("\n— Claude ayarları —")
        key = ask("Claude API anahtarın (sk-ant-... ; yoksa boş bırak)")
        if key:
            lines.append(f"ANTHROPIC_API_KEY={key}\n")
        print("\nModel seç:")
        print("  1) Haiku  - ucuz, hızlı (sesli asistan için ideal)")
        print("  2) Opus   - en yüksek kalite (biraz daha pahalı)")
        m = ask("Seçim (1/2)", "1")
        model = "claude-opus-4-8" if m == "2" else "claude-haiku-4-5"
        lines.append(f"JARVIS_CLAUDE_MODEL={model}\n")
        # Claude anahtarı verildiyse varsayılan beyin Claude olsun
        provider = "claude" if key else ("ollama" if use_ollama else "claude")

    if use_ollama:
        lines.append("JARVIS_MODEL=llama3.1\n")
        lines.append("OLLAMA_HOST=http://localhost:11434\n")

    # İkisi de seçildiyse hangisi varsayılan olsun?
    if use_ollama and use_claude:
        print("\nVarsayılan olarak hangisi çalışsın?")
        print("  1) Ollama (ücretsiz)")
        print("  2) Claude (pro)")
        dp = ask("Seçim (1/2)", "2" if provider == "claude" else "1")
        provider = "claude" if dp == "2" else "ollama"

    lines.insert(1, f"JARVIS_PROVIDER={provider}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\n✅ .env oluşturuldu. Varsayılan beyin: " + provider.upper())
    if use_ollama:
        print("ℹ️  Ollama modu için model indirilecek (ollama pull llama3.1).")
        print("    Ollama kurulu değilse: https://ollama.com")
    if use_claude and not any("ANTHROPIC_API_KEY" in l for l in lines):
        print("ℹ️  Claude için sonra .env'e ANTHROPIC_API_KEY ekleyebilirsin.")
    print("=" * 48 + "\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nSihirbaz iptal edildi.")
