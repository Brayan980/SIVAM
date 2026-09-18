# PENDIENTES DE DATOS - IMPORTACIÓN EXCEL

## Casos excluidos o con datos inciertos

### 1. María Elsi/Elsy Arena(s)
- **Estado**: EXCLUIDA por falta de datos confiables
- **Razón**: No tiene edad en VO2, no aparece en Historia Clínica
- **Datos disponibles**: Solo nombre (Maria Elsi Arena / Maria elsy Arenas)
- **Acción requerida**: Revisar con coordinación del proyecto para obtener datos completos

### 2. Cleotilde Cantillo/Castilla Torres
- **Estado**: CREADA con apellido sin confirmar
- **Nombre usado**: Cleotilde Cantillo Torres (de hoja Antropometría)
- **Datos disponibles**: Edad 77, Sexo Mujer
- **Nota**: Marcada como pendiente de confirmación en sistema
- **Acción requerida**: Confirmar apellido correcto con coordinación (Cantillo vs Castilla)

### 3. Yudith del Carmen Tello de Maturana
- **Estado**: SIN MATCH - pendiente de revisión
- **Razón**: No hay pacientes con mismo nombre en base de datos
- **Datos disponibles**: Nombre completo en Antropometría
- **Acción requerida**: Revisar con coordinación del proyecto

### 4. Ana Barbosa Perez
- **Estado**: SIN MATCH - pendiente de revisión
- **Razón**: No hay pacientes con mismo nombre en base de datos
- **Datos disponibles**: Nombre completo en MOCA
- **Acción requerida**: Revisar con coordinación del proyecto

### 5. Flor López Martinez
- **Estado**: EXCLUIDA por datos incompletos
- **Razón**: Nombre completo mal ubicado en Excel (en columna 'N' en lugar de 'NOMBRES'/'APELLIDOS'), columna 'APELLIDOS' contiene "nan"
- **Datos disponibles**: Tests completos (MOCA=BAJO, TINETTI=POBRE, CHAIR=X) pero estructura de columnas incorrecta
- **Acción requerida**: Revisar fuente original del Excel o corregir estructura manualmente

## Casos con match manual confirmado

### 1. Maria Trinidad Barbosa/Varbosa De Cañavera
- **Estado**: IMPORTADO con mapeo manual
- **Mapeo**: Barbosa → Varbosa (error de tipeo en Excel)
- **Hojas afectadas**: Antropometría, VO2, MOCA

### 2. Francisco Manuel Barreto/Barrero Perez
- **Estado**: IMPORTADO con mapeo manual
- **Mapeo**: Barreto → Barrero (error de tipeo en Excel)
- **Hojas afectadas**: Antropometría

### 3. Maria del Rosario Dora/Doria Mercado
- **Estado**: IMPORTADO con mapeo manual
- **Mapeo**: Dora → Doria (error de tipeo en Excel)
- **Hojas afectadas**: MOCA

### 4. Alba Marina Chavez Banqueth/Chávez
- **Estado**: IMPORTADO con mapeo manual
- **Mapeo**: Chavez Banqueth → Chávez (apellido truncado en Historia Clínica)
- **Hojas afectadas**: Antropometría

---
*Documento generado durante importación de datos del Excel a PostgreSQL*
*Fecha: 2026-09-03*
