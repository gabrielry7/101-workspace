"""Versioned marketing assertions. These are not Genome or global Truth decisions.

Scope uses the existing commerce profile and an optional canonical location resolver.
Every version is immutable; current pointers and dependency checks govern new exports.
"""

# ruff: noqa: B008 -- FastAPI dependency injection

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import ForeignKey, String, Text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .models import Base, utcnow
from .social_onboarding import OnboardingInput
from .social_production import FactReference, Strict, canonical, future, require

TABLES = {"social_contexts", "social_context_versions", "social_fact_dependencies"}


class Context(Base):
    __tablename__ = "social_contexts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision: Mapped[int] = mapped_column(default=0)


class ContextVersion(Base):
    __tablename__ = "social_context_versions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    context_id: Mapped[str] = mapped_column(ForeignKey("social_contexts.id"), index=True)
    document: Mapped[str] = mapped_column(Text)


class FactDependency(Base):
    __tablename__ = "social_fact_dependencies"
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"), primary_key=True)
    fact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    context_version_id: Mapped[str] = mapped_column(
        ForeignKey("social_context_versions.id"), index=True
    )
    fact_revision: Mapped[int]


class Assertion(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    label: str = Field(min_length=1, max_length=100)
    kind: Literal["text", "number", "money", "boolean"] = "text"
    value: str = Field(min_length=1, max_length=500)
    unit: str | None = Field(default=None, max_length=40)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=300)
    effective_at: AwareDatetime
    valid_until: AwareDatetime
    status: Literal["confirmed", "withdrawn"] = "confirmed"

    @model_validator(mode="after")
    def typed(self):
        require(self.valid_until > self.effective_at, "invalid_fact_validity", 422)
        if self.kind in ("number", "money"):
            try:
                number = Decimal(self.value)
            except InvalidOperation:
                raise ValueError("invalid_number") from None
            if not number.is_finite() or abs(number) > Decimal("1e15"):
                raise ValueError("invalid_number")
            self.value = format(number.normalize(), "f")
            if self.kind == "money" and (number < 0 or number.as_tuple().exponent < -2):
                raise ValueError("invalid_money")
        if (self.kind == "money") != (self.currency is not None):
            raise ValueError("money_requires_currency")
        if self.kind == "boolean" and self.value not in ("true", "false"):
            raise ValueError("invalid_boolean")
        for text in (self.value, self.label):
            if re.search(r"\[[^]]+\]", text) or any(ord(c) < 32 for c in text):
                raise ValueError("placeholder_or_control_character")
        return self


def statement(fact):
    value = fact["value"]
    if fact["kind"] == "text":
        return value
    if fact["kind"] == "boolean":
        value = "sí" if value == "true" else "no"
    suffix = fact.get("currency") or fact.get("unit")
    return f"{fact['label']}: {value}{' ' + suffix if suffix else ''}."


class BusinessBrief(Strict):
    offering: str | None = Field(default=None, min_length=1, max_length=3000)
    objective: str | None = Field(default=None, min_length=1, max_length=3000)
    buying_destination: str | None = Field(default=None, min_length=1, max_length=15000)
    constraints: str = Field(default="", max_length=15000)
    locale: str | None = Field(default=None, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    # Explicit unknowns, never inferred from absence or a social caption.
    capacity: str | None = Field(default=None, max_length=300)
    margin: str | None = Field(default=None, max_length=300)


class ContextInput(Strict):
    expected_revision: int = Field(ge=0)
    location_id: UUID | None = None
    brief: BusinessBrief
    facts: list[Assertion] = Field(max_length=40)
    confirmed: Literal[True]

    @model_validator(mode="after")
    def unique(self):
        if len({f.id for f in self.facts}) != len(self.facts):
            raise ValueError("duplicate_fact")
        return self


def scope_id(business, location):
    return hashlib.sha256((business + ":" + (location or "business")).encode()).hexdigest()[:32]


def read_context(session, business, location=None):
    row = session.get(Context, scope_id(business, location))
    if not row:
        return {
            "revision": 0,
            "business_id": business,
            "location_id": location,
            "facts": [],
            "brief": None,
        }
    version = session.get(ContextVersion, f"{row.id}:{row.revision}")
    result = json.loads(version.document)
    now = utcnow().replace(tzinfo=UTC)
    for fact in result["facts"]:
        fact["current_status"] = (
            "withdrawn"
            if fact["status"] == "withdrawn"
            else "not_effective"
            if datetime.fromisoformat(fact["effective_at"]) > now
            else "expired"
            if not future(fact["valid_until"], now)
            else "confirmed"
        )
    return result


def reference_fact(session, business, ref, now, location=None):
    version = session.get(ContextVersion, ref.context_version_id)
    require(version is not None, "fact_reference_not_found", 404)
    context = session.scalar(
        select(Context).where(Context.id == version.context_id).with_for_update()
    )
    require(
        context.business_id == business and context.location_id == location,
        "fact_scope_mismatch",
        404,
    )
    snapshot = json.loads(version.document)
    require(snapshot["basis"] == "owner_marketing_assertion", "legacy_fact_requires_confirmation")
    old = next((f for f in snapshot["facts"] if f["id"] == ref.fact_id), None)
    current = read_context(session, business, location)
    fact = next((f for f in current["facts"] if f["id"] == ref.fact_id), None)
    require(old is not None and fact is not None, "fact_removed")
    require(old["revision"] == ref.fact_revision == fact["revision"], "fact_changed")
    require(fact["current_status"] == "confirmed", "fact_" + fact["current_status"])
    return old


def validate_pack_context(session, business, payload, now):
    location = str(payload.location_id) if payload.location_id else None
    facts = {f.id: f for f in payload.facts}
    for ref in payload.fact_refs:
        source = reference_fact(session, business, ref, now, location)
        fact = facts.get(ref.fact_id)
        require(
            fact is not None
            and fact.text == source["text"]
            and fact.source == source["source"]
            and fact.valid_until.isoformat()
            == datetime.fromisoformat(source["valid_until"]).isoformat(),
            "fact_snapshot_mismatch",
        )
    if payload.context_version_id:
        version = session.get(ContextVersion, payload.context_version_id)
        require(version is not None, "context_not_found", 404)
        context = session.get(Context, version.context_id)
        require(
            context.business_id == business and context.location_id == location,
            "context_scope_mismatch",
            404,
        )
        snapshot = json.loads(version.document)
        require(
            snapshot["basis"] == "owner_marketing_assertion", "legacy_context_requires_confirmation"
        )
        require(
            snapshot["brief"] == read_context(session, business, location)["brief"],
            "business_brief_changed",
        )
        require(payload.objective == snapshot["brief"]["objective"], "objective_mismatch")
        return snapshot["brief"]
    return None


def stale_reasons(session, business, doc, now):
    reasons = []
    for ref in doc["brief"].get("fact_refs", []):
        try:
            reference_fact(
                session, business, FactReference(**ref), now, doc["brief"].get("location_id")
            )
        except HTTPException as error:
            reasons.append({"fact_id": ref["fact_id"], "reason": error.detail})
    version_id = doc["brief"].get("context_version_id")
    if version_id:
        version = session.get(ContextVersion, version_id)
        if (
            not version
            or json.loads(version.document)["brief"]
            != read_context(session, business, doc["brief"].get("location_id"))["brief"]
        ):
            reasons.append({"reason": "business_brief_changed"})
    return reasons


def attach_dependencies(session, revision_id, payload):
    for ref in payload.fact_refs:
        session.add(
            FactDependency(
                revision_id=revision_id,
                fact_id=ref.fact_id,
                context_version_id=ref.context_version_id,
                fact_revision=ref.fact_revision,
            )
        )


def backfill_legacy(connection):
    """Idempotent provenance backfill. Never rewrite a pack, image, digest or approval."""
    from .social_production import Pack, Revision

    with Session(bind=connection) as session:
        for revision, business in session.execute(select(Revision, Pack.business_id).join(Pack)):
            doc = json.loads(revision.document)
            if doc["brief"].get("fact_refs"):
                continue
            identifier = "legacy:" + revision.id
            if session.get(ContextVersion, identifier):
                continue
            cid = scope_id(business, doc["brief"].get("location_id"))
            if not session.get(Context, cid):
                # A legacy assertion does not become a current reusable confirmation.
                session.add(
                    Context(
                        id=cid,
                        business_id=business,
                        location_id=doc["brief"].get("location_id"),
                        revision=0,
                    )
                )
                session.flush()
                session.add(
                    ContextVersion(
                        id=cid + ":0",
                        context_id=cid,
                        document=canonical(
                            {
                                "id": cid + ":0",
                                "revision": 0,
                                "business_id": business,
                                "location_id": doc["brief"].get("location_id"),
                                "basis": "owner_marketing_assertion",
                                "brief": None,
                                "facts": [],
                            }
                        ),
                    )
                )
                session.flush()
            facts = [
                {**f, "revision": 1, "status": "legacy_unconfirmed"} for f in doc["brief"]["facts"]
            ]
            session.add(
                ContextVersion(
                    id=identifier,
                    context_id=cid,
                    document=canonical(
                        {
                            "basis": "legacy_pack_assertion",
                            "pack_revision_id": revision.id,
                            "business_id": business,
                            "facts": facts,
                            "confirmed_by": doc.get("confirmed_by"),
                            "confirmed_at": doc.get("confirmed_at"),
                        }
                    ),
                )
            )
            session.flush()
            for fact in facts:
                session.add(
                    FactDependency(
                        revision_id=revision.id,
                        fact_id=fact["id"],
                        context_version_id=identifier,
                        fact_revision=1,
                    )
                )
        session.commit()


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social/context"

    def check_scope(business, location):
        if location:
            resolver = getattr(app.state, "social_location_belongs_to_business", None)
            require(resolver is not None, "canonical_location_validation_unavailable", 503)
            require(resolver(business, location), "location_not_in_business", 404)

    @app.get(root, dependencies=[Depends(read)])
    def get(business_id: str, location_id: UUID | None = None, session=Depends(get_session)):
        location = str(location_id) if location_id else None
        check_scope(business_id, location)
        return read_context(session, business_id, location)

    @app.put(root)
    def put(
        business_id: str,
        payload: ContextInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        return save_context(business_id, payload, principal, session)

    def save_context(business_id, payload, principal, session, onboarding=None):
        location = str(payload.location_id) if payload.location_id else None
        check_scope(business_id, location)
        cid = scope_id(business_id, location)
        row = session.get(Context, cid)
        now = utcnow().replace(tzinfo=UTC)
        old = read_context(session, business_id, location)
        require(old["revision"] == payload.expected_revision, "context_revision_conflict")
        prior = {f["id"]: f for f in old["facts"]}
        facts = []
        for item in payload.facts:
            value = item.model_dump(mode="json")
            before = prior.get(item.id)
            unchanged = before and all(before.get(k) == v for k, v in value.items())
            if item.status == "confirmed" and not unchanged:
                require(
                    item.effective_at <= now and item.valid_until > now, "fact_not_current", 422
                )
            facts.append(
                {
                    **value,
                    "revision": before["revision"]
                    if unchanged
                    else (before["revision"] + 1 if before else 1),
                    "text": statement(value),
                    "verifier": before["verifier"] if unchanged else principal.actor_id,
                    "verified_at": before["verified_at"] if unchanged else now.isoformat(),
                }
            )
        # Omitted IDs become tombstones; re-adding one must never reset its revision.
        present = {f["id"] for f in facts}
        for identifier, before in prior.items():
            if identifier not in present:
                facts.append(
                    {
                        k: v
                        for k, v in {
                            **before,
                            "status": "withdrawn",
                            "revision": before["revision"] + (before["status"] != "withdrawn"),
                            "verifier": principal.actor_id,
                            "verified_at": now.isoformat(),
                        }.items()
                        if k != "current_status"
                    }
                )
        if row:
            changed = session.execute(
                update(Context)
                .where(Context.id == cid, Context.revision == payload.expected_revision)
                .values(revision=Context.revision + 1)
            )
            require(changed.rowcount == 1, "context_revision_conflict")
            session.refresh(row)
        else:
            row = Context(id=cid, business_id=business_id, location_id=location, revision=1)
            session.add(row)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "context_revision_conflict") from None
        vid = f"{cid}:{row.revision}"
        snapshot = {
            "id": vid,
            "revision": row.revision,
            "business_id": business_id,
            "location_id": location,
            "basis": "owner_marketing_assertion",
            "publication_authority": "none_manual_review_required",
            "brief": payload.brief.model_dump(mode="json"),
            "facts": facts,
            "onboarding": onboarding
            if onboarding is not None
            else (
                old.get("onboarding")
                if old.get("brief")
                and all(
                    old["brief"].get(key) == getattr(payload.brief, key)
                    for key in (
                        "offering",
                        "objective",
                        "buying_destination",
                        "constraints",
                        "locale",
                    )
                )
                else None
            ),
            "verifier": principal.actor_id,
            "verified_at": now.isoformat(),
        }
        session.add(ContextVersion(id=vid, context_id=cid, document=canonical(snapshot)))
        session.commit()
        return read_context(session, business_id, location)

    @app.put(root + "/onboarding")
    def onboarding(
        business_id: str,
        payload: OnboardingInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        location = str(payload.location_id) if payload.location_id else None
        check_scope(business_id, location)
        old = read_context(session, business_id, location)
        fields = {**(old.get("brief") or {}), **payload.answers.brief_fields()}
        # Existing fact IDs/versions and unknowns survive; choices are not fact assertions.
        facts = [{key: fact.get(key) for key in Assertion.model_fields} for fact in old["facts"]]
        value = ContextInput(
            expected_revision=payload.expected_revision,
            location_id=location,
            brief=fields,
            facts=facts,
            confirmed=True,
        )
        return save_context(
            business_id, value, principal, session, payload.answers.model_dump(mode="json")
        )

    @app.get(root + "/history", dependencies=[Depends(read)])
    def history(business_id: str, location_id: UUID | None = None, session=Depends(get_session)):
        location = str(location_id) if location_id else None
        check_scope(business_id, location)
        return {
            "versions": [
                json.loads(v.document)
                for v in session.scalars(
                    select(ContextVersion)
                    .where(ContextVersion.context_id == scope_id(business_id, location))
                    .order_by(ContextVersion.id)
                )
            ]
        }
