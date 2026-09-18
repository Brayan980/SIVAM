# ============================================================
# Crea la base de datos local SQLite (clinica.db) con el
# esquema completo del sistema SIVAM.
# ============================================================
import sqlite3
import os

DB = 'clinica.db'

# Si ya existe, hacer respaldo antes de recrear
if os.path.exists(DB):
    import shutil, time
    backup = f'clinica_backup_{int(time.time())}.db'
    shutil.copy(DB, backup)
    print(f'Respaldo creado: {backup}')

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.executescript('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    contraseña_hash TEXT,
    rol TEXT
);

CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombres TEXT,
    apellidos TEXT,
    edad INTEGER,
    fecha_de_nacimiento TEXT,
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
);

CREATE TABLE IF NOT EXISTS antropometria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    sexo TEXT,
    talla REAL, peso REAL, imc REAL,
    porcentaje_grasa_corporal REAL,
    musculo_esqueletico REAL,
    porcentaje_grasa_visceral REAL,
    circunferencia_cintura REAL,
    circunferencia_cadera REAL,
    circunferencia_cuadriceps REAL,
    circunferencia_pantorrilla REAL,
    circunferencia_brazo REAL,
    fuerza_lado_derecho REAL,
    fuerza_lado_izquierdo REAL,
    anchura_brazo REAL,
    anchura_muneca REAL,
    anchura_rodilla REAL,
    riesgo_cardiovascular TEXT,
    sarcopenia TEXT,
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS vo2_max (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    edad INTEGER, ta TEXT, fc TEXT, fc_max REAL, spo2 REAL, vo2_max REAL,
    resultado TEXT, observaciones TEXT,
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_moca (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    visuoespacial INTEGER, denominacion INTEGER, memoria INTEGER, atencion INTEGER,
    lenguaje INTEGER, abstraccion INTEGER, orientacion INTEGER,
    puntaje_total INTEGER,
    nada_mental INTEGER DEFAULT 0,
    indice_memoria INTEGER,
    resultado TEXT,
    evaluador TEXT,
    observaciones TEXT,
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_tinetti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS test_chair_stand (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    resultado TEXT,
    repeticiones INTEGER,
    percentil INTEGER,
    evaluador TEXT,
    observaciones TEXT,
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS caracterizacion_socioeconomica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    escolaridad TEXT,
    vivienda TEXT,
    con_quien_convive TEXT,
    estado_socioeconomico TEXT,
    fecha_examen TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_pacientes_busqueda ON pacientes(busqueda);
''')

conn.commit()
conn.close()
print('Base local clinica.db creada con el esquema completo.')
