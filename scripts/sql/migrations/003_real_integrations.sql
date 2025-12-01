-- ============================================
-- Real Integration Configurations
-- Salesforce, Stripe, SendGrid, Twilio
-- ============================================

-- ============================================
-- 1. Salesforce CRM Integration
-- ============================================

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
    default_headers,
    metadata
) VALUES (
    'salesforce-api',
    'Salesforce CRM API',
    'Salesforce integration for customer relationship management',
    'https://your-instance.my.salesforce.com',  -- CHANGE THIS to your Salesforce instance
    'oauth2',
    '{
        "auth_type": "oauth2",
        "oauth2_token_url": "https://login.salesforce.com/services/oauth2/token",
        "oauth2_client_id": "YOUR_SALESFORCE_CLIENT_ID",
        "oauth2_client_secret": "YOUR_SALESFORCE_CLIENT_SECRET"
    }'::jsonb,
    '{
        "create_account": {
            "endpoint": "/services/data/v55.0/sobjects/Account",
            "method": "POST",
            "description": "Create a new Account"
        },
        "get_account": {
            "endpoint": "/services/data/v55.0/sobjects/Account/{id}",
            "method": "GET",
            "description": "Get Account details"
        },
        "create_contact": {
            "endpoint": "/services/data/v55.0/sobjects/Contact",
            "method": "POST",
            "description": "Create a new Contact"
        },
        "create_case": {
            "endpoint": "/services/data/v55.0/sobjects/Case",
            "method": "POST",
            "description": "Create a support Case"
        },
        "create_lead": {
            "endpoint": "/services/data/v55.0/sobjects/Lead",
            "method": "POST",
            "description": "Create a new Lead"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/json"
    }'::jsonb,
    '{
        "provider": "salesforce",
        "category": "crm",
        "documentation": "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/"
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- 2. Stripe Payment API Integration
-- ============================================

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
    default_headers,
    webhook_secret,
    metadata
) VALUES (
    'stripe-api',
    'Stripe Payment API',
    'Stripe integration for payment processing',
    'https://api.stripe.com',
    'bearer',
    '{
        "auth_type": "bearer",
        "bearer_token": "sk_test_YOUR_STRIPE_SECRET_KEY"
    }'::jsonb,
    '{
        "create_payment_intent": {
            "endpoint": "/v1/payment_intents",
            "method": "POST",
            "description": "Create a payment intent"
        },
        "get_payment_intent": {
            "endpoint": "/v1/payment_intents/{id}",
            "method": "GET",
            "description": "Retrieve a payment intent"
        },
        "create_customer": {
            "endpoint": "/v1/customers",
            "method": "POST",
            "description": "Create a customer"
        },
        "get_customer": {
            "endpoint": "/v1/customers/{id}",
            "method": "GET",
            "description": "Retrieve a customer"
        },
        "list_payment_methods": {
            "endpoint": "/v1/payment_methods",
            "method": "GET",
            "description": "List payment methods"
        },
        "create_charge": {
            "endpoint": "/v1/charges",
            "method": "POST",
            "description": "Create a charge"
        },
        "create_refund": {
            "endpoint": "/v1/refunds",
            "method": "POST",
            "description": "Create a refund"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/x-www-form-urlencoded"
    }'::jsonb,
    'whsec_YOUR_STRIPE_WEBHOOK_SECRET',
    '{
        "provider": "stripe",
        "category": "payment",
        "documentation": "https://stripe.com/docs/api",
        "test_mode": true
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- 3. SendGrid Email API Integration
-- ============================================

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
    default_headers,
    metadata
) VALUES (
    'sendgrid-api',
    'SendGrid Email API',
    'SendGrid integration for transactional emails',
    'https://api.sendgrid.com',
    'bearer',
    '{
        "auth_type": "bearer",
        "bearer_token": "SG.YOUR_SENDGRID_API_KEY"
    }'::jsonb,
    '{
        "send_email": {
            "endpoint": "/v3/mail/send",
            "method": "POST",
            "description": "Send a single email"
        },
        "send_batch": {
            "endpoint": "/v3/mail/send",
            "method": "POST",
            "description": "Send batch emails"
        },
        "add_contact": {
            "endpoint": "/v3/marketing/contacts",
            "method": "PUT",
            "description": "Add contact to marketing list"
        },
        "get_stats": {
            "endpoint": "/v3/stats",
            "method": "GET",
            "description": "Get email statistics"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/json"
    }'::jsonb,
    '{
        "provider": "sendgrid",
        "category": "email",
        "documentation": "https://docs.sendgrid.com/api-reference"
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- 4. Twilio SMS/Voice API Integration
-- ============================================

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
    default_headers,
    metadata
) VALUES (
    'twilio-api',
    'Twilio SMS & Voice API',
    'Twilio integration for SMS and voice communications',
    'https://api.twilio.com',
    'basic',
    '{
        "auth_type": "basic",
        "basic_username": "YOUR_TWILIO_ACCOUNT_SID",
        "basic_password": "YOUR_TWILIO_AUTH_TOKEN"
    }'::jsonb,
    '{
        "send_sms": {
            "endpoint": "/2010-04-01/Accounts/{AccountSid}/Messages.json",
            "method": "POST",
            "description": "Send an SMS message"
        },
        "make_call": {
            "endpoint": "/2010-04-01/Accounts/{AccountSid}/Calls.json",
            "method": "POST",
            "description": "Make a voice call"
        },
        "list_messages": {
            "endpoint": "/2010-04-01/Accounts/{AccountSid}/Messages.json",
            "method": "GET",
            "description": "List SMS messages"
        },
        "get_message": {
            "endpoint": "/2010-04-01/Accounts/{AccountSid}/Messages/{MessageSid}.json",
            "method": "GET",
            "description": "Get message details"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/x-www-form-urlencoded"
    }'::jsonb,
    '{
        "provider": "twilio",
        "category": "communication",
        "documentation": "https://www.twilio.com/docs/usage/api"
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- 5. HubSpot CRM Integration
-- ============================================

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
    default_headers,
    metadata
) VALUES (
    'hubspot-api',
    'HubSpot CRM API',
    'HubSpot integration for marketing and sales',
    'https://api.hubapi.com',
    'bearer',
    '{
        "auth_type": "bearer",
        "bearer_token": "YOUR_HUBSPOT_API_KEY"
    }'::jsonb,
    '{
        "create_contact": {
            "endpoint": "/crm/v3/objects/contacts",
            "method": "POST",
            "description": "Create a contact"
        },
        "get_contact": {
            "endpoint": "/crm/v3/objects/contacts/{contactId}",
            "method": "GET",
            "description": "Get contact by ID"
        },
        "create_deal": {
            "endpoint": "/crm/v3/objects/deals",
            "method": "POST",
            "description": "Create a deal"
        },
        "create_ticket": {
            "endpoint": "/crm/v3/objects/tickets",
            "method": "POST",
            "description": "Create a support ticket"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/json"
    }'::jsonb,
    '{
        "provider": "hubspot",
        "category": "crm",
        "documentation": "https://developers.hubspot.com/docs/api/overview"
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- 6. Slack API Integration
-- ============================================

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
    default_headers,
    metadata
) VALUES (
    'slack-api',
    'Slack API',
    'Slack integration for team messaging',
    'https://slack.com/api',
    'bearer',
    '{
        "auth_type": "bearer",
        "bearer_token": "xoxb-YOUR_SLACK_BOT_TOKEN"
    }'::jsonb,
    '{
        "post_message": {
            "endpoint": "/chat.postMessage",
            "method": "POST",
            "description": "Post a message to a channel"
        },
        "create_channel": {
            "endpoint": "/conversations.create",
            "method": "POST",
            "description": "Create a channel"
        },
        "list_users": {
            "endpoint": "/users.list",
            "method": "GET",
            "description": "List users in workspace"
        }
    }'::jsonb,
    FALSE,  -- Set to TRUE after configuring credentials
    30,
    TRUE,
    TRUE,
    '{
        "Content-Type": "application/json"
    }'::jsonb,
    '{
        "provider": "slack",
        "category": "messaging",
        "documentation": "https://api.slack.com/methods"
    }'::jsonb
) ON CONFLICT (integration_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint_mappings = EXCLUDED.endpoint_mappings,
    metadata = EXCLUDED.metadata;

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE integration_configs IS 'Configuration for external API integrations';

-- ============================================
-- Usage Instructions
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Real Integrations Configured!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'The following integrations have been added:';
    RAISE NOTICE '1. Salesforce CRM (salesforce-api)';
    RAISE NOTICE '2. Stripe Payments (stripe-api)';
    RAISE NOTICE '3. SendGrid Email (sendgrid-api)';
    RAISE NOTICE '4. Twilio SMS/Voice (twilio-api)';
    RAISE NOTICE '5. HubSpot CRM (hubspot-api)';
    RAISE NOTICE '6. Slack Messaging (slack-api)';
    RAISE NOTICE '';
    RAISE NOTICE 'To activate an integration:';
    RAISE NOTICE '1. Update auth_config with your API credentials';
    RAISE NOTICE '2. Update base_url if needed (e.g., Salesforce instance)';
    RAISE NOTICE '3. Set is_active = TRUE';
    RAISE NOTICE '';
    RAISE NOTICE 'Example:';
    RAISE NOTICE 'UPDATE integration_configs';
    RAISE NOTICE 'SET auth_config = ''{"auth_type": "bearer", "bearer_token": "sk_live_YOUR_KEY"}''::jsonb,';
    RAISE NOTICE '    is_active = TRUE';
    RAISE NOTICE 'WHERE integration_id = ''stripe-api'';';
    RAISE NOTICE '========================================';
END $$;

-- ============================================
-- Query to view all integrations
-- ============================================

SELECT
    integration_id,
    name,
    base_url,
    auth_type,
    is_active,
    timeout_seconds,
    retry_enabled,
    circuit_breaker_enabled
FROM integration_configs
ORDER BY name;
