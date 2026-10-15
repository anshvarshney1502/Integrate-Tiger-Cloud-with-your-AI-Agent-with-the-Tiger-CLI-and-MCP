-- ==============================================================================
-- 03_hybrid_bm25_vector.sql
-- Pattern: Hybrid Search combining BM25 Keyword Search and Semantic Embeddings
-- Designed via Tiger MCP 'postgres-hybrid-text-search' skill
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Create table with both full-text search tsvector and embedding vector
CREATE TABLE IF NOT EXISTS articles_hybrid (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. GIN index for keyword text search
CREATE INDEX IF NOT EXISTS idx_articles_tsv ON articles_hybrid USING GIN(tsv);

-- 3. HNSW index for vector semantic search
CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles_hybrid USING hnsw (embedding vector_cosine_ops);

-- 4. Reciprocal Rank Fusion (RRF) query combining keyword BM25 with Vector similarity
/*
WITH keyword_search AS (
    SELECT id, RANK() OVER (ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('english', 'time series database')) DESC) AS rank
    FROM articles_hybrid
    WHERE tsv @@ websearch_to_tsquery('english', 'time series database')
    LIMIT 20
),
semantic_search AS (
    SELECT id, RANK() OVER (ORDER BY embedding <=> '[...]'::vector) AS rank
    FROM articles_hybrid
    LIMIT 20
)
SELECT
    COALESCE(k.id, s.id) AS article_id,
    COALESCE(1.0 / (60 + k.rank), 0.0) + COALESCE(1.0 / (60 + s.rank), 0.0) AS rrf_score
FROM keyword_search k
FULL OUTER JOIN semantic_search s ON k.id = s.id
ORDER BY rrf_score DESC
LIMIT 10;
*/
