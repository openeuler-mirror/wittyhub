-- Migration 004: Rename security_score → risk_score
-- Aligns with NVIDIA SkillSpector risk scoring: 0=safe, 100=critical

ALTER TABLE skills RENAME COLUMN security_score TO risk_score;
ALTER TABLE skill_versions RENAME COLUMN security_score TO risk_score;
ALTER TABLE agents RENAME COLUMN security_score TO risk_score;

COMMENT ON COLUMN skills.risk_score IS 'SkillSpector risk score (0-100, higher = riskier)';
COMMENT ON COLUMN skill_versions.risk_score IS 'SkillSpector risk score (0-100, higher = riskier)';
COMMENT ON COLUMN agents.risk_score IS 'SkillSpector risk score (0-100, higher = riskier)';
