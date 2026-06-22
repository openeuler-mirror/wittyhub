-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    platform VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    security_score INTEGER,
    download_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_indexed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_tags ON skills USING GIN(tags);
CREATE INDEX idx_skills_platform ON skills(platform);
CREATE INDEX idx_skills_source ON skills(source);
CREATE INDEX idx_skills_created_at ON skills(created_at DESC);

-- Agents table (for future expansion)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    security_score INTEGER,
    download_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_indexed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agents_category ON agents(category);
CREATE INDEX idx_agents_tags ON agents USING GIN(tags);

-- Security audit results table
CREATE TABLE IF NOT EXISTS security_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(20) NOT NULL,
    resource_id UUID NOT NULL,
    version VARCHAR(50),
    commit_id VARCHAR(40),
    audit_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    risk_signals JSONB DEFAULT '[]',
    details JSONB DEFAULT '{}',
    audited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_resource FOREIGN KEY (resource_id) REFERENCES skills(id) ON DELETE CASCADE
);

CREATE INDEX idx_audits_resource ON security_audits(resource_type, resource_id);
CREATE INDEX idx_audits_risk_level ON security_audits(risk_level);
CREATE INDEX idx_audits_audited_at ON security_audits(audited_at DESC);
CREATE INDEX IF NOT EXISTS idx_audits_version ON security_audits(resource_id, version, commit_id);

-- Download history table
CREATE TABLE IF NOT EXISTS download_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(20) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_downloads_resource ON download_history(resource_type, resource_id);
CREATE INDEX idx_downloads_date ON download_history(downloaded_at DESC);