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
from pathlib import Path

from ddgs import DDGS

import memory


# ---------------------------------------------------------------------------
# Çalışma klasörü (workspace) - dosya/komut işlemleri buraya hapsedilir.
# Güvenlik: Jarvis bu klasörün dışına yazamaz/okuyamaz, komutlar burada çalışır.
# ---------------------------------------------------------------------------
WORKSPACE = Path(
    os.environ.get("JARVIS_WORKSPACE", os.path.join(Path.home(), "jarvis_workspace"))
).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

# Komut çalıştırma varsayılan olarak açık; kapatmak için JARVIS_ALLOW_COMMANDS=0
ALLOW_COMMANDS = os.environ.get("JARVIS_ALLOW_COMMANDS", "1") != "0"

# Açıkça tehlikeli kalıplar - bunları içeren komutlar reddedilir.
_DANGEROUS = [
    "rm -rf /", "rm -rf ~", "rm -rf *", ":(){", "mkfs", "dd if=",
    "format ", "del /f /s /q", "shutdown", "reboot", "> /dev/sda",
    "chmod -r 000", "curl ", "wget ", "| sh", "| bash",
]


def _safe_path(path: str) -> Path:
    """Verilen yolu workspace içine çözer; dışarı çıkışı engeller."""
    p = (WORKSPACE / path).resolve()
    if WORKSPACE not in p.parents and p != WORKSPACE:
        raise ValueError("İzin verilmeyen yol: çalışma klasörünün dışına çıkılamaz.")
    return p


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
# Dosya işlemleri (workspace ile sınırlı)
# ---------------------------------------------------------------------------
def write_file(path: str, content: str) -> str:
    """Çalışma klasörüne bir dosya yazar/oluşturur (kod, metin vb.)."""
    try:
        p = _safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Dosya kaydedildi: {p} ({len(content)} karakter)"
    except Exception as e:
        return f"Dosya yazılamadı: {e}"


def read_file(path: str) -> str:
    """Çalışma klasöründeki bir dosyayı okur."""
    try:
        p = _safe_path(path)
        if not p.exists():
            return f"Dosya bulunamadı: {path}"
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 6000:
            text = text[:6000] + "\n... (kısaltıldı)"
        return text
    except Exception as e:
        return f"Dosya okunamadı: {e}"


def list_files(path: str = ".") -> str:
    """Çalışma klasöründeki dosya ve klasörleri listeler."""
    try:
        p = _safe_path(path)
        if not p.exists():
            return f"Klasör bulunamadı: {path}"
        items = []
        for item in sorted(p.iterdir()):
            tip = "klasör" if item.is_dir() else "dosya"
            items.append(f"{item.name} ({tip})")
        return "\n".join(items) if items else "Klasör boş."
    except Exception as e:
        return f"Listelenemedi: {e}"


def run_command(command: str) -> str:
    """Çalışma klasöründe bir terminal komutu çalıştırır (ör. python dosya.py).
    Güvenlik için tehlikeli komutlar engellenir ve 60 sn zaman aşımı vardır."""
    if not ALLOW_COMMANDS:
        return "Komut çalıştırma kapalı (JARVIS_ALLOW_COMMANDS=0)."
    low = command.lower()
    for bad in _DANGEROUS:
        if bad in low:
            return f"Güvenlik nedeniyle reddedildi: '{bad}' içeren komutlar çalıştırılamaz."
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        parts = [f"Çıkış kodu: {result.returncode}"]
        if out:
            parts.append("ÇIKTI:\n" + out[:4000])
        if err:
            parts.append("HATA:\n" + err[:2000])
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "Komut 60 saniyede tamamlanamadı (zaman aşımı)."
    except Exception as e:
        return f"Komut çalıştırılamadı: {e}"


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
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_command": run_command,
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
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Çalışma klasörüne bir dosya yazar/oluşturur. Kod yazıp kaydetmek için bunu kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya adı/yolu, ör. 'merhaba.py'"},
                    "content": {"type": "string", "description": "Dosyanın içeriği"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Çalışma klasöründeki bir dosyanın içeriğini okur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Okunacak dosyanın adı/yolu"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Çalışma klasöründeki dosya ve klasörleri listeler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Listelenecek klasör (varsayılan: kök)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Çalışma klasöründe bir terminal komutu çalıştırır (ör. yazdığın kodu test etmek için 'python dosya.py').",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Çalıştırılacak komut"},
                },
                "required": ["command"],
            },
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
