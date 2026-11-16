"""Manual receipts -> sourced observations -> bounded, reproducible next decisions."""

# ruff: noqa: B008
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from .social_production import Pack, Revision, canonical, owned, require
from .social_result_contracts import (
    METRICS,
    Effort,
    NextDecision,
    Observation,
    Plan,
    Receipt,
    ReceiptCorrection,
    utc,
)
from .social_result_models import Publication, PublicationVersion, ResultEvent
from .social_reviews import (
    current_time,
    digest,
    locked_current,
    scope,
    technical,
)
from .social_reviews import (
    events as review_events,
)

ACTIONS = {
    "repeat": "Repetir con una nueva revisión",
    "modify": "Cambiar un elemento",
    "stop": "Detener esta idea",
    "collect_evidence": "Recoger la información que falta",
    "inconclusive": "Mantener el resultado inconcluso",
}
MAX_EVENTS = 200


def as_time(value):
    return datetime.fromisoformat(value).astimezone(UTC)


def event_info(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "actor_id": row.actor_id,
        "at": row.created_at,
        "sequence": row.sequence,
        "supersedes_id": row.supersedes_id,
        "revision_id": row.revision_id,
        **json.loads(row.document),
    }


def active(rows):
    replaced = {r.supersedes_id for r in rows if r.supersedes_id}
    return [r for r in rows if r.id not in replaced]


def pub_document(session, pub):
    return json.loads(session.get(PublicationVersion, f"{pub.id}:{pub.revision}").document)


def lock_publication(session, business, identifier):
    owned(session, Publication, identifier, business)
    session.execute(
        update(Publication)
        .where(Publication.id == identifier, Publication.business_id == business)
        .values(event_sequence=Publication.event_sequence)
    )
    row = owned(session, Publication, identifier, business)
    session.refresh(row)
    return row


def publication_info(session, pub):
    doc = pub_document(session, pub)
    return {
        "id": pub.id,
        "pack_id": pub.pack_id,
        "revision_id": pub.revision_id,
        "revision": pub.revision,
        **doc,
    }


def publication_rows(session, business, pack_id):
    return list(
        session.scalars(
            select(Publication)
            .where(Publication.business_id == business, Publication.pack_id == pack_id)
            .order_by(Publication.id)
            .limit(31)
        )
    )


def current_plan(session, pack_id, revision_id):
    rows = list(
        session.scalars(
            select(ResultEvent).where(
                ResultEvent.pack_id == pack_id,
                ResultEvent.revision_id == revision_id,
                ResultEvent.kind == "plan",
            )
        )
    )
    heads = active(rows)
    require(len(heads) <= 1, "plan_history_conflict")
    return heads[0] if heads else None


def append_event(
    session, business, pack_id, revision_id, pub, kind, payload, principal, extra=None
):
    request = payload.model_dump(mode="json")
    eid = digest([business, principal.actor_id, kind, request["request_id"]])[:32]
    old = session.get(ResultEvent, eid)
    if old:
        value = json.loads(old.document)
        require(
            old.business_id == business
            and old.pack_id == pack_id
            and old.publication_id == (pub.id if pub else None)
            and value["request"] == request,
            "result_idempotency_conflict",
        )
        return old
    query = select(ResultEvent).where(
        ResultEvent.pack_id == pack_id, ResultEvent.publication_id == (pub.id if pub else None)
    )
    rows = list(session.scalars(query))
    require(len(rows) < MAX_EVENTS, "result_history_limit", 429)
    supersedes = getattr(payload, "supersedes_id", None)
    if supersedes:
        previous = next((e for e in active(rows) if e.id == supersedes), None)
        require(previous is not None and previous.kind == kind, "result_correction_conflict")
        if kind == "metric":
            require(
                json.loads(previous.document)["request"]["metric"] == request["metric"],
                "metric_correction_mismatch",
            )
    if kind == "plan":
        head = current_plan(session, pack_id, revision_id)
        require((head.id if head else None) == supersedes, "plan_correction_conflict")
    if pub:
        pub.event_sequence += 1
        sequence = pub.event_sequence
    else:
        sequence = max((r.sequence for r in rows), default=0) + 1
    value = {
        "request": request,
        "publication_version": f"{pub.id}:{pub.revision}" if pub else None,
        **(extra or {}),
    }
    row = ResultEvent(
        id=eid,
        business_id=business,
        pack_id=pack_id,
        revision_id=revision_id,
        publication_id=pub.id if pub else None,
        kind=kind,
        supersedes_id=supersedes,
        sequence=sequence,
        actor_id=principal.actor_id,
        document=canonical(value),
        created_at=current_time().timestamp(),
    )
    session.add(row)
    session.flush()
    return row


def operation_summary(session, pub):
    from .social_job_models import ProductionJob
    from .social_jobs import info

    # Count a shared generation job once, even when several revisions reused its text.
    revision_count = session.scalar(
        select(func.count()).select_from(Revision).where(Revision.pack_id == pub.pack_id)
    )
    documents = list(
        session.scalars(
            select(Revision.document)
            .where(Revision.pack_id == pub.pack_id)
            .order_by(Revision.id)
            .limit(1001)
        )
    )
    generation_ids = set()
    from .social_proposal_models import Proposal

    for document in documents[:1000]:
        doc = json.loads(document)
        if doc.get("speech_snapshot", {}).get("id"):
            generation_ids.add(doc["speech_snapshot"]["id"])
        if doc.get("proposal_snapshot"):
            proposal = session.get(Proposal, doc["proposal_snapshot"]["proposal_id"])
            if proposal:
                generation_ids.add(proposal.job_id)
    jobs = list(
        session.scalars(
            select(ProductionJob)
            .where(
                ProductionJob.business_id == pub.business_id,
                (ProductionJob.pack_id == pub.pack_id) | (ProductionJob.id.in_(generation_ids)),
            )
            .order_by(ProductionJob.created_at)
            .limit(101)
        )
    )
    coverage = (
        "pack_all_revisions"
        if len(jobs) <= 100 and len(documents) <= 1000
        else "first_100_jobs_only"
    )
    items = [info(session, j) for j in jobs[:100]]
    amounts = [j["cost"]["provider_microusd"] for j in items]
    cost = (
        sum(amounts)
        if amounts
        and all(v is not None for v in amounts)
        and len(jobs) <= 100
        and len(documents) <= 1000
        else None
    )
    effort = [e for j in items for e in j["effort"]]
    return {
        "coverage": coverage,
        "revision_count": revision_count,
        "job_count": len(items),
        "attempt_count": sum(j["attempt_count"] for j in items),
        "failed_attempts": sum(
            a["state"] in {"failed", "interrupted", "needs_input", "cancelled", "uncertain"}
            for j in items
            for a in j["attempts"]
        ),
        "provider_microusd": cost,
        "provider_cost_reason": None if cost is not None else "no_complete_job_cost_records",
        "compute_microusd": None,
        "storage_microusd": None,
        "total_microusd": None,
        "recorded_job_effort_seconds": {
            role: sum(e["seconds"] for e in effort if e["role"] == role)
            if any(e["role"] == role for e in effort)
            else None
            for role in ["owner", "reviewer"]
        },
        "elapsed_render_ms": sum(
            a["usage"].get("elapsed_ms") or 0 for j in items for a in j["attempts"]
        )
        if items
        else None,
    }


def report(session, business, pub_id):
    pub = owned(session, Publication, pub_id, business)
    p = publication_info(session, pub)
    revision = session.get(Revision, pub.revision_id)
    doc = json.loads(revision.document)
    rows = list(
        session.scalars(
            select(ResultEvent)
            .where(ResultEvent.publication_id == pub.id)
            .order_by(ResultEvent.sequence)
        )
    )
    heads = active(rows)
    observations = []
    for row in heads:
        if row.kind != "metric":
            continue
        value = event_info(row)
        value["stale"] = value["publication_version"] != f"{pub.id}:{pub.revision}"
        observations.append(value)
    plan = current_plan(session, pub.pack_id, pub.revision_id)
    planned = event_info(plan) if plan else None
    if planned:
        published = as_time(p["published_at_utc"])
        recorded = as_time(planned["recorded_at"])
        upper = (
            published + timedelta(minutes=1)
            if p["timestamp_precision"] == "minute"
            else published + timedelta(seconds=1)
        )
        planned["timing"] = (
            "prospective"
            if recorded < published
            else "retrospective"
            if recorded >= upper
            else "uncertain_within_timestamp_precision"
        )
    primary_key = (
        planned["request"]["primary_metric"]
        if planned
        else {"owner_effort": "owner_effort_seconds"}.get(
            doc["brief"]["primary_measure"], doc["brief"]["primary_measure"]
        )
    )
    candidates = [
        o
        for o in observations
        if o["request"]["metric"] == primary_key
        and not o["stale"]
        and not o["request"]["test_data"]
    ]
    primary = {
        "metric": primary_key,
        "value": None,
        "availability": "not_yet_collected",
        "reason": "no_current_observation",
        "event_id": None,
    }
    definitions = {
        (o["request"]["definition"], o["request"]["window_kind"], o["request"].get("currency"))
        for o in candidates
    }
    if len(definitions) > 1:
        primary.update(availability="unavailable", reason="incompatible_definitions_or_windows")
    elif candidates:
        end = max(as_time(o["request"]["window_end"]) for o in candidates)
        latest = [o for o in candidates if as_time(o["request"]["window_end"]) == end]
        if len(latest) > 1:
            primary.update(
                availability="unavailable", reason="multiple_reports_need_reconciliation"
            )
        else:
            o = latest[0]
            v = o["request"]
            primary.update(
                value=v["value"],
                availability=v["availability"],
                reason=v["reason"] or None,
                event_id=o["id"],
                definition=v["definition"],
                unit=METRICS[primary_key][1],
                source_kind=v["source_kind"],
                source_ref=v["source_ref"],
                window_kind=v["window_kind"],
                window_start=v["window_start"],
                window_end=v["window_end"],
                observed_at=v["observed_at"],
            )
    feedback = review_events(session, pub.revision_id)
    ops = operation_summary(session, pub)
    effort = [event_info(r) for r in heads if r.kind == "effort"]
    ops["reported_activity_effort_seconds"] = {
        role: sum(e["request"]["seconds"] for e in effort if e["request"]["role"] == role)
        if any(e["request"]["role"] == role for e in effort)
        else None
        for role in ["owner", "reviewer"]
    }
    ops["effort_note"] = (
        "Job entries, activity entries and effort metrics remain separate; "
        "overlapping self-reports are not summed."
    )
    evidence = [
        o["id"] for o in observations if not o["stale"] and not o["request"]["test_data"]
    ] + ([plan.id] if plan else [])
    evidence += ["review:" + e["id"] for e in feedback if e["kind"] == "assessment"]
    snapshot = {
        "publication": p,
        "observations": observations,
        "plan": planned,
        "feedback": feedback,
        "production": ops,
    }
    fingerprint = digest(snapshot)
    review_due = not planned or as_time(planned["request"]["review_at"]) <= current_time()
    suggestion = (
        "inconclusive"
        if not review_due
        else "collect_evidence"
        if primary["value"] is None
        else "modify"
        if primary["value"] == 0
        else "repeat"
    )
    summary = (
        (f"{METRICS[primary_key][0]}: {primary['value']}. {primary.get('definition', '')}.")
        if primary["value"] is not None
        else f"{METRICS[primary_key][0]}: sin un dato comparable disponible."
    )
    summary += (
        " Registro manual del negocio; no demuestra ventas adicionales "
        "causadas por esta publicación."
    )
    decisions = [event_info(r) for r in rows if r.kind == "decision"]
    for d in decisions:
        d["stale"] = d["evidence_digest"] != fingerprint
    return {
        **snapshot,
        "publication": p,
        "evidence_digest": fingerprint,
        "available_evidence_ids": evidence,
        "primary": primary,
        "summary": summary,
        "review_due": review_due,
        "suggested_action": suggestion,
        "comparison_type": "observational_not_randomized",
        "causal_effect": {"value": None, "reason": "no_controlled_experiment"},
        "confirmed_commerce_orders": {"value": None, "reason": "no_validated_order_links"},
        "reported_orders_note": (
            "Manually entered orders/revenue remain reports, not reconciled transactions; "
            "no cross-source totals are added."
        ),
        "fixture": doc["fixture"],
        "decisions": decisions,
        "history": [event_info(r) for r in rows],
        "record_count": len(rows),
    }


def learning_context(session, business, identifier):
    row = owned(session, ResultEvent, identifier, business)
    require(row.kind == "decision", "learning_decision_required")
    saved = json.loads(row.document)
    current = report(session, business, row.publication_id)
    require(
        current["publication"]["status"] == "active"
        and saved["evidence_digest"] == current["evidence_digest"],
        "learning_evidence_changed",
    )
    decisions = current["decisions"]
    require(decisions and decisions[-1]["id"] == identifier, "learning_decision_superseded")
    require(
        saved["request"]["action"] not in {"stop", "collect_evidence"},
        "learning_not_ready_for_production",
    )
    return {
        "id": row.id,
        "publication_id": row.publication_id,
        "source_pack_id": row.pack_id,
        "revision_id": row.revision_id,
        "evidence_digest": saved["evidence_digest"],
        "evidence_ids": saved["request"]["evidence_ids"],
        "action": saved["request"]["action"],
        "action_label": ACTIONS[saved["request"]["action"]],
        "owner_reason": saved["request"]["owner_reason"],
        "next_question": saved["request"]["next_question"],
        "observation": saved["summary"],
        "primary_metric": saved["primary_metric"],
        "reporting_basis": "owner_report_not_causal",
        "fixture": current["fixture"],
    }


def receipt_body(payload, approval_snapshot, fixture):
    now = current_time()
    published = payload.published_at.astimezone(UTC)
    require(published <= now, "publication_time_in_future")
    upper = (
        published + timedelta(minutes=1)
        if payload.timestamp_precision == "minute"
        else published + timedelta(seconds=1)
    )
    require(upper > as_time(approval_snapshot["at"]), "publication_before_approval")
    target = approval_snapshot["binding"]["destination"] or {}
    require(
        target.get("platform", "unspecified") in {"unspecified", payload.platform},
        "publication_destination_mismatch",
    )
    require(
        not target.get("account_label")
        or target["account_label"].strip().lstrip("@").casefold()
        == payload.account.strip().lstrip("@").casefold(),
        "publication_destination_mismatch",
    )
    parsed = urlsplit(payload.permalink)
    normalized = urlunsplit(
        ("https", parsed.hostname.lower().removeprefix("www."), parsed.path.rstrip("/"), "", "")
    )
    return {
        **payload.model_dump(mode="json"),
        "published_at_utc": utc(payload.published_at),
        "original_offset_seconds": int(payload.published_at.utcoffset().total_seconds()),
        "canonical_permalink": normalized,
        "verification": "fixture_owner_report" if fixture else "owner_report",
        "independently_verified": False,
        "fixture": fixture,
        "approval": approval_snapshot,
        "recorded_at": now.isoformat(),
    }


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social"

    @app.get(root + "/results/options", dependencies=[Depends(read)])
    def options(business_id: str):
        return {
            "metrics": {
                k: {"label": v[0], "unit": v[1], "level": v[2]} for k, v in METRICS.items()
            },
            "actions": ACTIONS,
            "publication_verification": "owner_report_only",
            "max_records_per_publication": MAX_EVENTS,
        }

    @app.get(root + "/packs/{pack_id}/publications", dependencies=[Depends(read)])
    def publications(business_id: str, pack_id: str, session=Depends(get_session)):
        owned(session, Pack, pack_id, business_id)
        return {
            "publications": [
                publication_info(session, p)
                for p in publication_rows(session, business_id, pack_id)
            ],
            "plans": [
                event_info(r)
                for r in session.scalars(
                    select(ResultEvent)
                    .where(ResultEvent.pack_id == pack_id, ResultEvent.kind == "plan")
                    .order_by(ResultEvent.created_at)
                )
            ],
        }

    @app.post(root + "/packs/{pack_id}/publications")
    def publish_record(
        business_id: str,
        pack_id: str,
        payload: Receipt,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        identifier = digest([business_id, pack_id, str(payload.request_id)])[:32]
        old = session.get(Publication, identifier)
        if old:
            require(
                old.business_id == business_id
                and old.request_json == canonical(payload.model_dump(mode="json")),
                "publication_idempotency_conflict",
            )
            return publication_info(session, old)
        _, rev, doc, approval = locked_current(session, business_id, pack_id)
        repeated = session.get(Publication, identifier)
        if repeated:
            require(
                repeated.request_json == canonical(payload.model_dump(mode="json")),
                "publication_idempotency_conflict",
            )
            return publication_info(session, repeated)
        require(
            approval is not None and approval.digest == payload.digest == rev.digest,
            "approved_publication_version_required",
        )
        require(technical(rev)["status"] == "passed", "publication_output_changed")
        require(
            len(publication_rows(session, business_id, pack_id)) < 30,
            "publication_history_limit",
            429,
        )
        binding = {
            "actor_id": approval.actor_id,
            "at": approval.approved_at,
            "review_id": getattr(approval, "review_id", None),
            "mode": getattr(approval, "mode", "legacy_checkbox"),
            "binding": scope(rev, doc),
        }
        value = receipt_body(payload, binding, doc["fixture"])
        value["recorded_by"] = principal.actor_id
        key = digest([payload.platform, value["canonical_permalink"]])
        if payload.status == "withdrawn":
            key = digest(["withdrawn", identifier])
        row = Publication(
            id=identifier,
            business_id=business_id,
            pack_id=pack_id,
            revision_id=rev.id,
            identity_key=key,
            native_key=native_identity(payload) if payload.status == "active" else None,
            revision=1,
            event_sequence=0,
            request_json=canonical(payload.model_dump(mode="json")),
        )
        session.add(row)
        try:
            session.flush()
            session.add(
                PublicationVersion(
                    id=f"{row.id}:1", publication_id=row.id, document=canonical(value)
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            require(False, "publication_already_recorded")
        return publication_info(session, row)

    @app.put(root + "/publications/{publication_id}")
    def correct(
        business_id: str,
        publication_id: str,
        payload: ReceiptCorrection,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        pub = lock_publication(session, business_id, publication_id)
        require(pub.revision < 50, "publication_correction_limit", 429)
        history = list(
            session.scalars(
                select(PublicationVersion).where(PublicationVersion.publication_id == pub.id)
            )
        )
        for version in history:
            old = json.loads(version.document)
            if old["request_id"] == str(payload.request_id):
                require(
                    old.get("correction_request") == payload.model_dump(mode="json"),
                    "publication_idempotency_conflict",
                )
                return publication_info(session, pub)
        require(pub.revision == payload.expected_revision, "publication_revision_changed")
        prior = pub_document(session, pub)
        require(
            payload.digest == prior["approval"]["binding"]["digest"], "publication_digest_changed"
        )
        value = receipt_body(payload, prior["approval"], prior["fixture"])
        value["correction_request"] = payload.model_dump(mode="json")
        value["corrected_by"] = principal.actor_id
        pub.revision += 1
        pub.native_key = native_identity(payload) if payload.status == "active" else None
        pub.identity_key = (
            digest(["withdrawn", pub.id])
            if payload.status == "withdrawn"
            else digest([payload.platform, value["canonical_permalink"]])
        )
        session.add(
            PublicationVersion(
                id=f"{pub.id}:{pub.revision}", publication_id=pub.id, document=canonical(value)
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            require(False, "publication_already_recorded")
        return publication_info(session, pub)

    @app.get(root + "/publications/{publication_id}/report", dependencies=[Depends(read)])
    def get_report(business_id: str, publication_id: str, session=Depends(get_session)):
        return report(session, business_id, publication_id)

    @app.get(root + "/publications/{publication_id}/history", dependencies=[Depends(read)])
    def receipt_history(business_id: str, publication_id: str, session=Depends(get_session)):
        pub = owned(session, Publication, publication_id, business_id)
        return {
            "versions": [
                {"id": v.id, **json.loads(v.document)}
                for v in session.scalars(
                    select(PublicationVersion)
                    .where(PublicationVersion.publication_id == pub.id)
                    .order_by(PublicationVersion.id)
                )
            ]
        }

    @app.post(root + "/publications/{publication_id}/observations")
    def observe(
        business_id: str,
        publication_id: str,
        payload: Observation,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        pub = lock_publication(session, business_id, publication_id)
        p = pub_document(session, pub)
        require(p["status"] == "active", "publication_withdrawn")
        require(payload.observed_at <= current_time(), "observation_in_future")
        require(
            payload.window_start >= as_time(p["published_at_utc"]), "observation_before_publication"
        )
        if payload.window_kind == "lifetime_snapshot":
            require(
                payload.window_start == as_time(p["published_at_utc"]), "lifetime_window_mismatch"
            )
        row = append_event(
            session,
            business_id,
            pub.pack_id,
            pub.revision_id,
            pub,
            "metric",
            payload,
            principal,
            {"unit": METRICS[payload.metric][1], "independently_verified": False},
        )
        session.commit()
        return event_info(row)

    @app.post(root + "/publications/{publication_id}/effort")
    def add_effort(
        business_id: str,
        publication_id: str,
        payload: Effort,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        pub = lock_publication(session, business_id, publication_id)
        row = append_event(
            session,
            business_id,
            pub.pack_id,
            pub.revision_id,
            pub,
            "effort",
            payload,
            principal,
            {"basis": "owner_entered_activity_time", "not_summed_with_job_entries": True},
        )
        session.commit()
        return event_info(row)

    @app.post(root + "/packs/{pack_id}/measurement-plan")
    def plan(
        business_id: str,
        pack_id: str,
        payload: Plan,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        _, rev, doc, approval = locked_current(session, business_id, pack_id)
        require(
            approval is not None and payload.digest == rev.digest, "approved_plan_version_required"
        )
        expected = {"owner_effort": "owner_effort_seconds"}.get(
            doc["brief"]["primary_measure"], doc["brief"]["primary_measure"]
        )
        require(payload.primary_metric == expected, "plan_primary_differs_from_brief")
        pubs = [
            p
            for p in publication_rows(session, business_id, pack_id)
            if p.revision_id == rev.id and pub_document(session, p)["status"] == "active"
        ]
        if not pubs:
            require(payload.review_at > current_time(), "prospective_review_must_be_future")
        row = append_event(
            session,
            business_id,
            pack_id,
            rev.id,
            None,
            "plan",
            payload,
            principal,
            {
                "timing": "retrospective" if pubs else "before_receipt_not_necessarily_before_post",
                "comparison_type": "observational_not_randomized",
                "recorded_at": current_time().isoformat(),
            },
        )
        session.commit()
        return event_info(row)

    @app.post(root + "/publications/{publication_id}/decisions")
    def decide(
        business_id: str,
        publication_id: str,
        payload: NextDecision,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        pub = lock_publication(session, business_id, publication_id)
        r = report(session, business_id, pub.id)
        require(r["publication"]["status"] == "active", "publication_withdrawn")
        require(payload.evidence_digest == r["evidence_digest"], "learning_evidence_changed")
        if r["primary"]["event_id"]:
            require(
                r["primary"]["event_id"] in payload.evidence_ids,
                "learning_primary_citation_required",
            )
        require(
            set(payload.evidence_ids) <= set(r["available_evidence_ids"]),
            "learning_evidence_not_in_report",
        )
        require(
            bool(
                set(payload.evidence_ids)
                & {
                    o["id"]
                    for o in r["observations"]
                    if not o["stale"] and not o["request"]["test_data"]
                }
            ),
            "learning_observation_required",
        )
        row = append_event(
            session,
            business_id,
            pub.pack_id,
            pub.revision_id,
            pub,
            "decision",
            payload,
            principal,
            {
                "evidence_digest": r["evidence_digest"],
                "summary": r["summary"],
                "primary_metric": r["primary"]["metric"],
                "primary_snapshot": r["primary"],
                "comparison_type": "observational_not_randomized",
                "causal_effect": None,
                "suggested_action_at_decision": r["suggested_action"],
                "review_due_at_decision": r["review_due"],
            },
        )
        session.commit()
        return event_info(row)


def native_identity(payload):
    return (
        digest(
            [
                payload.platform,
                payload.account.strip().lstrip("@").casefold(),
                payload.provider_post_id.strip(),
            ]
        )
        if payload.provider_post_id.strip()
        else None
    )


def pack_receipt_summary(session, business, pack_id, revision_id):
    rows = publication_rows(session, business, pack_id)
    active_records = [
        p
        for p in rows
        if p.revision_id == revision_id and pub_document(session, p)["status"] == "active"
    ]
    if not active_records:
        return {"status": "manual_export_only", "post_id": None, "independently_verified": False}
    p = publication_info(session, active_records[0])
    return {
        "status": "manual_reported",
        "post_id": p["provider_post_id"] or p["canonical_permalink"],
        "publication_id": p["id"],
        "receipt_count": len(active_records),
        "independently_verified": False,
    }
