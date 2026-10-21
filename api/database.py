import os
import sqlite3
from pathlib import Path

import hashlib
import secrets
import time

DB_PATH = Path(os.getenv("SPARK_DB_PATH", Path(__file__).resolve().parent.parent / "spark_ai.db"))

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS syllabi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
                CREATE TABLE IF NOT EXISTS login_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

def create_login_session(user_id, days=30):
    """Create a persistent login session."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = int(time.time()) + days * 24 * 60 * 60

    db = connect()
    try:
        db.execute(
            """
            INSERT INTO login_sessions
            (token_hash, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (token_hash, user_id, expires_at)
        )
        db.commit()
    finally:
        db.close()

    return token


def get_login_session_user(token):
    """Find a user with a valid login session."""
    if not token:
        return None

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    db = connect()
    try:
        row = db.execute(
            """
            SELECT users.id, users.name, users.email
            FROM login_sessions
            JOIN users ON users.id = login_sessions.user_id
            WHERE login_sessions.token_hash = ?
              AND login_sessions.expires_at > ?
            """,
            (token_hash, int(time.time()))
        ).fetchone()
    finally:
        db.close()

    return dict(row) if row else None


def delete_login_session(token):
    """Delete a login session during logout."""
    if not token:
        return

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    db = connect()
    try:
        db.execute(
            "DELETE FROM login_sessions WHERE token_hash = ?",
            (token_hash,)
        )
        db.commit()
    finally:
        db.close()