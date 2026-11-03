"""Campaign-owned state; customer and order authority remain in models.py."""
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, new_id, utcnow


class CampaignSettings(Base):
    __tablename__ = 'restaurant_campaign_settings'
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), primary_key=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    scope: Mapped[str] = mapped_column(String(24), default='test')
    config_json: Mapped[str] = mapped_column(Text, default='{}')
    # Incremented under lock to serialize shared per-business contact limits.
    dispatch_version: Mapped[int] = mapped_column(Integer, default=0)


class ContactPermission(Base):
    __tablename__ = 'restaurant_contact_permissions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('restaurant_customers.id'), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(24), default='marketing')
    scope: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(24))
    destination: Mapped[str] = mapped_column(String(320))
    source: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    registry_json: Mapped[str] = mapped_column(Text, default='{}')
    __table_args__ = (UniqueConstraint('business_id','customer_id','channel','purpose','scope'),)


class PermissionEvidence(Base):
    __tablename__ = 'restaurant_permission_evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    permission_id: Mapped[str] = mapped_column(ForeignKey('restaurant_contact_permissions.id'))
    evidence_json: Mapped[str] = mapped_column(Text)
    at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class Campaign(Base):
    __tablename__ = 'restaurant_campaigns'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), index=True)
    revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(24), default='draft')
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class CampaignRevision(Base):
    __tablename__ = 'restaurant_campaign_revisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaigns.id'), index=True)
    document: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class CampaignApproval(Base):
    __tablename__ = 'restaurant_campaign_approvals'
    revision_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_revisions.id'), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    digest: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(24))
    approved_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class CampaignJob(Base):
    __tablename__ = 'restaurant_campaign_jobs'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_revisions.id'), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('restaurant_customers.id'))
    destination: Mapped[str] = mapped_column(String(320))
    channel: Mapped[str] = mapped_column(String(16))
    scope: Mapped[str] = mapped_column(String(24), index=True)
    state: Mapped[str] = mapped_column(String(24), default='queued', index=True)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    claimed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_token: Mapped[str] = mapped_column(String(64), unique=True)
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True)
    __table_args__ = (UniqueConstraint('revision_id','customer_id','channel'),)


class CampaignAttempt(Base):
    __tablename__ = 'restaurant_campaign_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_jobs.id'), index=True)
    state: Mapped[str] = mapped_column(String(24))
    evidence_json: Mapped[str] = mapped_column(Text)
    at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class CampaignEvent(Base):
    __tablename__ = 'restaurant_campaign_events'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_jobs.id'), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    provider_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    evidence_json: Mapped[str] = mapped_column(Text)


class CampaignVisit(Base):
    __tablename__ = 'restaurant_campaign_visits'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    job_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_jobs.id'), index=True)
    at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    scanner: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_json: Mapped[str] = mapped_column(Text)
    rule: Mapped[str] = mapped_column(String(64), default='last-eligible-visit-7d-v1')


class CampaignOrderCredit(Base):
    __tablename__ = 'restaurant_campaign_order_credits'
    order_id: Mapped[str] = mapped_column(ForeignKey('restaurant_orders.id'), primary_key=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey('restaurant_campaign_revisions.id'))
    visit_id: Mapped[str | None] = mapped_column(ForeignKey('restaurant_campaign_visits.id'), nullable=True)
    rule: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(24))
