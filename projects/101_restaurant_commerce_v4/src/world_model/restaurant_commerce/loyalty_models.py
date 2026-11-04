"""Additive experimentation metadata. Existing wallets and orders remain authoritative."""

from datetime import datetime

from sqlalchemy import (
    DDL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, new_id, utcnow


class LoyaltyStrategy(Base):
    __tablename__ = "restaurant_loyalty_strategies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("restaurant_commerce_profiles.business_id"))
    request_key: Mapped[str] = mapped_column(String(100))
    creation_digest: Mapped[str] = mapped_column(String(64))
    draft_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __mapper_args__ = {"version_id_col": revision}
    __table_args__ = (
        UniqueConstraint("business_id", "request_key"),
        UniqueConstraint("id", "business_id"),
        CheckConstraint(
            "state IN ('draft','published','paused','archived')", name="ck_loyalty_strategy_state"
        ),
    )


class LoyaltyStrategyVersion(Base):
    __tablename__ = "restaurant_loyalty_strategy_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    strategy_id: Mapped[str] = mapped_column(String(36))
    business_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    document: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["strategy_id", "business_id"],
            ["restaurant_loyalty_strategies.id", "restaurant_loyalty_strategies.business_id"],
        ),
        UniqueConstraint("strategy_id", "revision"),
        UniqueConstraint("id", "business_id"),
    )


class LoyaltyExperiment(Base):
    __tablename__ = "restaurant_loyalty_experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("restaurant_commerce_profiles.business_id"))
    request_key: Mapped[str] = mapped_column(String(100))
    creation_digest: Mapped[str] = mapped_column(String(64))
    draft_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __mapper_args__ = {"version_id_col": revision}
    __table_args__ = (
        UniqueConstraint("business_id", "request_key"),
        UniqueConstraint("id", "business_id"),
        CheckConstraint(
            "state IN ('draft','published','paused','archived')", name="ck_loyalty_experiment_state"
        ),
    )


class LoyaltyExperimentVersion(Base):
    __tablename__ = "restaurant_loyalty_experiment_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(String(36))
    business_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    document: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    random_salt: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["experiment_id", "business_id"],
            ["restaurant_loyalty_experiments.id", "restaurant_loyalty_experiments.business_id"],
        ),
        UniqueConstraint("experiment_id", "revision"),
        UniqueConstraint("id", "business_id"),
    )


class LoyaltyExperimentVariant(Base):
    __tablename__ = "restaurant_loyalty_experiment_variants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_version_id: Mapped[str] = mapped_column(String(36))
    business_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(100))
    allocation_bps: Mapped[int] = mapped_column(Integer)
    strategy_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["experiment_version_id", "business_id"],
            [
                "restaurant_loyalty_experiment_versions.id",
                "restaurant_loyalty_experiment_versions.business_id",
            ],
        ),
        ForeignKeyConstraint(
            ["strategy_version_id", "business_id"],
            [
                "restaurant_loyalty_strategy_versions.id",
                "restaurant_loyalty_strategy_versions.business_id",
            ],
        ),
        UniqueConstraint("experiment_version_id", "name"),
        CheckConstraint(
            "allocation_bps > 0 AND allocation_bps <= 10000", name="ck_loyalty_variant_allocation"
        ),
    )


class LoyaltyConfigurationAudit(Base):
    __tablename__ = "restaurant_loyalty_configuration_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("restaurant_commerce_profiles.business_id"))
    actor_id: Mapped[str] = mapped_column(String(128))
    resource_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(40))
    revision: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


IMMUTABLE_TABLES = (
    LoyaltyStrategyVersion.__table__,
    LoyaltyExperimentVersion.__table__,
    LoyaltyExperimentVariant.__table__,
    LoyaltyConfigurationAudit.__table__,
)
LOYALTY_TABLES = frozenset(
    t.__tablename__
    for t in (
        LoyaltyStrategy,
        LoyaltyStrategyVersion,
        LoyaltyExperiment,
        LoyaltyExperimentVersion,
        LoyaltyExperimentVariant,
        LoyaltyConfigurationAudit,
    )
)

# Canonical protection definitions are also checked by schema readiness.
SQLITE_PROTECTIONS = {}
POSTGRES_PROTECTIONS = {}
IMMUTABLE_BODY = "BEGIN RAISE EXCEPTION 'Immutable loyalty history'; END"


def protect(table, suffix, operations, sqlite_body, postgres_body, trigger_type):
    name = f"{table.name}_{suffix}"
    statement = f"CREATE TRIGGER {name} BEFORE {operations} ON {table.name} {sqlite_body}"
    SQLITE_PROTECTIONS[name] = statement
    event.listen(table, "after_create", DDL(statement).execute_if(dialect="sqlite"))
    # SQLite has separate UPDATE/DELETE triggers; PG uses the same split for parity.
    POSTGRES_PROTECTIONS[name] = (table.name, postgres_body, trigger_type)
    event.listen(
        table,
        "after_create",
        DDL(
            f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ {postgres_body} $$"
        ).execute_if(dialect="postgresql"),
    )
    event.listen(
        table,
        "after_create",
        DDL(
            f"CREATE TRIGGER {name} BEFORE {operations} ON {table.name} "
            f"FOR EACH ROW EXECUTE FUNCTION {name}()"
        ).execute_if(dialect="postgresql"),
    )


for table in IMMUTABLE_TABLES:
    for operation, trigger_type in (("UPDATE", 19), ("DELETE", 11)):
        protect(
            table,
            operation.lower(),
            operation,
            "BEGIN SELECT RAISE(ABORT, 'Immutable loyalty history'); END",
            IMMUTABLE_BODY,
            trigger_type,
        )

# A separately inserted row cannot change the frozen variant set. Each row must
# match one declared variant exactly; uniqueness prevents inserting that row twice.
protect(
    LoyaltyExperimentVariant.__table__,
    "insert",
    "INSERT",
    """
BEGIN
 SELECT CASE WHEN NOT EXISTS (
   SELECT 1 FROM restaurant_loyalty_experiment_versions e, json_each(e.document, '$.variants') v
   WHERE e.id = NEW.experiment_version_id AND e.business_id = NEW.business_id
     AND json_extract(v.value, '$.name') = NEW.name
     AND json_extract(v.value, '$.allocation_bps') = NEW.allocation_bps
     AND json_extract(v.value, '$.strategy_version_id') IS NEW.strategy_version_id
 ) THEN RAISE(ABORT, 'Variant differs from published experiment') END;
END
""",
    """
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM restaurant_loyalty_experiment_versions e,
     jsonb_array_elements(e.document::jsonb -> 'variants') v
   WHERE e.id = NEW.experiment_version_id AND e.business_id = NEW.business_id
     AND v ->> 'name' = NEW.name
     AND (v ->> 'allocation_bps')::integer = NEW.allocation_bps
     AND (v ->> 'strategy_version_id') IS NOT DISTINCT FROM NEW.strategy_version_id
 ) THEN RAISE EXCEPTION 'Variant differs from published experiment'
   USING ERRCODE = '23514'; END IF;
 RETURN NEW;
END
""",
    7,
)
