"""Konuşma hafızası - SQLite tabanlı basit kalıcı hafıza."""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            due_at TEXT NOT NULL,
            fired INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_message(session_id: str, role: str, content: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int = 20):
    """Son N mesajı kronolojik sırayla döndürür."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def remember_fact(key: str, value: str):
    """Kullanıcı hakkında kalıcı bir bilgi kaydeder (ör. isim, tercih)."""
    conn = _connect()
    conn.execute(
        """
        INSERT INTO facts (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """,
        (key, value, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_facts() -> dict:
    conn = _connect()
    rows = conn.execute("SELECT key, value FROM facts").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def clear_session(session_id: str):
    conn = _connect()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Notlar
# ---------------------------------------------------------------------------
def add_note(text: str) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO notes (text, created_at) VALUES (?, ?)",
        (text, datetime.utcnow().isoformat()),
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id


def list_notes() -> list:
    conn = _connect()
    rows = conn.execute("SELECT id, text FROM notes ORDER BY id").fetchall()
    conn.close()
    return [{"id": r["id"], "text": r["text"]} for r in rows]


def delete_note(note_id: int) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# Hatırlatıcılar
# ---------------------------------------------------------------------------
def add_reminder(text: str, due_at_iso: str) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO reminders (text, due_at, fired, created_at) VALUES (?, ?, 0, ?)",
        (text, due_at_iso, datetime.utcnow().isoformat()),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_reminders(include_fired: bool = False) -> list:
    conn = _connect()
    q = "SELECT id, text, due_at, fired FROM reminders"
    if not include_fired:
        q += " WHERE fired = 0"
    q += " ORDER BY due_at"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [
        {"id": r["id"], "text": r["text"], "due_at": r["due_at"], "fired": r["fired"]}
        for r in rows
    ]


def pop_due_reminders() -> list:
    """Zamanı gelmiş ve henüz tetiklenmemiş hatırlatıcıları döndürür ve işaretler."""
    now = datetime.utcnow().isoformat()
    conn = _connect()
    rows = conn.execute(
        "SELECT id, text FROM reminders WHERE fired = 0 AND due_at <= ?", (now,)
    ).fetchall()
    due = [{"id": r["id"], "text": r["text"]} for r in rows]
    if due:
        ids = [d["id"] for d in due]
        conn.execute(
            f"UPDATE reminders SET fired = 1 WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        )
        conn.commit()
    conn.close()
    return due


def cancel_reminder(reminder_id: int) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok
