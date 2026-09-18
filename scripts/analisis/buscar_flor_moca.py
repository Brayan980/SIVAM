import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("BUSCANDO FLOR LOPEZ EN HOJA MOCA")
print("=" * 80)

df_moca = pd.read_excel(excel_file, sheet_name='MOCA')

# Encontrar fila de datos reales
for i in range(min(5, len(df_moca))):
    row = df_moca.iloc[i]
    if not all(pd.isna(row)):
        df_moca = df_moca.iloc[i:].reset_index(drop=True)
        break

print(f"Columnas MOCA: {df_moca.columns.tolist()}")
print(f"\nMostrando todas las filas...")

for idx, row in df_moca.iterrows():
    nombres = row.get('N', '')
    apellidos = row.get('Unnamed: 3', '')

    # Imprimir todas las filas para encontrar el caso
    if idx <= 20:  # Primeras 20 filas
        print(f"Fila {idx}: N='{nombres}', APELLIDOS='{apellidos}'")

# Buscar específicamente filas que tengan 'nan' como apellido
print("\n--- Filas con 'nan' en apellidos ---")
for idx, row in df_moca.iterrows():
    apellidos = row.get('Unnamed: 3', '')
    if pd.isna(apellidos) or str(apellidos).lower() == 'nan':
        nombres = row.get('N', '')
        print(f"Fila {idx}: N='{nombres}', APELLIDOS='{apellidos}'")
        # Mostrar datos de tests
        moca = row.get('TEST DE MOCA')
        tinetti = row.get('TINETTI')
        chair = row.get('CHAIR STAND')
        print(f"  MOCA: {moca}, TINETTI: {tinetti}, CHAIR: {chair}")
