# ============================================================
# Exportación de datos a Excel.
#  - generar_excel(): TODA la base en UNA sola hoja (un paciente por fila),
#    uniendo todas las tablas con LEFT JOIN desde 'pacientes'.
#  - generar_excel_individual(): un paciente en formato vertical
#    (Campo / Valor) organizado por secciones.
# ============================================================
from io import BytesIO
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage

from db import conectar
import graficas


# --- Estilos ---
_FILL_HEADER = PatternFill(start_color='2E7D32', end_color='2E7D32', fill_type='solid')
_FONT_HEADER = Font(bold=True, color='FFFFFF', size=11)
_ALIGN_HEADER = Alignment(horizontal='center', vertical='center', wrap_text=True)

# Colores de encabezado por módulo para el export general (ancho).
# Cada grupo de columnas se pinta con su color para diferenciarlos.
_COLOR_MODULO = {
    'pacientes': '2E7D32',                       # verde  - Historia Clínica
    'antropometria': '1565C0',                   # azul   - Antropometría
    'vo2_max': '6A1B9A',                         # morado - VO2 Max
    'test_moca': 'C62828',                       # rojo   - MoCA
    'test_tinetti': 'EF6C00',                    # naranja- Tinetti
    'test_chair_stand': '00838F',                # teal   - Chair Stand
    'caracterizacion_socioeconomica': '5D4037',  # café   - Caracterización
}

# Sección (encabezado de grupo) para el formato vertical individual
_FILL_SECCION = PatternFill(start_color='1F6F78', end_color='1F6F78', fill_type='solid')
_FONT_SECCION = Font(bold=True, color='FFFFFF', size=12)
_FONT_CAMPO = Font(bold=True, color='333333')
_ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)


# ============================================================
# Definición de módulos.
#   'alias'    -> alias de la tabla en el JOIN
#   'tabla'    -> nombre real de la tabla
#   'seccion'  -> título legible de la sección
#   'columnas' -> lista de (columna_real, etiqueta_legible, alias_columna)
#                 alias_columna es el nombre único (con prefijo) para el export ancho.
# ============================================================
_HISTORIA = {
    'alias': 'p',
    'tabla': 'pacientes',
    'seccion': 'Historia Clínica',
    'columnas': [
        ('nombres', 'Nombres', 'nombres'),
        ('apellidos', 'Apellidos', 'apellidos'),
        ('edad', 'Edad', 'edad'),
        ('fecha_de_nacimiento', 'Fecha de nacimiento', 'fecha_de_nacimiento'),
        ('sexo', 'Sexo', 'sexo'),
        ('barrio', 'Barrio', 'barrio'),
        ('antecedentes_familiares', 'Antecedentes familiares', 'antecedentes_familiares'),
        ('con_quien_vives', 'Con quién vive', 'con_quien_vives'),
        ('caidas_previas', 'Caídas previas', 'caidas_previas'),
        ('lesiones_musculoesqueleticas_o_cirugia', 'Lesiones musculoesqueléticas o cirugía', 'lesiones_musculoesqueleticas_o_cirugia'),
        ('medicacion_y_suplementacion', 'Medicación y suplementación', 'medicacion_y_suplementacion'),
        ('patologia_actual', 'Patología actual', 'patologia_actual'),
        ('habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados', 'Hábitos y estilos de vida', 'habitos_y_estilos_de_vida'),
        ('alergias', 'Alergias', 'alergias'),
        ('ejercicio_y_actividad_fisica_leve_moderado_intenso', 'Ejercicio y actividad física', 'ejercicio_y_actividad_fisica'),
        ('actividad_sexual', 'Actividad sexual', 'actividad_sexual'),
        ('riesgo_cardiovascular_con_riesgo_o_sin_riesgo', 'Riesgo cardiovascular', 'riesgo_cardiovascular_hc'),
    ],
}

# Módulos que se unen por paciente_id (LEFT JOIN). 'sexo' de antropometría se OMITE
# a propósito para no duplicar el de Historia Clínica.
_MODULOS = [
    {
        'alias': 'a',
        'tabla': 'antropometria',
        'seccion': 'Antropometría',
        'columnas': [
            ('talla', 'Talla', 'talla'),
            ('peso', 'Peso', 'peso'),
            ('imc', 'IMC', 'imc'),
            ('porcentaje_grasa_corporal', '% Grasa corporal', 'porcentaje_grasa_corporal'),
            ('musculo_esqueletico', 'Músculo esquelético', 'musculo_esqueletico'),
            ('porcentaje_grasa_visceral', '% Grasa visceral', 'porcentaje_grasa_visceral'),
            ('circunferencia_cintura', 'Circunferencia cintura', 'circunferencia_cintura'),
            ('circunferencia_cadera', 'Circunferencia cadera', 'circunferencia_cadera'),
            ('circunferencia_cuadriceps', 'Circunferencia cuádriceps', 'circunferencia_cuadriceps'),
            ('circunferencia_pantorrilla', 'Circunferencia pantorrilla', 'circunferencia_pantorrilla'),
            ('circunferencia_brazo', 'Circunferencia brazo', 'circunferencia_brazo'),
            ('fuerza_lado_derecho', 'Fuerza lado derecho', 'fuerza_lado_derecho'),
            ('fuerza_lado_izquierdo', 'Fuerza lado izquierdo', 'fuerza_lado_izquierdo'),
            ('anchura_brazo', 'Anchura brazo', 'anchura_brazo'),
            ('anchura_muneca', 'Anchura muñeca', 'anchura_muneca'),
            ('anchura_rodilla', 'Anchura rodilla', 'anchura_rodilla'),
            ('riesgo_cardiovascular', 'Riesgo cardiovascular (antropometría)', 'antro_riesgo_cardiovascular'),
            ('sarcopenia', 'Sarcopenia', 'sarcopenia'),
            ('fecha_examen', 'Fecha examen (antropometría)', 'antro_fecha_examen'),
        ],
    },
    {
        'alias': 'v',
        'tabla': 'vo2_max',
        'seccion': 'VO2 Max',
        'columnas': [
            ('ta', 'TA', 'vo2_ta'),
            ('fc', 'FC', 'vo2_fc'),
            ('fc_max', 'FC Max', 'vo2_fc_max'),
            ('spo2', 'SpO2', 'vo2_spo2'),
            ('vo2_max', 'VO2 Max', 'vo2_max'),
            ('resultado', 'Resultado VO2', 'vo2_resultado'),
            ('observaciones', 'Observaciones VO2', 'vo2_observaciones'),
            ('fecha_examen', 'Fecha examen (VO2)', 'vo2_fecha_examen'),
        ],
    },
    {
        'alias': 'm',
        'tabla': 'test_moca',
        'seccion': 'Test MoCA',
        'columnas': [
            ('visuoespacial', 'Visuoespacial', 'moca_visuoespacial'),
            ('denominacion', 'Denominación', 'moca_denominacion'),
            ('memoria', 'Memoria', 'moca_memoria'),
            ('atencion', 'Atención', 'moca_atencion'),
            ('lenguaje', 'Lenguaje', 'moca_lenguaje'),
            ('abstraccion', 'Abstracción', 'moca_abstraccion'),
            ('orientacion', 'Orientación', 'moca_orientacion'),
            ('puntaje_total', 'Puntaje total MoCA', 'moca_puntaje_total'),
            ('indice_memoria', 'Índice memoria', 'moca_indice_memoria'),
            ('resultado', 'Resultado MoCA', 'moca_resultado'),
            ('evaluador', 'Evaluador MoCA', 'moca_evaluador'),
            ('observaciones', 'Observaciones MoCA', 'moca_observaciones'),
            ('fecha_examen', 'Fecha examen (MoCA)', 'moca_fecha_examen'),
        ],
    },
    {
        'alias': 't',
        'tabla': 'test_tinetti',
        'seccion': 'Test Tinetti',
        'columnas': [
            ('puntaje_equilibrio', 'Puntaje equilibrio', 'tinetti_puntaje_equilibrio'),
            ('puntaje_marcha', 'Puntaje marcha', 'tinetti_puntaje_marcha'),
            ('puntaje_total', 'Puntaje total Tinetti', 'tinetti_puntaje_total'),
            ('resultado', 'Resultado Tinetti', 'tinetti_resultado'),
            ('evaluador', 'Evaluador Tinetti', 'tinetti_evaluador'),
            ('observaciones', 'Observaciones Tinetti', 'tinetti_observaciones'),
            ('fecha_examen', 'Fecha examen (Tinetti)', 'tinetti_fecha_examen'),
        ],
    },
    {
        'alias': 'c',
        'tabla': 'test_chair_stand',
        'seccion': 'Test Chair Stand',
        'columnas': [
            ('resultado', 'Resultado Chair Stand', 'chairstand_resultado'),
            ('repeticiones', 'Repeticiones', 'chairstand_repeticiones'),
            ('percentil', 'Percentil', 'chairstand_percentil'),
            ('evaluador', 'Evaluador Chair Stand', 'chairstand_evaluador'),
            ('observaciones', 'Observaciones Chair Stand', 'chairstand_observaciones'),
            ('fecha_examen', 'Fecha examen (Chair Stand)', 'chairstand_fecha_examen'),
        ],
    },
    {
        'alias': 'ce',
        'tabla': 'caracterizacion_socioeconomica',
        'seccion': 'Caracterización',
        'columnas': [
            ('escolaridad', 'Escolaridad', 'escolaridad'),
            ('vivienda', 'Vivienda', 'vivienda'),
            ('con_quien_convive', 'Con quién convive', 'con_quien_convive'),
            ('estado_socioeconomico', 'Estado socioeconómico', 'estado_socioeconomico'),
            ('fecha_examen', 'Fecha examen (Caracterización)', 'caracterizacion_fecha_examen'),
        ],
    },
]


# ============================================================
# Export INDIVIDUAL: para las secciones de test solo se muestran estas
# columnas (Resultado / Observación + trazabilidad). El resto de columnas
# (puntajes, repeticiones, vo2_max, etc.) siguen existiendo en la BD y en
# el export general, y se usan internamente para las gráficas.
# Las secciones NO listadas aquí (Historia Clínica, Antropometría,
# Caracterización) se muestran completas.
# ============================================================
_COLUMNAS_VISIBLES_INDIVIDUAL = {
    'vo2_max': ['resultado', 'observaciones', 'evaluador', 'fecha_examen'],
    'test_moca': ['resultado', 'observaciones', 'evaluador', 'fecha_examen'],
    'test_tinetti': ['resultado', 'observaciones', 'evaluador', 'fecha_examen'],
    'test_chair_stand': ['resultado', 'observaciones', 'evaluador', 'fecha_examen'],
}

# Etiquetas simplificadas para las filas visibles del individual.
_ETIQUETAS_INDIVIDUAL = {
    'resultado': 'Resultado',
    'observaciones': 'Observación',
    'evaluador': 'Evaluador',
    'fecha_examen': 'Fecha del examen',
}


def _calcular_icc(cintura, cadera):
    """Calcula el Índice Cintura-Cadera (cintura / cadera).
    Devuelve el ICC redondeado a 2 decimales o None si no hay datos válidos."""
    try:
        if cintura in (None, '') or cadera in (None, ''):
            return None
        cintura = float(cintura)
        cadera = float(cadera)
        if cadera <= 0:
            return None
        return round(cintura / cadera, 2)
    except (TypeError, ValueError):
        return None


def _clasificar_icc(icc, sexo):
    """Clasifica el riesgo del ICC según sexo (umbrales OMS).
    Hombre/Masculino -> 0.90; Mujer/Femenino -> 0.85. Devuelve 'Alto'/'Normal'
    o None si no hay ICC."""
    if icc is None:
        return None
    sexo = (sexo or '').lower()
    # Hombre/Masculino: acepta 'h' (Hombre) y 'm' de Masculino (excluyendo 'mu' de Mujer)
    if sexo.startswith('h') or (sexo.startswith('m') and not sexo.startswith('mu')):
        limite_alto = 0.90
    else:  # Mujer/Femenino (y por defecto el umbral más conservador)
        limite_alto = 0.85
    return 'Alto' if icc >= limite_alto else 'Normal'


def _construir_select_ancho():
    """Arma la lista de SELECT, los encabezados y la tabla de origen de
    cada columna para el export ancho (una fila por paciente)."""
    select_parts = []
    encabezados = []
    tablas_por_col = []  # tabla de origen de cada encabezado (para el color)

    # Historia clínica (tabla pacientes, alias p)
    for col, etiqueta, alias_col in _HISTORIA['columnas']:
        select_parts.append(f'{_HISTORIA["alias"]}.{col} AS "{alias_col}"')
        encabezados.append(etiqueta)
        tablas_por_col.append(_HISTORIA['tabla'])

    # Módulos con LEFT JOIN
    for modulo in _MODULOS:
        for col, etiqueta, alias_col in modulo['columnas']:
            select_parts.append(f'{modulo["alias"]}.{col} AS "{alias_col}"')
            encabezados.append(etiqueta)
            tablas_por_col.append(modulo['tabla'])

    return select_parts, encabezados, tablas_por_col


def _construir_joins():
    """Arma la parte FROM ... LEFT JOIN ... del export ancho."""
    joins = ['FROM pacientes p']
    for modulo in _MODULOS:
        joins.append(
            f'LEFT JOIN {modulo["tabla"]} {modulo["alias"]} '
            f'ON {modulo["alias"]}.paciente_id = p.id'
        )
    return '\n'.join(joins)


def _autoajustar_columnas(ws, num_cols, filas):
    """Ajusta el ancho de columnas según el contenido."""
    for col_idx in range(1, num_cols + 1):
        max_len = 10
        for fila in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=True):
            v = fila[0]
            if v is not None:
                max_len = max(max_len, len(str(v)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 45)


def generar_excel(paciente_id=None):
    """Export ANCHO: una sola hoja, un paciente por fila.
    Todas las tablas unidas por LEFT JOIN desde pacientes."""
    conexion = conectar()
    cursor = conexion.cursor()

    select_parts, encabezados, tablas_por_col = _construir_select_ancho()
    joins = _construir_joins()

    consulta = f'SELECT {", ".join(select_parts)}\n{joins}'
    if paciente_id:
        consulta += ' WHERE p.id = %s ORDER BY p.apellidos, p.nombres'
        cursor.execute(consulta, (paciente_id,))
    else:
        consulta += ' ORDER BY p.apellidos, p.nombres'
        cursor.execute(consulta)

    filas = cursor.fetchall()
    conexion.close()

    # Índices (0-based) de las columnas necesarias para calcular el ICC al vuelo.
    # El ICC no se guarda en BD; se calcula aquí igual que en la vista web.
    idx_sexo = encabezados.index('Sexo') if 'Sexo' in encabezados else None
    idx_cintura = (encabezados.index('Circunferencia cintura')
                   if 'Circunferencia cintura' in encabezados else None)
    idx_cadera = (encabezados.index('Circunferencia cadera')
                  if 'Circunferencia cadera' in encabezados else None)

    # Insertar los encabezados "ICC" y "Riesgo ICC" justo después de
    # "Circunferencia cadera" (o al final si no se encontró).
    if idx_cadera is not None:
        pos_insert = idx_cadera + 1
    else:
        pos_insert = len(encabezados)
    encabezados = (encabezados[:pos_insert] + ['ICC', 'Riesgo ICC']
                   + encabezados[pos_insert:])
    tablas_por_col = (tablas_por_col[:pos_insert] + ['antropometria', 'antropometria']
                      + tablas_por_col[pos_insert:])

    # Reconstruir cada fila insertando los valores calculados de ICC y riesgo.
    filas_calculadas = []
    for fila in filas:
        sexo = fila[idx_sexo] if idx_sexo is not None else None
        cintura = fila[idx_cintura] if idx_cintura is not None else None
        cadera = fila[idx_cadera] if idx_cadera is not None else None
        icc = _calcular_icc(cintura, cadera)
        riesgo = _clasificar_icc(icc, sexo)
        fila = list(fila)
        fila[pos_insert:pos_insert] = [icc, riesgo]
        filas_calculadas.append(fila)
    filas = filas_calculadas

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Datos SIVAM'

    # Encabezados: cada columna se pinta con el color de su módulo, para
    # diferenciar visualmente los grupos (Historia, Antropometría, tests...).
    _cache_fills = {}
    for col_idx, (titulo, tabla) in enumerate(zip(encabezados, tablas_por_col), start=1):
        celda = ws.cell(row=1, column=col_idx, value=titulo)
        color = _COLOR_MODULO.get(tabla, '2E7D32')
        fill = _cache_fills.get(color)
        if fill is None:
            fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
            _cache_fills[color] = fill
        celda.fill = fill
        celda.font = _FONT_HEADER
        celda.alignment = _ALIGN_HEADER

    # Datos
    for fila_idx, fila in enumerate(filas, start=2):
        for col_idx, valor in enumerate(fila, start=1):
            ws.cell(row=fila_idx, column=col_idx, value=valor)

    ws.freeze_panes = 'A2'
    _autoajustar_columnas(ws, len(encabezados), filas)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _seccion_tiene_datos(cursor, modulo, paciente_id):
    """Devuelve un dict {columna_real: valor} si el módulo tiene registro para el paciente,
    o None si no tiene ninguna fila."""
    cols = [c[0] for c in modulo['columnas']]
    select = ', '.join(cols)
    cursor.execute(
        f'SELECT {select} FROM {modulo["tabla"]} WHERE paciente_id = %s',
        (paciente_id,)
    )
    fila = cursor.fetchone()
    if fila is None:
        return None
    return dict(zip(cols, fila))


def generar_excel_individual(paciente_id):
    """Export VERTICAL: un paciente, formato Campo / Valor por secciones.
    Omite las secciones donde el paciente no tenga datos."""
    conexion = conectar()
    cursor = conexion.cursor()

    # Datos de historia clínica (siempre presente porque parte de pacientes)
    cols_hist = [c[0] for c in _HISTORIA['columnas']]
    cursor.execute(
        f'SELECT {", ".join(cols_hist)} FROM pacientes WHERE id = %s',
        (paciente_id,)
    )
    fila_hist = cursor.fetchone()
    if fila_hist is None:
        conexion.close()
        return None
    datos_hist = dict(zip(cols_hist, fila_hist))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Ficha paciente'

    # Encabezado de las dos columnas
    ws.cell(row=1, column=1, value='Campo').fill = _FILL_HEADER
    ws.cell(row=1, column=1).font = _FONT_HEADER
    ws.cell(row=1, column=2, value='Valor').fill = _FILL_HEADER
    ws.cell(row=1, column=2).font = _FONT_HEADER

    fila_actual = 2
    # Gráficas a insertar. Se recolectan en orden y se apilan al final en la
    # columna D con una separación fija, para que NO se superpongan entre sí
    # (las secciones de tests son muy cortas y las imágenes más altas).
    imagenes = []

    def escribir_seccion(titulo, columnas_def, datos, tabla=None):
        nonlocal fila_actual
        # Encabezado de sección (fusiona 2 columnas)
        ws.merge_cells(start_row=fila_actual, start_column=1, end_row=fila_actual, end_column=2)
        celda = ws.cell(row=fila_actual, column=1, value=titulo)
        celda.fill = _FILL_SECCION
        celda.font = _FONT_SECCION
        celda.alignment = _ALIGN_LEFT
        fila_actual += 1

        # Para las secciones de test se muestran solo columnas simplificadas
        # (Resultado / Observación / Evaluador / Fecha). Para el resto,
        # se muestran todas las columnas del módulo.
        visibles = _COLUMNAS_VISIBLES_INDIVIDUAL.get(tabla)

        fila_inicio_datos = fila_actual
        for col, etiqueta, _alias in columnas_def:
            if visibles is not None and col not in visibles:
                continue  # ocultar detalle técnico (sigue en BD y export general)
            etiqueta_mostrar = _ETIQUETAS_INDIVIDUAL.get(col, etiqueta) if visibles else etiqueta
            valor = datos.get(col)
            celda_campo = ws.cell(row=fila_actual, column=1, value=etiqueta_mostrar)
            celda_campo.font = _FONT_CAMPO
            celda_campo.alignment = _ALIGN_LEFT
            celda_valor = ws.cell(row=fila_actual, column=2,
                                  value=valor if valor not in (None, '') else '-')
            celda_valor.alignment = _ALIGN_LEFT
            fila_actual += 1

        # Sección Antropometría: agregar ICC y su riesgo (calculados al vuelo).
        # El sexo se toma de Historia Clínica (datos_hist).
        if tabla == 'antropometria':
            icc = _calcular_icc(datos.get('circunferencia_cintura'),
                                datos.get('circunferencia_cadera'))
            riesgo = _clasificar_icc(icc, datos_hist.get('sexo'))
            for etiqueta_mostrar, valor in (('ICC', icc), ('Riesgo ICC', riesgo)):
                celda_campo = ws.cell(row=fila_actual, column=1, value=etiqueta_mostrar)
                celda_campo.font = _FONT_CAMPO
                celda_campo.alignment = _ALIGN_LEFT
                celda_valor = ws.cell(row=fila_actual, column=2,
                                      value=valor if valor not in (None, '') else '-')
                celda_valor.alignment = _ALIGN_LEFT
                fila_actual += 1

        # Gráfica de la prueba (si aplica y hay valor numérico), anclada a
        # la derecha de la sección (columna D) en la fila de inicio de datos.
        if tabla in graficas.GRAFICA_POR_TABLA:
            datos_grafica = datos
            # VO2 Max y Chair Stand necesitan sexo y edad (de Historia Clínica)
            # para dibujar sus bandas por grupo normativo.
            if tabla in ('vo2_max', 'test_chair_stand'):
                datos_grafica = dict(datos)
                datos_grafica.setdefault('sexo', datos_hist.get('sexo'))
                if datos_grafica.get('edad') in (None, ''):
                    datos_grafica['edad'] = datos_hist.get('edad')
            png = graficas.GRAFICA_POR_TABLA[tabla](datos_grafica)
            if png is not None:
                imagenes.append(png)

    # Historia Clínica siempre se incluye (completa)
    escribir_seccion(_HISTORIA['seccion'], _HISTORIA['columnas'], datos_hist)

    # Módulos: solo si tienen datos
    for modulo in _MODULOS:
        datos = _seccion_tiene_datos(cursor, modulo, paciente_id)
        if datos is not None:
            escribir_seccion(modulo['seccion'], modulo['columnas'], datos,
                             tabla=modulo['tabla'])

    conexion.close()

    # Insertar las gráficas apiladas en la columna D, una debajo de otra.
    # El paso entre gráficas se calcula según el ALTO REAL de cada imagen
    # (convertido a filas de Excel) más un margen, para que NUNCA se solapen
    # aunque la sección de arriba sea muy corta.
    ALTO_FILA_PX = 20      # alto aprox. de una fila por defecto (15 pt ≈ 20 px)
    MARGEN_FILAS = 3       # filas de aire entre una gráfica y la siguiente
    fila_grafica = 2
    for png in imagenes:
        img = XLImage(png)
        # Filas que ocupa la imagen según su alto en píxeles.
        alto_px = getattr(img, 'height', None) or 231
        filas_img = -(-int(alto_px) // ALTO_FILA_PX)  # ceil
        ws.add_image(img, f'D{fila_grafica}')
        fila_grafica += filas_img + MARGEN_FILAS

    # Ancho de columnas
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 45
    ws.column_dimensions['C'].width = 3
    ws.freeze_panes = 'A2'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def nombre_archivo(paciente_id=None, nombre_paciente=None):
    """Genera un nombre de archivo con fecha."""
    fecha = datetime.now().strftime('%Y%m%d_%H%M')
    if paciente_id and nombre_paciente:
        limpio = ''.join(c for c in nombre_paciente if c.isalnum() or c in (' ', '_')).strip()
        limpio = limpio.replace(' ', '_')
        return f'SIVAM_{limpio}_{fecha}.xlsx'
    return f'SIVAM_datos_completos_{fecha}.xlsx'
