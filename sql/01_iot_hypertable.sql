-- ==============================================================================
-- 01_iot_hypertable.sql
-- Pattern: TimescaleDB Hypertables, Compression, and Continuous Aggregates
-- Designed via Tiger MCP 'setup-timescaledb-hypertables' skill
-- ==============================================================================

-- 1. Create standard table with TimescaleDB hypertable clause
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    firmware_version TEXT,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    battery_level DOUBLE PRECISION,
    status TEXT DEFAULT 'OK'
) WITH (
    tsdb.hypertable,
    tsdb.partition_column = 'time',
    tsdb.chunk_interval = '1 day'
);

-- 2. Create compound index optimized for device + time queries
CREATE INDEX IF NOT EXISTS idx_sensor_telemetry_device_time
ON sensor_telemetry (device_id, time DESC);

-- 3. Enable columnstore compression
-- Segments by device_id and orders by time DESC for extreme (90%+) compression
ALTER TABLE sensor_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'time DESC'
);

-- 4. Add automatic compression policy (compress chunks older than 7 days)
SELECT add_compression_policy('sensor_telemetry', INTERVAL '7 days', if_not_exists => TRUE);

-- 5. Add automatic data retention policy (drop raw chunks older than 90 days)
SELECT add_retention_policy('sensor_telemetry', INTERVAL '90 days', if_not_exists => TRUE);

-- 6. Create Continuous Aggregate for hourly rollups
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_device_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    device_id,
    AVG(temperature) AS avg_temp,
    MAX(temperature) AS max_temp,
    MIN(temperature) AS min_temp,
    AVG(humidity) AS avg_humidity,
    COUNT(*) AS readings_count
FROM sensor_telemetry
GROUP BY bucket, device_id
WITH NO DATA;

-- 7. Add continuous aggregate refresh policy
SELECT add_continuous_aggregate_policy('hourly_device_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);
