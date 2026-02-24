"""
Banco de dados SQLite para leads e admin.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'vidaarroz.db')


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Cria as tabelas se não existirem."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                email TEXT NOT NULL,
                mensagem TEXT,
                origem TEXT NOT NULL DEFAULT 'whatsapp',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def insert_lead(nome, telefone, email, mensagem='', origem='whatsapp'):
    """Insere um lead e retorna o id."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO leads (nome, telefone, email, mensagem, origem, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, telefone, email, mensagem or '', origem, datetime.utcnow().isoformat())
        )
        conn.commit()
        return cur.lastrowid


def get_all_leads():
    """Retorna todos os leads ordenados do mais recente."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, nome, telefone, email, mensagem, origem, created_at FROM leads ORDER BY created_at DESC"
        )
        return [dict(row) for row in cur.fetchall()]


def get_admin_by_username(username):
    """Retorna o admin pelo username ou None."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT id, username, password_hash FROM admin_users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_admin_if_empty(username, password_hash):
    """Cria o usuário admin padrão se não existir nenhum."""
    with get_connection() as conn:
        cur = conn.execute("SELECT 1 FROM admin_users LIMIT 1")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, datetime.utcnow().isoformat())
            )
            conn.commit()
