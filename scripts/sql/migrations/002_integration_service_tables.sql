-- ============================================
-- Integration Service Database Schema
-- Phase 2: External System Integration Tables
-- ============================================

-- ============================================
-- 1. Integration Executions Table
-- ============================================

CREATE TABLE IF NOT EXISTS integration_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id VARCHAR(100) NOT NULL,
    session_id UUID REFERENCES sessions(session_id),
    endpoint VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_data JSONB DEFAULT '{}'::jsonb,
    response_data JSONB,
    status_code INTEGER,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    execution_time_ms FLOAT NOT NULL,
    retries INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for integration_executions
CREATE INDEX IF NOT EXISTS idx_integration_executions_integration_id
    ON integration_executions(integration_id);
CREATE INDEX IF NOT EXISTS idx_integration_executions_session_id
    ON integration_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_integration_executions_created_at
    ON integration_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_integration_executions_success
    ON integration_executions(success);

-- ============================================
-- 2. Webhook Events Table
-- ============================================

CREATE TABLE IF NOT EXISTS webhook_events (
    webhook_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    signature VARCHAR(500),
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP,
    error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for webhook_events
CREATE INDEX IF NOT EXISTS idx_webhook_events_integration_id
    ON webhook_events(integration_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type
    ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed
    ON webhook_events(processed) WHERE NOT processed;
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at
    ON webhook_events(created_at DESC);

-- ============================================
-- 3. Update integration_configs table
-- Add new columns for Integration Service
-- ============================================

-- Add webhook_secret column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='integration_configs'
        AND column_name='webhook_secret'
    ) THEN
        ALTER TABLE integration_configs
        ADD COLUMN webhook_secret VARCHAR(500);
    END IF;
END $$;

-- Add timeout_seconds column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='integration_configs'
        AND column_name='timeout_seconds'
    ) THEN
        ALTER TABLE integration_configs
        ADD COLUMN timeout_seconds INTEGER DEFAULT 30;
    END IF;
END $$;

-- Add retry_enabled column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='integration_configs'
        AND column_name='retry_enabled'
    ) THEN
        ALTER TABLE integration_configs
        ADD COLUMN retry_enabled BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- Add circuit_breaker_enabled column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='integration_configs'
        AND column_name='circuit_breaker_enabled'
    ) THEN
        ALTER TABLE integration_configs
        ADD COLUMN circuit_breaker_enabled BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- Add default_headers column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='integration_configs'
        AND column_name='default_headers'
    ) THEN
        ALTER TABLE integration_configs
        ADD COLUMN default_headers JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- ============================================
-- 4. Sample Integration Configurations
-- ============================================

-- Generic REST API Integration (example)
INSERT INTO integration_configs (
    integration_id,
    name,
    description,
    base_url,
    auth_type,
    auth_config,
    endpoint_mappings,
    is_active,
    timeout_seconds,
    retry_enabled,
    circuit_breaker_enabled,
    metadata
) VALUES (
    'generic-rest-api',
    'Generic REST API',
    'Generic REST API integration for testing',
    'https://jsonplaceholder.typicode.com',
    'none',
    '{"auth_type": "none"}'::jsonb,
    '{
        "get_user": {
            "endpoint": "/users/{user_id}",
            "method": "GET"
        },
        "create_post": {
            "endpoint": "/posts",
            "method": "POST"
        }
    }'::jsonb,
    TRUE,
    30,
    TRUE,
    TRUE,
    '{
        "type": "demo",
        "purpose": "testing"
    }'::jsonb
) ON CONFLICT (integration_id) DO NOTHING;

-- Stripe API Integration (example - requires API key)
INSERT INTO integration_configs (
    integration_id,
    name,
    description,
    base_url,
    auth_type,
    auth_config,
    endpoint_mappings,
    is_active,
    timeout_seconds,
    retry_enabled,
    circuit_breaker_enabled,
    webhook_secret,
    metadata
) VALUES (
    'stripe-api',
    'Stripe Payment API',
    'Stripe payment processing integration',
    'https://api.stripe.com',
    'bearer',
    '{"auth_type": "bearer", "bearer_token": "sk_test_YOUR_KEY_HERE"}'::jsonb,
    '{
        "create_payment_intent": {
            "endpoint": "/v1/payment_intents",
            "method": "POST"
        },
        "get_payment_intent": {
            "endpoint": "/v1/payment_intents/{id}",
            "method": "GET"
        },
        "list_customers": {
            "endpoint": "/v1/customers",
            "method": "GET"
        }
    }'::jsonb,
    FALSE,  -- Inactive by default (requires valid API key)
    30,
    TRUE,
    TRUE,
    'whsec_YOUR_WEBHOOK_SECRET_HERE',
    '{
        "type": "payment",
        "provider": "stripe"
    }'::jsonb
) ON CONFLICT (integration_id) DO NOTHING;

-- ============================================
-- 5. Analytics Views
-- ============================================

-- Integration performance view
CREATE OR REPLACE VIEW integration_performance_stats AS
SELECT
    integration_id,
    COUNT(*) as total_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_calls,
    ROUND(AVG(execution_time_ms)::numeric, 2) as avg_execution_time_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::numeric, 2) as p95_execution_time_ms,
    MIN(created_at) as first_call,
    MAX(created_at) as last_call
FROM integration_executions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY integration_id;

-- Webhook processing stats view
CREATE OR REPLACE VIEW webhook_processing_stats AS
SELECT
    integration_id,
    event_type,
    COUNT(*) as total_events,
    SUM(CASE WHEN processed THEN 1 ELSE 0 END) as processed_events,
    SUM(CASE WHEN NOT processed THEN 1 ELSE 0 END) as pending_events,
    SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as failed_events,
    MIN(created_at) as first_event,
    MAX(created_at) as last_event
FROM webhook_events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY integration_id, event_type;

-- ============================================
-- 6. Comments
-- ============================================

COMMENT ON TABLE integration_executions IS 'Execution log for all integration API calls';
COMMENT ON TABLE webhook_events IS 'Incoming webhook events from external systems';

COMMENT ON COLUMN integration_executions.execution_time_ms IS 'Total execution time in milliseconds';
COMMENT ON COLUMN integration_executions.retries IS 'Number of retry attempts made';

COMMENT ON COLUMN webhook_events.signature IS 'Webhook signature for verification (e.g., HMAC-SHA256)';
COMMENT ON COLUMN webhook_events.processed IS 'Whether the webhook has been processed';

-- ============================================
-- Migration Complete
-- ============================================

SELECT 'Integration Service tables created successfully!' as status;
