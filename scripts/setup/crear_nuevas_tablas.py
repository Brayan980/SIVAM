import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Conectar a PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("Creando nuevas tablas en PostgreSQL...")

# Tabla test_moca
crear_test_moca = sql.SQL("""
    CREATE TABLE IF NOT EXISTS test_moca (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        visuoespacial INTEGER, denominacion INTEGER, memoria INTEGER, atencion INTEGER,
        lenguaje INTEGER, abstraccion INTEGER, orientacion INTEGER,
        puntaje_total INTEGER,
        nada_mental BOOLEAN DEFAULT FALSE,
        indice_memoria INTEGER,
        resultado TEXT,
        evaluador TEXT,
        observaciones TEXT,
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_test_moca)
print("Tabla test_moca creada")

# Tabla test_tinetti
crear_test_tinetti = sql.SQL("""
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
        resultado TEXT,
        evaluador TEXT,
        observaciones TEXT,
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_test_tinetti)
print("Tabla test_tinetti creada")

# Tabla test_chair_stand
crear_test_chair_stand = sql.SQL("""
    CREATE TABLE IF NOT EXISTS test_chair_stand (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        resultado TEXT,
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_test_chair_stand)
print("Tabla test_chair_stand creada")

# Tabla antropometria
crear_antropometria = sql.SQL("""
    CREATE TABLE IF NOT EXISTS antropometria (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        sexo TEXT,
        talla NUMERIC(5,2),
        peso NUMERIC(5,2),
        imc NUMERIC(5,2),
        porcentaje_grasa_corporal NUMERIC(5,2),
        musculo_esqueletico NUMERIC(5,2),
        porcentaje_grasa_visceral NUMERIC(5,2),
        circunferencia_cintura NUMERIC(5,2),
        circunferencia_cadera NUMERIC(5,2),
        circunferencia_cuadriceps NUMERIC(5,2),
        circunferencia_pantorrilla NUMERIC(5,2),
        circunferencia_brazo NUMERIC(5,2),
        fuerza_lado_derecho NUMERIC(5,2),
        fuerza_lado_izquierdo NUMERIC(5,2),
        anchura_brazo NUMERIC(5,2),
        anchura_muneca NUMERIC(5,2),
        anchura_rodilla NUMERIC(5,2),
        riesgo_cardiovascular TEXT CHECK (riesgo_cardiovascular IN ('Con riesgo', 'Sin riesgo')),
        sarcopenia TEXT CHECK (sarcopenia IN ('Sin sarcopenia', 'Sospecha de sarcopenia', 'Sarcopenia')),
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_antropometria)
print("Tabla antropometria creada")

# Tabla vo2_max
crear_vo2_max = sql.SQL("""
    CREATE TABLE IF NOT EXISTS vo2_max (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        edad INTEGER,
        ta TEXT,
        fc TEXT,
        fc_max NUMERIC(5,2),
        spo2 NUMERIC(5,2),
        vo2_max NUMERIC(5,2),
        resultado TEXT,
        observaciones TEXT,
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_vo2_max)
print("Tabla vo2_max creada")

# Tabla caracterizacion_socioeconomica
crear_caracterizacion = sql.SQL("""
    CREATE TABLE IF NOT EXISTS caracterizacion_socioeconomica (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        escolaridad TEXT CHECK (escolaridad IN ('Bachiller', 'Técnico', 'Universitarios', 'Ninguno')),
        vivienda TEXT CHECK (vivienda IN ('Propia', 'Familiar', 'Arrendada')),
        con_quien_convive TEXT CHECK (con_quien_convive IN ('Solo', 'Familia', 'Otro')),
        estado_socioeconomico TEXT CHECK (estado_socioeconomico IN ('Pensionado', 'Otros')),
        fecha_examen DATE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
""")
cursor.execute(crear_caracterizacion)
print("Tabla caracterizacion_socioeconomica creada")

conn.commit()
conn.close()

print("\nTodas las nuevas tablas creadas exitosamente")
