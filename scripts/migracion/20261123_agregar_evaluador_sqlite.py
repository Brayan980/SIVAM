"""Añade ``evaluador`` a las tablas locales existentes de SIVAM.

Ejecutar una sola vez en desarrollo local:
    python scripts/migracion/20261123_agregar_evaluador_sqlite.py
"""
import sqlite3

from db import DB_PATH


TABLAS = ('antropometria', 'vo2_max', 'caracterizacion_socioeconomica')


def main():
    conexion = sqlite3.connect(DB_PATH)
    try:
        for tabla in TABLAS:
            columnas = {fila[1] for fila in conexion.execute(f'PRAGMA table_info({tabla})')}
            if 'evaluador' not in columnas:
                conexion.execute(f'ALTER TABLE {tabla} ADD COLUMN evaluador TEXT')
                print(f'{tabla}: columna evaluador agregada')
            else:
                print(f'{tabla}: columna evaluador ya existe')
        conexion.commit()
    finally:
        conexion.close()


if __name__ == '__main__':
    main()
