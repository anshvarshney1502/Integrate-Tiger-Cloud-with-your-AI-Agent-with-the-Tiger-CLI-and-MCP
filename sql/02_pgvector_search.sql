-- ==============================================================================
-- 02_pgvector_search.sql
-- Pattern: AI Vector Similarity Search using pgvector & HNSW Indexing
-- Designed via Tiger MCP 'pgvector-semantic-search' skill
-- ==============================================================================

-- 1. Ensure the vector extension is installed
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create knowledge base documents table with vector embeddings
CREATE TABLE IF NOT EXISTS document_embeddings (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    -- 1536-dimensional embedding (e.g. OpenAI text-embedding-3-small or Gemini text-embedding-004)
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create HNSW (Hierarchical Navigable Small World) index for fast cosine similarity
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_hnsw_cosine
ON document_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4. Sample vector query (Cosine distance: <=> operator)
-- Query finds top-5 most semantically similar documents
/*
SELECT
    id,
    title,
    content,
    1 - (embedding <=> '[0.012, -0.023, ...]'::vector) AS similarity_score
FROM document_embeddings
ORDER BY embedding <=> '[0.012, -0.023, ...]'::vector
LIMIT 5;
*/
