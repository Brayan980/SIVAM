import pandas as pd

# Leer el Excel y mostrar las hojas
excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'
xls = pd.ExcelFile(excel_file)

print("Hojas encontradas en el Excel:")
for i, sheet_name in enumerate(xls.sheet_names, 1):
    print(f"{i}. {sheet_name}")

print("\n" + "="*50 + "\n")

# Analizar cada hoja
for sheet_name in xls.sheet_names:
    print(f"HOJA: {sheet_name}")
    print("-" * 30)
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    print(f"Filas: {len(df)}")
    print(f"Columnas: {list(df.columns)}")
    print(f"Primeras filas:")
    print(df.head(3))
    print("\n" + "="*50 + "\n")
