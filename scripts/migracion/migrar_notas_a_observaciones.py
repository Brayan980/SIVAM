# ============================================================
# Migración: renombrar la columna 'notas' -> 'observaciones' en las
# tablas test_moca, test_tinetti y test_chair_stand, para que las 4
# tablas de test usen el mismo nombre que vo2_max ('observaciones').
#
# Es idempotente: si la columna ya se llama 'observaciones', la salta.
# Hace un backup de la BD antes de tocar nada.
# ============================================================
import sqlite3
import shutil
import time
import os

DB_PATH = 'clinica.db'
TABLAS = ['test_moca', 'test_tinetti', 'test_chair_stand']


def _columnas(cur, tabla):
    return [r[1] for r in cur.execute(f'PRAGMA table_info({tabla})').fetchall()]


def migrar():
    if not os.path.exists(DB_PATH):
        print(f'No se encontró {DB_PATH}, nada que migrar.')
        return

    # Backup por seguridad
    backup = f'clinica_backup_notas_{int(time.time())}.db'
    shutil.copyfile(DB_PATH, backup)
    print(f'Backup creado: {backup}')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for tabla in TABLAS:
        cols = _columnas(cur, tabla)
        if 'observaciones' in cols:
            print(f'[{tabla}] ya tiene columna "observaciones", se omite.')
            continue
        if 'notas' not in cols:
            print(f'[{tabla}] no tiene columna "notas" ni "observaciones" (?), se omite.')
            continue
        # SQLite 3.25+ soporta RENAME COLUMN
        cur.execute(f'ALTER TABLE {tabla} RENAME COLUMN notas TO observaciones')
        print(f'[{tabla}] columna "notas" renombrada a "observaciones".')

    conn.commit()
    conn.close()
    print('Migración completada.')


if __name__ == '__main__':
    migrar()
