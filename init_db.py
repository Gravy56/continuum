# init_db.py
import sqlite3
from datetime import datetime

DB = 'project-continuum/continuum.db'

schema = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL,
    cooldown_until TEXT
);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    nickname TEXT,
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    turn_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS state (
    k TEXT PRIMARY KEY,
    v TEXT
);
"""

def init_state(conn):
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", ("turn_number", "0"))
    cur.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", ("current_user_id", "NULL"))
    cur.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", ("turn_start", "NULL"))
    cur.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", ("current_draft", ""))
    conn.commit()

def main():
    conn = sqlite3.connect(DB)
    conn.executescript(schema)
    init_state(conn)
    conn.close()
    print("Database initialized:", DB)

if __name__ == "__main__":
    main()
