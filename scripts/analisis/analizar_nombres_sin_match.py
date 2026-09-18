import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
import unicodedata
from difflib import SequenceMatcher

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

def similitud_apellidos(apellido1, apellido2):
    """Calcula similitud entre dos apellidos"""
    return SequenceMatcher(None, apellido1, apellido2).ratio()

# Conectar a PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Obtener todos los pacientes de la base
cursor.execute("SELECT id, nombres, apellidos FROM pacientes")
pacientes_base = []
for row in cursor.fetchall():
    paciente = {
        'id': row[0],
        'nombres': row[1],
        'apellidos': row[2],
        'nombres_norm': normalizar_nombre(row[1]),
        'apellidos_norm': normalizar_nombre(row[2])
    }
    pacientes_base.append(paciente)

print(f"Pacientes en base de datos: {len(pacientes_base)}")
print("=" * 80)

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

# Analizar cada hoja
hojas = {
    'Antropometria ': 'antropometria',
    'VO2': 'vo2_max',
    'MOCA': 'tests'
}

for nombre_hoja, tipo in hojas.items():
    print(f"\n{'='*80}")
    print(f"HOJA: {nombre_hoja}")
    print('='*80)

    df = pd.read_excel(excel_file, sheet_name=nombre_hoja)

    # Encontrar fila de datos reales
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        if not all(pd.isna(row)):
            df = df.iloc[i:].reset_index(drop=True)
            break

    # Determinar columnas de nombres según la hoja
    if nombre_hoja == 'MOCA':
        col_nombres = 'N'
        col_apellidos = 'Unnamed: 3'
    else:
        col_nombres = 'NOMBRES'
        col_apellidos = 'APELLIDOS'

    nombres_sin_match = []

    for _, row in df.iterrows():
        nombres = row.get(col_nombres, '')
        apellidos = row.get(col_apellidos, '')

        if pd.isna(nombres) or pd.isna(apellidos):
            continue

        nombres_norm = normalizar_nombre(nombres)
        apellidos_norm = normalizar_nombre(apellidos)
        clave_busqueda = f"{nombres_norm} {apellidos_norm}"

        # Buscar coincidencia exacta
        match_exacto = None
        for paciente in pacientes_base:
            clave_paciente = f"{paciente['nombres_norm']} {paciente['apellidos_norm']}"
            if clave_busqueda == clave_paciente:
                match_exacto = paciente
                break

        if match_exacto:
            continue  # Tiene match exacto

        # No tiene match exacto, buscar posibles coincidencias por nombre
        nombres_sin_match.append({
            'nombres': nombres,
            'apellidos': apellidos,
            'nombres_norm': nombres_norm,
            'apellidos_norm': apellidos_norm
        })

    if not nombres_sin_match:
        print("✓ Todos los nombres encontraron coincidencia exacta")
        continue

    print(f"\n{len(nombres_sin_match)} nombres SIN MATCH exacto:\n")

    for item in nombres_sin_match:
        print(f"• {item['nombres']} {item['apellidos']}")

        # Buscar pacientes con mismo nombre pero apellido diferente
        posibles_matches = []
        for paciente in pacientes_base:
            if item['nombres_norm'] == paciente['nombres_norm']:
                posibles_matches.append(paciente)

        if posibles_matches:
            print(f"  Posibles matches (mismo nombre, apellido diferente):")
            for match in posibles_matches:
                similitud = similitud_apellidos(item['apellidos_norm'], match['apellidos_norm'])
                print(f"    - {match['nombres']} {match['apellidos']} (similitud: {similitud:.2f})")
        else:
            print(f"  ATENCION: No hay pacientes con el mismo nombre en la base")

        print()

conn.close()
