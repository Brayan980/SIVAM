import sqlite3
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Conectar a SQLite
sqlite_conn = sqlite3.connect('clinica.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Conectar a PostgreSQL
postgres_conn = psycopg2.connect(DATABASE_URL)
postgres_cursor = postgres_conn.cursor()

print("Conectado a SQLite y PostgreSQL")

# Obtener estructura de SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tablas_sqlite = [row[0] for row in sqlite_cursor.fetchall()]
print(f"Tablas en SQLite: {tablas_sqlite}")

# Migrar tabla pacientes
print("\nMigrando tabla pacientes...")
sqlite_cursor.execute("PRAGMA table_info(pacientes)")
columnas_pacientes = sqlite_cursor.fetchall()
print(f"Columnas de pacientes: {[col[1] for col in columnas_pacientes]}")

# Crear tabla pacientes en PostgreSQL
crear_pacientes = sql.SQL("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id SERIAL PRIMARY KEY,
        nombres TEXT,
        apellidos TEXT,
        edad INTEGER,
        fecha_de_nacimiento DATE,
        sexo TEXT,
        barrio TEXT,
        antecedentes_familiares TEXT,
        con_quien_vives TEXT,
        caidas_previas TEXT,
        lesiones_musculoesqueleticas_o_cirugia TEXT,
        medicacion_y_suplementacion TEXT,
        medicacion_sumplementacion TEXT,
        patologia_actual TEXT,
        habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados TEXT,
        alergias TEXT,
        ejercicio_y_actividad_fisica_leve_moderado_intenso TEXT,
        actividad_sexual TEXT,
        riesgo_cardiovascular_con_riesgo_o_sin_riesgo TEXT,
        busqueda TEXT
    )
""")
postgres_cursor.execute(crear_pacientes)
postgres_conn.commit()

# Migrar datos de pacientes
sqlite_cursor.execute("SELECT * FROM pacientes")
filas_pacientes = sqlite_cursor.fetchall()
print(f"Migrando {len(filas_pacientes)} pacientes...")

insertar_paciente = sql.SQL("""
    INSERT INTO pacientes (nombres, apellidos, edad, fecha_de_nacimiento, sexo, barrio,
    antecedentes_familiares, con_quien_vives, caidas_previas, lesiones_musculoesqueleticas_o_cirugia,
    medicacion_y_suplementacion, medicacion_sumplementacion, patologia_actual,
    habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados, alergias,
    ejercicio_y_actividad_fisica_leve_moderado_intenso, actividad_sexual,
    riesgo_cardiovascular_con_riesgo_o_sin_riesgo, busqueda)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""")

for fila in filas_pacientes:
    paciente_dict = dict(fila)

    # Convertir edad a entero si viene como float
    edad = paciente_dict.get('edad')
    if edad:
        try:
            edad = int(float(edad)) if edad else None
        except (ValueError, TypeError):
            edad = None

    valores = (
        paciente_dict.get('nombres'),
        paciente_dict.get('apellidos'),
        edad,
        paciente_dict.get('fecha_de_nacimiento'),
        paciente_dict.get('sexo'),
        paciente_dict.get('barrio'),
        paciente_dict.get('antecedentes_familiares'),
        paciente_dict.get('con_quien_vives'),
        paciente_dict.get('caidas_previas'),
        paciente_dict.get('lesiones_musculoesqueleticas_o_cirugia'),
        paciente_dict.get('medicacion_y_suplementacion'),
        paciente_dict.get('medicacion_sumplementacion'),
        paciente_dict.get('patologia_actual'),
        paciente_dict.get('habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados'),
        paciente_dict.get('alergias'),
        paciente_dict.get('ejercicio_y_actividad_fisica_leve_moderado_intenso'),
        paciente_dict.get('actividad_sexual'),
        paciente_dict.get('riesgo_cardiovascular_con_riesgo_o_sin_riesgo'),
        paciente_dict.get('busqueda')
    )
    postgres_cursor.execute(insertar_paciente, valores)

postgres_conn.commit()
print(f"Pacientes migrados: {len(filas_pacientes)}")

# Migrar tabla usuarios
print("\nMigrando tabla usuarios...")
crear_usuarios = sql.SQL("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario TEXT UNIQUE,
        contraseña_hash TEXT,
        rol TEXT
    )
""")
postgres_cursor.execute(crear_usuarios)
postgres_conn.commit()

sqlite_cursor.execute("SELECT * FROM usuarios")
filas_usuarios = sqlite_cursor.fetchall()
print(f"Migrando {len(filas_usuarios)} usuarios...")

insertar_usuario = sql.SQL("""
    INSERT INTO usuarios (usuario, contraseña_hash, rol)
    VALUES (%s, %s, %s)
""")

for fila in filas_usuarios:
    usuario_dict = dict(fila)
    valores = (
        usuario_dict.get('usuario'),
        usuario_dict.get('contraseña_hash'),
        usuario_dict.get('rol')
    )
    postgres_cursor.execute(insertar_usuario, valores)

postgres_conn.commit()
print(f"Usuarios migrados: {len(filas_usuarios)}")

# Cerrar conexiones
sqlite_conn.close()
postgres_conn.close()

print("\nMigración básica completada (pacientes y usuarios)")
