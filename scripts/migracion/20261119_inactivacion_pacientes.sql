-- SIVAM / PostgreSQL
-- Migración aditiva: conserva íntegros los pacientes y sus relaciones.
-- Ejecutar después de realizar un respaldo de la base de datos.

ALTER TABLE pacientes
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS fecha_inactivacion TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS inactivado_por INTEGER REFERENCES usuarios(id),
    ADD COLUMN IF NOT EXISTS fecha_reactivacion TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reactivado_por INTEGER REFERENCES usuarios(id);

CREATE INDEX IF NOT EXISTS idx_pacientes_activo ON pacientes (activo);
