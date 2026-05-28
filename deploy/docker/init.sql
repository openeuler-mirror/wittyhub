-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create Chinese text search configuration
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS zhcfg (COPY = pg_catalog.simple);
ALTER TEXT SEARCH CONFIGURATION zhcfg ALTER MAPPING FOR asciiword, word WITH unaccent, simple;

-- Verify extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');

-- Add embedding column to skills table (run manually if needed)
-- ALTER TABLE skills ADD COLUMN embedding vector(768);
