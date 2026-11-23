from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_PATH = ROOT / 'docs' / 'PROYECTO_FINAL_PRACTICAS_SIVAM.docx'

BLUE = '#1F4E79'
GREEN = '#2E7D32'
LIGHT_BLUE = '#EAF2F8'
LIGHT_GREEN = '#EAF4EA'
GRAY = '#F4F6F7'
TEXT = '#1E2A35'


def save_figure(fig, path):
    fig.savefig(path, dpi=220, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def box(ax, x, y, width, height, label, color=LIGHT_BLUE, edge=BLUE, fontsize=10):
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle='round,pad=0.02,rounding_size=0.025',
        linewidth=1.8, edgecolor=edge, facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, label, ha='center', va='center',
            fontsize=fontsize, color=TEXT, weight='semibold', wrap=True)
    return patch


def arrow(ax, start, end, color=BLUE, rad=0.0):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle='-|>', mutation_scale=15, linewidth=1.5,
        color=color, connectionstyle=f'arc3,rad={rad}', shrinkA=5, shrinkB=5,
    ))


def architecture_diagram(path):
    fig, ax = plt.subplots(figsize=(11.4, 5.7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.subplots_adjust(left=0.03, right=0.97, top=0.90, bottom=0.06)
    ax.set_title('Arquitectura lógica verificada de SIVAM', fontsize=16, weight='bold', color=TEXT, pad=14)

    box(ax, 4.0, 5.65, 4.0, 0.8, 'Usuarios\nAdministrador y profesional de salud', LIGHT_GREEN, GREEN)
    box(ax, 4.0, 4.25, 4.0, 0.9, 'Interfaz web\nPlantillas Jinja2, HTML y CSS')
    box(ax, 3.55, 2.55, 4.9, 1.0, 'Aplicación Flask\nRutas, validaciones, sesión, roles y cálculos', '#E8F0FE', BLUE)
    box(ax, 0.45, 0.7, 3.4, 1.0, 'SQLite\nDesarrollo local', '#F8F9F9', '#566573')
    box(ax, 4.25, 0.7, 3.4, 1.0, 'PostgreSQL o Supabase\nCuando DATABASE_URL está configurada', '#F8F9F9', '#566573')
    box(ax, 8.15, 0.7, 3.4, 1.0, 'Reportes y exportación\nExcel y gráficas', '#FFF6E5', '#B9770E')
    box(ax, 8.65, 3.75, 2.9, 1.0, 'Configuración prevista\nRender y Gunicorn', '#F8F9F9', '#566573', 9.2)

    arrow(ax, (6, 5.65), (6, 5.15), GREEN)
    arrow(ax, (6, 4.25), (6, 3.55))
    arrow(ax, (4.85, 2.55), (2.3, 1.7))
    arrow(ax, (6, 2.55), (5.95, 1.7))
    arrow(ax, (7.25, 2.55), (9.85, 1.7))
    arrow(ax, (8.45, 3.05), (9.65, 3.75), '#566573')
    ax.text(6, 0.15, 'Las fuentes de datos se seleccionan según la configuración del entorno.',
            ha='center', va='center', fontsize=9, color='#566573')
    save_figure(fig, path)


def methodology_diagram(path):
    fig, ax = plt.subplots(figsize=(11.4, 5.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.subplots_adjust(left=0.03, right=0.97, top=0.90, bottom=0.06)
    ax.set_title('Ciclo iterativo e incremental aplicado a SIVAM', fontsize=16, weight='bold', color=TEXT, pad=14)

    steps = [
        (4.55, 5.3, '1. Análisis de necesidad\ny requisitos'),
        (8.0, 3.55, '2. Diseño de datos\ny pantallas'),
        (6.6, 0.75, '3. Desarrollo de módulos\ny reglas programadas'),
        (2.0, 0.75, '4. Prueba funcional\ny corrección'),
        (0.55, 3.55, '5. Ajuste y nuevo\nincremento'),
    ]
    centers = []
    for index, (x, y, label) in enumerate(steps):
        color = LIGHT_GREEN if index in (0, 4) else LIGHT_BLUE
        edge = GREEN if index in (0, 4) else BLUE
        box(ax, x, y, 2.8, 1.0, label, color, edge, 9.4)
        centers.append((x + 1.4, y + 0.5))
    for index in range(len(centers)):
        arrow(ax, centers[index], centers[(index + 1) % len(centers)], GREEN if index == 4 else BLUE, 0.10)
    ax.text(6, 3.45, 'Cada ciclo deja\nun resultado\nfuncional revisable', ha='center', va='center',
            fontsize=10, color=TEXT, weight='semibold',
            bbox=dict(boxstyle='round,pad=0.45', fc='#FCFCFC', ec='#AAB7B8', lw=1.2))
    ax.text(6, 0.13, 'Caracterización analítica: no implica la adopción formal de Scrum, Kanban u otro marco.',
            ha='center', va='center', fontsize=9, color='#566573')
    save_figure(fig, path)


def functionality_chart(path):
    labels = ['Acceso y\nusuarios', 'Pacientes y\nhistoria', 'Módulos de\nvaloración', 'Consulta y\nreportes', 'Datos y\nautorización']
    values = [3, 4, 6, 4, 3]
    colors = [BLUE, '#2E86C1', GREEN, '#B9770E', '#6C3483']
    fig, ax = plt.subplots(figsize=(10.8, 5.4))
    bars = ax.bar(labels, values, color=colors, width=0.64)
    ax.set_title('Inventario de capacidades funcionales observadas', fontsize=16, weight='bold', color=TEXT, pad=14)
    ax.set_ylabel('Capacidades agrupadas')
    ax.set_ylim(0, 7)
    ax.grid(axis='y', color='#D5DBDB', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(axis='y', length=0)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.15, str(value), ha='center', va='bottom',
                fontsize=12, weight='bold', color=TEXT)
    fig.text(0.5, 0.02,
             'Síntesis del repositorio: conteo de capacidades documentadas por bloque; no representa uso, rendimiento ni impacto clínico.',
             ha='center', fontsize=8.8, color='#566573')
    fig.tight_layout(rect=(0.03, 0.07, 0.97, 0.96))
    save_figure(fig, path)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=None):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(text)
    run.font.name = 'Aptos'
    run._element.rPr.rFonts.set(qn('w:ascii'), 'Aptos')
    run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Aptos')
    run.font.size = Pt(9)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table_after(doc, anchor, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    table.autofit = True
    for cell, header in zip(table.rows[0].cells, headers):
        shade(cell, '1F4E79')
        set_cell_text(cell, header, bold=True, color=(255, 255, 255))
    for row_index, row_values in enumerate(rows):
        cells = table.add_row().cells
        for cell, value in zip(cells, row_values):
            if row_index % 2 == 1:
                shade(cell, 'F6F8FA')
            set_cell_text(cell, value)
    anchor.addnext(table._element)
    return table._element


def make_paragraph(doc, text='', style=None, alignment=None, bold_lead=None):
    p = doc.add_paragraph(style=style)
    if alignment is not None:
        p.alignment = alignment
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.line_spacing = 1.15
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p


def add_paragraph_after(doc, anchor, text='', style=None, alignment=None, bold_lead=None):
    p = make_paragraph(doc, text, style, alignment, bold_lead)
    anchor.addnext(p._p)
    return p._p


def add_picture_after(doc, anchor, image_path, width_inches, description, caption, label):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(3)
    shape = p.add_run().add_picture(str(image_path), width=Inches(width_inches))
    shape._inline.docPr.set('descr', description)
    anchor.addnext(p._p)
    caption_p = make_paragraph(doc, caption, style='Caption', alignment=WD_ALIGN_PARAGRAPH.CENTER)
    caption_p.paragraph_format.space_after = Pt(8)
    caption_p._p.get_or_add_pPr().append(OxmlElement('w:keepNext'))
    p._p.addnext(caption_p._p)
    return caption_p._p


def find_paragraph(doc, exact_text):
    for paragraph in doc.paragraphs:
        if paragraph.text == exact_text:
            return paragraph
    raise ValueError(f'No se encontró el párrafo: {exact_text}')


def remove_architecture_placeholder_and_insert(doc, image_path):
    target = None
    for table in doc.tables:
        if 'Diagrama de arquitectura de SIVAM' in table.cell(0, 0).text:
            target = table
            break
    if target is None:
        raise ValueError('No se encontró el marcador de arquitectura')
    table_element = target._element
    lead = make_paragraph(
        doc,
        'El Diagrama 01 representa las relaciones técnicas comprobadas entre la interfaz, la aplicación, la capa de datos y las salidas de información. La conexión a PostgreSQL o Supabase depende de la configuración del entorno; por ello se presenta como posibilidad implementada, no como evidencia de un servicio activo.',
    )
    table_element.addprevious(lead._p)
    image_p = doc.add_paragraph()
    image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_p.paragraph_format.space_after = Pt(3)
    shape = image_p.add_run().add_picture(str(image_path), width=Inches(6.9))
    shape._inline.docPr.set('descr', 'Diagrama de arquitectura lógica verificada de SIVAM')
    lead._p.addnext(image_p._p)
    caption = make_paragraph(doc, 'Diagrama 01. Arquitectura lógica verificada de SIVAM.', style='Caption', alignment=WD_ALIGN_PARAGRAPH.CENTER)
    image_p._p.addnext(caption._p)
    table_element.getparent().remove(table_element)


def update_appendix_row(doc):
    for table in doc.tables:
        if table.cell(0, 0).text.strip() == 'Figura' and table.cell(0, 1).text.strip() == 'Sección':
            first_row = table.rows[1].cells
            set_cell_text(first_row[0], 'Diagrama 01')
            set_cell_text(first_row[1], 'Arquitectura')
            set_cell_text(first_row[2], 'No requiere captura: se incluye en el documento.')
            set_cell_text(first_row[3], 'Arquitectura lógica verificada de SIVAM.')
            return
    raise ValueError('No se encontró la tabla de anexos de figuras')


def main():
    with TemporaryDirectory(prefix='sivam_visual_') as tmp:
        tmp_path = Path(tmp)
        architecture = tmp_path / 'diagrama_arquitectura_sivam.png'
        methodology = tmp_path / 'diagrama_metodologia_iterativa.png'
        chart = tmp_path / 'grafico_capacidades_sivam.png'
        architecture_diagram(architecture)
        methodology_diagram(methodology)
        functionality_chart(chart)

        doc = Document(DOCUMENT_PATH)
        methodology_intro = find_paragraph(doc, 'La evidencia disponible permite caracterizar el proceso como iterativo e incremental, sin afirmar la adopción formal de Scrum, Kanban u otro marco. El avance inicial describe análisis de necesidades, depuración de datos, diseño de arquitectura, construcción de formularios y pruebas; el repositorio conserva artefactos que corresponden a esas actividades. La secuencia reconstruida es la siguiente:')
        anchor = methodology_intro._p
        anchor = add_paragraph_after(doc, anchor, 'Enfoque seleccionado Desarrollo iterativo e incremental', style='Heading 2')
        anchor = add_paragraph_after(doc, anchor, 'Se adopta como enfoque de interpretación del proyecto el desarrollo iterativo e incremental. Un incremento es una porción usable del sistema que amplía el alcance sin esperar a que toda la solución esté terminada; la iteración permite revisar esa porción, corregirla y usar el aprendizaje para el siguiente ciclo. Esta elección describe la secuencia observable del trabajo y no atribuye al proyecto ceremonias, roles o artefactos de Scrum, Kanban u otro marco que no se encuentran documentados.')
        anchor = add_paragraph_after(doc, anchor, 'En SIVAM, el patrón se identifica al contrastar los antecedentes con el repositorio actual. La solución parte de la necesidad de ordenar información y digitalizar instrumentos de valoración; posteriormente se consolidan el acceso con usuarios, la historia clínica y los módulos de evaluación. Más adelante aparecen controles de autorización, fecha de nacimiento y edad estimada, campos opcionales de identificación y teléfono, inactivación de pacientes, unificación del evaluador y ajustes de formularios. Cada ampliación responde a un aspecto funcional concreto y preserva la relación con la entidad paciente.')
        anchor = add_paragraph_after(doc, anchor, 'El ciclo propuesto inicia con la revisión de una necesidad o regla de negocio, continúa con la adecuación de datos e interfaz, implementa rutas, plantillas y validaciones, y finaliza con prueba funcional y corrección. El resultado se incorpora al siguiente incremento solo cuando mantiene la coherencia con los módulos ya existentes. Así se evita confundir una mejora de interfaz con una modificación de datos o una regla clínica no validada.')
        anchor = add_paragraph_after(doc, anchor, 'La evidencia disponible permite demostrar los artefactos implementados, pero no permite reconstruir la duración de cada ciclo, las reuniones realizadas, responsables específicos ni una herramienta formal de seguimiento. Por esta razón, el enfoque se presenta como una caracterización razonada del desarrollo y no como certificación de una metodología institucional.')
        anchor = add_picture_after(doc, anchor, methodology, 6.8, 'Diagrama del ciclo iterativo e incremental aplicado a SIVAM', 'Diagrama 02. Ciclo iterativo e incremental reconstruido para el desarrollo de SIVAM.', 'Diagrama 02')
        anchor = add_table_after(doc, anchor, ['Incremento', 'Resultado observable', 'Contribución al siguiente ciclo'], [
            ('Base operativa', 'Inicio de sesión, usuarios, roles y protección de rutas.', 'Establece quién puede acceder y operar los registros.'),
            ('Atención y valoración', 'Historia clínica y seis módulos de evaluación relacionados con paciente_id.', 'Centraliza el registro y habilita cálculos o clasificaciones programadas.'),
            ('Consulta y salida', 'Dashboards, búsqueda, reporte de pendientes y exportación a Excel.', 'Facilita la consulta y la revisión de cobertura de evaluaciones.'),
            ('Ciclo de vida y datos', 'Autorización, evidencia preservada, edad calculada, datos opcionales e inactivación.', 'Refuerza la trazabilidad funcional y abre necesidades de validación institucional.'),
        ])
        anchor = add_picture_after(doc, anchor, chart, 6.7, 'Gráfico de inventario de capacidades funcionales observadas en SIVAM', 'Gráfico 01. Capacidades funcionales agrupadas identificadas en la revisión del repositorio.', 'Gráfico 01')
        anchor = add_paragraph_after(doc, anchor, 'El Gráfico 01 es una síntesis de alcance: cuenta capacidades agrupadas para mostrar dónde se concentra la funcionalidad revisada. No mide pacientes atendidos, desempeño, adopción, calidad clínica, tiempo ahorrado ni nivel de seguridad.')

        remove_architecture_placeholder_and_insert(doc, architecture)
        update_appendix_row(doc)
        doc.core_properties.title = 'Proyecto final de prácticas profesionales SIVAM'
        doc.core_properties.subject = 'Documento académico con metodología iterativa e incremental y diagramas técnicos'
        doc.core_properties.author = 'Brayan Alfonso Contreras Ustate'
        doc.save(DOCUMENT_PATH)
        print(f'Actualizado: {DOCUMENT_PATH}')


if __name__ == '__main__':
    main()
