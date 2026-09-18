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

print("PASO 1: Crear paciente Cleotilde Cantillo Torres")
print("=" * 60)

# Verificar si ya existe
cursor.execute(
    "SELECT id FROM pacientes WHERE nombres = %s AND apellidos = %s",
    ('Cleotilde', 'Cantillo Torres')
)
if cursor.fetchone():
    print("El paciente ya existe, saltando creación...")
else:
    # Crear paciente Cleotilde
    nombres = 'Cleotilde'
    apellidos = 'Cantillo Torres'
    edad = 77
    sexo = 'Mujer'
    barrio = 'APELLIDO SIN CONFIRMAR - revisar con coordinación'
    antecedentes = 'APELLIDO SIN CONFIRMAR - revisar con coordinación (Cantillo vs Castilla)'

    busqueda = normalizar_nombre(f'{nombres} {apellidos}')

    cursor.execute(
        """INSERT INTO pacientes (nombres, apellidos, edad, sexo, barrio,
           antecedentes_familiares, busqueda)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (nombres, apellidos, edad, sexo, barrio, antecedentes, busqueda)
    )
    cleotilde_id = cursor.fetchone()[0]
    print(f"Paciente Cleotilde creado con ID: {cleotilde_id}")

conn.commit()

print("\nPASO 2: Re-importar con mapeos manuales")
print("=" * 60)

# Obtener pacientes actualizados
cursor.execute("SELECT id, nombres, apellidos FROM pacientes")
pacientes_existentes = {f"{normalizar_nombre(row[1])} {normalizar_nombre(row[2])}": row[0] for row in cursor.fetchall()}

# Mapeos manuales confirmados (Excel → Base)
mapeos_manuales = {
    'maria trinidad barbosa de canavera': 'maria trinidad varbosa de canavera',
    'francisco manuel barreto perez': 'francisco manuel barrero perez',
    'maria del rosario dora mercado': 'maria del rosario doria mercado',
    'alba marina chavez banqueth': 'alba marina chavez'
}

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

# Función para obtener paciente_id con mapeo manual
def obtener_paciente_id(nombres, apellidos):
    clave_normal = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"

    # Verificar mapeo manual
    if clave_normal in mapeos_manuales:
        clave_mapeada = mapeos_manuales[clave_normal]
        if clave_mapeada in pacientes_existentes:
            return pacientes_existentes[clave_mapeada]

    # Verificar match directo
    if clave_normal in pacientes_existentes:
        return pacientes_existentes[clave_normal]

    return None

# Antropometria
print("\n--- Re-importando Antropometria ---")
df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

mapeo_antro = {
    'sexo': 'sexo', 'talla': 'talla', 'peso': 'peso', 'imc': 'imc',
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
    'anchura_brazo': 'anchura_brazo', 'anchura_muneca': 'anchura_muneca',
    'anchura_rodilla': 'anchura_rodilla',
    'riesgo_cardiovascular': 'riesgo_cardiovascular'
}

insertados_antro = 0
for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    paciente_id = obtener_paciente_id(nombres, apellidos)
    if not paciente_id:
        continue

    # Verificar si ya existe
    cursor.execute("SELECT id FROM antropometria WHERE paciente_id = %s", (paciente_id,))
    if cursor.fetchone():
        continue

    valores = {'paciente_id': paciente_id, 'fecha_examen': None, 'creado_por': None}
    for col_excel, col_db in mapeo_antro.items():
        valor = row.get(col_excel)
        if not pd.isna(valor):
            valores[col_db] = valor

    columnas = list(valores.keys())
    placeholders = ', '.join(['%s'] * len(columnas))
    query = sql.SQL("INSERT INTO antropometria ({}) VALUES ({})").format(
        sql.SQL(', '.join(columnas)), sql.SQL(placeholders)
    )

    try:
        cursor.execute(query, list(valores.values()))
        insertados_antro += 1
    except Exception as e:
        print(f"Error: {e}")

conn.commit()
print(f"Antropometria insertados (nuevos): {insertados_antro}")

# VO2 Max
print("\n--- Re-importando VO2 Max ---")
df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

mapeo_vo2 = {
    'edad': 'edad', 'ta': 'ta', 'fc': 'fc', 'fc_max': 'fc_max',
    'spo2': 'spo2', 'vo2_max': 'vo2_max', 'resultado': 'resultado',
    'observaciones': 'observaciones'
}

insertados_vo2 = 0
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    paciente_id = obtener_paciente_id(nombres, apellidos)
    if not paciente_id:
        continue

    cursor.execute("SELECT id FROM vo2_max WHERE paciente_id = %s", (paciente_id,))
    if cursor.fetchone():
        continue

    valores = {'paciente_id': paciente_id, 'fecha_examen': None, 'creado_por': None}
    for col_excel, col_db in mapeo_vo2.items():
        valor = row.get(col_excel)
        if not pd.isna(valor):
            valores[col_db] = valor

    columnas = list(valores.keys())
    placeholders = ', '.join(['%s'] * len(columnas))
    query = sql.SQL("INSERT INTO vo2_max ({}) VALUES ({})").format(
        sql.SQL(', '.join(columnas)), sql.SQL(placeholders)
    )

    try:
        cursor.execute(query, list(valores.values()))
        insertados_vo2 += 1
    except Exception as e:
        print(f"Error: {e}")

conn.commit()
print(f"VO2 Max insertados (nuevos): {insertados_vo2}")

# Tests
print("\n--- Re-importando Tests ---")
df_tests = pd.read_excel(excel_file, sheet_name='MOCA')
for i in range(min(5, len(df_tests))):
    row = df_tests.iloc[i]
    if not all(pd.isna(row)):
        df_tests = df_tests.iloc[i:].reset_index(drop=True)
        break

insertados_moca = 0
insertados_tinetti = 0
insertados_chair = 0

for _, row in df_tests.iterrows():
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    paciente_id = obtener_paciente_id(nombres, apellidos)
    if not paciente_id:
        continue

    # Excluir Maria Elsi (confirmado por usuario)
    if 'els' in str(nombres).lower() and 'arena' in str(apellidos).lower():
        continue

    # Test MoCA
    resultado_moca = row.get('TEST DE MOCA')
    if not pd.isna(resultado_moca):
        cursor.execute("SELECT id FROM test_moca WHERE paciente_id = %s", (paciente_id,))
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_moca (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_moca)
                )
                insertados_moca += 1
            except Exception as e:
                print(f"Error MoCA: {e}")

    # Test Tinetti
    resultado_tinetti = row.get('TINETTI')
    if not pd.isna(resultado_tinetti):
        cursor.execute("SELECT id FROM test_tinetti WHERE paciente_id = %s", (paciente_id,))
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_tinetti (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_tinetti)
                )
                insertados_tinetti += 1
            except Exception as e:
                print(f"Error Tinetti: {e}")

    # Test Chair Stand
    resultado_chair = row.get('CHAIR STAND')
    if not pd.isna(resultado_chair):
        cursor.execute("SELECT id FROM test_chair_stand WHERE paciente_id = %s", (paciente_id,))
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO test_chair_stand (paciente_id, resultado, fecha_examen, creado_por) VALUES (%s, %s, NULL, NULL)",
                    (paciente_id, resultado_chair)
                )
                insertados_chair += 1
            except Exception as e:
                print(f"Error Chair: {e}")

conn.commit()
print(f"Test MoCA insertados (nuevos): {insertados_moca}")
print(f"Test Tinetti insertados (nuevos): {insertados_tinetti}")
print(f"Test Chair Stand insertados (nuevos): {insertados_chair}")

conn.close()
print("\nRe-importación completada")
