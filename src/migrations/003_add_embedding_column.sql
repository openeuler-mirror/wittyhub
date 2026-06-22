-- Migration: Add embedding column for semantic search
-- Requires pgvector extension

-- Add embedding column (run this after the initial migration)
ALTER TABLE skills ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_skills_embedding ON skills USING ivfflat (embedding vector_l2_ops);

-- Or use HNSW index for better performance (PostgreSQL 15+)
-- CREATE INDEX IF NOT EXISTS idx_skills_embedding_hnsw ON skills USING hnsw (embedding vector_l2_ops);
