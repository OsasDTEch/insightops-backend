# models.py
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, Date,
    ForeignKey, DECIMAL, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship, declarative_base

from database.db import Base

# ---------------------------------------------------------------------
# Subscription plans (seed these on deploy)
# ---------------------------------------------------------------------
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)  # free, pro, enterprise
    price_monthly = Column(DECIMAL(10, 2), default=0)
    price_yearly = Column(DECIMAL(10, 2), default=0)
    max_feedback_items = Column(Integer, default=0)
    max_integrations = Column(Integer, default=0)
    ai_analysis_limit = Column(Integer, default=0)  # per month
    features = Column(JSONB, default=list)  # e.g. ["advanced_insights"]
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------
# Workspace - represents a tenant/org (MVP: one workspace per user by default)
# ---------------------------------------------------------------------
class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(120), unique=True, nullable=True)

    # Subscription fields
    subscription_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True)
    subscription_status = Column(String(50), default="free")  # free, pro, enterprise, past_due
    subscription_period_start = Column(Date)
    subscription_period_end = Column(Date)
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))

    # Usage counters (for limits enforcement)
    current_feedback_count = Column(Integer, default=0)
    monthly_ai_analysis_count = Column(Integer, default=0)
    last_reset_date = Column(Date, default=date.today)

    settings = Column(JSONB, default=dict)  # workspace-specific settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    memberships = relationship("Membership", back_populates="workspace", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="workspace", cascade="all, delete-orphan")
    feedback_items = relationship("FeedbackItem", back_populates="workspace", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="workspace", cascade="all, delete-orphan")
    insights_snapshots = relationship("InsightsSnapshot", back_populates="workspace", cascade="all, delete-orphan")
    usage = relationship("UsageTracking", back_populates="workspace", cascade="all, delete-orphan")


# ---------------------------------------------------------------------
# User
# ---------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)  # nullable if SSO-only
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    # SSO metadata (optional, useful later)
    sso_provider = Column(String(100), nullable=True)  # e.g., "google", "azure", "okta"
    sso_subject = Column(String(255), nullable=True)   # subject/id from IdP
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------
# Membership: links user <-> workspace with role
# ---------------------------------------------------------------------
class Membership(Base):
    __tablename__ = "memberships"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    role = Column(String(50), default="member")  # owner, admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memberships")
    workspace = relationship("Workspace", back_populates="memberships")

    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace"),)


# ---------------------------------------------------------------------
# Invitation flow
# ---------------------------------------------------------------------
class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    invited_email = Column(String(255), nullable=False)
    role = Column(String(50), default="member")
    token = Column(String(255), nullable=False, unique=True)  # random token or signed JWT
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="invitations")


# ---------------------------------------------------------------------
# Integrations (CSV, Zendesk, Intercom, etc.)
# - config/credentials should be encrypted at rest (store JSON in config)
# ---------------------------------------------------------------------
class Integration(Base):
    __tablename__ = "integrations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    type = Column(String(50), nullable=False)  # csv, zendesk, intercom, slack, etc.
    name = Column(String(255), nullable=True)
    config = Column(JSONB, nullable=False, default=dict)  # e.g., oauth tokens, settings (encrypt in app)
    webhook_url = Column(String(500), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(50), default="pending")  # pending, syncing, completed, error
    total_items_synced = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="integrations")
    feedback_items = relationship("FeedbackItem", back_populates="integration", cascade="all, delete-orphan")
    webhook_events = relationship("WebhookEvent", back_populates="integration", cascade="all, delete-orphan")


# ---------------------------------------------------------------------
# Unified Feedback Items table: the magic hub
# - Stores raw content and AI enrichment columns
# ---------------------------------------------------------------------
class FeedbackItem(Base):
    __tablename__ = "feedback_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True)

    # source info
    source_type = Column(String(50), nullable=False)  # csv, zendesk, intercom
    external_id = Column(String(255), nullable=True)  # e.g., ticket id in Zendesk
    source_url = Column(String(500), nullable=True)

    # customer & content
    customer_email = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)
    raw_content = Column(Text, nullable=False)
    cleaned_content = Column(Text, nullable=True)  # optional cleaned text

    # source metadata from provider
    source_metadata = Column(JSONB, default=dict)  # status, priority, tags, assignee...

    # AI enrichment (filled by background task)
    sentiment = Column(String(20), nullable=True)  # positive, neutral, negative
    sentiment_score = Column(DECIMAL(3, 2), nullable=True)  # -1.0 .. 1.0
    confidence_score = Column(DECIMAL(3, 2), nullable=True)  # 0.0 .. 1.0
    primary_category = Column(String(100), nullable=True)
    categories = Column(ARRAY(String), nullable=True)
    ai_summary = Column(Text, nullable=True)
    priority_score = Column(Integer, default=0)  # 0-10
    keywords = Column(ARRAY(String), nullable=True)

    # processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    reviewed_by_user = Column(Boolean, default=False)
    user_category_override = Column(String(100), nullable=True)

    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="feedback_items")
    integration = relationship("Integration", back_populates="feedback_items")

    __table_args__ = (
        UniqueConstraint("workspace_id", "external_id", "source_type", name="uq_feedback_unique"),
        Index("idx_feedback_workspace_created", "workspace_id", "created_at"),
        Index("idx_feedback_sentiment", "workspace_id", "sentiment"),
        Index("idx_feedback_category", "workspace_id", "primary_category"),
        Index("idx_feedback_processed", "workspace_id", "is_processed"),
    )


# ---------------------------------------------------------------------
# AI analysis job record (for background tasks - no Celery required)
# - Create a job entry when new feedback needs processing
# - Background worker (FastAPI background task or worker process) picks up and updates
# ---------------------------------------------------------------------
class AIAnalysisJob(Base):
    __tablename__ = "ai_analysis_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    feedback_item_id = Column(UUID(as_uuid=True), ForeignKey("feedback_items.id", ondelete="CASCADE"))
    job_type = Column(String(50), nullable=False)  # sentiment, categorization, summary
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------
# Usage tracking (daily) - used for billing and limit enforcement
# ---------------------------------------------------------------------
class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    feedback_items_processed = Column(Integer, default=0)
    ai_analyses_run = Column(Integer, default=0)
    api_requests = Column(Integer, default=0)
    export_requests = Column(Integer, default=0)
    ai_cost_usd = Column(DECIMAL(10, 4), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="usage")
    __table_args__ = (UniqueConstraint("workspace_id", "date", name="uq_usage_workspace_date"),)


# ---------------------------------------------------------------------
# Billing event records (Stripe)
# ---------------------------------------------------------------------
class BillingEvent(Base):
    __tablename__ = "billing_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    event_type = Column(String(100), nullable=False)  # subscription_created, payment_succeeded, invoice_failed
    stripe_event_id = Column(String(255), nullable=True, unique=True)
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String(3), default="USD")
    event_data = Column(JSONB, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------
# Insights snapshot (aggregated AI content for dashboards)
# ---------------------------------------------------------------------
class InsightsSnapshot(Base):
    __tablename__ = "insights_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly

    total_feedback_count = Column(Integer, default=0)
    sentiment_breakdown = Column(JSONB, nullable=True)  # {"positive": 45, "neutral": 30, "negative": 25}
    category_breakdown = Column(JSONB, nullable=True)  # [{"category":"billing","count":12}, ...]
    top_issues = Column(JSONB, nullable=True)  # [{"issue":"Billing portal errors","description":"..."}]
    trend_analysis = Column(Text, nullable=True)
    recommendations = Column(ARRAY(String), nullable=True)
    risk_alerts = Column(ARRAY(String), nullable=True)

    sentiment_change = Column(DECIMAL(5, 2), nullable=True)  # percentage change
    volume_change = Column(DECIMAL(5, 2), nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="insights_snapshots")
    __table_args__ = (UniqueConstraint("workspace_id", "period_start", "period_type", name="uq_insight_period"),)


# ---------------------------------------------------------------------
# Webhook events (raw payload buffer for retries & debugging)
# ---------------------------------------------------------------------
class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"))
    webhook_id = Column(String(255), nullable=True)  # id from external provider
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    integration = relationship("Integration", back_populates="webhook_events")


# ---------------------------------------------------------------------
# Agent runs (storing output from pydantic_ai / langchain / langgraph)
# ---------------------------------------------------------------------
class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    request_id = Column(String(255), nullable=False, index=True)  # maps to workflow request
    agent_name = Column(String(100), nullable=False)  # e.g., "AnalyticsAgent", "LLMQA"
    status = Column(String(50), default="pending")  # pending | success | failed
    message = Column(Text, nullable=True)  # optional human-readable explanation
    data = Column(JSONB, nullable=True)  # serialized AgentResponse / AnalyticsInsight / LLMAnswer
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace")

    __table_args__ = (
        Index("idx_agentrun_workspace_request", "workspace_id", "request_id"),
        Index("idx_agentrun_status", "status"),
    )

