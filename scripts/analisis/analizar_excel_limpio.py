import pandas as pd
import unicodedata

def normalizar_nombre(nombre):
    """Normaliza nombres de columnas: minúsculas, sin tildes, espacios por guiones bajos"""
    if pd.isna(nombre) or nombre == '' or 'Unnamed' in str(nombre):
        return None
    texto = str(nombre).strip()
    # Corregir errores obvios
    texto = texto.replace('CIRCUFERENCIA', 'CIRCUNFERENCIA')
    texto = texto.replace('FIESGO', 'RIESGO')
    texto = texto.replace('MUSCULO', 'MUSCULO')
    texto = texto.replace('ESQUELETICO', 'ESQUELETICO')
    texto = texto.replace('CUADRICEP', 'CUADRICEPS')
    texto = texto.replace('RODILLA', 'RODILLA')
    texto = texto.replace('BRAZO', 'BRAZO')
    texto = texto.replace('MUÑECA', 'MUNECA')
    texto = texto.replace('Ñ', 'N')
    texto = texto.replace('Ó', 'O')
    texto = texto.replace('Á', 'A')
    texto = texto.replace('É', 'E')
    texto = texto.replace('Í', 'I')
    # Normalizar
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    texto = texto.lower().replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('-', '_').replace('%', 'porcentaje')
    return texto

excel_file = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'

# Analizar cada hoja en detalle
for sheet_name in ['MOCA', 'VO2', 'Antropometria ']:
    print(f"\n{'='*60}")
    print(f"HOJA: {sheet_name}")
    print('='*60)
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    # Encontrar fila de datos reales
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        if not all(pd.isna(row)):
            print(f"Fila de datos reales: {i}")
            print(f"Columnas utilies:")
            for col in df.columns:
                norm = normalizar_nombre(col)
                if norm:
                    val = row[col]
                    if not pd.isna(val):
                        print(f"  {norm}: {val}")
            break
