"""Owner-authorized connections; provider content is an expiring cache, not evidence history."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, new_id, utcnow


class BusinessConnection(Base):
    __tablename__ = 'restaurant_business_connections'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), index=True)
    provider: Mapped[str] = mapped_column(String(32), default='google_business')
    mode: Mapped[str] = mapped_column(String(12))
    state: Mapped[str] = mapped_column(String(40), default='disconnected')
    generation: Mapped[int] = mapped_column(Integer, default=0)
    secret: Mapped[str | None] = mapped_column(Text)
    selected: Mapped[str | None] = mapped_column(String(160))
    assets: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[str | None] = mapped_column(Text)
    assets_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint('business_id', 'provider', 'mode'),)


class ConnectionAuthorization(Base):
    __tablename__ = 'restaurant_connection_authorizations'
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey(BusinessConnection.id), index=True)
    session_hash: Mapped[str] = mapped_column(String(64))
    generation: Mapped[int] = mapped_column(Integer)
    verifier: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConnectionJob(Base):
    __tablename__ = 'restaurant_connection_jobs'
    connection_id: Mapped[str] = mapped_column(ForeignKey(BusinessConnection.id), primary_key=True)
    generation: Mapped[int] = mapped_column(Integer)
    operation: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default='pending')
    lease: Mapped[str | None] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Disconnect immediately removes credentials from the connection. Revocation
    # retains encrypted credentials only in this expiring, private worker record.
    secret: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


TABLES = frozenset(t for t in Base.metadata.tables if t.startswith('restaurant_connection_') or t == 'restaurant_business_connections')


def upgrade_connections(engine):
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=[t for t in Base.metadata.sorted_tables if t.name in TABLES])


def schema_ready(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    return all(t in inspector.get_table_names() and set(Base.metadata.tables[t].columns.keys()).issubset(
        {c['name'] for c in inspector.get_columns(t)}) for t in TABLES)
