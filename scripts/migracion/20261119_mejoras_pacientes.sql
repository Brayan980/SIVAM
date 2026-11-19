-- SIVAM / PostgreSQL
-- Migración aditiva para instalaciones que ya aplicaron la migración de privacidad.
-- No actualiza ni elimina información existente.

ALTER TABLE pacientes
    ADD COLUMN IF NOT EXISTS edad_es_estimada BOOLEAN,
    ADD COLUMN IF NOT EXISTS tipo_documento TEXT,
    ADD COLUMN IF NOT EXISTS numero_documento TEXT,
    ADD COLUMN IF NOT EXISTS telefono TEXT;

ALTER TABLE test_chair_stand
    ADD COLUMN IF NOT EXISTS edad_evaluacion INTEGER;
