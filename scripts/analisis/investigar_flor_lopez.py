import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

print("INVESTIGANDO CASO: FLOR LOPEZ MARTINEZ")
print("=" * 80)

# Buscar en todas las hojas
hojas = ['Antropometria ', 'VO2', 'MOCA']

for nombre_hoja in hojas:
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

    print(f"Columnas: {df.columns.tolist()}")
    print(f"\nBuscando 'Flor' o 'Lopez' en la hoja...")

    for idx, row in df.iterrows():
        # Revisar todas las columnas que podrían contener nombres
        for col in df.columns:
            valor = row[col]
            if not pd.isna(valor) and isinstance(valor, str):
                valor_str = str(valor)
                if 'flor' in valor_str.lower() and 'lopez' in valor_str.lower():
                    print(f"\nFila {idx}:")
                    print(f"Columna '{col}': {valor}")
                    print(f"Contenido completo de la fila:")
                    for c in df.columns:
                        val = row[c]
                        if not pd.isna(val):
                            print(f"  {c}: {val}")
                    print()
