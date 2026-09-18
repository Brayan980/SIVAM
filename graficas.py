# ============================================================
# Generación de gráficas de barra para el export individual.
# Cada gráfica muestra el valor real de la prueba sobre una escala
# con bandas de referencia coloreadas y ETIQUETADAS, más un marcador
# claro (rombo azul) que indica dónde cae el paciente. El título
# resume el valor y el nivel alcanzado.
#
# Se usa el backend 'Agg' (sin ventana) para render a imagen PNG en
# memoria (BytesIO), que luego openpyxl inserta en la hoja de Excel.
# ============================================================
from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # backend sin GUI, seguro en servidor
import matplotlib.pyplot as plt


# --- Paleta consistente con SIVAM ---
_VERDE = '#2E7D32'
_NARANJA = '#F39C12'
_ROJO = '#C0392B'
_MARCADOR = '#0D3B66'   # azul oscuro: contrasta con las 3 bandas

# --- Paleta para las 5 bandas de VO2 Max (peor -> mejor) ---
_VO2_BAJO = '#C0392B'      # rojo
_VO2_REGULAR = '#E67E22'   # naranja
_VO2_BUENO = '#F1C40F'     # amarillo
_VO2_EXCELENTE = '#7DB33A' # verde claro
_VO2_SUPERIOR = '#2E7D32'  # verde


# ============================================================
# Clasificación de VO2 Max (ml/kg/min) - escala estándar Cooper Institute
# (ACSM), por sexo y grupo de edad. Es la ÚNICA fuente de verdad tanto
# para el cálculo del resultado (app.py la importa) como para las bandas
# de la gráfica del reporte. Cada tupla marca el límite INFERIOR (>=) para
# alcanzar la categoría: (Superior, Excelente, Bueno, Regular).
# ============================================================
VO2_TABLA = {
    'hombre': [
        # (edad_min, edad_max, superior, excelente, bueno, regular)
        (0, 29, 55.4, 51.1, 45.4, 41.7),
        (30, 39, 54.0, 48.3, 44.0, 40.5),
        (40, 49, 52.5, 46.4, 42.4, 38.5),
        (50, 59, 48.9, 43.4, 39.2, 35.6),
        (60, 69, 45.7, 39.5, 35.5, 32.3),
        (70, 200, 42.1, 36.7, 32.3, 29.4),
    ],
    'mujer': [
        (0, 29, 49.6, 43.9, 39.5, 36.1),
        (30, 39, 47.4, 42.4, 37.8, 34.4),
        (40, 49, 45.3, 39.7, 36.3, 33.0),
        (50, 59, 41.1, 36.7, 33.0, 30.1),
        (60, 69, 37.8, 33.0, 30.0, 27.5),
        (70, 200, 36.7, 30.9, 28.1, 25.9),
    ],
}


def _vo2_fila(edad, sexo):
    """Devuelve la fila de umbrales (superior, excelente, bueno, regular)
    para la edad y sexo dados, o None si no se puede determinar."""
    try:
        edad = int(float(edad)) if edad not in (None, '') else None
    except (TypeError, ValueError):
        edad = None
    if edad is None:
        return None
    sexo = (sexo or '').lower()
    # Hombre/Masculino: acepta 'h' (Hombre) y 'm' de Masculino (excluye 'mu' de Mujer)
    if sexo.startswith('h') or (sexo.startswith('m') and not sexo.startswith('mu')):
        tabla = VO2_TABLA['hombre']
    else:
        tabla = VO2_TABLA['mujer']
    for edad_min, edad_max, superior, excelente, bueno, regular in tabla:
        if edad_min <= edad <= edad_max:
            return superior, excelente, bueno, regular
    return None


def clasificar_vo2_max(vo2, edad, sexo):
    """Devuelve el nivel cualitativo (Superior/Excelente/Bueno/Regular/Bajo)
    a partir del VO2 Max (ml/kg/min), la edad y el sexo del paciente.
    Devuelve None si faltan datos para clasificar."""
    valor = _to_float(vo2)
    if valor is None:
        return None
    fila = _vo2_fila(edad, sexo)
    if fila is None:
        return None
    superior, excelente, bueno, regular = fila
    if valor >= superior:
        return 'Superior'
    if valor >= excelente:
        return 'Excelente'
    if valor >= bueno:
        return 'Bueno'
    if valor >= regular:
        return 'Regular'
    return 'Bajo'


# ============================================================
# Clasificación del Test Chair Stand (30-Second Chair Stand del Senior
# Fitness Test, Rikli & Jones). El rango "normal" de repeticiones depende
# del SEXO y la EDAD. Única fuente de verdad para el cálculo (app.py) y las
# bandas de la gráfica. Cada tupla: (edad_min, edad_max, normal_bajo, normal_alto).
# ============================================================
CHAIR_STAND_TABLA = {
    'hombre': [
        (0, 64, 14, 19),
        (65, 69, 12, 18),
        (70, 74, 12, 17),
        (75, 79, 11, 17),
        (80, 84, 10, 15),
        (85, 89, 8, 14),
        (90, 200, 7, 12),
    ],
    'mujer': [
        (0, 64, 12, 17),
        (65, 69, 11, 16),
        (70, 74, 10, 15),
        (75, 79, 10, 15),
        (80, 84, 9, 14),
        (85, 89, 8, 13),
        (90, 200, 4, 11),
    ],
}

# Paleta de las 6 bandas del Chair Stand (peor -> mejor)
_CS_MUY_POBRE = '#922B21'   # rojo oscuro
_CS_POBRE = '#C0392B'       # rojo
_CS_REGULAR = '#E67E22'     # naranja
_CS_PROMEDIO = '#F1C40F'    # amarillo
_CS_ALTO = '#7DB33A'        # verde claro
_CS_SUPERIOR = '#2E7D32'    # verde


def _chair_stand_rango(edad, sexo):
    """Devuelve (normal_bajo, normal_alto) para la edad y sexo dados,
    o None si no se puede determinar (sin edad)."""
    try:
        edad = int(float(edad)) if edad not in (None, '') else None
    except (TypeError, ValueError):
        edad = None
    if edad is None:
        return None
    sexo = (sexo or '').lower()
    if sexo.startswith('h') or (sexo.startswith('m') and not sexo.startswith('mu')):
        tabla = CHAIR_STAND_TABLA['hombre']
    else:
        tabla = CHAIR_STAND_TABLA['mujer']
    for edad_min, edad_max, normal_bajo, normal_alto in tabla:
        if edad_min <= edad <= edad_max:
            return normal_bajo, normal_alto
    return tabla[-1][2], tabla[-1][3]


def clasificar_chair_stand(repeticiones, edad, sexo):
    """Clasifica el Chair Stand cruzando repeticiones con el rango normal por
    edad y sexo (Senior Fitness Test). Devuelve (resultado, percentil).
    Si falta la edad, usa una escala genérica de respaldo por repeticiones.

    Niveles: Muy Pobre, Pobre, Regular, Promedio, Alto, Superior.
    """
    try:
        repeticiones = int(repeticiones)
    except (TypeError, ValueError):
        repeticiones = 0

    rango = _chair_stand_rango(edad, sexo)
    if rango is None:
        # Escala genérica de respaldo (sin edad) para no bloquear el guardado.
        if repeticiones <= 10:
            return 'Muy Pobre', 10
        if repeticiones == 11:
            return 'Pobre', 25
        if repeticiones == 12:
            return 'Regular', 50
        if repeticiones == 13:
            return 'Promedio', 60
        if repeticiones <= 15:
            return 'Alto', 85
        return 'Superior', 95

    normal_bajo, normal_alto = rango
    ancho = max(1, normal_alto - normal_bajo)
    medio = (normal_bajo + normal_alto) / 2

    if repeticiones < normal_bajo - ancho:
        return 'Muy Pobre', 5
    if repeticiones < normal_bajo:
        return 'Pobre', 20
    if repeticiones < medio:
        return 'Regular', 40
    if repeticiones <= normal_alto:
        return 'Promedio', 55
    if repeticiones <= normal_alto + ancho:
        return 'Alto', 80
    return 'Superior', 95


def _bandas_chair_stand(edad, sexo, maximo):
    """Construye las 6 bandas (inicio, fin, color, nombre) del Chair Stand
    según sexo y edad, alineadas con clasificar_chair_stand. Devuelve None
    si no hay rango (sin edad)."""
    rango = _chair_stand_rango(edad, sexo)
    if rango is None:
        return None
    normal_bajo, normal_alto = rango
    ancho = max(1, normal_alto - normal_bajo)
    medio = (normal_bajo + normal_alto) / 2
    # Cortes coherentes con clasificar_chair_stand:
    #  Muy Pobre: [0, normal_bajo - ancho)
    #  Pobre:     [normal_bajo - ancho, normal_bajo)
    #  Regular:   [normal_bajo, medio)
    #  Promedio:  [medio, normal_alto]  (usamos normal_alto+1 como fin exclusivo)
    #  Alto:      (normal_alto, normal_alto + ancho]
    #  Superior:  (normal_alto + ancho, maximo]
    c1 = max(0, normal_bajo - ancho)
    c2 = normal_bajo
    c3 = medio
    c4 = normal_alto + 1
    c5 = normal_alto + ancho + 1
    return [
        (0,  c1, _CS_MUY_POBRE, 'Muy Pobre'),
        (c1, c2, _CS_POBRE,     'Pobre'),
        (c2, c3, _CS_REGULAR,   'Regular'),
        (c3, c4, _CS_PROMEDIO,  'Promedio'),
        (c4, c5, _CS_ALTO,      'Alto'),
        (c5, maximo, _CS_SUPERIOR, 'Superior'),
    ]


def _bandas_vo2(edad, sexo, maximo):
    """Construye las 5 bandas (inicio, fin, color, nombre) del VO2 Max según
    sexo y edad, para que coincidan EXACTAMENTE con la clasificación del
    reporte. Devuelve None si no hay umbrales para ese sexo/edad."""
    fila = _vo2_fila(edad, sexo)
    if fila is None:
        return None
    superior, excelente, bueno, regular = fila
    return [
        (0,         regular,   _VO2_BAJO,      'Bajo'),
        (regular,   bueno,     _VO2_REGULAR,   'Regular'),
        (bueno,     excelente, _VO2_BUENO,     'Bueno'),
        (excelente, superior,  _VO2_EXCELENTE, 'Excelente'),
        (superior,  maximo,    _VO2_SUPERIOR,  'Superior'),
    ]


def _fig_a_bytes(fig):
    """Renderiza una figura matplotlib a PNG en memoria y la cierra."""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def _nivel_de(valor, bandas):
    """Devuelve el nombre de la banda en la que cae el valor."""
    for inicio, fin, _color, nombre in bandas:
        if inicio <= valor < fin:
            return nombre
    # Si es igual al máximo, cae en la última banda
    if bandas and valor >= bandas[-1][1]:
        return bandas[-1][3]
    return ''


def _grafica_barra(titulo, valor, minimo, maximo, bandas, unidad=''):
    """Dibuja una escala horizontal con bandas de referencia etiquetadas y
    un marcador (rombo) en el valor del paciente.

    bandas: lista de tuplas (inicio, fin, color, nombre).
    valor:  valor real del paciente (numérico).
    """
    fig, ax = plt.subplots(figsize=(5.2, 2.2))

    valor_acotado = max(minimo, min(valor, maximo))
    rango_total = max(1e-9, maximo - minimo)

    # Bandas de referencia (barra de fondo coloreada, opacas y sólidas)
    for inicio, fin, color, _nombre in bandas:
        ax.axvspan(inicio, fin, ymin=0.45, ymax=0.80, color=color, alpha=0.85)

    # Líneas divisorias entre bandas
    for inicio, fin, _color, _nombre in bandas[1:]:
        ax.axvline(inicio, color='white', linewidth=1.2, ymin=0.45, ymax=0.80, zorder=3)

    # Etiquetas de las bandas. Los tramos angostos se rotan en diagonal (y con
    # fuente algo menor) para que los nombres no se solapen; los tramos anchos
    # quedan horizontales. Una línea guía tenue conecta cada nombre con su banda.
    ancho_min_horizontal = 0.16 * rango_total  # bajo este ancho se rota la etiqueta
    for inicio, fin, _color, nombre in bandas:
        centro = (inicio + fin) / 2
        estrecho = (fin - inicio) < ancho_min_horizontal
        # Línea guía desde debajo de la barra hasta el inicio de la etiqueta
        ax.plot([centro, centro], [0.10, 0.42],
                color='#CCCCCC', linewidth=0.7, zorder=1)
        if estrecho:
            ax.text(centro, 0.05, nombre, ha='right', va='top',
                    fontsize=7.5, color='#444444', rotation=40,
                    rotation_mode='anchor')
        else:
            ax.text(centro, 0.02, nombre, ha='center', va='top',
                    fontsize=8, color='#444444')

    # Marcador del valor del paciente: rombo azul + línea guía
    ax.axvline(valor_acotado, color=_MARCADOR, linewidth=1.4,
               ymin=0.45, ymax=0.80, zorder=4)
    ax.plot([valor_acotado], [0.625], marker='D', markersize=11,
            color=_MARCADOR, zorder=5,
            markeredgecolor='white', markeredgewidth=1.2)

    # Título con valor y nivel
    nivel = _nivel_de(valor, bandas)
    val_txt = f'{valor:g}{unidad}'
    encabezado = f'{titulo}\nPaciente: {val_txt}'
    if nivel:
        encabezado += f'  \u2192  {nivel}'
    ax.set_title(encabezado, fontsize=9.5, fontweight='bold',
                 color='#333333', pad=8)

    ax.set_xlim(minimo, maximo)
    ax.set_ylim(-0.75, 1.05)
    ax.set_yticks([])
    ax.tick_params(axis='x', labelsize=8)
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)
    # Bajar el eje X (línea + números) para que no choque con las etiquetas.
    ax.spines['bottom'].set_position(('data', -0.62))
    ax.spines['bottom'].set_color('#BBBBBB')

    return _fig_a_bytes(fig)


def _to_float(valor):
    """Convierte a float de forma segura. Devuelve None si no se puede."""
    if valor is None or valor == '':
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


# ============================================================
# Una función por prueba. Cada una recibe el dict de datos de la
# sección y devuelve un BytesIO con el PNG, o None si no hay valor
# numérico para graficar.
#
# Nota sobre colores: en cada prueba el color se asigna según sea
# mejor o peor clínicamente (verde = mejor, rojo = peor), no según la
# posición en la escala.
# ============================================================

def grafica_vo2(datos):
    """VO2 Max (ml/kg/min): más alto es mejor.

    Dibuja las MISMAS 5 bandas de la web (Bajo, Regular, Bueno, Excelente,
    Superior) calculadas según el sexo y la edad del paciente, para que la
    gráfica coincida con el resultado cualitativo del reporte."""
    valor = _to_float(datos.get('vo2_max'))
    if valor is None:
        return None

    maximo = 60
    bandas = _bandas_vo2(datos.get('edad'), datos.get('sexo'), maximo)
    if bandas is None:
        # Sin edad no se pueden aplicar los umbrales estándar: se omite la
        # gráfica para no mostrar bandas genéricas que contradigan el texto.
        # (El umbral por sexo usa el mismo criterio que el cálculo de la web.)
        return None
    # Asegurar que la escala cubra el valor del paciente si excede el máximo
    maximo = max(maximo, valor + 2)
    bandas[-1] = (bandas[-1][0], maximo, bandas[-1][2], bandas[-1][3])

    return _grafica_barra('VO2 Max (ml/kg/min)', valor, 0, maximo, bandas)


def grafica_moca(datos):
    """MoCA (0-30): más alto es mejor. Normal >= 26."""
    valor = _to_float(datos.get('puntaje_total'))
    if valor is None:
        return None
    bandas = [
        (0, 18, _ROJO, 'Deterioro'),
        (18, 26, _NARANJA, 'Leve'),
        (26, 30, _VERDE, 'Normal'),
    ]
    return _grafica_barra('MoCA - Puntaje total', valor, 0, 30, bandas)


def grafica_tinetti(datos):
    """Tinetti (0-28): más alto es mejor (menor riesgo de caída)."""
    valor = _to_float(datos.get('puntaje_total'))
    if valor is None:
        return None
    bandas = [
        (0, 19, _ROJO, 'Alto riesgo'),
        (19, 24, _NARANJA, 'Riesgo mod.'),
        (24, 28, _VERDE, 'Bajo riesgo'),
    ]
    return _grafica_barra('Tinetti - Puntaje total', valor, 0, 28, bandas)


def grafica_chair_stand(datos):
    """Chair Stand (repeticiones): más repeticiones es mejor.

    Dibuja las MISMAS 6 clasificaciones de la web (Muy Pobre, Pobre, Regular,
    Promedio, Alto, Superior) calculadas según el rango normal por sexo y edad
    (Senior Fitness Test), para que la gráfica coincida con el resultado."""
    valor = _to_float(datos.get('repeticiones'))
    if valor is None:
        return None

    maximo = 25
    bandas = _bandas_chair_stand(datos.get('edad'), datos.get('sexo'), maximo)
    if bandas is None:
        # Sin edad no se pueden aplicar los rangos normativos: se omite la
        # gráfica para no mostrar bandas genéricas que contradigan el texto.
        return None
    # Asegurar que la escala cubra el valor si excede el máximo previsto.
    maximo = max(maximo, valor + 2)
    bandas[-1] = (bandas[-1][0], maximo, bandas[-1][2], bandas[-1][3])

    return _grafica_barra('Chair Stand - Repeticiones', valor, 0, maximo, bandas)


# Mapa tabla -> función de gráfica, usado por el export individual.
GRAFICA_POR_TABLA = {
    'vo2_max': grafica_vo2,
    'test_moca': grafica_moca,
    'test_tinetti': grafica_tinetti,
    'test_chair_stand': grafica_chair_stand,
}
