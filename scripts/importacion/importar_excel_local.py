# ============================================================
# Importa los datos del Excel a la base local SQLite.
# Fuente: BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx
# ============================================================
import sqlite3
import pandas as pd
import unicodedata
import math

DB = 'clinica.db'
EXCEL = 'BASE DTAOS PROYECTA JOSE MARTINEZ (1).xlsx'


def normalizar(t):
    if t is None:
        return ''
    if isinstance(t, float) and math.isnan(t):
        return ''
    t = unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('utf-8')
    return t.lower().strip()


def limpiar(v):
    """Convierte NaN/vacío a None; deja texto/numero limpio."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str):
        v = v.strip().replace('\u200b', '')
        return v if v else None
    return v


def num(v):
    """Intenta convertir a float; None si no se puede."""
    v = limpiar(v)
    if v is None:
        return None
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def entero(v):
    n = num(v)
    return int(n) if n is not None else None


conn = sqlite3.connect(DB)
cur = conn.cursor()

# Limpiar datos previos para evitar duplicados (idempotente).
# No borra la tabla usuarios.
print('Limpiando datos previos...')
for t in ['antropometria', 'vo2_max', 'test_moca', 'test_tinetti',
          'test_chair_stand', 'caracterizacion_socioeconomica', 'pacientes']:
    cur.execute(f'DELETE FROM {t}')
    cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (t,))
conn.commit()

# ------------------------------------------------------------
# 1) PACIENTES (desde Historia Clinica)
# ------------------------------------------------------------
print('Importando pacientes (Historia Clínica)...')
df_hc = pd.read_excel(EXCEL, sheet_name='Historia Clinica ')

def fecha_nac(v):
    v = limpiar(v)
    if v is None:
        return None
    try:
        return pd.to_datetime(v).strftime('%Y-%m-%d')
    except Exception:
        return str(v)

pacientes_insertados = 0
for _, row in df_hc.iterrows():
    nombres = limpiar(row.get('NOMBRES'))
    apellidos = limpiar(row.get('APELLIDOS'))
    if not nombres or not apellidos:
        continue
    busqueda = normalizar(f'{nombres} {apellidos}')
    cur.execute('''
        INSERT INTO pacientes
        (nombres, apellidos, edad, fecha_de_nacimiento, sexo, barrio,
         antecedentes_familiares, con_quien_vives, caidas_previas,
         lesiones_musculoesqueleticas_o_cirugia, medicacion_y_suplementacion,
         medicacion_sumplementacion, patologia_actual,
         habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados,
         alergias, ejercicio_y_actividad_fisica_leve_moderado_intenso,
         actividad_sexual, riesgo_cardiovascular_con_riesgo_o_sin_riesgo, busqueda)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        nombres, apellidos, entero(row.get('EDAD')), fecha_nac(row.get('FECHA DE NACIMIENTO')),
        limpiar(row.get('SEXO')), limpiar(row.get('BARRIO')),
        limpiar(row.get('ANTECEDENTES FAMILIARES')), limpiar(row.get('CON QUIEN VIVES?')),
        limpiar(row.get('CAIDAS PREVIAS')),
        limpiar(row.get('LESIONES MUSCULOESQUELETICAS O CIRUGIA')),
        limpiar(row.get('Medicación y suplementación')),
        limpiar(row.get('MEDICACIÓN/SUMPLEMENTACIÓN')),
        limpiar(row.get('PATOLOGIA ACTUAL')),
        limpiar(row.get('HABITOS Y ESTILOS DE VIDA (alcohol, tabaco, azucares, alimentos procesados)')),
        limpiar(row.get('ALERGIAS')),
        limpiar(row.get('EJERCICIO Y ACTIVIDAD FISICA (leve, moderado, intenso)')),
        limpiar(row.get('ACTIVIDAD SEXUAL')),
        limpiar(row.get('RIESGO CARDIOVASCULAR (Con Riesgo o Sin Riesgo)')),
        busqueda,
    ))
    pacientes_insertados += 1

# Poner fecha_creacion a los registros que quedaron sin ella
cur.execute("UPDATE pacientes SET fecha_creacion = date('now') WHERE fecha_creacion IS NULL")

conn.commit()
print(f'  Pacientes insertados: {pacientes_insertados}')

# Índice nombre -> id para emparejar módulos
cur.execute('SELECT id, nombres, apellidos FROM pacientes')
idx = {}
for pid, nom, ape in cur.fetchall():
    idx[normalizar(f'{nom} {ape}')] = pid

# Mapeos manuales (typos documentados en PENDIENTES_DATOS.md)
MAPEO_MANUAL = {
    normalizar('Maria Trinidad Barbosa de Cañavera'): normalizar('Maria Trinidad Varbosa De Cañavera'),
    normalizar('Francisco Manuel Barreto Perez'): normalizar('Francisco Manuel Barrero Perez'),
    normalizar('Maria del Rosario Dora Mercado'): normalizar('Maria del Rosario Doria Mercado'),
    normalizar('Alba Marina Chavez Banqueth'): normalizar('Alba Marina Chávez'),
}

def buscar_pid(nombres, apellidos):
    clave = normalizar(f'{nombres} {apellidos}')
    if clave in idx:
        return idx[clave]
    if clave in MAPEO_MANUAL and MAPEO_MANUAL[clave] in idx:
        return idx[MAPEO_MANUAL[clave]]
    return None


# ------------------------------------------------------------
# 2) ANTROPOMETRIA
# ------------------------------------------------------------
print('Importando antropometría...')
df_a = pd.read_excel(EXCEL, sheet_name='Antropometria ')
sin_match_a = 0
ok_a = 0
for _, row in df_a.iterrows():
    nombres = limpiar(row.get('NOMBRES'))
    apellidos = limpiar(row.get('APELLIDOS'))
    if not nombres or not apellidos:
        continue
    if num(row.get('TALLA')) is None and num(row.get('PESO')) is None:
        continue  # fila sin medición
    pid = buscar_pid(nombres, apellidos)
    if not pid:
        sin_match_a += 1
        continue
    riesgo = limpiar(row.get('FIESGO CARDIOVASCULAR'))
    if riesgo:
        riesgo = 'Con riesgo' if 'con' in riesgo.lower() else ('Sin riesgo' if 'sin' in riesgo.lower() else None)
    cur.execute('''
        INSERT INTO antropometria
        (paciente_id, sexo, talla, peso, imc, porcentaje_grasa_corporal,
         musculo_esqueletico, porcentaje_grasa_visceral, circunferencia_cintura,
         circunferencia_cadera, circunferencia_cuadriceps, circunferencia_pantorrilla,
         circunferencia_brazo, fuerza_lado_derecho, fuerza_lado_izquierdo,
         anchura_brazo, anchura_muneca, anchura_rodilla, riesgo_cardiovascular)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        pid, limpiar(row.get('SEXO')), num(row.get('TALLA')), num(row.get('PESO')),
        num(row.get('IMC')), num(row.get('% DE GRASA CORPORAL')),
        num(row.get('MUSCULO ESQUELETICO')), num(row.get('% DE GRASA VISERAL')),
        num(row.get('CIRCUFERENCIA CINTURA')), num(row.get('CIRCUFERENCIA CADERA')),
        num(row.get('CIRCUNFERENCIA CUADRICEP')), num(row.get('CIRCUNFERENCIA PANTORRILLA')),
        num(row.get('CIRCUNFERENCIA DE BRAZO')), num(row.get('FUERZA DE LADO DERECHO')),
        num(row.get('FUERZA DE LADO IZQUIERDO')), num(row.get('ANCHURA BRAZO')),
        num(row.get('ANCHURA DE MUÑECA')), num(row.get('ANCHURA DE RODILLA')), riesgo,
    ))
    ok_a += 1
conn.commit()
print(f'  Antropometría insertadas: {ok_a} (sin match: {sin_match_a})')

# ------------------------------------------------------------
# 3) VO2 MAX
# ------------------------------------------------------------
print('Importando VO2 Max...')
df_v = pd.read_excel(EXCEL, sheet_name='VO2')
ok_v = 0
sin_match_v = 0
for _, row in df_v.iterrows():
    nombres = limpiar(row.get('NOMBRES'))
    apellidos = limpiar(row.get('APELLIDOS'))
    if not nombres or not apellidos:
        continue
    if num(row.get('VO2 MAX')) is None and num(row.get('FC MAX')) is None:
        continue
    pid = buscar_pid(nombres, apellidos)
    if not pid:
        sin_match_v += 1
        continue
    cur.execute('''
        INSERT INTO vo2_max
        (paciente_id, edad, ta, fc, fc_max, spo2, vo2_max, resultado, observaciones)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (
        pid, entero(row.get('EDAD')), limpiar(row.get('TA')), limpiar(row.get('FC')),
        num(row.get('FC MAX')), num(row.get('SPO2')), num(row.get('VO2 MAX')),
        limpiar(row.get('OBSERVACIONES')), limpiar(row.get('OBSERVACIONES')),
    ))
    ok_v += 1
conn.commit()
print(f'  VO2 insertadas: {ok_v} (sin match: {sin_match_v})')

# ------------------------------------------------------------
# 4) MOCA / TINETTI / CHAIR STAND (hoja MOCA, columnas desalineadas)
#    NOMBRES real -> 'N', APELLIDOS real -> 'Unnamed: 3'
# ------------------------------------------------------------
print('Importando MoCA / Tinetti / Chair Stand...')
df_m = pd.read_excel(EXCEL, sheet_name='MOCA')
ok_moca = ok_tin = ok_chair = 0
for _, row in df_m.iterrows():
    nombres = limpiar(row.get('N'))
    apellidos = limpiar(row.get('Unnamed: 3'))
    if not nombres or not apellidos:
        continue
    pid = buscar_pid(nombres, apellidos)
    if not pid:
        continue

    # MoCA: la columna 'APELLIDOS' contiene el resultado tipo "PDCL 18 / M 9"
    moca_txt = limpiar(row.get('APELLIDOS'))
    if moca_txt:
        # clasificacion = primera palabra
        clasif = moca_txt.split()[0].upper() if moca_txt.split() else None
        cur.execute('INSERT INTO test_moca (paciente_id, resultado, observaciones) VALUES (?,?,?)',
                    (pid, clasif, moca_txt))
        ok_moca += 1

    # Tinetti: columna 'TEST DE MOCA' contiene la clasificación Tinetti (BAJO/MODERADO/ALTO)
    tin_txt = limpiar(row.get('TEST DE MOCA'))
    if tin_txt:
        cur.execute('INSERT INTO test_tinetti (paciente_id, resultado) VALUES (?,?)',
                    (pid, tin_txt.upper()))
        ok_tin += 1

    # Chair Stand: columna 'TINETTI' contiene la clasificación Chair Stand (SUPERIOR/REGULAR/POBRE...)
    chair_txt = limpiar(row.get('TINETTI'))
    if chair_txt and chair_txt.lower() != 'x':
        cur.execute('INSERT INTO test_chair_stand (paciente_id, resultado) VALUES (?,?)',
                    (pid, chair_txt.upper()))
        ok_chair += 1

conn.commit()
print(f'  MoCA: {ok_moca} | Tinetti: {ok_tin} | Chair Stand: {ok_chair}')

conn.close()
print('\nImportación completada.')
