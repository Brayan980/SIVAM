# ============================================================
# Capa de acceso a datos.
#
# - En LOCAL (sin DATABASE_URL): usa SQLite (data/clinica.db) con una capa
#   de compatibilidad que traduce la sintaxis estilo Postgres (%s, RETURNING id)
#   que usa el resto del código.
# - En PRODUCCIÓN (con DATABASE_URL, ej. Supabase): usa PostgreSQL directamente
#   vía psycopg2, sin traducción, porque el código ya está escrito para Postgres.
#
# Así el mismo código funciona en ambos entornos sin cambios.
# ============================================================
import os
import re
import sqlite3

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# Ruta a la base de datos SQLite, relativa a la raíz del proyecto.
_RAIZ = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv('SQLITE_PATH', os.path.join(_RAIZ, 'data', 'clinica.db'))


# ------------------------------------------------------------
# Capa de compatibilidad SQLite (solo para uso local)
# ------------------------------------------------------------
class _CursorCompat:
    """Envuelve un cursor de SQLite y traduce las consultas escritas
    para psycopg2 (%s -> ?, RETURNING id -> lastrowid)."""

    def __init__(self, cursor):
        self._cur = cursor
        self._returning = False

    def execute(self, query, params=None):
        q = query.replace('%s', '?')

        self._returning = False
        if re.search(r'returning\s+id', q, re.IGNORECASE):
            q = re.sub(r'\s+returning\s+id', '', q, flags=re.IGNORECASE)
            self._returning = True

        if params is None:
            self._cur.execute(q)
        else:
            self._cur.execute(q, params)
        return self

    def fetchone(self):
        if self._returning:
            self._returning = False
            return (self._cur.lastrowid,)
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def description(self):
        return self._cur.description

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    def close(self):
        self._cur.close()


class _ConexionCompat:
    """Envuelve una conexión SQLite para exponer cursor()/commit()/close()
    igual que psycopg2."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _CursorCompat(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def conectar():
    """Devuelve una conexión lista para usar.

    Si hay DATABASE_URL (producción / Supabase) -> PostgreSQL.
    Si no -> SQLite local con capa de compatibilidad.
    """
    if DATABASE_URL:
        # Import perezoso: psycopg2 solo se necesita en producción.
        import psycopg2
        return psycopg2.connect(DATABASE_URL)

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    return _ConexionCompat(conn)
