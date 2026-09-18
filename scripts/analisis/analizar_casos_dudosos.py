import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("ANALISIS DE CASOS DUDOSOS")
print("=" * 80)

# Caso 1: Cleotilde
print("\nCASO 1: CLEOTILDE")
print("-" * 40)

# Buscar en Antropometria
df_antro = pd.read_excel(excel_file, sheet_name='Antropometria ')
for i in range(min(5, len(df_antro))):
    row = df_antro.iloc[i]
    if not all(pd.isna(row)):
        df_antro = df_antro.iloc[i:].reset_index(drop=True)
        break

print("En Antropometria:")
for _, row in df_antro.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    if 'cleotilde' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print(f"  Edad: {row.get('EDAD')}")
        print(f"  Sexo: {row.get('SEXO')}")
        print(f"  Barrio: {row.get('BARRIO') if 'BARRIO' in row else 'N/A'}")
        print()

# Buscar en VO2
df_vo2 = pd.read_excel(excel_file, sheet_name='VO2')
for i in range(min(5, len(df_vo2))):
    row = df_vo2.iloc[i]
    if not all(pd.isna(row)):
        df_vo2 = df_vo2.iloc[i:].reset_index(drop=True)
        break

print("En VO2:")
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    if 'cleotilde' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print(f"  Edad: {row.get('EDAD')}")
        print()

# Caso 2: Maria Elsi/Maria elsy
print("\nCASO 2: MARIA ELSI/MARIA ELSY")
print("-" * 40)

# Buscar en MOCA
df_moca = pd.read_excel(excel_file, sheet_name='MOCA')
for i in range(min(5, len(df_moca))):
    row = df_moca.iloc[i]
    if not all(pd.isna(row)):
        df_moca = df_moca.iloc[i:].reset_index(drop=True)
        break

print("En MOCA:")
for _, row in df_moca.iterrows():
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')
    if 'els' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print()

# Buscar en VO2
print("En VO2:")
for _, row in df_vo2.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    if 'els' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print(f"  Edad: {row.get('EDAD')}")
        print()

# Verificar si hay datos suficientes en la hoja Historia Clinica para crear pacientes
print("\nVERIFICACION DE DATOS EN HISTORIA CLINICA")
print("-" * 40)

df_hc = pd.read_excel(excel_file, sheet_name='Historia Clinica ')
for i in range(min(5, len(df_hc))):
    row = df_hc.iloc[i]
    if not all(pd.isna(row)):
        df_hc = df_hc.iloc[i:].reset_index(drop=True)
        break

print("Buscando Cleotilde en Historia Clinica:")
for _, row in df_hc.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    if 'cleotilde' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print(f"  Edad: {row.get('EDAD')}")
        print(f"  Sexo: {row.get('SEXO')}")
        print(f"  Barrio: {row.get('BARRIO')}")
        print(f"  Fecha nacimiento: {row.get('FECHA DE NACIMIENTO')}")
        print()

print("Buscando Maria Elsi/Maria elsy en Historia Clinica:")
for _, row in df_hc.iterrows():
    nombres = row.get('NOMBRES', '')
    apellidos = row.get('APELLIDOS', '')
    if 'els' in str(nombres).lower():
        print(f"  {nombres} {apellidos}")
        print(f"  Edad: {row.get('EDAD')}")
        print(f"  Sexo: {row.get('SEXO')}")
        print(f"  Barrio: {row.get('BARRIO')}")
        print(f"  Fecha nacimiento: {row.get('FECHA DE NACIMIENTO')}")
        print()
