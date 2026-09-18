import pandas as pd
import unicodedata

def normalizar_nombre(nombre):
    """Normaliza nombres de columnas: minúsculas, sin tildes, espacios por guiones bajos"""
    if pd.isna(nombre) or nombre == '':
        return None
    texto = str(nombre).strip()
    # Corregir errores obvios
    texto = texto.replace('CIRCUFERENCIA', 'CIRCUNFERENCIA')
    texto = texto.replace('FIESGO', 'RIESGO')
    texto = texto.replace('MUSCULO', 'MÚSCULO')
    texto = texto.replace('ESQUELETICO', 'ESQUELÉTICO')
    texto = texto.replace('CUADRICEP', 'CUÁDRICEPS')
    texto = texto.replace('PANTORRILLA', 'PANTORRILLA')
    texto = texto.replace('BRAZO', 'BRAZO')
    texto = texto.replace('MUÑECA', 'MUÑECA')
    texto = texto.replace('RODILLA', 'RODILLA')
    # Normalizar
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    texto = texto.lower().replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('-', '_')
    return texto

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

# Analizar cada hoja en detalle
for sheet_name in ['MOCA', 'VO2', 'Antropometria ']:
    print(f"\n{'='*60}")
    print(f"HOJA: {sheet_name}")
    print('='*60)
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    # Encontrar fila de datos reales (saltar headers duplicados)
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        if not all(pd.isna(row)):
            print(f"Fila de datos reales: {i}")
            print(f"Columnas originales: {list(df.columns)}")
            print(f"Columnas normalizadas: {[normalizar_nombre(col) for col in df.columns]}")
            print(f"\nDatos de ejemplo (fila {i}):")
            for col in df.columns:
                val = row[col]
                if not pd.isna(val):
                    print(f"  {col}: {val}")
            break
