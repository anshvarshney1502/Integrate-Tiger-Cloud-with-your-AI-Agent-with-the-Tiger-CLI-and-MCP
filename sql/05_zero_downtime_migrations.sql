-- ==============================================================================
-- 05_zero_downtime_migrations.sql
-- Pattern: Safe, Zero-Downtime PostgreSQL Schema Migrations
-- Designed via Tiger MCP 'postgres-database-migration' skill
-- ==============================================================================

-- RULE 1: Never add a NOT NULL column without a DEFAULT in one step on large tables
-- Safe pattern for adding a new column with default:
ALTER TABLE sensor_telemetry ADD COLUMN IF NOT EXISTS battery_voltage DOUBLE PRECISION DEFAULT 3.3;

-- RULE 2: Always create indexes CONCURRENTLY to avoid AccessExclusiveLock table locks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_telemetry_status
ON sensor_telemetry (status);

-- RULE 3: Adding NOT NULL constraint safely without table lock:
-- Step 3a: Add check constraint NOT VALID (instantaneous)
ALTER TABLE sensor_telemetry ADD CONSTRAINT chk_sensor_device_id_not_null CHECK (device_id IS NOT NULL) NOT VALID;
-- Step 3b: Validate constraint in background without blocking writes
ALTER TABLE sensor_telemetry VALIDATE CONSTRAINT chk_sensor_device_id_not_null;

-- RULE 4: Zero-downtime column rename via view or blue-green staging
-- (Test first on service fork with 'tiger service fork <service-id>')
