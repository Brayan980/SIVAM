# ============================================================
# Campos de la tabla "pacientes" y utilidades compartidas
# entre importar_a_sqlite.py y app.py
# ============================================================
import unicodedata

# Todas las columnas clínicas (sin contar id, nombres, apellidos, busqueda)
CAMPOS_CLINICOS = [
    'edad', 'fecha_de_nacimiento', 'sexo', 'barrio',
    'antecedentes_familiares', 'con_quien_vives', 'caidas_previas',
    'lesiones_musculoesqueleticas_o_cirugia', 'medicacion_y_suplementacion',
    'medicacion_sumplementacion', 'patologia_actual',
    'habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados',
    'alergias', 'ejercicio_y_actividad_fisica_leve_moderado_intenso',
    'actividad_sexual', 'riesgo_cardiovascular_con_riesgo_o_sin_riesgo',
]

CAMPOS = ['nombres', 'apellidos'] + CAMPOS_CLINICOS

# Etiquetas legibles para mostrar en el formulario y en la ficha
ETIQUETAS = {
    'edad': 'Edad',
    'fecha_de_nacimiento': 'Fecha de nacimiento',
    'sexo': 'Sexo',
    'barrio': 'Barrio',
    'antecedentes_familiares': 'Antecedentes familiares',
    'con_quien_vives': 'Con quién vive',
    'caidas_previas': 'Caídas previas',
    'lesiones_musculoesqueleticas_o_cirugia': 'Lesiones musculoesqueléticas / cirugías',
    'medicacion_y_suplementacion': 'Medicación y suplementación',
    'medicacion_sumplementacion': 'Medicación / suplementación (adicional)',
    'patologia_actual': 'Patología actual',
    'habitos_y_estilos_de_vida_alcohol_tabaco_azucares_alimentos_procesados': 'Hábitos y estilo de vida',
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
