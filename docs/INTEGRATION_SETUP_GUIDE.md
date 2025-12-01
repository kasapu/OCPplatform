# Integration Setup Guide

Complete guide for configuring real external API integrations with the OCP Platform.

---

## Overview

The OCP Platform Integration Service supports connecting to any REST API. This guide covers setup for the most common integrations:

1. **Salesforce CRM** - Customer relationship management
2. **Stripe** - Payment processing
3. **SendGrid** - Transactional emails
4. **Twilio** - SMS and voice
5. **HubSpot** - Marketing and sales CRM
6. **Slack** - Team messaging

---

## Prerequisites

1. **Integration Service Running**
   ```bash
   curl http://localhost:8002/health
   ```

2. **Database Migration Applied**
   ```bash
   docker cp scripts/sql/migrations/003_real_integrations.sql ocp-postgres:/tmp/
   docker-compose exec postgres psql -U ocpuser -d ocplatform -f /tmp/003_real_integrations.sql
   ```

3. **API Credentials** - You'll need credentials for each service you want to use

---

## 1. Salesforce CRM Setup

### Get Credentials

1. **Create Connected App**:
   - Go to Setup → App Manager → New Connected App
   - Enable OAuth Settings
   - Selected OAuth Scopes: `api`, `refresh_token`
   - Callback URL: `https://your-domain.com/oauth/callback`
   - Save and note **Consumer Key** (Client ID) and **Consumer Secret**

2. **Get Access Token**:
   ```bash
   curl -X POST https://login.salesforce.com/services/oauth2/token \
     -d "grant_type=client_credentials" \
     -d "client_id=YOUR_CONSUMER_KEY" \
     -d "client_secret=YOUR_CONSUMER_SECRET"
   ```

### Configure Integration

```sql
UPDATE integration_configs
SET
    base_url = 'https://your-instance.my.salesforce.com',  -- YOUR Salesforce instance
    auth_config = '{
        "auth_type": "oauth2",
        "oauth2_token_url": "https://login.salesforce.com/services/oauth2/token",
        "oauth2_client_id": "YOUR_CONSUMER_KEY",
        "oauth2_client_secret": "YOUR_CONSUMER_SECRET"
    }'::jsonb,
    is_active = TRUE
WHERE integration_id = 'salesforce-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "salesforce-api",
    "endpoint": "/services/data/v55.0/sobjects/Account",
    "method": "POST",
    "body": {
      "Name": "Test Company",
      "BillingCity": "San Francisco"
    }
  }'
```

### Use in Dialogue Flow

```json
{
  "node_id": "create_salesforce_account",
  "type": "api_caller",
  "config": {
    "integration_id": "salesforce-api",
    "endpoint": "/services/data/v55.0/sobjects/Account",
    "method": "POST",
    "body_template": {
      "Name": "{company_name}",
      "BillingCity": "{city}",
      "Phone": "{phone}"
    },
    "success_message_template": "Account created successfully!",
    "failure_message_template": "Sorry, I couldn't create the account.",
    "on_success": "account_created_node",
    "on_failure": "error_node",
    "response_mapping": {
      "salesforce_account_id": "id"
    }
  }
}
```

---

## 2. Stripe Payment Setup

### Get Credentials

1. Go to https://dashboard.stripe.com/apikeys
2. Copy your **Secret Key** (starts with `sk_test_` for test mode or `sk_live_` for production)
3. Copy your **Webhook Secret** from Developers → Webhooks

### Configure Integration

```sql
UPDATE integration_configs
SET
    auth_config = '{
        "auth_type": "bearer",
        "bearer_token": "sk_test_YOUR_SECRET_KEY"
    }'::jsonb,
    webhook_secret = 'whsec_YOUR_WEBHOOK_SECRET',
    is_active = TRUE
WHERE integration_id = 'stripe-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "stripe-api",
    "endpoint": "/v1/payment_intents",
    "method": "POST",
    "body": {
      "amount": 2000,
      "currency": "usd",
      "payment_method_types": ["card"]
    }
  }'
```

### Use in Dialogue Flow

```json
{
  "node_id": "process_payment",
  "type": "api_caller",
  "config": {
    "integration_id": "stripe-api",
    "endpoint": "/v1/payment_intents",
    "method": "POST",
    "body_template": {
      "amount": "{amount}",
      "currency": "usd",
      "payment_method": "{payment_method_id}",
      "confirm": true
    },
    "success_message_template": "Payment of ${amount} completed successfully!",
    "failure_message_template": "Payment failed. Please try again.",
    "on_success": "payment_success",
    "on_failure": "payment_error",
    "response_mapping": {
      "payment_intent_id": "id",
      "payment_status": "status"
    }
  }
}
```

### Configure Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/v1/webhooks/stripe-api/payment.succeeded`
3. Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`

---

## 3. SendGrid Email Setup

### Get Credentials

1. Go to https://app.sendgrid.com/settings/api_keys
2. Create API Key with **Full Access** or **Mail Send** permission
3. Copy the key (starts with `SG.`)

### Configure Integration

```sql
UPDATE integration_configs
SET
    auth_config = '{
        "auth_type": "bearer",
        "bearer_token": "SG.YOUR_API_KEY"
    }'::jsonb,
    is_active = TRUE
WHERE integration_id = 'sendgrid-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "sendgrid-api",
    "endpoint": "/v3/mail/send",
    "method": "POST",
    "body": {
      "personalizations": [{
        "to": [{"email": "test@example.com"}],
        "subject": "Test Email"
      }],
      "from": {"email": "noreply@yourdomain.com"},
      "content": [{
        "type": "text/plain",
        "value": "This is a test email"
      }]
    }
  }'
```

### Use in Dialogue Flow

```json
{
  "node_id": "send_confirmation_email",
  "type": "api_caller",
  "config": {
    "integration_id": "sendgrid-api",
    "endpoint": "/v3/mail/send",
    "method": "POST",
    "body_template": {
      "personalizations": [{
        "to": [{"email": "{customer_email}"}],
        "subject": "Order Confirmation"
      }],
      "from": {"email": "orders@yourdomain.com"},
      "content": [{
        "type": "text/html",
        "value": "<h1>Thank you for your order!</h1><p>Order ID: {order_id}</p>"
      }]
    },
    "success_message_template": "Confirmation email sent!",
    "failure_message_template": "Failed to send email.",
    "on_success": "email_sent",
    "on_failure": "email_error"
  }
}
```

---

## 4. Twilio SMS/Voice Setup

### Get Credentials

1. Go to https://console.twilio.com
2. Copy your **Account SID** and **Auth Token**
3. Get a phone number from Phone Numbers → Buy a Number

### Configure Integration

```sql
UPDATE integration_configs
SET
    auth_config = '{
        "auth_type": "basic",
        "basic_username": "YOUR_ACCOUNT_SID",
        "basic_password": "YOUR_AUTH_TOKEN"
    }'::jsonb,
    base_url = 'https://api.twilio.com',
    is_active = TRUE
WHERE integration_id = 'twilio-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "twilio-api",
    "endpoint": "/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json",
    "method": "POST",
    "body": {
      "From": "+1234567890",
      "To": "+1234567891",
      "Body": "Test SMS from OCP Platform"
    }
  }'
```

### Use in Dialogue Flow

```json
{
  "node_id": "send_sms_notification",
  "type": "api_caller",
  "config": {
    "integration_id": "twilio-api",
    "endpoint": "/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json",
    "method": "POST",
    "body_template": {
      "From": "+1234567890",
      "To": "{customer_phone}",
      "Body": "Your verification code is: {verification_code}"
    },
    "success_message_template": "SMS sent successfully!",
    "failure_message_template": "Failed to send SMS.",
    "on_success": "sms_sent",
    "on_failure": "sms_error",
    "response_mapping": {
      "message_sid": "sid",
      "message_status": "status"
    }
  }
}
```

---

## 5. HubSpot CRM Setup

### Get Credentials

1. Go to https://app.hubspot.com/settings/account/integrations/api-key
2. Create API Key (or use OAuth)
3. Copy the API key

### Configure Integration

```sql
UPDATE integration_configs
SET
    auth_config = '{
        "auth_type": "bearer",
        "bearer_token": "YOUR_HUBSPOT_API_KEY"
    }'::jsonb,
    is_active = TRUE
WHERE integration_id = 'hubspot-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "hubspot-api",
    "endpoint": "/crm/v3/objects/contacts",
    "method": "POST",
    "body": {
      "properties": {
        "email": "test@example.com",
        "firstname": "John",
        "lastname": "Doe"
      }
    }
  }'
```

---

## 6. Slack API Setup

### Get Credentials

1. Go to https://api.slack.com/apps
2. Create New App → From Scratch
3. Add Bot Token Scopes: `chat:write`, `channels:manage`
4. Install App to Workspace
5. Copy **Bot User OAuth Token** (starts with `xoxb-`)

### Configure Integration

```sql
UPDATE integration_configs
SET
    auth_config = '{
        "auth_type": "bearer",
        "bearer_token": "xoxb-YOUR_SLACK_BOT_TOKEN"
    }'::jsonb,
    is_active = TRUE
WHERE integration_id = 'slack-api';
```

### Test Integration

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "slack-api",
    "endpoint": "/chat.postMessage",
    "method": "POST",
    "body": {
      "channel": "#general",
      "text": "Test message from OCP Platform"
    }
  }'
```

---

## Security Best Practices

### 1. **Use Environment Variables**

Never hardcode credentials in SQL. Use environment variables:

```bash
# .env file
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
STRIPE_SECRET_KEY=sk_live_your_key
SENDGRID_API_KEY=SG.your_key
```

### 2. **Rotate Credentials Regularly**

Update API keys every 90 days:

```sql
UPDATE integration_configs
SET auth_config = jsonb_set(
    auth_config,
    '{bearer_token}',
    '"NEW_API_KEY"'::jsonb
)
WHERE integration_id = 'stripe-api';
```

### 3. **Use Test Mode First**

Always test with sandbox/test credentials before production:

- Stripe: Use `sk_test_` keys
- Salesforce: Use sandbox instance
- Twilio: Use test credentials

### 4. **Monitor API Usage**

```sql
SELECT
    integration_id,
    COUNT(*) as total_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
    ROUND(AVG(execution_time_ms)::numeric, 2) as avg_time_ms
FROM integration_executions
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY integration_id
ORDER BY total_calls DESC;
```

### 5. **Set Rate Limits**

```sql
UPDATE integration_configs
SET metadata = jsonb_set(
    metadata,
    '{rate_limit}',
    '{"requests_per_minute": 60, "requests_per_day": 10000}'::jsonb
)
WHERE integration_id = 'stripe-api';
```

---

## Troubleshooting

### Integration Returns 401/403

**Problem**: Authentication failure

**Solutions**:
1. Check credentials are correct
2. Verify API key hasn't expired
3. For OAuth2, check token hasn't been revoked
4. Verify API permissions/scopes

### Circuit Breaker is OPEN

**Problem**: Integration is failing repeatedly

**Solutions**:
```bash
# Check circuit breaker status
curl http://localhost:8002/v1/integrations/circuit-breakers

# Reset if API is back online
curl -X POST http://localhost:8002/v1/integrations/circuit-breakers/stripe-api/reset
```

### Slow Response Times

**Problem**: Integrations taking too long

**Solutions**:
1. Increase timeout:
   ```sql
   UPDATE integration_configs
   SET timeout_seconds = 60
   WHERE integration_id = 'salesforce-api';
   ```

2. Check Integration Service performance:
   ```sql
   SELECT * FROM integration_performance_stats
   WHERE integration_id = 'salesforce-api';
   ```

### Webhook Signature Fails

**Problem**: Webhook signature verification fails

**Solutions**:
1. Verify webhook secret is correct
2. Check signature header name (varies by provider)
3. Ensure raw body is used for verification

---

## Testing Checklist

Before going to production:

- [ ] Test each integration with valid credentials
- [ ] Test error handling (invalid requests)
- [ ] Test circuit breaker (simulate failures)
- [ ] Test retry logic (temporary network issues)
- [ ] Test webhook receiving and verification
- [ ] Monitor performance metrics
- [ ] Set up alerts for circuit breaker state changes
- [ ] Document API rate limits
- [ ] Configure production credentials
- [ ] Enable is_active for production integrations

---

## Next Steps

1. **Add Custom Integrations**: Use the same pattern for any REST API
2. **Create Reusable Templates**: Save common API call patterns
3. **Build Admin UI**: Manage integrations via web interface
4. **Set Up Monitoring**: Track API usage and performance
5. **Configure Alerts**: Get notified of integration failures

---

## Support

- **Documentation**: See Integration Service README
- **API Docs**: http://localhost:8002/docs
- **Database Schema**: `scripts/sql/migrations/002_integration_service_tables.sql`
- **Examples**: `PHASE2_INTEGRATION_SERVICE.md`

---

**Last Updated**: 2025-01-21
**Version**: 1.0.0
