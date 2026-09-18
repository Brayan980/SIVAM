import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("BUSCANDO LOS 3 CASOS CONFIRMADOS EN EL EXCEL")
print("=" * 60)

# Casos que el usuario confirmó
casos_confirmados = [
    'Maria Trinidad Barbosa',
    'Francisco Manuel Barreto',
    'Maria del Rosario Dora'
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

    for caso in casos_confirmados:
        if caso.lower() in nombres.lower():
            print(f"  {nombres} {apellidos}")

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

    for caso in casos_confirmados:
        if caso.lower() in nombres.lower():
            print(f"  {nombres} {apellidos}")

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

    for caso in casos_confirmados:
        if caso.lower() in nombres.lower():
            print(f"  {nombres} {apellidos}")
