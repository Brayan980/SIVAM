import pandas as pd

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'
df_tests = pd.read_excel(excel_file, sheet_name='MOCA')

print("Columnas:", df_tests.columns.tolist())
print("\nPrimeras 5 filas:")
print(df_tests.head(5))

print("\nFila 1 (donde están los datos):")
row = df_tests.iloc[1]
for col in df_tests.columns:
    val = row[col]
    if not pd.isna(val):
        print(f"{col}: {val}")
