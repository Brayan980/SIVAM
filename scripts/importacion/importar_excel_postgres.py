import pandas as pd
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
import unicodedata

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def normalizar_nombre(texto):
    """Normaliza nombres para comparación: minúsculas, sin tildes"""
    if pd.isna(texto) or texto == '':
        return ''
    texto = str(texto).strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower()

# Conectar a PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("Conectado a PostgreSQL")
print("Importando datos del Excel...")

# Obtener pacientes existentes para cruzar
cursor.execute("SELECT id, nombres, apellidos FROM pacientes")
pacientes_existentes = {f"{normalizar_nombre(row[1])} {normalizar_nombre(row[2])}": row[0] for row in cursor.fetchall()}
print(f"Pacientes existentes en base: {len(pacientes_existentes)}")

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

# Importar Antropometria
print("\n--- Importando Antropometria ---")
df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')

# Encontrar fila de datos reales
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

# Normalizar nombres de columnas
columnas_norm = {}
for col in df_antro.columns:
    norm = normalizar_nombre(col)
    if norm and not 'unnamed' in norm:
        columnas_norm[col] = norm

# Mapeo de columnas Excel a PostgreSQL
mapeo_antro = {
    'sexo': 'sexo',
    'talla': 'talla',
    'peso': 'peso',
    'imc': 'imc',
    'porcentaje_de_grasa_corporal': 'porcentaje_grasa_corporal',
    'musculo_esqueletico': 'musculo_esqueletico',
    'porcentaje_de_grasa_visceral': 'porcentaje_grasa_visceral',
    'circunferencia_cintura': 'circunferencia_cintura',
    'circunferencia_cadera': 'circunferencia_cadera',
    'circunferencia_cuadriceps': 'circunferencia_cuadriceps',
    'circunferencia_pantorrilla': 'circunferencia_pantorrilla',
    'circunferencia_brazo': 'circunferencia_brazo',
    'fuerza_lado_derecho': 'fuerza_lado_derecho',
    'fuerza_lado_izquierdo': 'fuerza_lado_izquierdo',
    'anchura_brazo': 'anchura_brazo',
    'anchura_muneca': 'anchura_muneca',
    'anchura_rodilla': 'anchura_rodilla',
    'riesgo_cardiovascular': 'riesgo_cardiovascular'
}

insertados_antro = 0
for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave_paciente = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave_paciente not in pacientes_existentes:
        continue

    paciente_id = pacientes_existentes[clave_paciente]

    # Verificar si ya existe
    cursor.execute(
        "SELECT id FROM antropometria WHERE paciente_id = %s",
        (paciente_id,)
    )
    if cursor.fetchone():
        continue

    # Preparar valores
    valores = {
        'paciente_id': paciente_id,
        'fecha_examen': None,  # No hay fecha en el Excel
        'creado_por': None     # No hay info de creador
    }

    for col_excel, col_db in mapeo_antro.items():
        valor = row.get(col_excel)
        if not pd.isna(valor):
            valores[col_db] = valor

    # Construir query
    columnas = list(valores.keys())
    placeholders = ', '.join(['%s'] * len(columnas))
    query = sql.SQL("INSERT INTO antropometria ({}) VALUES ({})").format(
        sql.SQL(', '.join(columnas)),
        sql.SQL(placeholders)
    )

    try:
        cursor.execute(query, list(valores.values()))
        insertados_antro += 1
    except Exception as e:
        print(f"Error insertando antropometria para {clave_paciente}: {e}")

conn.commit()
print(f"Antropometria insertados: {insertados_antro}")

# Importar VO2 Max
print("\n--- Importando VO2 Max ---")
df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')

# Encontrar fila de datos reales
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

mapeo_vo2 = {
    'edad': 'edad',
    'ta': 'ta',
    'fc': 'fc',
    'fc_max': 'fc_max',
    'spo2': 'spo2',
    'vo2_max': 'vo2_max',
    'resultado': 'resultado',
    'observaciones': 'observaciones'
}

insertados_vo2 = 0
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave_paciente = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave_paciente not in pacientes_existentes:
        continue

    paciente_id = pacientes_existentes[clave_paciente]

    # Verificar si ya existe
    cursor.execute(
        "SELECT id FROM vo2_max WHERE paciente_id = %s",
        (paciente_id,)
    )
    if cursor.fetchone():
        continue

    # Preparar valores
    valores = {
        'paciente_id': paciente_id,
        'fecha_examen': None,
        'creado_por': None
    }

    for col_excel, col_db in mapeo_vo2.items():
        valor = row.get(col_excel)
        if not pd.isna(valor):
            valores[col_db] = valor

    # Construir query
    columnas = list(valores.keys())
    placeholders = ', '.join(['%s'] * len(columnas))
    query = sql.SQL("INSERT INTO vo2_max ({}) VALUES ({})").format(
        sql.SQL(', '.join(columnas)),
        sql.SQL(placeholders)
    )

    try:
        cursor.execute(query, list(valores.values()))
        insertados_vo2 += 1
    except Exception as e:
        print(f"Error insertando VO2 para {clave_paciente}: {e}")

conn.commit()
print(f"VO2 Max insertados: {insertados_vo2}")

# Importar Tests (MOCA, Tinetti, Chair Stand)
print("\n--- Importando Tests ---")
df_tests = pd.read_excel(excel_file, sheet_name='MOCA')

# Encontrar fila de datos reales
for i in range(min(5, len(df_tests))):
    row = df_tests.iloc[i]
    if not all(pd.isna(row)):
        df_tests = df_tests.iloc[i:].reset_index(drop=True)
        break

insertados_moca = 0
insertados_tinetti = 0
insertados_chair = 0

for _, row in df_tests.iterrows():
    # En la hoja MOCA, nombres está en columna 'N' y apellidos en 'Unnamed: 3'
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave_paciente = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave_paciente not in pacientes_existentes:
        continue

    paciente_id = pacientes_existentes[clave_paciente]

    # Test MoCA
    resultado_moca = row.get('TEST DE MOCA')
    if not pd.isna(resultado_moca):
        cursor.execute(
            "SELECT id FROM test_moca WHERE paciente_id = %s",
            (paciente_id,)
        )
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_moca (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_moca)
                )
                insertados_moca += 1
            except Exception as e:
                print(f"Error insertando MoCA para {clave_paciente}: {e}")

    # Test Tinetti
    resultado_tinetti = row.get('TINETTI')
    if not pd.isna(resultado_tinetti):
        cursor.execute(
            "SELECT id FROM test_tinetti WHERE paciente_id = %s",
            (paciente_id,)
        )
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_tinetti (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_tinetti)
                )
                insertados_tinetti += 1
            except Exception as e:
                print(f"Error insertando Tinetti para {clave_paciente}: {e}")

    # Test Chair Stand
    resultado_chair = row.get('CHAIR STAND')
    if not pd.isna(resultado_chair):
        cursor.execute(
            "SELECT id FROM test_chair_stand WHERE paciente_id = %s",
            (paciente_id,)
        )
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_chair_stand (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_chair)
                )
                insertados_chair += 1
            except Exception as e:
                print(f"Error insertando Chair Stand para {clave_paciente}: {e}")

conn.commit()
print(f"Test MoCA insertados: {insertados_moca}")
print(f"Test Tinetti insertados: {insertados_tinetti}")
print(f"Test Chair Stand insertados: {insertados_chair}")

conn.close()
print("\nImportación completada")
