import pandas as pd
import psycopg2
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

# Obtener pacientes existentes
cursor.execute("SELECT id, nombres, apellidos FROM pacientes")
pacientes_existentes = {f"{normalizar_nombre(row[1])} {normalizar_nombre(row[2])}": row[0] for row in cursor.fetchall()}

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("ANALISIS PRECISO DE IMPORTACION")
print("=" * 80)

# Mapeos manuales (incluyendo el nuevo caso)
mapeos_manuales = {
    'maria trinidad barbosa de canavera': 'maria trinidad varbosa de canavera',
    'francisco manuel barreto perez': 'francisco manuel barrero perez',
    'maria del rosario dora mercado': 'maria del rosario doria mercado',
    'alba marina chavez banqueth': 'alba marina chavez'
}

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

# ANÁLISIS ANTROPOMETRÍA
print("\n" + "="*80)
print("ANTROPOMETRÍA")
print("="*80)

df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

# Contar filas con valor real en una columna clave (ej: peso)
filas_con_valor = 0
filas_sin_importar = []

for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    peso = row.get('PESO')

    # Si tiene peso, consideramos que tiene datos de antropometría
    if not pd.isna(peso) and peso != '':
        filas_con_valor += 1

        if pd.isna(nombres) or pd.isna(apellidos):
            filas_sin_importar.append((nombres, apellidos, "Sin nombres/apellidos"))
            continue

        paciente_id = obtener_paciente_id(nombres, apellidos)
        if not paciente_id:
            filas_sin_importar.append((nombres, apellidos, "Sin match en base"))

print(f"(1) Filas con valor real (PESO): {filas_con_valor}")
print(f"(2) Importadas con éxito: {filas_con_valor - len(filas_sin_importar)}")
print(f"(3) Filas con valor PERO NO importadas: {len(filas_sin_importar)}")

if filas_sin_importar:
    print("\nLista de filas con valor pero NO importadas:")
    for nombres, apellidos, razon in filas_sin_importar:
        print(f"  - {nombres} {apellidos} ({razon})")

# ANÁLISIS VO2 MAX
print("\n" + "="*80)
print("VO2 MAX")
print("="*80)

df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

filas_con_valor = 0
filas_sin_importar = []

for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    vo2 = row.get('VO2 MAX')

    if not pd.isna(vo2) and vo2 != '':
        filas_con_valor += 1

        if pd.isna(nombres) or pd.isna(apellidos):
            filas_sin_importar.append((nombres, apellidos, "Sin nombres/apellidos"))
            continue

        paciente_id = obtener_paciente_id(nombres, apellidos)
        if not paciente_id:
            filas_sin_importar.append((nombres, apellidos, "Sin match en base"))

print(f"(1) Filas con valor real (VO2 MAX): {filas_con_valor}")
print(f"(2) Importadas con éxito: {filas_con_valor - len(filas_sin_importar)}")
print(f"(3) Filas con valor PERO NO importadas: {len(filas_sin_importar)}")

if filas_sin_importar:
    print("\nLista de filas con valor pero NO importadas:")
    for nombres, apellidos, razon in filas_sin_importar:
        print(f"  - {nombres} {apellidos} ({razon})")

# ANÁLISIS TESTS
print("\n" + "="*80)
print("TESTS (MOCA, TINETTI, CHAIR STAND)")
print("="*80)

df_tests = pd.read_excel(excel_file, sheet_name='MOCA')
for i in range(min(5, len(df_tests))):
    row = df_tests.iloc[i]
    if not all(pd.isna(row)):
        df_tests = df_tests.iloc[i:].reset_index(drop=True)
        break

for test_nombre, columna in [('MOCA', 'TEST DE MOCA'), ('TINETTI', 'TINETTI'), ('CHAIR STAND', 'CHAIR STAND')]:
    print(f"\n--- {test_nombre} ---")

    filas_con_valor = 0
    filas_sin_importar = []

    for _, row in df_tests.iterrows():
        nombres = row.get('N', '')
        apellidos = row.get('Unnamed: 3', '')
        resultado = row.get(columna)

        if not pd.isna(resultado) and resultado != '' and resultado != 'x':
            filas_con_valor += 1

            if pd.isna(nombres) or pd.isna(apellidos):
                filas_sin_importar.append((nombres, apellidos, "Sin nombres/apellidos"))
                continue

            # Excluir Maria Elsi (confirmado por usuario)
            if 'els' in str(nombres).lower() and 'arena' in str(apellidos).lower():
                filas_sin_importar.append((nombres, apellidos, "Excluido por usuario (falta datos)"))
                continue

            paciente_id = obtener_paciente_id(nombres, apellidos)
            if not paciente_id:
                filas_sin_importar.append((nombres, apellidos, "Sin match en base"))

    print(f"(1) Filas con valor real ({columna}): {filas_con_valor}")
    print(f"(2) Importadas con éxito: {filas_con_valor - len(filas_sin_importar)}")
    print(f"(3) Filas con valor PERO NO importadas: {len(filas_sin_importar)}")

    if filas_sin_importar:
        print("Lista de filas con valor pero NO importadas:")
        for nombres, apellidos, razon in filas_sin_importar:
            print(f"  - {nombres} {apellidos} ({razon})")

conn.close()
