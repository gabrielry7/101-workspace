"""Configuration lifecycle only. Publication does not issue or activate rewards."""

import hashlib
import json
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from .errors import ConcurrencyConflictError, NotFoundError, ValidationError
from .loyalty_models import (
    LoyaltyConfigurationAudit,
    LoyaltyExperiment,
    LoyaltyExperimentVariant,
    LoyaltyExperimentVersion,
    LoyaltyStrategy,
    LoyaltyStrategyVersion,
)
from .loyalty_schemas import ExperimentDocument, StrategyDocument
from .models import Customer, Menu, MenuCategory, MenuItem, RestaurantCommerceProfile

KINDS = {
    "programs": (LoyaltyStrategy, LoyaltyStrategyVersion, StrategyDocument, "strategy_id"),
    "experiments": (
        LoyaltyExperiment,
        LoyaltyExperimentVersion,
        ExperimentDocument,
        "experiment_id",
    ),
}


def canonical(document):
    return json.dumps(
        document.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def digest(document):
    return hashlib.sha256(document.encode()).hexdigest()


class LoyaltyConfigurationService:
    def __init__(self, session, actor_id):
        self.session = session
        self.actor_id = actor_id

    def _commit(self):
        try:
            self.session.commit()
        except (StaleDataError, IntegrityError) as exc:
            self.session.rollback()
            raise ConcurrencyConflictError("Configuration changed; reload before retrying") from exc

    def _flush(self):
        try:
            self.session.flush()
        except (StaleDataError, IntegrityError) as exc:
            self.session.rollback()
            raise ConcurrencyConflictError("Configuration changed; retry the same request") from exc

    def _audit(self, row, action):
        self.session.add(
            LoyaltyConfigurationAudit(
                business_id=row.business_id,
                actor_id=self.actor_id,
                resource_id=row.id,
                action=action,
                revision=row.revision,
                digest=digest(row.draft_json),
            )
        )

    def _get(self, kind, business_id, resource_id, *, lock=False):
        model = KINDS[kind][0]
        query = select(model).where(model.id == resource_id, model.business_id == business_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise NotFoundError("Loyalty configuration not found")
        return row

    def describe(self, kind, row):
        _, version_model, _, parent = KINDS[kind]
        versions = self.session.scalars(
            select(version_model)
            .where(getattr(version_model, parent) == row.id)
            .order_by(version_model.revision)
        ).all()
        return {
            "id": row.id,
            "business_id": row.business_id,
            "state": row.state,
            "revision": row.revision,
            "document": json.loads(row.draft_json),
            "digest": digest(row.draft_json),
            "execution_enabled": False,
            "versions": [
                {
                    "id": v.id,
                    "revision": v.revision,
                    "digest": v.digest,
                    "document": json.loads(v.document),
                    "actor_id": v.actor_id,
                    "published_at": v.published_at,
                }
                for v in versions
            ],
        }

    def get(self, kind, business_id, resource_id):
        return self.describe(kind, self._get(kind, business_id, resource_id))

    def list(self, kind, business_id):
        model = KINDS[kind][0]
        return [
            self.describe(kind, row)
            for row in self.session.scalars(
                select(model)
                .where(model.business_id == business_id)
                .order_by(model.created_at, model.id)
            )
        ]

    def _validate_references(self, kind, business_id, document):
        eligibility = document.eligibility
        customers = set(eligibility.customer_ids)
        if (
            customers
            and set(
                self.session.scalars(
                    select(Customer.id).where(
                        Customer.business_id == business_id, Customer.id.in_(customers)
                    )
                )
            )
            != customers
        ):
            raise ValidationError("Eligibility customers must belong to this business")
        products = set(eligibility.included_product_ids + eligibility.excluded_product_ids)
        reward = getattr(document, "reward", None)
        if reward is not None and reward.type == "product":
            products.add(reward.product_id)
        if (
            products
            and set(
                self.session.scalars(
                    select(MenuItem.id)
                    .join(MenuCategory)
                    .join(Menu)
                    .where(Menu.business_id == business_id, MenuItem.id.in_(products))
                )
            )
            != products
        ):
            raise ValidationError("Eligibility products must belong to this business")
        if kind != "experiments":
            return
        for variant in document.variants:
            if variant.strategy_version_id is None:
                continue
            version = self.session.scalar(
                select(LoyaltyStrategyVersion).where(
                    LoyaltyStrategyVersion.id == variant.strategy_version_id,
                    LoyaltyStrategyVersion.business_id == business_id,
                )
            )
            if version is None:
                raise ValidationError("Variant requires a published version in this business")
            if json.loads(version.document)["currency"] != document.currency:
                raise ValidationError("Experiment and program currencies must match")

    def create(self, kind, business_id, request):
        if self.session.get(RestaurantCommerceProfile, business_id) is None:
            raise NotFoundError("Business not found")
        model = KINDS[kind][0]
        document = canonical(request.document)
        existing = self.session.scalar(
            select(model).where(
                model.business_id == business_id, model.request_key == request.request_key
            )
        )
        if existing:
            if existing.creation_digest != digest(document):
                raise ConcurrencyConflictError("Request key reused with different configuration")
            return self.describe(kind, existing)
        self._validate_references(kind, business_id, request.document)
        row = model(
            business_id=business_id,
            request_key=request.request_key,
            creation_digest=digest(document),
            draft_json=document,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConcurrencyConflictError("Concurrent creation; retry with the same key") from exc
        self._audit(row, kind + ".created")
        self._commit()
        return self.describe(kind, row)

    def edit(self, kind, business_id, resource_id, request):
        row = self._get(kind, business_id, resource_id, lock=True)
        if row.revision != request.expected_revision:
            raise ConcurrencyConflictError("Draft revision changed")
        if row.state == "archived":
            raise ValidationError("Archived configuration cannot be edited")
        self._validate_references(kind, business_id, request.document)
        row.draft_json = canonical(request.document)
        if row.state != "paused":
            row.state = "draft"
        row.revision += 1
        self._audit(row, kind + ".edited")
        self._commit()
        return self.describe(kind, row)

    def publish(self, kind, business_id, resource_id, request):
        row = self._get(kind, business_id, resource_id, lock=True)
        _, version_model, schema, parent = KINDS[kind]
        # A retry of a successful publish returns that exact retained version.
        existing = self.session.scalar(
            select(version_model).where(
                getattr(version_model, parent) == row.id,
                version_model.revision == request.expected_revision,
            )
        )
        if existing:
            if existing.digest != request.digest:
                raise ConcurrencyConflictError("Publication digest mismatch")
            return {
                "version_id": existing.id,
                "digest": existing.digest,
                "execution_enabled": False,
            }
        if row.revision != request.expected_revision or digest(row.draft_json) != request.digest:
            raise ConcurrencyConflictError("Review is stale; reload the exact draft")
        if row.state not in {"draft", "paused"}:
            raise ValidationError("Only a draft or paused proposal can be published")
        document = schema.model_validate_json(row.draft_json)
        self._validate_references(kind, business_id, document)
        fields = {
            parent: row.id,
            "business_id": business_id,
            "revision": row.revision,
            "document": row.draft_json,
            "digest": request.digest,
            "actor_id": self.actor_id,
        }
        if kind == "experiments":
            fields["random_salt"] = secrets.token_hex(32)
        version = version_model(**fields)
        self.session.add(version)
        self._flush()
        if kind == "experiments":
            for variant in document.variants:
                self.session.add(
                    LoyaltyExperimentVariant(
                        experiment_version_id=version.id,
                        business_id=business_id,
                        **variant.model_dump(),
                    )
                )
        if row.state != "paused":
            row.state = "published"
        row.revision += 1
        self._audit(row, kind + ".published")
        self._commit()
        return {"version_id": version.id, "digest": version.digest, "execution_enabled": False}

    def transition(self, kind, business_id, resource_id, request):
        row = self._get(kind, business_id, resource_id, lock=True)
        if row.revision != request.expected_revision:
            raise ConcurrencyConflictError("Configuration revision changed")
        if request.state == "active":
            raise ValidationError(
                "Activation unavailable: reward execution and measurement gates are not implemented"
            )
        if row.state == "archived":
            raise ValidationError("Archived configuration is terminal")
        if request.state == "paused":
            _, version_model, _, parent = KINDS[kind]
            if self.session.scalar(select(version_model.id).where(
                getattr(version_model, parent) == row.id
            ).limit(1)) is None:
                raise ValidationError("Only a configuration with published history can be paused")
        row.state = request.state
        row.revision += 1
        self._audit(row, kind + "." + request.state)
        self._commit()
        return self.describe(kind, row)
