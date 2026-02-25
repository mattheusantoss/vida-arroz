"""
Banco de dados - Vida Arroz.
SQLite em arquivo (persistente). Sem MongoDB. Site e admin sempre abrem;
em caso de erro de disco, as páginas carregam sem quebrar e as receitas
voltam quando o banco estiver acessível.
"""
import os
import re
import sqlite3
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime

# Caminho do banco: use VIDAARROZ_DB_PATH para apontar para pasta sem sync (ex.: C:\\Dados\\VidaArroz\\vidaarroz.db)
_DB_DIR = os.environ.get('VIDAARROZ_DB_PATH') or os.path.join(os.path.dirname(__file__), 'data')
if os.path.isdir(_DB_DIR) or not _DB_DIR.endswith('.db'):
    DB_PATH = os.path.join(_DB_DIR, 'vidaarroz.db')
else:
    DB_PATH = _DB_DIR
_db_lock = threading.Lock()


def _get_connection():
    """Abre conexão por operação; evita conexão única que pode dar I/O error."""
    parent = os.path.dirname(DB_PATH)
    if parent:
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError:
            pass
    return sqlite3.connect(DB_PATH, timeout=15.0)


@contextmanager
def _db():
    """Context manager: abre, usa, fecha. Em erro, não propaga para não derrubar o site."""
    conn = None
    try:
        conn = _get_connection()
        yield conn
        conn.commit()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError):
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _safe_db(fn, default):
    """Executa fn() e em qualquer erro de DB retorna default (ex.: [] ou None)."""
    try:
        return fn()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError):
        return default


def slugify(text):
    if not text or not isinstance(text, str):
        return ''
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def get_db_backend():
    return 'sqlite'


def init_db():
    def _init():
        with _db_lock:
            with _db() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS leads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL, telefone TEXT NOT NULL, email TEXT NOT NULL,
                        mensagem TEXT, origem TEXT NOT NULL DEFAULT 'whatsapp', created_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
                        nome TEXT, email TEXT, ativo INTEGER DEFAULT 1, permissao TEXT DEFAULT 'editor', created_at TEXT NOT NULL
                    )
                """)
                # Migração: adicionar colunas em tabelas antigas que não as têm
                cur = conn.execute("PRAGMA table_info(admin_users)")
                cols = [row[1] for row in cur.fetchall()]
                if 'nome' not in cols:
                    conn.execute("ALTER TABLE admin_users ADD COLUMN nome TEXT")
                if 'email' not in cols:
                    conn.execute("ALTER TABLE admin_users ADD COLUMN email TEXT")
                if 'ativo' not in cols:
                    conn.execute("ALTER TABLE admin_users ADD COLUMN ativo INTEGER DEFAULT 1")
                if 'permissao' not in cols:
                    conn.execute("ALTER TABLE admin_users ADD COLUMN permissao TEXT DEFAULT 'editor'")
                    conn.execute("UPDATE admin_users SET permissao = 'admin' WHERE permissao IS NULL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS receitas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        titulo TEXT NOT NULL,
                        slug TEXT,
                        ingredientes TEXT,
                        conteudo TEXT,
                        modo_preparo TEXT,
                        imagem_destaque TEXT,
                        video_url TEXT,
                        video_arquivo TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                cur = conn.execute("PRAGMA table_info(receitas)")
                cols = [row[1] for row in cur.fetchall()]
                if 'slug' not in cols:
                    conn.execute("ALTER TABLE receitas ADD COLUMN slug TEXT")
    _safe_db(_init, None)


def insert_lead(nome, telefone, email, mensagem='', origem='whatsapp'):
    def _insert():
        with _db_lock:
            with _db() as conn:
                cur = conn.execute(
                    "INSERT INTO leads (nome, telefone, email, mensagem, origem, created_at) VALUES (?,?,?,?,?,?)",
                    (nome, telefone, email, mensagem or '', origem or 'whatsapp', datetime.utcnow().isoformat())
                )
                return cur.lastrowid
    return _safe_db(_insert, None)


def get_all_leads():
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, nome, telefone, email, mensagem, origem, created_at FROM leads ORDER BY created_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]
    return _safe_db(_get, [])


def count_receitas_por_mes(ano, mes):
    """Quantidade de receitas publicadas no mês (created_at no formato ISO/YYYY-MM-DD...)."""
    def _count():
        with _db() as conn:
            prefixo = f"{int(ano):04d}-{int(mes):02d}-"
            cur = conn.execute("SELECT COUNT(*) FROM receitas WHERE created_at LIKE ?", (prefixo + "%",))
            return cur.fetchone()[0] or 0
    return _safe_db(_count, 0)


def count_leads_por_mes(ano, mes):
    """Quantidade de leads convertidos no mês (created_at no formato ISO/YYYY-MM-DD...)."""
    def _count():
        with _db() as conn:
            prefixo = f"{int(ano):04d}-{int(mes):02d}-"
            cur = conn.execute("SELECT COUNT(*) FROM leads WHERE created_at LIKE ?", (prefixo + "%",))
            return cur.fetchone()[0] or 0
    return _safe_db(_count, 0)


def get_admin_by_username(username):
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, username, password_hash, nome, email, ativo, permissao FROM admin_users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    return _safe_db(_get, None)


def create_admin_if_empty(username, password_hash):
    def _create():
        with _db_lock:
            with _db() as conn:
                cur = conn.execute("SELECT 1 FROM admin_users LIMIT 1")
                if cur.fetchone() is None:
                    conn.execute(
                        "INSERT INTO admin_users (username, password_hash, nome, ativo, permissao, created_at) VALUES (?,?,?,1,'admin',?)",
                        (username, password_hash, username, datetime.utcnow().isoformat())
                    )
    _safe_db(_create, None)


def get_all_admin_users():
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, username, password_hash, nome, email, ativo, permissao, created_at FROM admin_users ORDER BY id"
            )
            return [dict(row) for row in cur.fetchall()]
    return _safe_db(_get, [])


def insert_admin_user(username, password_hash, nome=None, email=None, ativo=1, permissao='editor'):
    def _insert():
        with _db_lock:
            with _db() as conn:
                role = (permissao or 'editor').lower()
                if role not in ('admin', 'editor', 'visualizador'):
                    role = 'editor'
                cur = conn.execute(
                    """INSERT INTO admin_users (username, password_hash, nome, email, ativo, permissao, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (username, password_hash, nome or username, email or '', 1 if ativo else 0, role, datetime.utcnow().isoformat())
                )
                return cur.lastrowid
    return _safe_db(_insert, None)


def update_admin_user(user_id, nome=None, email=None, ativo=None, permissao=None):
    def _update():
        with _db_lock:
            with _db() as conn:
                updates, params = [], []
                if nome is not None:
                    updates.append("nome = ?")
                    params.append(nome)
                if email is not None:
                    updates.append("email = ?")
                    params.append(email)
                if ativo is not None:
                    updates.append("ativo = ?")
                    params.append(1 if ativo else 0)
                if permissao is not None:
                    role = (permissao or 'editor').lower()
                    if role not in ('admin', 'editor', 'visualizador'):
                        role = 'editor'
                    updates.append("permissao = ?")
                    params.append(role)
                if not updates:
                    return True
                params.append(user_id)
                conn.execute(
                    "UPDATE admin_users SET " + ", ".join(updates) + " WHERE id = ?",
                    params
                )
                return True
    return _safe_db(_update, False)


def set_admin_ativo(user_id, ativo):
    def _set():
        with _db_lock:
            with _db() as conn:
                conn.execute("UPDATE admin_users SET ativo = ? WHERE id = ?", (1 if ativo else 0, user_id))
                return True
    return _safe_db(_set, False)


def delete_admin_user(user_id):
    """Remove usuário. Retorna True se removeu, False se falhou ou se é o último usuário."""

    def _delete():
        with _db_lock:
            with _db() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM admin_users")
                n = cur.fetchone()[0]
                if n <= 1:
                    return False
                cur = conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
                return cur.rowcount > 0
    return _safe_db(_delete, False)


def _row_to_receita(row):
    d = dict(row)
    d['created_at'] = d.get('created_at') or ''
    return d


def get_all_receitas():
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, titulo, slug, ingredientes, conteudo, modo_preparo, imagem_destaque, video_url, video_arquivo, created_at FROM receitas ORDER BY created_at DESC"
            )
            return [_row_to_receita(row) for row in cur.fetchall()]
    return _safe_db(_get, [])


def get_receita_by_slug(slug):
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, titulo, slug, ingredientes, conteudo, modo_preparo, imagem_destaque, video_url, video_arquivo, created_at FROM receitas WHERE slug = ?",
                (slug,)
            )
            row = cur.fetchone()
            return _row_to_receita(row) if row else None
    return _safe_db(_get, None)


def get_receita_by_id(receita_id):
    def _get():
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, titulo, slug, ingredientes, conteudo, modo_preparo, imagem_destaque, video_url, video_arquivo, created_at FROM receitas WHERE id = ?",
                (receita_id,)
            )
            row = cur.fetchone()
            return _row_to_receita(row) if row else None
    return _safe_db(_get, None)


def _slug_unique(conn, slug_base, exclude_id=None):
    slug = (slug_base or 'receita').strip('-') or 'receita'
    candidate = slug
    n = 1
    while True:
        if exclude_id is not None:
            cur = conn.execute("SELECT 1 FROM receitas WHERE slug = ? AND id != ?", (candidate, exclude_id))
        else:
            cur = conn.execute("SELECT 1 FROM receitas WHERE slug = ?", (candidate,))
        if cur.fetchone() is None:
            return candidate
        n += 1
        candidate = f"{slug}-{n}"


def insert_receita(titulo, ingredientes, conteudo, modo_preparo, imagem_destaque=None, video_url=None, video_arquivo=None, created_at=None):
    """Inserir receita. created_at opcional (para migração); se omitido usa agora."""
    def _insert():
        with _db_lock:
            with _db() as conn:
                slug = _slug_unique(conn, slugify(titulo))
                if created_at is not None:
                    when = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
                else:
                    when = datetime.utcnow().isoformat()
                cur = conn.execute(
                    "INSERT INTO receitas (titulo, slug, ingredientes, conteudo, modo_preparo, imagem_destaque, video_url, video_arquivo, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (titulo or '', slug, ingredientes or '', conteudo or '', modo_preparo or '', imagem_destaque or '', video_url or '', video_arquivo or '', when)
                )
                return cur.lastrowid
    return _safe_db(_insert, None)


def update_receita(receita_id, titulo, ingredientes, conteudo, modo_preparo, imagem_destaque=None, video_url=None, video_arquivo=None):
    def _update():
        with _db_lock:
            with _db() as conn:
                slug = _slug_unique(conn, slugify(titulo), exclude_id=receita_id)
                cur = conn.execute(
                    """UPDATE receitas SET titulo=?, slug=?, ingredientes=?, conteudo=?, modo_preparo=?,
                       imagem_destaque=?, video_url=?, video_arquivo=? WHERE id=?""",
                    (titulo, slug, ingredientes, conteudo, modo_preparo, imagem_destaque, video_url, video_arquivo, receita_id)
                )
                return cur.rowcount > 0
    return _safe_db(_update, False)
