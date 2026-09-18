import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("BUSCANDO VARIANTES DE LOS CASOS CONFIRMADOS")
print("=" * 60)

# Variantes a buscar
variantes = [
    'Barbosa', 'Varbosa',
    'Barreto', 'Barrero',
    'Dora', 'Doria'
]

# Antropometria
df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

print("\nEn Antropometria:")
for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    for variante in variantes:
        if variante.lower() in apellidos.lower():
            print(f"  {nombres} {apellidos}")
            break

# MOCA
df_moca = pd.read_excel(excel_file, sheet_name='MOCA')
for i in range(min(5, len(df_moca))):
    row = df_moca.iloc[i]
    if not all(pd.isna(row)):
        df_moca = df_moca.iloc[i:].reset_index(drop=True)
        break

print("\nEn MOCA:")
for _, row in df_moca.iterrows():
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    for variante in variantes:
        if variante.lower() in apellidos.lower():
            print(f"  {nombres} {apellidos}")
            break

# VO2
df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

print("\nEn VO2:")
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')

    if pd.isna(nombres) or pd.isna(apellidos):
        continue

    for variante in variantes:
        if variante.lower() in apellidos.lower():
            print(f"  {nombres} {apellidos}")
            break
