"""Controlled pre-purchase enrollment. All methods share the caller's transaction.

Customer identity must come from a trusted adapter, never request JSON or phone
matching. No HTTP enrollment or automatic experiment activation is exposed here.
"""

import hashlib
import json
from datetime import timedelta

from sqlalchemy import func, or_, select

from .errors import IdempotencyConflictError, NotFoundError, ValidationError
from .loyalty_assignment_migrations import installed
from .loyalty_assignment_models import (
    LoyaltyAssignment as Assignment,
)
from .loyalty_assignment_models import (
    LoyaltyAssignmentExposure as Exposure,
)
from .loyalty_assignment_models import (
    LoyaltyAssignmentOrder as OrderBinding,
)
from .loyalty_assignment_models import (
    LoyaltyAssignmentOverlap as Overlap,
)
from .loyalty_assignment_models import (
    LoyaltyEnrollmentDecision as Decision,
)
from .loyalty_assignment_models import (
    LoyaltyExperimentRun as Run,
)
from .loyalty_config import digest
from .loyalty_models import (
    LoyaltyExperiment,
    LoyaltyExperimentVariant,
    LoyaltyExperimentVersion,
    LoyaltyStrategyVersion,
)
from .loyalty_schemas import ExperimentDocument, StrategyDocument
from .loyalty_wallet import aware
from .models import Customer, RestaurantCommerceProfile, new_id, utcnow
from .reliability import acquire_idempotency, complete_idempotency, request_fingerprint


def bounded(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValidationError(
            f"{name} must be nonempty text of at most {maximum} characters without NUL"
        )
    return value


def assignment_bucket(salt, experiment_version_id, business_id, customer_id):
    value = json.dumps(
        [
            "101-loyalty-assignment",
            "sha256-v1",
            salt,
            experiment_version_id,
            business_id,
            customer_id,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest(), "big") % 10000


def choose_variant(document, bucket):
    end = 0
    for variant in document.variants:  # The published document order is authoritative.
        end += variant.allocation_bps
        if bucket < end:
            return variant
    raise ValidationError("Invalid frozen allocation")


def frozen_version(session, business_id, version_id):
    version = session.get(LoyaltyExperimentVersion, version_id)
    if not version or version.business_id != business_id:
        raise NotFoundError("Published experiment version not found")
    if digest(version.document) != version.digest:
        raise ValidationError("Experiment configuration digest mismatch")
    return version, ExperimentDocument.model_validate_json(version.document)


def require_executable_variants(session, version, document):
    rows = session.scalars(
        select(LoyaltyExperimentVariant).where(
            LoyaltyExperimentVariant.experiment_version_id == version.id
        )
    ).all()
    actual = {row.name: row for row in rows}
    if len(actual) != len(document.variants):
        raise ValidationError("Frozen variant rows are incomplete")
    for variant in document.variants:
        row = actual.get(variant.name)
        if (
            row is None
            or row.business_id != version.business_id
            or row.allocation_bps != variant.allocation_bps
            or row.strategy_version_id != variant.strategy_version_id
        ):
            raise ValidationError("Variant differs from frozen experiment")
        if variant.strategy_version_id is None:
            continue
        strategy = session.get(LoyaltyStrategyVersion, variant.strategy_version_id)
        if (
            not strategy
            or strategy.business_id != version.business_id
            or digest(strategy.document) != strategy.digest
        ):
            raise ValidationError("Variant program scope or digest mismatch")
        rules = StrategyDocument.model_validate_json(strategy.document)
        if (
            rules.currency != document.currency
            or rules.reward is not None
            and rules.reward.type != "fixed_value"
            or rules.earning is not None
            and rules.estimated_cost_per_point_minor <= 0
        ):
            raise ValidationError(
                "Every variant must support controlled points/fixed-value execution "
                "with explicit costs"
            )
    return actual


def assignment_out(session, row):
    variant = session.get(LoyaltyExperimentVariant, row.variant_id)
    return {
        "assignment_id": row.id,
        "business_id": row.business_id,
        "customer_id": row.customer_id,
        "experiment_id": row.experiment_id,
        "experiment_version_id": row.experiment_version_id,
        "variant_id": row.variant_id,
        "variant_name": variant.name,
        "strategy_version_id": row.strategy_version_id,
        "control": row.strategy_version_id is None,
        "algorithm": row.algorithm,
        "bucket": row.bucket,
        "assigned_at": aware(row.assigned_at).isoformat(),
        "evaluation_ends_at": aware(row.evaluation_ends_at).isoformat(),
        "exclusion_ends_at": aware(row.exclusion_ends_at).isoformat(),
        "eligibility_decision_id": row.eligibility_decision_id,
    }


class LoyaltyAssignmentService:
    def __init__(self, session, actor_id, *, enabled=False, mode=None):
        self.session = session
        self.actor_id = bounded(actor_id, "actor_id", 128)
        self.enabled, self.mode = enabled, mode

    def _gate(self):
        if self.enabled is not True or self.mode != "synthetic":
            raise ValidationError("Assignment requires explicit synthetic enablement")
        if not installed(self.session):
            raise ValidationError("Offline loyalty assignment upgrade required")

    def _claim(self, kind, business_id, request_key, payload):
        bounded(business_id, "business_id", 64)
        bounded(request_key, "request_key", 100)
        return acquire_idempotency(
            self.session,
            scope=f"loyalty.{kind}:{business_id}",
            key=request_key,
            fingerprint=request_fingerprint(payload),
        )

    def _result(self, decision_id):
        decision = self.session.get(Decision, decision_id)
        if decision is None:
            raise ValidationError("Enrollment history is missing")
        row = self.session.scalar(
            select(Assignment).where(Assignment.eligibility_decision_id == decision.id)
        )
        if decision.eligible and row is None:
            raise ValidationError("Eligible decision has no retained assignment")
        return {
            "decision_id": decision.id,
            "eligible": decision.eligible,
            "reasons": json.loads(decision.reasons_json),
            "assessed_at": aware(decision.assessed_at).isoformat(),
            "assignment": assignment_out(self.session, row) if row else None,
        }

    def enroll(
        self,
        business_id,
        version_id,
        *,
        verified_customer_id=None,
        identity_evidence_ref=None,
        request_key,
    ):
        self._gate()
        bounded(version_id, "version_id", 36)
        if verified_customer_id is not None:
            bounded(verified_customer_id, "verified_customer_id", 36)
            bounded(identity_evidence_ref, "identity_evidence_ref", 200)
        claim = self._claim(
            "enroll",
            business_id,
            request_key,
            {
                "version_id": version_id,
                "verified_customer_id": verified_customer_id,
                "identity_evidence_ref": identity_evidence_ref,
            },
        )
        if not claim.acquired:
            return self._result(claim.entity_id)
        version, document = frozen_version(self.session, business_id, version_id)
        now = utcnow()
        customer = None
        if verified_customer_id is not None:
            customer = self.session.scalar(
                select(Customer)
                .where(Customer.id == verified_customer_id, Customer.business_id == business_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if customer is None:
                raise ValidationError("Verified customer does not belong to this business")
            existing = self.session.scalar(
                select(Assignment).where(
                    Assignment.business_id == business_id,
                    Assignment.experiment_id == version.experiment_id,
                    Assignment.customer_id == customer.id,
                )
            )
            if existing is not None:
                # Replay original eligibility/assignment even if caller names a newer
                # version, enrollment ended, or either parent is paused/archived.
                complete_idempotency(
                    self.session, claim.record_id, entity_id=existing.eligibility_decision_id
                )
                self.session.flush()
                return self._result(existing.eligibility_decision_id)
        experiment = self.session.scalar(
            select(LoyaltyExperiment)
            .where(LoyaltyExperiment.id == version.experiment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        run = self.session.get(Run, version.experiment_id)
        if run and run.experiment_version_id != version.id:
            raise IdempotencyConflictError(
                "Experiment enrollment is frozen to its original version; create a new experiment"
            )
        now = utcnow()  # Reassess after serialized customer/experiment lock waits.
        reasons = []
        if customer is None:
            reasons.append("verified_identity_required")
        if experiment.state in {"paused", "archived"} or (
            run is None and experiment.state != "published"
        ):
            reasons.append("experiment_not_enrolling")
        if not aware(document.enrollment_start) <= now < aware(document.enrollment_end):
            reasons.append("outside_enrollment_window")
        policy = document.eligibility
        if (
            policy.minimum_purchase_minor
            or policy.included_product_ids
            or policy.excluded_product_ids
        ):
            reasons.append("unsupported_pre_purchase_eligibility")
        if customer and policy.customer_ids and customer.id not in policy.customer_ids:
            reasons.append("customer_not_included")
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if profile.currency != document.currency:
            reasons.append("currency_mismatch")
        active = []
        if customer:
            active = self.session.scalars(
                select(Assignment)
                .where(
                    Assignment.business_id == business_id,
                    Assignment.customer_id == customer.id,
                    Assignment.exclusion_group == document.exclusion_group,
                    Assignment.exclusion_ends_at > now,
                )
                .order_by(Assignment.id)
            ).all()
            if any(not document.allow_overlap or not other.allow_overlap for other in active):
                reasons.append("overlap_protected")
        try:
            evaluation_end = now + timedelta(days=document.observation_days)
            exclusion_end = evaluation_end + timedelta(days=document.carryover_days)
        except OverflowError as exc:
            raise ValidationError("Observation window exceeds supported dates") from exc
        variants = (
            require_executable_variants(self.session, version, document) if not reasons else {}
        )
        decision = Decision(
            id=new_id(),
            business_id=business_id,
            experiment_version_id=version.id,
            customer_id=customer.id if customer else None,
            eligible=not reasons,
            reasons_json=json.dumps(reasons),
            evidence_json=json.dumps(
                {
                    "identity_source": "trusted_service_adapter" if customer else None,
                    "identity_evidence_ref": identity_evidence_ref,
                    "configuration_digest": version.digest,
                    "overlapping_assignment_ids": [row.id for row in active],
                },
                sort_keys=True,
            ),
            actor_id=self.actor_id,
            assessed_at=now,
        )
        self.session.add(decision)
        self.session.flush()
        if not reasons:
            if run is None:
                self.session.add(
                    Run(
                        experiment_id=version.experiment_id,
                        business_id=business_id,
                        experiment_version_id=version.id,
                        actor_id=self.actor_id,
                        opened_at=now,
                    )
                )
                self.session.flush()
            bucket = assignment_bucket(version.random_salt, version.id, business_id, customer.id)
            variant = variants[choose_variant(document, bucket).name]
            row = Assignment(
                id=new_id(),
                business_id=business_id,
                experiment_id=version.experiment_id,
                experiment_version_id=version.id,
                customer_id=customer.id,
                eligibility_decision_id=decision.id,
                variant_id=variant.id,
                strategy_version_id=variant.strategy_version_id,
                algorithm="sha256-v1",
                bucket=bucket,
                exclusion_group=document.exclusion_group,
                allow_overlap=document.allow_overlap,
                assigned_at=now,
                evaluation_ends_at=evaluation_end,
                exclusion_ends_at=exclusion_end,
            )
            self.session.add(row)
            self.session.flush()
            for other in active:
                first, second = sorted((row.id, other.id))
                self.session.add(
                    Overlap(
                        first_assignment_id=first,
                        second_assignment_id=second,
                        evidence_json=json.dumps(
                            {
                                "new_version_id": version.id,
                                "new_overlap_reason": document.overlap_reason,
                                "existing_version_id": other.experiment_version_id,
                                "actor_id": self.actor_id,
                            },
                            sort_keys=True,
                        ),
                    )
                )
        complete_idempotency(self.session, claim.record_id, entity_id=decision.id)
        self.session.flush()
        return self._result(decision.id)

    def record_exposure(
        self,
        business_id,
        assignment_id,
        *,
        verified_customer_id,
        request_key,
        kind,
        surface,
        source_ref,
    ):
        self._gate()
        bounded(verified_customer_id, "verified_customer_id", 36)
        bounded(assignment_id, "assignment_id", 36)
        bounded(surface, "surface", 100)
        bounded(source_ref, "source_ref", 200)
        if kind not in {"offer_surface_rendered", "control_surface_rendered"}:
            raise ValidationError("Unsupported exposure kind")
        claim = self._claim(
            "exposure",
            business_id,
            request_key,
            {
                "assignment_id": assignment_id,
                "customer_id": verified_customer_id,
                "kind": kind,
                "surface": surface,
                "source_ref": source_ref,
            },
        )
        if not claim.acquired:
            row = self.session.get(Exposure, claim.entity_id)
            if row is None:
                raise ValidationError("Exposure history is missing")
            return {
                "exposure_id": row.id,
                "assignment_id": row.assignment_id,
                "warnings": json.loads(row.warnings_json),
            }
        customer = self.session.scalar(
            select(Customer)
            .where(Customer.id == verified_customer_id, Customer.business_id == business_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = self.session.get(Assignment, assignment_id)
        if (
            customer is None
            or row is None
            or row.business_id != business_id
            or row.customer_id != customer.id
        ):
            raise ValidationError("Exposure assignment does not match verified identity")
        expected = (
            "control_surface_rendered"
            if row.strategy_version_id is None
            else "offer_surface_rendered"
        )
        if kind != expected:
            raise ValidationError("Exposure kind does not match assigned variant")
        existing = self.session.scalar(
            select(Exposure).where(
                Exposure.assignment_id == row.id,
                Exposure.kind == kind,
                Exposure.surface == surface,
                Exposure.source_ref == source_ref,
            )
        )
        if existing:
            complete_idempotency(self.session, claim.record_id, entity_id=existing.id)
            self.session.flush()
            return {
                "exposure_id": existing.id,
                "assignment_id": row.id,
                "warnings": json.loads(existing.warnings_json),
            }
        warnings = []
        now = utcnow()
        if not aware(row.assigned_at) <= now < aware(row.evaluation_ends_at):
            warnings.append("outside_offer_window")
        experiment = self.session.get(LoyaltyExperiment, row.experiment_id)
        if experiment.state in {"paused", "archived"}:
            warnings.append("experiment_paused_or_archived")
        exposure = Exposure(
            id=new_id(),
            business_id=business_id,
            customer_id=customer.id,
            assignment_id=row.id,
            kind=kind,
            surface=surface,
            source_ref=source_ref,
            warnings_json=json.dumps(warnings),
            actor_id=self.actor_id,
            observed_at=now,
        )
        self.session.add(exposure)
        complete_idempotency(self.session, claim.record_id, entity_id=exposure.id)
        self.session.flush()
        return {"exposure_id": exposure.id, "assignment_id": row.id, "warnings": warnings}


def assignment_summary(session, business_id, experiment_id):
    """Enrollment diagnostics only. No outcome inference, lift or winner claims."""
    if not installed(session):
        raise ValidationError("Offline loyalty assignment upgrade required")
    experiment = session.get(LoyaltyExperiment, experiment_id)
    if experiment is None or experiment.business_id != business_id:
        raise NotFoundError("Experiment not found")
    scope = (Assignment.business_id == business_id, Assignment.experiment_id == experiment_id)
    counts = dict(
        session.execute(
            select(Assignment.variant_id, func.count())
            .where(*scope)
            .group_by(Assignment.variant_id)
        ).all()
    )
    total = sum(counts.values())
    run = session.get(Run, experiment_id)
    variants = []
    if run:
        version, doc = frozen_version(session, business_id, run.experiment_version_id)
        by_name = {
            v.name: v
            for v in session.scalars(
                select(LoyaltyExperimentVariant).where(
                    LoyaltyExperimentVariant.experiment_version_id == version.id
                )
            )
        }
        for definition in doc.variants:
            variant = by_name[definition.name]
            count = counts.get(variant.id, 0)
            variants.append(
                {
                    "name": definition.name,
                    "control": definition.strategy_version_id is None,
                    "allocation_bps": definition.allocation_bps,
                    "assigned_customers": count,
                    "expected_customers": {
                        "numerator": total * definition.allocation_bps,
                        "denominator": 10000,
                    },
                }
            )
    ids = select(Assignment.id).where(*scope)
    exposures = session.scalar(
        select(func.count()).select_from(Exposure).where(Exposure.assignment_id.in_(ids))
    )
    overlaps = session.scalar(
        select(func.count())
        .select_from(Overlap)
        .where(or_(Overlap.first_assignment_id.in_(ids), Overlap.second_assignment_id.in_(ids)))
    )
    orders = session.scalar(
        select(func.count()).select_from(OrderBinding).where(OrderBinding.assignment_id.in_(ids))
    )
    from .loyalty_execution_models import LoyaltyExecutionEvent
    from .models import LoyaltyLedgerEntry

    activity = session.execute(
        select(LoyaltyLedgerEntry.reason, func.count(), func.sum(LoyaltyLedgerEntry.delta_points))
        .join(LoyaltyExecutionEvent, LoyaltyExecutionEvent.ledger_id == LoyaltyLedgerEntry.id)
        .join(OrderBinding, OrderBinding.order_id == LoyaltyExecutionEvent.order_id)
        .where(OrderBinding.assignment_id.in_(ids))
        .group_by(LoyaltyLedgerEntry.reason)
        .order_by(LoyaltyLedgerEntry.reason)
    ).all()
    return {
        "experiment_id": experiment_id,
        "experiment_version_id": run.experiment_version_id if run else None,
        "assigned_customers": total,
        "variants": variants,
        "exposure_receipts": exposures,
        "bound_orders": orders,
        "reward_ledger_activity": [
            {"reason": reason, "entries": count, "net_points": points}
            for reason, count, points in activity
        ],
        "allowed_overlap_pairs": overlaps,
        "warnings": (["experiment_contamination"] if overlaps else []),
        "enrollment_is_not_exposure": True,
        "profit_analysis_available": False,
        "allocation_counts_are_descriptive": True,
    }
