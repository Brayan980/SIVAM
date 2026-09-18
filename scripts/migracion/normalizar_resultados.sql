-- ============================================================
-- Normalización de la columna 'resultado' en las tablas de tests.
--
-- Motivo: los registros históricos importados desde Excel se guardaron en
-- MAYÚSCULAS o con textos incompletos (p. ej. 'SUPERIOR', 'BAJO', 'MODERADO'),
-- mientras que los registros creados desde la web (app.py) usan un formato
-- capitalizado y descriptivo (p. ej. 'Superior', 'Bajo Riesgo', 'Riesgo Moderado').
-- Esto hacía que el dashboard mostrara porciones duplicadas para el mismo nivel.
--
-- Este script convierte los valores antiguos al formato EXACTO de la web.
-- Es idempotente: volver a ejecutarlo no cambia nada una vez normalizado.
--
-- Motor: SQLite (clinica.db). Se usa UPPER(TRIM(resultado)) en el WHERE para
-- capturar cualquier variante de mayúsculas/minúsculas o espacios sobrantes.
--
-- RECOMENDACIÓN: hacer una copia de clinica.db antes de ejecutar.
-- ============================================================

BEGIN TRANSACTION;

-- ------------------------------------------------------------
-- VO2 Max  -> Superior / Excelente / Bueno / Regular / Bajo
-- ------------------------------------------------------------
UPDATE vo2_max SET resultado = 'Superior'  WHERE UPPER(TRIM(resultado)) = 'SUPERIOR';
UPDATE vo2_max SET resultado = 'Excelente' WHERE UPPER(TRIM(resultado)) = 'EXCELENTE';
UPDATE vo2_max SET resultado = 'Bueno'     WHERE UPPER(TRIM(resultado)) = 'BUENO';
UPDATE vo2_max SET resultado = 'Regular'   WHERE UPPER(TRIM(resultado)) = 'REGULAR';
UPDATE vo2_max SET resultado = 'Bajo'      WHERE UPPER(TRIM(resultado)) = 'BAJO';

-- ------------------------------------------------------------
-- Test MoCA  -> Normal / PDCL / PDCM / NADA MENTAL
-- (PDCL, PDCM y NADA MENTAL ya coinciden con la web; solo se ajusta NORMAL)
-- ------------------------------------------------------------
UPDATE test_moca SET resultado = 'Normal'      WHERE UPPER(TRIM(resultado)) = 'NORMAL';
UPDATE test_moca SET resultado = 'NADA MENTAL' WHERE UPPER(TRIM(resultado)) = 'NADA MENTAL';

-- ------------------------------------------------------------
-- Test Tinetti  -> Bajo Riesgo / Riesgo Moderado / Alto Riesgo
-- (los históricos guardan solo el nivel: 'BAJO', 'MODERADO', 'ALTO')
-- ------------------------------------------------------------
UPDATE test_tinetti SET resultado = 'Bajo Riesgo'     WHERE UPPER(TRIM(resultado)) IN ('BAJO', 'BAJO RIESGO');
UPDATE test_tinetti SET resultado = 'Riesgo Moderado' WHERE UPPER(TRIM(resultado)) IN ('MODERADO', 'RIESGO MODERADO');
UPDATE test_tinetti SET resultado = 'Alto Riesgo'     WHERE UPPER(TRIM(resultado)) IN ('ALTO', 'ALTO RIESGO');

-- ------------------------------------------------------------
-- Test Chair Stand  -> Muy Pobre / Pobre / Regular / Promedio / Alto / Superior
-- ------------------------------------------------------------
UPDATE test_chair_stand SET resultado = 'Muy Pobre' WHERE UPPER(TRIM(resultado)) = 'MUY POBRE';
UPDATE test_chair_stand SET resultado = 'Pobre'     WHERE UPPER(TRIM(resultado)) = 'POBRE';
UPDATE test_chair_stand SET resultado = 'Regular'   WHERE UPPER(TRIM(resultado)) = 'REGULAR';
UPDATE test_chair_stand SET resultado = 'Promedio'  WHERE UPPER(TRIM(resultado)) = 'PROMEDIO';
UPDATE test_chair_stand SET resultado = 'Alto'      WHERE UPPER(TRIM(resultado)) = 'ALTO';
UPDATE test_chair_stand SET resultado = 'Superior'  WHERE UPPER(TRIM(resultado)) = 'SUPERIOR';

COMMIT;
