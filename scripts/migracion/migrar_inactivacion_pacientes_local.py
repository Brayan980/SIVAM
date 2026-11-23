"""Agrega inactivación reversible a SQLite sin alterar pacientes existentes.

El script crea primero un respaldo fechado en data/backups. Es idempotente:
puede ejecutarse de nuevo sin duplicar columnas ni modificar registros.
"""
import os
import shutil
import sqlite3
from datetime import datetime


RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(RAIZ, 'data', 'clinica.db')
CARPETA_BACKUPS = os.path.join(RAIZ, 'data', 'backups')


def migrar():
    if not os.path.exists(DB):
        raise SystemExit(f'No se encontró la base local: {DB}')

    os.makedirs(CARPETA_BACKUPS, exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    respaldo = os.path.join(CARPETA_BACKUPS, f'clinica_pre_inactivacion_{marca}.db')
    shutil.copy2(DB, respaldo)

    conn = sqlite3.connect(DB, timeout=15)
    try:
        conn.execute('PRAGMA busy_timeout = 15000')
        cur = conn.cursor()
        existentes = {fila[1] for fila in cur.execute('PRAGMA table_info(pacientes)')}
        columnas = (
            ('activo', 'INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))'),
            ('fecha_inactivacion', 'TEXT'),
            ('inactivado_por', 'INTEGER REFERENCES usuarios(id)'),
            ('fecha_reactivacion', 'TEXT'),
            ('reactivado_por', 'INTEGER REFERENCES usuarios(id)'),
        )
        agregadas = []
        for nombre, definicion in columnas:
            if nombre not in existentes:
                cur.execute(f'ALTER TABLE pacientes ADD COLUMN {nombre} {definicion}')
                agregadas.append(nombre)
        cur.execute('CREATE INDEX IF NOT EXISTS idx_pacientes_activo ON pacientes(activo)')
        conn.commit()
    finally:
        conn.close()

    resultado = ', '.join(agregadas) if agregadas else 'ninguna; el esquema ya estaba actualizado'
    print(f'Respaldo creado: {respaldo}')
    print(f'Migración de inactivación aplicada: {resultado}')


if __name__ == '__main__':
    migrar()
