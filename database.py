import sqlite3
import secrets

DB_PATH = "api_keys.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            label TEXT DEFAULT 'default',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def create_key(label: str) -> str:
    key = f"sk-{secrets.token_urlsafe(24)}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO api_keys (key, label) VALUES (?, ?)", (key, label))
    conn.commit()
    conn.close()
    return key

def create_custom_key(custom_key: str, label: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO api_keys (key, label) VALUES (?, ?)", (custom_key, label))
        conn.commit()
        return custom_key
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_key_info(key: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM api_keys WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row

def toggle_key(key: str, active: bool):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE api_keys SET is_active = ? WHERE key = ?", (int(active), key))
    conn.commit()
    conn.close()

def list_keys():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, key, label, is_active, created_at, last_used_at FROM api_keys").fetchall()
    conn.close()
    return rows

def update_last_used(key: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE key = ?", (key,))
    conn.commit()
    conn.close()
