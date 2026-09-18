import pandas as pd
import unicodedata

def normalizar_nombre(texto):
    if pd.isna(texto) or texto == '':
        return ''
    texto = str(texto).strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower()

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("VERIFICANDO MAPEOS MANUALES")
print("=" * 60)

# Mapeos manuales que definí
mapeos_manuales = {
    'maria trinidad varbosa de canavera': 'maria trinidad barbosa de canavera',
    'francisco manuel barrero perez': 'francisco manuel barreto perez',
    'maria del rosario doria mercado': 'maria del rosario dora mercado'
}

# Antropometria
df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

print("\nBuscando casos de mapeo manual en Antropometria:")
for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave in mapeos_manuales:
        print(f"[OK] Encontrado: {nombres} {apellidos}")
        print(f"  Clave normalizada: {clave}")
        print(f"  Debería mapear a: {mapeos_manuales[clave]}")

# MOCA
df_moca = pd.read_excel(excel_file, sheet_name='MOCA')
for i in range(min(5, len(df_moca))):
    row = df_moca.iloc[i]
    if not all(pd.isna(row)):
        df_moca = df_moca.iloc[i:].reset_index(drop=True)
        break

print("\nBuscando casos de mapeo manual en MOCA:")
for _, row in df_moca.iterrows():
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave in mapeos_manuales:
        print(f"[OK] Encontrado: {nombres} {apellidos}")
        print(f"  Clave normalizada: {clave}")
        print(f"  Debería mapear a: {mapeos_manuales[clave]}")

# VO2
df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

print("\nBuscando casos de mapeo manual en VO2:")
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    clave = f"{normalizar_nombre(nombres)} {normalizar_nombre(apellidos)}"
    if clave in mapeos_manuales:
        print(f"[OK] Encontrado: {nombres} {apellidos}")
        print(f"  Clave normalizada: {clave}")
        print(f"  Debería mapear a: {mapeos_manuales[clave]}")
