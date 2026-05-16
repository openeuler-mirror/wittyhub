-- Add version and commit_id columns to security_audits table
-- These columns were missing from the initial migration but are required by the SecurityAudit model

ALTER TABLE security_audits ADD COLUMN IF NOT EXISTS version VARCHAR(50);
ALTER TABLE security_audits ADD COLUMN IF NOT EXISTS commit_id VARCHAR(40);

-- Add index for version lookup
CREATE INDEX IF NOT EXISTS idx_audits_version ON security_audits(resource_id, version, commit_id);