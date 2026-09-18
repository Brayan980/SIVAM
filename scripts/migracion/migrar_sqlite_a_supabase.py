# ============================================================
# Migración COMPLETA de SQLite (data/clinica.db) a Supabase/PostgreSQL.
#
# Crea el esquema (8 tablas) en Postgres y copia todos los datos respetando
# los IDs originales para no romper las relaciones (paciente_id, creado_por).
#
# Uso:
#   1. Poner la cadena de conexión de Supabase en la variable de entorno
#      DATABASE_URL (o en el archivo .env).
#   2. Ejecutar desde la raíz del proyecto:
#        python scripts/migracion/migrar_sqlite_a_supabase.py
#
# Es idempotente en el esquema (CREATE TABLE IF NOT EXISTS) pero NO en los
# datos: correrlo dos veces duplicaría filas. Ejecutar sobre una base vacía.
# ============================================================
import os
import sqlite3

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise SystemExit('Falta DATABASE_URL (cadena de conexión de Supabase).')

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQLITE_PATH = os.path.join(_RAIZ, 'data', 'clinica.db')

# Orden de creación/inserción respetando dependencias (FKs).
TABLAS = [
    'pacientes',
    'usuarios',
    'antropometria',
    'vo2_max',
    'test_moca',
    'test_tinetti',
    'test_chair_stand',
    'caracterizacion_socioeconomica',
]

# Esquema Postgres equivalente al de SQLite. Se usa SERIAL para los IDs, pero
# luego se resetea la secuencia para no chocar con los IDs migrados.
DDL = """
CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    nombres TEXT, apellidos TEXT, edad TEXT,
    fecha_de_nacimiento TEXT, sexo TEXT, barrio TEXT,
    antecedentes_familiares TEXT, con_quien_vives TEXT, caidas_previas TEXT,
    lesiones_musculoesqueleticas_o_cirugia TEXT,
    medicacion_y_suplementacion TEXT, medicacion_sumplementacion TEXT,
    patologia_actual TEXT,
    habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados TEXT,
    alergias TEXT, ejercicio_y_actividad_fisica_leve_moderado_intenso TEXT,
    actividad_sexual TEXT, riesgo_cardiovascular_con_riesgo_o_sin_riesgo TEXT,
    busqueda TEXT, fecha_creacion TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario TEXT UNIQUE,
    "contraseña_hash" TEXT,
    rol TEXT,
    nombre_completo TEXT,
    fecha_creacion TIMESTAMP
);

CREATE TABLE IF NOT EXISTS antropometria (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    sexo TEXT, talla REAL, peso REAL, imc REAL,
    porcentaje_grasa_corporal REAL, musculo_esqueletico REAL,
    porcentaje_grasa_visceral REAL, circunferencia_cintura REAL,
    circunferencia_cadera REAL, circunferencia_cuadriceps REAL,
    circunferencia_pantorrilla REAL, circunferencia_brazo REAL,
    fuerza_lado_derecho REAL, fuerza_lado_izquierdo REAL,
    anchura_brazo REAL, anchura_muneca REAL, anchura_rodilla REAL,
    riesgo_cardiovascular TEXT, sarcopenia TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS vo2_max (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    edad INTEGER, ta TEXT, fc TEXT, fc_max REAL, spo2 REAL, vo2_max REAL,
    resultado TEXT, observaciones TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_moca (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    visuoespacial INTEGER, denominacion INTEGER, memoria INTEGER, atencion INTEGER,
    lenguaje INTEGER, abstraccion INTEGER, orientacion INTEGER,
    puntaje_total INTEGER, nada_mental INTEGER DEFAULT 0, indice_memoria INTEGER,
    resultado TEXT, evaluador TEXT, observaciones TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_tinetti (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    eq_sentado INTEGER, eq_levanta INTEGER, eq_intenta_levantar INTEGER,
    eq_inmediato_pie INTEGER, eq_de_pie INTEGER, eq_tocado INTEGER,
    eq_ojos_cerrados INTEGER, eq_giro_pasos INTEGER, eq_giro_estabilidad INTEGER,
    eq_sentandose INTEGER,
    ma_inicio INTEGER, ma_longitud INTEGER, ma_altura INTEGER, ma_simetria INTEGER,
    ma_continuidad INTEGER, ma_trayectoria INTEGER, ma_equilibrio INTEGER,
    puntaje_equilibrio INTEGER, puntaje_marcha INTEGER, puntaje_total INTEGER,
    resultado TEXT, evaluador TEXT, observaciones TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_chair_stand (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    resultado TEXT, repeticiones INTEGER, percentil INTEGER,
    evaluador TEXT, observaciones TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS caracterizacion_socioeconomica (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    escolaridad TEXT, vivienda TEXT, con_quien_convive TEXT,
    estado_socioeconomico TEXT, fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);
"""


def _quote_ident(nombre):
    """Cita identificadores para Postgres (necesario para 'contraseña_hash')."""
    return '"' + nombre.replace('"', '""') + '"'


def migrar_tabla(sqlite_cur, pg_cur, tabla):
    sqlite_cur.execute(f'SELECT * FROM {tabla}')
    filas = sqlite_cur.fetchall()
    if not filas:
        print(f'  {tabla}: 0 filas (vacía)')
        return

    columnas = [desc[0] for desc in sqlite_cur.description]
    cols_sql = ', '.join(_quote_ident(c) for c in columnas)
    placeholders = ', '.join(['%s'] * len(columnas))
    insert = f'INSERT INTO {tabla} ({cols_sql}) VALUES ({placeholders})'

    for fila in filas:
        pg_cur.execute(insert, tuple(fila))

    print(f'  {tabla}: {len(filas)} filas migradas')


def resetear_secuencia(pg_cur, tabla):
    """Ajusta la secuencia del id para que los nuevos registros no choquen
    con los IDs ya migrados."""
    pg_cur.execute(
        f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {tabla}), 1))"
    )


def main():
    print(f'SQLite: {SQLITE_PATH}')
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cur = pg_conn.cursor()

    print('Creando esquema en Postgres/Supabase...')
    pg_cur.execute(DDL)
    pg_conn.commit()

    print('Migrando datos...')
    for tabla in TABLAS:
        migrar_tabla(sqlite_cur, pg_cur, tabla)
    pg_conn.commit()

    print('Reajustando secuencias de IDs...')
    for tabla in TABLAS:
        resetear_secuencia(pg_cur, tabla)
    pg_conn.commit()

    sqlite_conn.close()
    pg_conn.close()
    print('\nMigración completada.')


if __name__ == '__main__':
    main()
