"""
Pydantic models for request/response validation
"""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


# ============================================
# Integration Configuration Schemas
# ============================================

class IntegrationAuthConfig(BaseModel):
    """Authentication configuration for integration"""
    auth_type: Literal["none", "api_key", "bearer", "basic", "oauth2"]
    api_key_header: Optional[str] = None
    api_key_value: Optional[str] = None
    bearer_token: Optional[str] = None
    basic_username: Optional[str] = None
    basic_password: Optional[str] = None
    oauth2_token_url: Optional[str] = None
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    oauth2_scope: Optional[str] = None


class IntegrationConfig(BaseModel):
    """Integration configuration"""
    integration_id: str
    name: str
    description: Optional[str] = None
    base_url: HttpUrl
    auth_config: IntegrationAuthConfig
    default_headers: Optional[Dict[str, str]] = {}
    timeout: int = 30
    retry_enabled: bool = True
    circuit_breaker_enabled: bool = True
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = {}


# ============================================
# API Request/Response Schemas
# ============================================

class APIRequest(BaseModel):
    """Generic API request"""
    integration_id: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None


class APIResponse(BaseModel):
    """Generic API response"""
    success: bool
    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    raw_body: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Template Mapping Schemas
# ============================================

class RequestTemplate(BaseModel):
    """Request template with Jinja2 mapping"""
    endpoint_template: str
    method: str = "POST"
    headers_template: Optional[Dict[str, str]] = None
    body_template: Optional[str] = None  # Jinja2 template as string
    query_params_template: Optional[Dict[str, str]] = None


class ResponseTemplate(BaseModel):
    """Response template for mapping external API response"""
    mapping: Dict[str, str]  # Jinja2 expressions for extracting data
    success_condition: Optional[str] = None  # Jinja2 expression


class IntegrationTemplate(BaseModel):
    """Complete integration template"""
    integration_id: str
    template_name: str
    request_template: RequestTemplate
    response_template: ResponseTemplate


# ============================================
# Webhook Schemas
# ============================================

class WebhookConfig(BaseModel):
    """Webhook configuration"""
    webhook_id: str
    integration_id: str
    event_type: str
    url: HttpUrl
    secret: Optional[str] = None
    is_active: bool = True
    retry_on_failure: bool = True
    max_retries: int = 3


class WebhookPayload(BaseModel):
    """Webhook payload"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook delivery response"""
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    attempts: int = 1
    delivered_at: Optional[datetime] = None


# ============================================
# Execution Schemas
# ============================================

class IntegrationExecution(BaseModel):
    """Integration execution record"""
    execution_id: str
    integration_id: str
    session_id: Optional[str] = None
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    success: bool
    error: Optional[str] = None
    execution_time_ms: float
    retries: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Health Check Schemas
# ============================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, bool]
    details: Optional[Dict[str, Any]] = None


# ============================================
# Batch Processing Schemas
# ============================================

class BatchRequest(BaseModel):
    """Batch API request"""
    integration_id: str
    requests: List[APIRequest]
    parallel: bool = True
    stop_on_error: bool = False


class BatchResponse(BaseModel):
    """Batch API response"""
    total: int
    successful: int
    failed: int
    results: List[APIResponse]
    execution_time_ms: float
