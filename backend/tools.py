"""Jarvis araçları (tools) - sistem kontrolü, web arama, zaman, hafıza.

Bu fonksiyonlar Ollama'nın tool-calling özelliği ile çağrılır.
Her fonksiyon basit tipler alır ve string sonuç döndürür.
"""
import os
import sys
import platform
import subprocess
import shutil
import webbrowser
from datetime import datetime

from ddgs import DDGS

import memory


# ---------------------------------------------------------------------------
# Zaman / tarih
# ---------------------------------------------------------------------------
def get_current_time() -> str:
    """Şu anki tarih ve saati döndürür."""
    now = datetime.now()
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return f"{now.strftime('%d.%m.%Y %H:%M')} - {gunler[now.weekday()]}"


# ---------------------------------------------------------------------------
# Web arama
# ---------------------------------------------------------------------------
def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo ile internette arama yapar (ücretsiz, API anahtarı gerekmez)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "Arama sonucu bulunamadı."
        lines = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"- {title}: {body} ({href})")
        return "\n".join(lines)
    except Exception as e:
        return f"Web araması başarısız: {e}"


# ---------------------------------------------------------------------------
# Sistem kontrolü (yerel sunucuda çalışır)
# ---------------------------------------------------------------------------
# Güvenlik: yalnızca bilinen, zararsız uygulamalara izin verilir.
_APP_ALIASES = {
    "windows": {
        "notepad": "notepad.exe",
        "not defteri": "notepad.exe",
        "hesap makinesi": "calc.exe",
        "calculator": "calc.exe",
        "tarayıcı": None,  # webbrowser ile açılır
        "browser": None,
        "dosya gezgini": "explorer.exe",
        "explorer": "explorer.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "cmd.exe",
    },
    "darwin": {
        "not defteri": "TextEdit",
        "notepad": "TextEdit",
        "hesap makinesi": "Calculator",
        "calculator": "Calculator",
        "finder": "Finder",
        "dosya gezgini": "Finder",
        "terminal": "Terminal",
    },
    "linux": {
        "hesap makinesi": "gnome-calculator",
        "calculator": "gnome-calculator",
        "dosya gezgini": "nautilus",
        "terminal": "gnome-terminal",
        "metin editörü": "gedit",
    },
}


def open_application(name: str) -> str:
    """İsme göre yerel bir uygulamayı açar (ör. 'hesap makinesi', 'tarayıcı')."""
    osname = platform.system().lower()
    name_l = name.strip().lower()

    if name_l in ("tarayıcı", "browser", "internet"):
        webbrowser.open("https://www.google.com")
        return "Tarayıcı açıldı."

    aliases = _APP_ALIASES.get(osname, {})
    target = aliases.get(name_l)

    try:
        if osname == "darwin":
            app = target or name
            subprocess.Popen(["open", "-a", app])
        elif osname == "windows":
            app = target or name
            os.startfile(app)  # type: ignore[attr-defined]
        else:  # linux
            app = target or name
            if shutil.which(app) is None:
                return f"'{name}' uygulaması bulunamadı."
            subprocess.Popen([app])
        return f"'{name}' açılıyor."
    except Exception as e:
        return f"'{name}' açılamadı: {e}"


def open_website(url: str) -> str:
    """Belirtilen web sitesini varsayılan tarayıcıda açar."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} açıldı."


def set_volume(level: int) -> str:
    """Sistem ses seviyesini 0-100 arası ayarlar (platforma göre)."""
    level = max(0, min(100, int(level)))
    osname = platform.system().lower()
    try:
        if osname == "darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
        elif osname == "linux":
            if shutil.which("amixer"):
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"], check=True)
            else:
                return "Ses ayarı için 'amixer' bulunamadı."
        elif osname == "windows":
            # Windows'ta harici bağımlılık olmadan ses kontrolü sınırlıdır.
            return "Windows'ta ses kontrolü için ek kurulum gerekiyor (nircmd/pycaw)."
        return f"Ses seviyesi %{level} yapıldı."
    except Exception as e:
        return f"Ses ayarlanamadı: {e}"


# ---------------------------------------------------------------------------
# Hafıza araçları
# ---------------------------------------------------------------------------
def remember(key: str, value: str) -> str:
    """Kullanıcı hakkında kalıcı bir bilgi kaydeder (ör. ismini, tercihlerini)."""
    memory.remember_fact(key, value)
    return f"Kaydettim: {key} = {value}"


def recall() -> str:
    """Kullanıcı hakkında kaydedilen tüm bilgileri getirir."""
    facts = memory.get_facts()
    if not facts:
        return "Henüz kayıtlı bilgi yok."
    return "\n".join(f"{k}: {v}" for k, v in facts.items())


# ---------------------------------------------------------------------------
# Tool kayıt tablosu - Ollama'ya verilecek şema + çalıştırılabilir referans
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "web_search": web_search,
    "open_application": open_application,
    "open_website": open_website,
    "set_volume": set_volume,
    "remember": remember,
    "recall": recall,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Şu anki tarih ve saati öğrenir.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Güncel bilgi, haber, hava durumu gibi konularda internette arama yapar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Arama sorgusu"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Bilgisayardaki bir uygulamayı açar (ör. hesap makinesi, not defteri, tarayıcı).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Açılacak uygulamanın adı"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Belirtilen web sitesini tarayıcıda açar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Açılacak web adresi"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Sistem ses seviyesini ayarlar (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "0 ile 100 arası ses seviyesi"},
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Kullanıcı hakkında kalıcı bir bilgi kaydeder (isim, tercih vb.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Bilginin anahtarı, ör. 'isim'"},
                    "value": {"type": "string", "description": "Bilginin değeri"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Kullanıcı hakkında daha önce kaydedilmiş bilgileri getirir.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def run_tool(name: str, arguments: dict) -> str:
    """Adı ve argümanlarıyla bir aracı çalıştırır."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Bilinmeyen araç: {name}"
    try:
        return str(func(**(arguments or {})))
    except TypeError as e:
        return f"Araç argümanları hatalı ({name}): {e}"
    except Exception as e:
        return f"Araç çalışırken hata ({name}): {e}"
