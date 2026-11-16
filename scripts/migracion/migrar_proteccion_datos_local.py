"""Añade protección de datos a una base SQLite local existente sin borrar datos."""
import os
import sqlite3

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(RAIZ, 'data', 'clinica.db')

conn = sqlite3.connect(DB)
cur = conn.cursor()
existentes = {fila[1] for fila in cur.execute('PRAGMA table_info(pacientes)')}
for nombre, definicion in (
    ('autoriza_tratamiento_datos', 'INTEGER CHECK (autoriza_tratamiento_datos IN (0, 1))'),
    ('fecha_autorizacion', 'TEXT'),
    ('version_politica', 'TEXT'),
    ('texto_autorizacion_aceptado', 'TEXT'),
):
    if nombre not in existentes:
        cur.execute(f'ALTER TABLE pacientes ADD COLUMN {nombre} {definicion}')

cur.executescript('''
CREATE TABLE IF NOT EXISTS consentimientos_tratamiento_datos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    autoriza_tratamiento_datos INTEGER NOT NULL CHECK (autoriza_tratamiento_datos = 1),
    fecha_autorizacion TEXT NOT NULL,
    version_politica TEXT NOT NULL,
    texto_autorizacion_aceptado TEXT NOT NULL,
    registrado_por INTEGER REFERENCES usuarios(id),
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS consentimientos_solo_insercion_actualizar
BEFORE UPDATE ON consentimientos_tratamiento_datos
BEGIN SELECT RAISE(ABORT, 'La evidencia de consentimiento no puede modificarse'); END;
CREATE TRIGGER IF NOT EXISTS consentimientos_solo_insercion_eliminar
BEFORE DELETE ON consentimientos_tratamiento_datos
BEGIN SELECT RAISE(ABORT, 'La evidencia de consentimiento no puede eliminarse'); END;
''')
conn.commit()
conn.close()
print(f'Migración aplicada sin modificar pacientes históricos: {DB}')
