"""app/db.py"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

def _url():
    try:
        from dotenv import load_dotenv; load_dotenv()
    except ImportError: pass
    return os.getenv("DATABASE_URL",
                     "postgresql://postgres:admin@localhost:5432/rshu_ai")

def get_connection():
    try: return psycopg2.connect(_url(), connect_timeout=5)
    except psycopg2.OperationalError as exc:
        raise ConnectionError(f"DB tidak bisa dijangkau: {exc}") from exc

@contextmanager
def get_cursor(dict_cursor=True):
    conn = get_connection()
    try:
        cf = RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=cf) as cur:
            yield conn, cur
        conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()

def check_connection():
    try: get_connection().close(); return True
    except Exception: return False
