-- ==============================================================================
-- 04_timescaledb_hyperfunctions.sql
-- Pattern: Advanced Time-Series Analytics with TimescaleDB Toolkit Hyperfunctions
-- Designed via Tiger MCP 'timescaledb-hyperfunctions' skill
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;

-- 1. Financial ticks table
CREATE TABLE IF NOT EXISTS market_trades (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL
) WITH (
    tsdb.hypertable,
    tsdb.partition_column = 'time',
    tsdb.chunk_interval = '1 day'
);

-- 2. Build 1-minute OHLCV (Open, High, Low, Close, Volume) & VWAP candlesticks
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    FIRST(price, time) AS open_price,
    MAX(price) AS high_price,
    MIN(price) AS low_price,
    LAST(price, time) AS close_price,
    SUM(volume) AS total_volume,
    -- Volume Weighted Average Price (VWAP)
    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap
FROM market_trades
GROUP BY bucket, symbol
WITH NO DATA;

-- 3. Percentiles and statistical summaries with percentile_agg & uddsketch
/*
SELECT
    symbol,
    approx_percentile(0.50, percentile_agg(price)) AS median_price,
    approx_percentile(0.95, percentile_agg(price)) AS p95_price,
    approx_percentile(0.99, percentile_agg(price)) AS p99_price
FROM market_trades
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY symbol;
*/
