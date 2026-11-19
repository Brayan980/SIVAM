# ============================================================
# Campos de la tabla "pacientes" y utilidades compartidas
# entre importar_a_sqlite.py y app.py
# ============================================================
import unicodedata
from datetime import date

# Todas las columnas clínicas (sin contar id, nombres, apellidos, busqueda)
CAMPOS_CLINICOS = [
    'edad', 'fecha_de_nacimiento', 'tipo_documento', 'numero_documento', 'telefono', 'sexo', 'barrio',
    'antecedentes_familiares', 'con_quien_vives', 'caidas_previas',
    'lesiones_musculoesqueleticas_o_cirugia', 'medicacion_y_suplementacion',
    'medicacion_sumplementacion', 'patologia_actual',
    'habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados',
    'alergias', 'ejercicio_y_actividad_fisica_leve_moderado_intenso',
    'actividad_sexual', 'riesgo_cardiovascular_con_riesgo_o_sin_riesgo',
]

CAMPOS = ['nombres', 'apellidos'] + CAMPOS_CLINICOS + ['edad_es_estimada']

# Etiquetas legibles para mostrar en el formulario y en la ficha
ETIQUETAS = {
    'edad': 'Edad',
    'edad_es_estimada': 'Edad estimada',
    'fecha_de_nacimiento': 'Fecha de nacimiento',
    'tipo_documento': 'Tipo de documento',
    'numero_documento': 'Número de documento',
    'telefono': 'Teléfono',
    'fecha_creacion': 'Fecha de registro',
    'sexo': 'Sexo',
    'barrio': 'Barrio',
    'antecedentes_familiares': 'Antecedentes familiares',
    'con_quien_vives': 'Con quién vive',
    'caidas_previas': 'Caídas previas',
    'lesiones_musculoesqueleticas_o_cirugia': 'Lesiones musculoesqueléticas / cirugías',
    'medicacion_y_suplementacion': 'Medicación y suplementación',
    'medicacion_sumplementacion': 'Medicación / suplementación (adicional)',
    'patologia_actual': 'Patología actual',
    'habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados': 'Hábitos y estilos de vida',
    'alergias': 'Alergias',
    'ejercicio_y_actividad_fisica_leve_moderado_intenso': 'Ejercicio y actividad física',
    'actividad_sexual': 'Actividad sexual',
    'riesgo_cardiovascular_con_riesgo_o_sin_riesgo': 'Riesgo cardiovascular',
}


def normalizar(texto):
    """Minusculas y sin tildes, para busquedas que ignoren como se escriban."""
    if texto is None:
        return ''
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().strip()


def calcular_edad(fecha_de_nacimiento, fecha_referencia=None):
    """Devuelve años cumplidos o None si la fecha no es válida o es futura."""
    if not fecha_de_nacimiento:
        return None
    try:
        nacimiento = date.fromisoformat(str(fecha_de_nacimiento)[:10])
    except (TypeError, ValueError):
        return None
    referencia = fecha_referencia or date.today()
    if nacimiento > referencia:
        return None
    return referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )
