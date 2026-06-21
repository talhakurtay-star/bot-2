"""Jarvis araçları (tools) - sistem kontrolü, web arama, zaman, hafıza.

Bu fonksiyonlar Ollama'nın tool-calling özelliği ile çağrılır.
Her fonksiyon basit tipler alır ve string sonuç döndürür.
"""
import os
import re
import ast
import sys
import ssl
import smtplib
import platform
import subprocess
import shutil
import operator
import webbrowser
import urllib.parse
from email.message import EmailMessage
from datetime import datetime, timedelta
from pathlib import Path

import requests
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
# Web sayfası okuma
# ---------------------------------------------------------------------------
def web_fetch(url: str) -> str:
    """Bir web sayfasının metin içeriğini getirir (özetlemek/okumak için)."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 Jarvis"})
        resp.raise_for_status()
        html = resp.text
        # script/style at, etiketleri temizle, boşlukları sadeleştir
        html = re.sub(r"(?is)<(script|style|head|nav|footer)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return "Sayfada okunabilir metin bulunamadı."
        return text[:4000] + ("\n... (kısaltıldı)" if len(text) > 4000 else "")
    except Exception as e:
        return f"Sayfa getirilemedi: {e}"


# ---------------------------------------------------------------------------
# Güvenli hesap makinesi
# ---------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Geçersiz ifade")


def calculate(expression: str) -> str:
    """Matematiksel bir ifadeyi güvenle hesaplar (ör. '12*(3+4)/2')."""
    try:
        result = _eval_node(ast.parse(expression, mode="eval").body)
        return f"{expression} = {result}"
    except Exception:
        return "Bu ifadeyi hesaplayamadım."


# ---------------------------------------------------------------------------
# Sistem bilgisi
# ---------------------------------------------------------------------------
def system_info() -> str:
    """İşletim sistemi, CPU, RAM, disk ve batarya durumunu döndürür."""
    parts = [f"İşletim sistemi: {platform.system()} {platform.release()}"]
    parts.append(f"CPU çekirdek: {os.cpu_count()}")
    try:
        total, used, free = shutil.disk_usage("/")
        gb = 1024 ** 3
        parts.append(f"Disk: {free // gb} GB boş / {total // gb} GB toplam")
    except Exception:
        pass
    try:
        import psutil
        vm = psutil.virtual_memory()
        gb = 1024 ** 3
        parts.append(f"RAM: {vm.available // gb} GB boş / {vm.total // gb} GB toplam (%{vm.percent} dolu)")
        bat = psutil.sensors_battery()
        if bat is not None:
            durum = "şarjda" if bat.power_plugged else "bataryada"
            parts.append(f"Batarya: %{int(bat.percent)} ({durum})")
    except Exception:
        pass
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Notlar
# ---------------------------------------------------------------------------
def add_note(text: str) -> str:
    """Bir not kaydeder."""
    nid = memory.add_note(text)
    return f"Not eklendi (#{nid}): {text}"


def list_notes() -> str:
    """Kayıtlı tüm notları listeler."""
    notes = memory.list_notes()
    if not notes:
        return "Hiç not yok."
    return "\n".join(f"#{n['id']}: {n['text']}" for n in notes)


def delete_note(note_id: int) -> str:
    """Numarasına göre bir notu siler."""
    return "Not silindi." if memory.delete_note(int(note_id)) else "O numarada not yok."


# ---------------------------------------------------------------------------
# Hatırlatıcılar
# ---------------------------------------------------------------------------
def set_reminder(minutes: float, text: str) -> str:
    """Belirtilen dakika sonrası için bir hatırlatıcı kurar."""
    due = datetime.utcnow() + timedelta(minutes=float(minutes))
    rid = memory.add_reminder(text, due.isoformat())
    return f"Tamam efendim, {minutes} dakika sonra hatırlatacağım: {text} (#{rid})"


def list_reminders() -> str:
    """Bekleyen hatırlatıcıları listeler."""
    rems = memory.list_reminders()
    if not rems:
        return "Bekleyen hatırlatıcı yok."
    out = []
    for r in rems:
        try:
            local = datetime.fromisoformat(r["due_at"])
            when = local.strftime("%H:%M")
        except Exception:
            when = r["due_at"]
        out.append(f"#{r['id']} ({when} UTC): {r['text']}")
    return "\n".join(out)


def cancel_reminder(reminder_id: int) -> str:
    """Numarasına göre bir hatırlatıcıyı iptal eder."""
    return "Hatırlatıcı iptal edildi." if memory.cancel_reminder(int(reminder_id)) else "O numarada hatırlatıcı yok."


# ---------------------------------------------------------------------------
# Müzik / medya kontrolü
# ---------------------------------------------------------------------------
def play_music(query: str) -> str:
    """Bir şarkı/sanatçıyı YouTube'da arar ve tarayıcıda açar."""
    q = urllib.parse.quote(query)
    webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
    return f"YouTube'da '{query}' açıldı."


def media_control(action: str) -> str:
    """Medya oynatıcıyı kontrol eder: play, pause, next, previous, stop."""
    action = action.strip().lower()
    osname = platform.system().lower()
    try:
        if osname == "linux":
            if shutil.which("playerctl") is None:
                return "Medya kontrolü için 'playerctl' kurulu değil."
            cmd = {"play": "play", "pause": "pause", "stop": "stop",
                   "next": "next", "previous": "previous"}.get(action, "play-pause")
            subprocess.run(["playerctl", cmd], check=False)
        elif osname == "darwin":
            app_action = {"play": "play", "pause": "pause", "stop": "pause",
                          "next": "next track", "previous": "previous track"}.get(action, "playpause")
            subprocess.run(["osascript", "-e",
                            f'tell application "Spotify" to {app_action}'], check=False)
        elif osname == "windows":
            keys = {"play": 0xB3, "pause": 0xB3, "next": 0xB0,
                    "previous": 0xB1, "stop": 0xB2}.get(action, 0xB3)
            ps = (
                "$c='[DllImport(\"user32.dll\")]public static extern void keybd_event"
                "(byte b,byte s,uint f,int e);';"
                "$t=Add-Type -MemberDefinition $c -Name K -PassThru;"
                f"$t::keybd_event({keys},0,0,0);$t::keybd_event({keys},0,2,0)"
            )
            subprocess.run(["powershell", "-Command", ps], check=False)
        return f"Medya: {action}"
    except Exception as e:
        return f"Medya kontrolü başarısız: {e}"


# ---------------------------------------------------------------------------
# E-posta (SMTP/IMAP - ortam değişkenleriyle yapılandırılır)
# ---------------------------------------------------------------------------
def send_email(to: str, subject: str, body: str) -> str:
    """Bir e-posta gönderir. SMTP ayarları ortam değişkenlerinden okunur."""
    host = os.environ.get("JARVIS_SMTP_HOST")
    user = os.environ.get("JARVIS_SMTP_USER")
    password = os.environ.get("JARVIS_SMTP_PASS")
    port = int(os.environ.get("JARVIS_SMTP_PORT", "465"))
    sender = os.environ.get("JARVIS_SMTP_FROM", user or "")
    if not (host and user and password):
        return "E-posta ayarlı değil (JARVIS_SMTP_HOST/USER/PASS gerekli)."
    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx) as server:
            server.login(user, password)
            server.send_message(msg)
        return f"E-posta gönderildi: {to}"
    except Exception as e:
        return f"E-posta gönderilemedi: {e}"


def get_unread_emails(limit: int = 5) -> str:
    """Okunmamış e-postaların başlıklarını getirir. IMAP ayarları ortamdan okunur."""
    import imaplib
    import email as email_lib
    host = os.environ.get("JARVIS_IMAP_HOST")
    user = os.environ.get("JARVIS_SMTP_USER")
    password = os.environ.get("JARVIS_SMTP_PASS")
    if not (host and user and password):
        return "E-posta okuma ayarlı değil (JARVIS_IMAP_HOST gerekli)."
    try:
        with imaplib.IMAP4_SSL(host) as m:
            m.login(user, password)
            m.select("INBOX")
            _, data = m.search(None, "UNSEEN")
            ids = data[0].split()[-int(limit):]
            if not ids:
                return "Okunmamış e-posta yok."
            out = []
            for i in reversed(ids):
                _, msg_data = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
                hdr = email_lib.message_from_bytes(msg_data[0][1])
                out.append(f"- {hdr.get('From','?')}: {hdr.get('Subject','(konu yok)')}")
            return "\n".join(out)
    except Exception as e:
        return f"E-posta okunamadı: {e}"


# ---------------------------------------------------------------------------
# Takvim
# ---------------------------------------------------------------------------
def add_event(title: str, when: str) -> str:
    """Takvime etkinlik ekler. 'when' ISO 8601 biçiminde olmalı (ör. 2026-06-22T15:00)."""
    eid = memory.add_event(title, when)
    return f"Etkinlik eklendi (#{eid}): {title} - {when}"


def list_events() -> str:
    """Yaklaşan takvim etkinliklerini listeler."""
    events = memory.list_events(upcoming_only=True)
    if not events:
        return "Yaklaşan etkinlik yok."
    out = []
    for e in events:
        try:
            when = datetime.fromisoformat(e["when_at"]).strftime("%d.%m %H:%M")
        except Exception:
            when = e["when_at"]
        out.append(f"#{e['id']} {when}: {e['title']}")
    return "\n".join(out)


def delete_event(event_id: int) -> str:
    """Numarasına göre bir etkinliği siler."""
    return "Etkinlik silindi." if memory.delete_event(int(event_id)) else "O numarada etkinlik yok."


# ---------------------------------------------------------------------------
# Hava durumu (wttr.in - ücretsiz, anahtar gerekmez)
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    """Bir şehrin güncel hava durumunu döndürür."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%l:+%C+%t+(hissedilen+%f),+nem+%h,+r%C3%BCzgar+%w&lang=tr"
        resp = requests.get(url, timeout=12, headers={"User-Agent": "curl/8"})
        resp.raise_for_status()
        text = resp.text.strip()
        return text if text and "Unknown" not in text else f"'{city}' için hava durumu bulunamadı."
    except Exception as e:
        return f"Hava durumu alınamadı: {e}"


# ---------------------------------------------------------------------------
# Akıllı ev - Philips Hue (ortam değişkenleriyle yapılandırılır)
# ---------------------------------------------------------------------------
def hue_lights(action: str, brightness: int = None) -> str:
    """Philips Hue ışıklarını kontrol eder: on, off veya parlaklık (0-100)."""
    bridge = os.environ.get("JARVIS_HUE_BRIDGE")
    key = os.environ.get("JARVIS_HUE_KEY")
    if not (bridge and key):
        return "Akıllı ev ayarlı değil (JARVIS_HUE_BRIDGE ve JARVIS_HUE_KEY gerekli)."
    body = {}
    action = (action or "").strip().lower()
    if action == "on":
        body["on"] = True
    elif action == "off":
        body["on"] = False
    if brightness is not None:
        body["on"] = True
        body["bri"] = max(1, min(254, int(int(brightness) * 254 / 100)))
    if not body:
        return "Geçersiz işlem. 'on', 'off' veya parlaklık ver."
    try:
        url = f"http://{bridge}/api/{key}/groups/0/action"
        requests.put(url, json=body, timeout=8)
        return f"Işıklar: {action}" + (f" %{brightness}" if brightness is not None else "")
    except Exception as e:
        return f"Işıklar kontrol edilemedi: {e}"


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
    "web_fetch": web_fetch,
    "calculate": calculate,
    "system_info": system_info,
    "add_note": add_note,
    "list_notes": list_notes,
    "delete_note": delete_note,
    "set_reminder": set_reminder,
    "list_reminders": list_reminders,
    "cancel_reminder": cancel_reminder,
    "play_music": play_music,
    "media_control": media_control,
    "send_email": send_email,
    "get_unread_emails": get_unread_emails,
    "add_event": add_event,
    "list_events": list_events,
    "delete_event": delete_event,
    "get_weather": get_weather,
    "hue_lights": hue_lights,
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
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Belirli bir web sayfasının metin içeriğini getirir; bir makaleyi/sayfayı okuyup özetlemek için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Okunacak sayfanın adresi"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Matematiksel bir ifadeyi hesaplar (ör. '12*(3+4)/2').",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Hesaplanacak ifade"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Bilgisayarın durumunu döndürür: işletim sistemi, CPU, RAM, disk, batarya.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Kullanıcının istediği bir notu kaydeder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Not içeriği"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Kayıtlı tüm notları listeler.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_note",
            "description": "Numarasına göre bir notu siler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "Silinecek notun numarası"},
                },
                "required": ["note_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Belirtilen dakika sonrası için bir hatırlatıcı kurar (ör. 10 dakika sonra).",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "number", "description": "Kaç dakika sonra"},
                    "text": {"type": "string", "description": "Hatırlatma metni"},
                },
                "required": ["minutes", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "Bekleyen hatırlatıcıları listeler.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "Numarasına göre bir hatırlatıcıyı iptal eder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer", "description": "İptal edilecek hatırlatıcının numarası"},
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Bir şarkı veya sanatçıyı YouTube'da arayıp çalar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Şarkı/sanatçı adı"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Çalan medyayı kontrol eder: play, pause, next, previous, stop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "play, pause, next, previous veya stop"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Bir e-posta gönderir (SMTP ayarları yapılandırılmışsa).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Alıcı e-posta adresi"},
                    "subject": {"type": "string", "description": "Konu"},
                    "body": {"type": "string", "description": "E-posta metni"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_unread_emails",
            "description": "Okunmamış e-postaların başlıklarını getirir (IMAP yapılandırılmışsa).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Kaç e-posta gösterilsin"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_event",
            "description": "Takvime etkinlik ekler. when alanı ISO 8601 olmalı (ör. 2026-06-22T15:00).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Etkinlik başlığı"},
                    "when": {"type": "string", "description": "ISO 8601 tarih-saat"},
                },
                "required": ["title", "when"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "Yaklaşan takvim etkinliklerini listeler.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Numarasına göre bir takvim etkinliğini siler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Silinecek etkinliğin numarası"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Bir şehrin güncel hava durumunu döndürür.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Şehir adı"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hue_lights",
            "description": "Akıllı ev ışıklarını (Philips Hue) açar, kapatır veya parlaklığını ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "on, off"},
                    "brightness": {"type": "integer", "description": "0-100 parlaklık (opsiyonel)"},
                },
                "required": ["action"],
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
