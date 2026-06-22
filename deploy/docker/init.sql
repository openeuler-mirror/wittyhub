-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create Chinese text search configuration (ignore errors if it already exists)
DO $$ BEGIN
    CREATE TEXT SEARCH CONFIGURATION zhcfg (COPY = pg_catalog.simple);
EXCEPTION WHEN duplicate_object THEN null;
END $$;
ALTER TEXT SEARCH CONFIGURATION zhcfg ALTER MAPPING FOR asciiword, word WITH unaccent, simple;

-- Verify extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');

-- Create skills table
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    commit_id VARCHAR(40),
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    platform VARCHAR(100),
    extra_metadata JSONB DEFAULT '{}',
    content TEXT,
    security_score INTEGER,
    download_count INTEGER DEFAULT 0,
    rating VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_indexed_at TIMESTAMP WITH TIME ZONE,
    embedding REAL[]
);

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    extra_metadata JSONB DEFAULT '{}',
    security_score INTEGER,
    download_count INTEGER DEFAULT 0,
    rating VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_indexed_at TIMESTAMP WITH TIME ZONE
);

-- Create security_audits table
CREATE TABLE IF NOT EXISTS security_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type VARCHAR(20) NOT NULL,
    resource_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    version VARCHAR(50),
    commit_id VARCHAR(40),
    audit_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    risk_signals JSONB DEFAULT '[]',
    details JSONB DEFAULT '{}',
    audited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create download_history table
CREATE TABLE IF NOT EXISTS download_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type VARCHAR(20) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_platform ON skills(platform);
CREATE INDEX IF NOT EXISTS idx_skills_source ON skills(source);
CREATE INDEX IF NOT EXISTS idx_skills_created_at ON skills(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skills_tags ON skills USING GIN(tags);
CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_unique ON skills(source, source_url, version, commit_id);

CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category);
CREATE INDEX IF NOT EXISTS idx_agents_tags ON agents USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_audits_resource ON security_audits(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audits_risk_level ON security_audits(risk_level);
CREATE INDEX IF NOT EXISTS idx_audits_audited_at ON security_audits(audited_at DESC);
CREATE INDEX IF NOT EXISTS idx_audits_version ON security_audits(resource_id, version, commit_id);

CREATE INDEX IF NOT EXISTS idx_downloads_resource ON download_history(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_downloads_date ON download_history(downloaded_at DESC);
