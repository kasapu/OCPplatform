# Integration Service

**Version**: 1.0.0
**Port**: 8002
**Phase**: 2

## Overview

The Integration Service provides a flexible, production-ready framework for integrating the OCP Platform with external systems and APIs. It handles authentication, retry logic, circuit breakers, and webhook processing automatically.

## Features

### ✅ Multi-Protocol Support
- REST APIs (GET, POST, PUT, PATCH, DELETE)
- GraphQL (via POST requests)
- SOAP APIs (via XML body)
- Webhooks (incoming callbacks)

### ✅ Authentication Methods
- **None**: For public APIs
- **API Key**: Header or query parameter
- **Bearer Token**: OAuth2 access tokens
- **Basic Auth**: Username/password
- **OAuth2 Client Credentials**: Automatic token management with refresh

### ✅ Fault Tolerance
- **Retry Logic**: Exponential backoff with configurable attempts
- **Circuit Breaker**: Prevents cascading failures
- **Timeout Management**: Configurable per integration
- **Error Handling**: Structured error responses

### ✅ Observability
- Request/response logging to database
- Performance metrics (execution time, success rate)
- Circuit breaker status monitoring
- Webhook event tracking

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Integration Service                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   API        │  │   Auth       │  │    Retry      │ │
│  │  Connector   │──│   Handler    │──│    Handler    │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
│         │                                       │        │
│         ▼                                       ▼        │
│  ┌──────────────┐                    ┌───────────────┐ │
│  │   Circuit    │                    │   Webhook     │ │
│  │   Breaker    │                    │   Handler     │ │
│  └──────────────┘                    └───────────────┘ │
└─────────────────────────────────────────────────────────┘
           │                                       │
           ▼                                       ▼
    ┌──────────────┐                      ┌──────────────┐
    │  PostgreSQL  │                      │  External    │
    │  (Logging)   │                      │  APIs        │
    └──────────────┘                      └──────────────┘
```

## Quick Start

### 1. Start the Service

```bash
# Using Docker Compose (recommended)
docker-compose up -d integration-service

# Or standalone
cd services/integration-service
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### 2. Check Health

```bash
curl http://localhost:8002/health
```

### 3. Make Your First API Call

```bash
curl -X POST http://localhost:8002/v1/integrations/execute \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": "generic-rest-api",
    "endpoint": "/users/1",
    "method": "GET"
  }'
```

## API Endpoints

### Health Check
- `GET /health` - Service health status
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

### Integration Execution
- `POST /v1/integrations/execute` - Execute single API call
- `POST /v1/integrations/execute/batch` - Execute multiple API calls

### Circuit Breakers
- `GET /v1/integrations/circuit-breakers` - Get all circuit breaker states
- `POST /v1/integrations/circuit-breakers/{integration_id}/reset` - Reset circuit breaker

### Webhooks
- `POST /v1/webhooks/{integration_id}/{event_type}` - Receive webhook
- `GET /v1/webhooks/{integration_id}/events` - List webhook events
- `POST /v1/webhooks/{integration_id}/events/{event_id}/process` - Process webhook event

## Usage Examples

### Example 1: Simple GET Request

```python
import httpx

response = await httpx.post(
    "http://localhost:8002/v1/integrations/execute",
    json={
        "integration_id": "generic-rest-api",
        "endpoint": "/users/1",
        "method": "GET"
    }
)

data = response.json()
print(f"Success: {data['success']}")
print(f"Status: {data['status_code']}")
print(f"Body: {data['body']}")
```

### Example 2: POST Request with Authentication

```python
response = await httpx.post(
    "http://localhost:8002/v1/integrations/execute",
    json={
        "integration_id": "stripe-api",
        "endpoint": "/v1/payment_intents",
        "method": "POST",
        "body": {
            "amount": 2000,
            "currency": "usd",
            "payment_method": "pm_card_visa"
        }
    }
)
```

### Example 3: Batch Requests (Parallel)

```python
response = await httpx.post(
    "http://localhost:8002/v1/integrations/execute/batch",
    json={
        "integration_id": "generic-rest-api",
        "requests": [
            {
                "integration_id": "generic-rest-api",
                "endpoint": "/users/1",
                "method": "GET"
            },
            {
                "integration_id": "generic-rest-api",
                "endpoint": "/users/2",
                "method": "GET"
            },
            {
                "integration_id": "generic-rest-api",
                "endpoint": "/users/3",
                "method": "GET"
            }
        ],
        "parallel": True
    }
)

data = response.json()
print(f"Total: {data['total']}")
print(f"Successful: {data['successful']}")
print(f"Failed: {data['failed']}")
```

### Example 4: From Dialogue Flow (api_caller node)

```python
# In your dialogue flow definition
{
    "node_id": "call_crm",
    "type": "api_caller",
    "config": {
        "integration_id": "salesforce-api",
        "endpoint": "/services/data/v55.0/sobjects/Contact",
        "method": "POST",
        "body_template": {
            "FirstName": "{{context.first_name}}",
            "LastName": "{{context.last_name}}",
            "Email": "{{context.email}}",
            "Phone": "{{context.phone}}"
        },
        "on_success": "success_response",
        "on_failure": "error_response"
    }
}
```

## Configuration

### Database Schema

Integration configurations are stored in `integration_configs` table:

```sql
-- Create new integration
INSERT INTO integration_configs (
    integration_id,
    name,
    base_url,
    auth_type,
    auth_config,
    is_active
) VALUES (
    'my-api',
    'My Custom API',
    'https://api.example.com',
    'bearer',
    '{"auth_type": "bearer", "bearer_token": "your-token-here"}'::jsonb,
    TRUE
);
```

### Environment Variables

```bash
# Service Configuration
SERVICE_PORT=8002
DEBUG=False

# Database
DATABASE_URL=postgresql+asyncpg://ocpuser:ocppassword@postgres:5432/ocplatform

# Redis (optional for caching)
REDIS_URL=redis://redis:6379/2

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3

# Retry Settings
RETRY_MAX_ATTEMPTS=3
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=60.0
RETRY_EXPONENTIAL_BASE=2.0

# HTTP Client
HTTP_TIMEOUT=30
HTTP_MAX_CONNECTIONS=100

# Webhooks
WEBHOOK_SECRET_KEY=your-webhook-secret
```

## Authentication Examples

### API Key (Header)

```sql
INSERT INTO integration_configs (
    integration_id, name, base_url, auth_type, auth_config
) VALUES (
    'api-key-example',
    'API Key Example',
    'https://api.example.com',
    'api_key',
    '{
        "auth_type": "api_key",
        "api_key_header": "X-API-Key",
        "api_key_value": "your-api-key-here"
    }'::jsonb
);
```

### Bearer Token

```sql
INSERT INTO integration_configs (
    integration_id, name, base_url, auth_type, auth_config
) VALUES (
    'bearer-example',
    'Bearer Token Example',
    'https://api.example.com',
    'bearer',
    '{
        "auth_type": "bearer",
        "bearer_token": "your-access-token-here"
    }'::jsonb
);
```

### Basic Authentication

```sql
INSERT INTO integration_configs (
    integration_id, name, base_url, auth_type, auth_config
) VALUES (
    'basic-auth-example',
    'Basic Auth Example',
    'https://api.example.com',
    'basic',
    '{
        "auth_type": "basic",
        "basic_username": "username",
        "basic_password": "password"
    }'::jsonb
);
```

### OAuth2 Client Credentials

```sql
INSERT INTO integration_configs (
    integration_id, name, base_url, auth_type, auth_config
) VALUES (
    'oauth2-example',
    'OAuth2 Example',
    'https://api.example.com',
    'oauth2',
    '{
        "auth_type": "oauth2",
        "oauth2_token_url": "https://auth.example.com/oauth/token",
        "oauth2_client_id": "your-client-id",
        "oauth2_client_secret": "your-client-secret",
        "oauth2_scope": "read write"
    }'::jsonb
);
```

## Circuit Breaker

The circuit breaker prevents cascading failures when external APIs are down.

### States

1. **CLOSED** (Normal): Requests pass through
2. **OPEN** (Failing): Requests are blocked
3. **HALF_OPEN** (Testing): Limited requests to test recovery

### Monitoring

```bash
# Get circuit breaker status
curl http://localhost:8002/v1/integrations/circuit-breakers

# Response:
{
    "salesforce-api": {
        "name": "salesforce-api",
        "state": "closed",
        "failure_count": 0,
        "can_execute": true
    },
    "stripe-api": {
        "name": "stripe-api",
        "state": "open",
        "failure_count": 5,
        "can_execute": false
    }
}
```

### Manual Reset

```bash
# Reset circuit breaker manually
curl -X POST http://localhost:8002/v1/integrations/circuit-breakers/stripe-api/reset
```

## Webhooks

### Receiving Webhooks

External systems can send webhooks to:

```
POST http://your-domain.com/v1/webhooks/{integration_id}/{event_type}
```

Example:
```bash
# Stripe webhook
POST http://localhost:8002/v1/webhooks/stripe-api/payment.succeeded
Headers:
  X-Webhook-Signature: sha256=abc123...
Body:
  {
    "id": "evt_123",
    "type": "payment.succeeded",
    "data": {
      "object": {
        "id": "pi_123",
        "amount": 2000,
        "currency": "usd"
      }
    }
  }
```

### Signature Verification

Webhooks can be verified using HMAC-SHA256:

```sql
-- Set webhook secret for integration
UPDATE integration_configs
SET webhook_secret = 'your-webhook-secret'
WHERE integration_id = 'stripe-api';
```

The service automatically verifies the `X-Webhook-Signature` header.

### Processing Webhooks

```bash
# List unprocessed webhooks
curl http://localhost:8002/v1/webhooks/stripe-api/events?processed=false

# Process webhook manually
curl -X POST http://localhost:8002/v1/webhooks/stripe-api/events/{event_id}/process
```

## Performance Metrics

The service tracks execution metrics in the `integration_executions` table:

```sql
-- Get integration performance stats
SELECT * FROM integration_performance_stats
WHERE integration_id = 'salesforce-api';

-- Result:
┌─────────────────┬─────────────┬──────────────────┬───────────────┬──────────────────────┐
│ integration_id  │ total_calls │ successful_calls │ failed_calls  │ avg_execution_time_ms│
├─────────────────┼─────────────┼──────────────────┼───────────────┼──────────────────────┤
│ salesforce-api  │        1234 │             1200 │            34 │               245.67 │
└─────────────────┴─────────────┴──────────────────┴───────────────┴──────────────────────┘
```

## Troubleshooting

### Integration Returns 503

**Problem**: Circuit breaker is OPEN

**Solution**:
```bash
# Check circuit breaker status
curl http://localhost:8002/v1/integrations/circuit-breakers

# Reset if needed
curl -X POST http://localhost:8002/v1/integrations/circuit-breakers/{integration_id}/reset
```

### Slow Response Times

**Problem**: Integration taking too long

**Solutions**:
1. Increase timeout: Update `timeout_seconds` in `integration_configs`
2. Disable retry: Set `retry_enabled = FALSE`
3. Check external API status

### Authentication Fails

**Problem**: 401 Unauthorized

**Solutions**:
1. Verify credentials in `auth_config`
2. For OAuth2, check token expiration
3. Clear cached token: Restart service

### Webhooks Not Verified

**Problem**: Signature verification fails

**Solutions**:
1. Check `webhook_secret` matches external system
2. Verify signature format (should be `sha256=...`)
3. Check raw body encoding

## API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

## Security

### Best Practices

1. **Secrets Management**:
   - Never commit API keys to version control
   - Use environment variables or secrets manager
   - Rotate credentials regularly

2. **Webhook Security**:
   - Always set `webhook_secret`
   - Use HTTPS in production
   - Validate webhook sources by IP if possible

3. **Rate Limiting**:
   - Configure rate limits per integration
   - Monitor usage to prevent abuse

4. **Network Security**:
   - Use VPC/private networks in production
   - Whitelist IP ranges for sensitive APIs
   - Enable mutual TLS if supported

## Next Steps

1. **Add More Integrations**: See `scripts/sql/migrations/002_integration_service_tables.sql`
2. **Create Custom Mappings**: Implement Jinja2 templates for complex transformations
3. **Monitor Performance**: Use `integration_performance_stats` view
4. **Set Up Alerts**: Configure monitoring for circuit breaker state changes

## Support

- **Documentation**: See `/docs` directory
- **API Docs**: http://localhost:8002/docs
- **Issues**: GitHub Issues
- **Architecture**: See `ARCHITECTURE.md`

---

**Version**: 1.0.0
**Last Updated**: 2025-01-21
**Phase**: 2
