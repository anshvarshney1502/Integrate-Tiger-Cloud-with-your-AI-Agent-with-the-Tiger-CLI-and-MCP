# Agent Instructions & Tiger Cloud Guardrails

This project integrates Tiger Cloud with AI Agents using Tiger CLI and the Model Context Protocol (MCP).

## Database Access Rules via Tiger MCP

- **Production Service Safety**:
  - Treat all production services as **READ-ONLY**.
  - NEVER call mutating service tools (`service_create`, `service_delete`, `service_resize`, `service_stop`, `service_update_password`) against production services without explicit confirmation.
  - NEVER execute unconstrained `UPDATE` or `DELETE` queries, or run destructive DDL (`DROP TABLE`, `TRUNCATE`).
  - Read-only mode configuration: `tiger config set read_only prod` (or `all` / `off`).
- **Development & Testing on Forks**:
  - For schema migrations, index additions, or data exploration, always fork the service first:
    ```bash
    tiger service fork <service-id>
    ```
    Or call the MCP tool `service_fork`.
  - Development services may be modified freely.
- **Query Guidelines**:
  - Always verify queries include a reasonable `LIMIT` clause (default: 50-100 rows).
  - Prefer single computed aggregates over large raw record egress.
  - Explain the SQL statement before executing it with `db_query`.

## Tiger MCP Capabilities

- **Tools (19)**:
  - Service Management: `service_create`, `service_get`, `service_list`, `service_fork`, `service_resize`, `service_start`, `service_stop`, `service_rename`, `service_update_password`, `service_delete`, `service_logs`
  - Metrics: `service_metrics_available`, `service_metrics_details`, `service_metrics_series`
  - Data Operations: `db_query`, `db_schema`
  - Knowledge & Skills: `search_docs`, `view_skill`, `feedback`
- **Built-in Skills & Prompts (11)**:
  - `setup-timescaledb-hypertables`: Hypertable design, chunk sizing, compression, continuous aggregates.
  - `find-hypertable-candidates`: Table inspection and candidacy scoring.
  - `pgvector-semantic-search`: Vector embeddings, HNSW indexing, halfvec, cosine similarity.
  - `postgres-hybrid-text-search`: BM25 full-text search combined with vector search via RRF.
  - `postgres-database-migration`: Zero-downtime migrations, safe ALTER TABLE patterns, and lock levels.
  - `timescaledb-hyperfunctions`: Toolkit aggregations (percentiles, candelstick_agg, vwap).
  - `design-postgres-tables` & `design-postgis-tables`: Relational and geospatial schema designs.
