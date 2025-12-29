-- ============================================================================
-- Detection System - Initial Database Schema
-- ============================================================================
-- 
-- This script creates the initial database schema for the Detection System.
-- It includes tables for users, sessions, detection results, and API keys.
--
-- Usage:
--   psql -U detector -d detection_db -f init.sql
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    
    -- Credentials
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name VARCHAR(100),
    company VARCHAR(100),
    
    -- Roles and permissions (JSON arrays)
    roles JSONB NOT NULL DEFAULT '["user"]'::jsonb,
    permissions JSONB NOT NULL DEFAULT '["detect"]'::jsonb,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_active ON users(is_active);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    
    -- Foreign key
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session data
    refresh_token_hash VARCHAR(255) UNIQUE NOT NULL,
    access_token_jti VARCHAR(255),
    
    -- Client info
    ip_address VARCHAR(45),  -- IPv6 support
    user_agent VARCHAR(500),
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_session_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_token ON sessions(refresh_token_hash);
CREATE INDEX IF NOT EXISTS idx_session_active ON sessions(is_active, expires_at);

-- ============================================================================
-- DETECTION_RESULTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS detection_results (
    id SERIAL PRIMARY KEY,
    
    -- Foreign key (nullable - can be anonymous)
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Detection data
    image_path VARCHAR(500),
    image_hash VARCHAR(64),  -- SHA-256
    
    -- Results
    niveau_y INTEGER,  -- Pixel position
    niveau_percentage FLOAT,  -- Percentage (0-100)
    niveau_ml FLOAT,  -- Volume in mL (if calibrated)
    
    confiance FLOAT NOT NULL,  -- Confidence score (0-1)
    methode_utilisee VARCHAR(50),  -- 'hough', 'clustering', etc.
    
    -- Performance
    temps_traitement_ms FLOAT,
    
    -- Metadata
    image_width INTEGER,
    image_height INTEGER,
    calibration_used BOOLEAN DEFAULT FALSE,
    erreurs JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for detection_results
CREATE INDEX IF NOT EXISTS idx_detection_user_id ON detection_results(user_id);
CREATE INDEX IF NOT EXISTS idx_detection_created ON detection_results(created_at);
CREATE INDEX IF NOT EXISTS idx_detection_hash ON detection_results(image_hash);

-- ============================================================================
-- API_KEYS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    
    -- Foreign key
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Key data
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    name VARCHAR(100) NOT NULL,
    
    -- Permissions
    permissions JSONB DEFAULT '[]'::jsonb,
    
    -- Rate limiting
    rate_limit INTEGER DEFAULT 1000,  -- Requests per hour
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used TIMESTAMP
);

-- Indexes for api_keys
CREATE INDEX IF NOT EXISTS idx_apikey_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_apikey_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_apikey_active ON api_keys(is_active);

-- ============================================================================
-- DEFAULT DATA
-- ============================================================================

-- Insert demo user (password: DemoPassword123!)
-- Password hash generated with bcrypt (12 rounds)
INSERT INTO users (username, email, password_hash, full_name, roles, permissions, is_active, is_verified)
VALUES (
    'demo',
    'demo@detection-system.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ufzNvjBxXvuG',  -- DemoPassword123!
    'Demo User',
    '["user"]'::jsonb,
    '["detect"]'::jsonb,
    TRUE,
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- Insert admin user (password: AdminPassword123!)
INSERT INTO users (username, email, password_hash, full_name, roles, permissions, is_active, is_verified)
VALUES (
    'admin',
    'admin@detection-system.local',
    '$2b$12$6H.Q5zCgE.xGH2WOBpN3qO8xGxKZvLKp3rN7pGxYOQN8yMxQxKxPW',  -- AdminPassword123!
    'Administrator',
    '["user", "admin"]'::jsonb,
    '["detect", "calibrate", "admin"]'::jsonb,
    TRUE,
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- ============================================================================
-- CLEANUP FUNCTIONS
-- ============================================================================

-- Function to clean expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions 
    WHERE expires_at < NOW() OR (is_active = FALSE AND last_used < NOW() - INTERVAL '7 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean old detection results (older than 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_detection_results()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM detection_results 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS (for convenience)
-- ============================================================================

-- View for active users
CREATE OR REPLACE VIEW active_users AS
SELECT 
    id,
    username,
    email,
    full_name,
    company,
    roles,
    permissions,
    created_at,
    last_login
FROM users
WHERE is_active = TRUE;

-- View for recent detections (last 24 hours)
CREATE OR REPLACE VIEW recent_detections AS
SELECT 
    dr.id,
    dr.user_id,
    u.username,
    dr.niveau_percentage,
    dr.confiance,
    dr.methode_utilisee,
    dr.temps_traitement_ms,
    dr.created_at
FROM detection_results dr
LEFT JOIN users u ON dr.user_id = u.id
WHERE dr.created_at > NOW() - INTERVAL '24 hours'
ORDER BY dr.created_at DESC;

-- ============================================================================
-- GRANTS (adjust based on your security needs)
-- ============================================================================

-- Grant permissions to detector user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO detector;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO detector;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables were created
DO $$
BEGIN
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users: % rows', (SELECT COUNT(*) FROM users);
    RAISE NOTICE '  - sessions: % rows', (SELECT COUNT(*) FROM sessions);
    RAISE NOTICE '  - detection_results: % rows', (SELECT COUNT(*) FROM detection_results);
    RAISE NOTICE '  - api_keys: % rows', (SELECT COUNT(*) FROM api_keys);
    RAISE NOTICE '';
    RAISE NOTICE 'Database initialized successfully!';
END $$;
