from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

# ---------------------
# Token + User Info
# ---------------------
class LoginUserOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr

class LoginResponse(BaseModel):
    status_code: int
    message: str
    user: LoginUserOut
    access_token: str
    token_type: str = "Bearer"

# ---------------------
# Base Response Wrapper
# ---------------------
class ResponseBase(BaseModel):
    status_code: int
    message: str

# ---------------------
# Auth / User
# ---------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(ResponseBase):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    workspace_id: UUID
    role: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
from typing import List
from uuid import UUID
from pydantic import BaseModel

class UserMembership(BaseModel):
    workspace_id: str
    role: str

class UserOutMultiple(BaseModel):
    status_code: int
    message: str
    id: UUID
    email: str
    full_name: str
    is_active: bool
    memberships: List[UserMembership]
    created_at: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

# ---------------------
# Workspace
# ---------------------
class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceOut(ResponseBase):
    id: UUID
    name: str
    slug: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Membership
# ---------------------
class MembershipOut(ResponseBase):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    role: str

    model_config = {
        "from_attributes": True
    }

class MembershipCreate(BaseModel):
    user_id: UUID
    role: str = "member"

# ---------------------
# Invitation
# ---------------------
class InviteCreate(BaseModel):
    invited_email: EmailStr
    role: str = "member"
    expires_in_days: Optional[int] = 7

class InviteOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    invited_email: EmailStr
    role: str
    accepted: bool
    created_at: datetime
    expires_at: Optional[datetime]

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Integration
# ---------------------
class IntegrationCreate(BaseModel):
    type: str = Field(..., description="csv | zendesk | intercom")
    name: Optional[str] = None
    config: Optional[dict] = None

class IntegrationOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    type: str
    name: Optional[str]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Feedback
# ---------------------
class FeedbackCreate(BaseModel):
    source_type: str
    raw_content: str
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    external_id: Optional[str] = None
    source_url: Optional[str] = None
    source_metadata: Optional[dict] = None

class FeedbackOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    integration_id: Optional[UUID]
    source_type: str
    external_id: Optional[str]
    source_url: Optional[str]
    customer_email: Optional[EmailStr]
    customer_name: Optional[str]
    raw_content: str

    sentiment: Optional[str]
    sentiment_score: Optional[float]
    confidence_score: Optional[float]
    primary_category: Optional[str]
    categories: Optional[List[str]]
    ai_summary: Optional[str]
    priority_score: Optional[int]
    keywords: Optional[List[str]]

    is_processed: bool
    processed_at: Optional[datetime]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# AI Analysis Job
# ---------------------
class AIJobCreate(BaseModel):
    feedback_item_id: UUID
    job_type: str
    input_data: Optional[dict] = None

class AIJobOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    feedback_item_id: UUID
    job_type: str
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Usage & Billing
# ---------------------
class UsageOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    date: date
    feedback_items_processed: int
    ai_analyses_run: int
    ai_cost_usd: float

    model_config = {
        "from_attributes": True
    }

class BillingEventOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    event_type: str
    stripe_event_id: Optional[str]
    amount_cents: Optional[int]
    currency: Optional[str]
    event_data: Optional[dict]
    processed_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Insights Snapshot
# ---------------------
class InsightsSnapshotCreate(BaseModel):
    period_start: date
    period_end: date
    period_type: str

class InsightsSnapshotOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    period_start: date
    period_end: date
    period_type: str
    total_feedback_count: int
    sentiment_breakdown: Optional[dict]
    category_breakdown: Optional[list]
    top_issues: Optional[list]
    trend_analysis: Optional[str]
    recommendations: Optional[List[str]]
    generated_at: datetime

    model_config = {
        "from_attributes": True
    }

# ---------------------
# Webhook Event
# ---------------------
class WebhookEventCreate(BaseModel):
    integration_id: UUID
    webhook_id: Optional[str]
    event_type: str
    payload: dict

class WebhookEventOut(ResponseBase):
    id: UUID
    workspace_id: UUID
    integration_id: UUID
    webhook_id: Optional[str]
    event_type: str
    payload: dict
    processed: bool
    received_at: datetime

    model_config = {
        "from_attributes": True
    }
