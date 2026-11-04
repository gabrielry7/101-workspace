"""Phone access and business membership links; Customer remains the contact authority."""
from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, new_id, utcnow


class CustomerAccount(Base):
    __tablename__ = 'restaurant_signup_accounts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    channel: Mapped[str] = mapped_column(String(10))
    identifier: Mapped[str] = mapped_column(String(254))
    scope: Mapped[str] = mapped_column(String(16))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint('scope', 'channel', 'identifier'),)


class CustomerMembership(Base):
    __tablename__ = 'restaurant_signup_memberships'
    account_id: Mapped[str] = mapped_column(ForeignKey(CustomerAccount.id), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('restaurant_customers.id'), unique=True)
    source: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CustomerLoginSession(Base):
    __tablename__ = 'restaurant_signup_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey(CustomerAccount.id), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignupChallenge(Base):
    __tablename__ = 'restaurant_signup_challenges'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    destination: Mapped[str] = mapped_column(String(254), index=True)
    scope: Mapped[str] = mapped_column(String(16))
    binding_hash: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default='submitting')
    provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignupThrottle(Base):
    __tablename__ = 'restaurant_signup_throttles'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class SignupEvent(Base):
    __tablename__ = 'restaurant_signup_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    scope: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    stage: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


TABLES = frozenset(t for t in Base.metadata.tables if t.startswith('restaurant_signup_'))

