"""Reviewed reference/search evidence → deterministic comparisons → proposal snapshot."""

# ruff: noqa: B008 -- FastAPI injection
import hashlib
import json
from statistics import median

from fastapi import Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .social_context import scope_id
from .social_creative import read_board, reference_available
from .social_production import canonical, future, owned, require
from .social_research_contracts import ResearchInput
from .social_research_models import ResearchBoard, ResearchVersion
from .social_reviews import current_time


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_research(session, business, location=None):
    board = session.get(ResearchBoard, scope_id(business, location), populate_existing=True)
    if not board:
        return {
            "revision": 0,
            "id": None,
            "business_id": business,
            "location_id": location,
            "posts": [],
            "searches": [],
        }
    return json.loads(session.get(ResearchVersion, f"{board.id}:{board.revision}").document)


def available(session, business, item, kind, brand, now):
    require(
        item["status"] == "active" and future(item["valid_until"], now),
        "research_source_unavailable",
    )
    if kind == "posts":
        ref = next((r for r in brand["references"] if r["id"] == item["reference_id"]), None)
        require(ref is not None, "research_reference_missing")
        reference_available(session, business, ref, now)
        require(digest(ref) == item["reference_hash"], "research_reference_changed")
    else:
        question = next((q for q in brand["questions"] if q["id"] == item["question_id"]), None)
        require(
            question is not None
            and question["status"] == "active"
            and future(question["valid_until"], now),
            "research_question_unavailable",
        )
        require(digest(question) == item["question_hash"], "research_question_changed")


def metric_summary(posts, selected):
    rows = []
    for m in selected["metrics"]:
        base = {
            "metric": m["metric"],
            "window": m["window"],
            "value": m["value"],
            "definition": m["definition"],
            "observed_at": m["observed_at"],
            "sample_size": 0,
            "median": None,
            "range": None,
            "relative_to_median": None,
            "reason": "age_matched_baseline_unavailable",
            "baseline_sources": [],
            "baseline_model_processing_allowed": True,
        }
        if m["availability"] != "measured":
            base["reason"] = m["reason"]
            rows.append(base)
            continue
        if m["window"] == "lifetime":
            base["reason"] = "lifetime_counts_cannot_reconstruct_age_matched_history"
            rows.append(base)
            continue
        values = []
        for p in posts:
            if p["id"] == selected["id"] or any(
                p[k] != selected[k]
                for k in ("reference_id", "account_key", "platform", "format", "paid_support")
            ):
                continue
            match = next(
                (
                    v
                    for v in p["metrics"]
                    if v["metric"] == m["metric"]
                    and v["window"] == m["window"]
                    and v["definition"] == m["definition"]
                    and v["availability"] == "measured"
                ),
                None,
            )
            if match:
                values.append(match["value"])
                base["baseline_sources"].append(
                    {"id": p["id"], "revision": p["revision"], "sha256": digest(p)}
                )
                base["baseline_model_processing_allowed"] &= p["model_processing_allowed"]
        base.update(
            sample_size=len(values),
            median=median(values) if values else None,
            range=[min(values), max(values)] if values else None,
        )
        if len(values) < 3:
            base["reason"] = "sparse_comparable_baseline"
        elif base["median"] == 0:
            base["reason"] = "zero_baseline_raw_values_only"
        else:
            base.update(
                relative_to_median=m["value"] / base["median"],
                reason="descriptive_account_comparison_not_causal",
            )
        rows.append(base)
    return rows


def active_posts(session, business, board, brand, now):
    result = []
    for p in board["posts"]:
        try:
            available(session, business, p, "posts", brand, now)
        except HTTPException:
            continue
        result.append(p)
    return result


def report(session, business, location=None):
    board = read_research(session, business, location)
    brand = read_board(session, business, location)
    posts = active_posts(session, business, board, brand, current_time())
    return {
        "revision": board["revision"],
        "coverage": "owner_selected_examples_not_complete_account_history",
        "posts": [
            {
                "id": p["id"],
                "subject": p["subject"],
                "account_key": p["account_key"],
                "platform": p["platform"],
                "format": p["format"],
                "timestamp_precision": p["timestamp_precision"],
                "observation": p["observation"],
                "hypothesis": p["hypothesis"],
                "alternatives": p["alternatives"],
                "adaptation": p["adaptation"],
                "fixture": p["fixture"],
                "comparisons": metric_summary(posts, p),
            }
            for p in posts
        ],
        "timing_advice": None,
        "timing_reason": "no_causal_or_minute_optimum_claim",
        "private_competitor_metrics": None,
        "search_volume": None,
        "search_traffic": None,
    }


def snapshot(session, business, version_id, post_ids, search_ids, location=None):
    require(version_id or not (post_ids or search_ids), "research_version_required")
    if not version_id:
        return None
    require(post_ids or search_ids, "select_research_evidence", 422)
    require(
        len(set(post_ids)) == len(post_ids) and len(set(search_ids)) == len(search_ids),
        "duplicate_research_selection",
        422,
    )
    version = session.get(ResearchVersion, version_id)
    require(version is not None, "research_version_missing", 404)
    board = owned(session, ResearchBoard, version.board_id, business)
    require(board.location_id == location, "research_scope_mismatch", 404)
    brand = read_board(session, business, location, lock=True)
    current = read_research(session, business, location)
    previous = json.loads(version.document)
    now = current_time()
    chosen = {"posts": [], "searches": []}
    candidates = active_posts(session, business, current, brand, now)
    for kind, ids in (("posts", post_ids), ("searches", search_ids)):
        for identifier in ids:
            old = next((p for p in previous[kind] if p["id"] == identifier), None)
            live = next((p for p in current[kind] if p["id"] == identifier), None)
            require(old is not None and old == live, "research_evidence_changed")
            available(session, business, old, kind, brand, now)
            shared = {
                k: old[k]
                for k in (
                    "id",
                    "revision",
                    "source",
                    "source_url",
                    "permission",
                    "allowed_use",
                    "model_processing_allowed",
                    "observed_at",
                    "valid_until",
                    "fixture",
                    "observation",
                )
            }
            shared["item_hash"] = digest(old)
            if kind == "posts":
                ref = next(r for r in brand["references"] if r["id"] == old["reference_id"])
                shared.update(
                    {
                        k: old[k]
                        for k in (
                            "account_key",
                            "platform",
                            "format",
                            "subject",
                            "opening",
                            "sequence",
                            "visual_treatment",
                            "customer_action",
                            "duration_ms",
                            "sound",
                            "paid_support",
                            "published_at",
                            "publication_day",
                            "timestamp_precision",
                            "timezone",
                            "hypothesis",
                            "alternatives",
                            "adaptation",
                        )
                    }
                )
                shared.update(
                    reference_id=ref["id"],
                    reference_hash=old["reference_hash"],
                    group=ref["purpose"],
                    comparisons=metric_summary(candidates, old),
                )
            else:
                q = next(q for q in brand["questions"] if q["id"] == old["question_id"])
                shared.update(
                    {
                        k: old[k]
                        for k in (
                            "question_id",
                            "platform",
                            "locale",
                            "geography",
                            "source_kind",
                            "observation_context",
                            "sampled_position",
                        )
                    }
                )
                shared.update(
                    query=q["text"],
                    question_hash=old["question_hash"],
                    ranking_scope="sample_only_not_universal",
                    search_volume=None,
                )
            chosen[kind].append(shared)
    return {
        "version_id": version_id,
        **chosen,
        "coverage": "curated_examples_not_comprehensive_research",
        "causal_effect": None,
        "search_volume": None,
        "account_access": "not_claimed_by_manual_evidence",
    }


def stale_reasons(session, business, document):
    b = document["brief"]
    if not b.get("research_version_id"):
        return []
    try:
        value = snapshot(
            session,
            business,
            b["research_version_id"],
            b.get("research_post_ids", []),
            b.get("research_search_ids", []),
            b.get("location_id"),
        )
        require(value == document.get("research_snapshot"), "research_baseline_changed")
        return []
    except HTTPException as e:
        return [{"reason": e.detail, "scope": "research"}]


def model_summary(value):
    """Only permitted annotations; exclude raw reference copy/URLs/account identifiers."""
    if not value:
        return None
    require(
        all(p["model_processing_allowed"] for group in ("posts", "searches") for p in value[group]),
        "research_model_processing_not_authorized",
    )
    require(
        all(
            c["baseline_model_processing_allowed"] for p in value["posts"] for c in p["comparisons"]
        ),
        "research_baseline_model_processing_not_authorized",
    )
    return {
        "posts": [
            {
                k: p[k]
                for k in (
                    "id",
                    "revision",
                    "group",
                    "subject",
                    "opening",
                    "sequence",
                    "visual_treatment",
                    "observation",
                    "hypothesis",
                    "alternatives",
                    "adaptation",
                    "comparisons",
                )
            }
            for p in value["posts"]
        ],
        "searches": [
            {
                k: p[k]
                for k in (
                    "id",
                    "revision",
                    "query",
                    "platform",
                    "locale",
                    "geography",
                    "source_kind",
                    "observation",
                    "observation_context",
                    "sampled_position",
                    "ranking_scope",
                )
            }
            for p in value["searches"]
        ],
        "search_volume": None,
        "causal_effect": None,
    }


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social/research"

    def scope(business, location):
        if location:
            resolver = getattr(app.state, "social_location_belongs_to_business", None)
            require(resolver is not None, "canonical_location_validation_unavailable", 503)
            require(resolver(business, location), "location_not_in_business", 404)

    @app.get(root, dependencies=[Depends(read)])
    def get(business_id: str, location_id: str | None = None, session=Depends(get_session)):
        scope(business_id, location_id)
        return {
            **read_research(session, business_id, location_id),
            "analysis": report(session, business_id, location_id),
        }

    @app.put(root)
    def save(
        business_id: str,
        payload: ResearchInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        location = str(payload.location_id) if payload.location_id else None
        scope(business_id, location)
        previous = read_research(session, business_id, location)
        require(previous["revision"] == payload.expected_revision, "research_revision_conflict")
        brand = read_board(session, business_id, location, lock=True)
        value = payload.model_dump(
            mode="json", exclude={"expected_revision", "confirmed", "location_id"}
        )
        for kind in ("posts", "searches"):
            for item in value[kind]:
                old = next((p for p in previous[kind] if p["id"] == item["id"]), None)
                if kind == "posts":
                    ref = next(
                        (r for r in brand["references"] if r["id"] == item["reference_id"]), None
                    )
                    require(ref is not None, "research_reference_missing", 422)
                    item["reference_hash"] = digest(ref)
                else:
                    q = next(
                        (q for q in brand["questions"] if q["id"] == item["question_id"]), None
                    )
                    require(q is not None, "research_question_unavailable", 422)
                    item["question_hash"] = digest(q)
                if item["status"] == "active":
                    available(session, business_id, item, kind, brand, current_time())
                unchanged = old and all(old.get(k) == v for k, v in item.items())
                item.update(
                    revision=old["revision"] if unchanged else old["revision"] + 1 if old else 1,
                    reviewed_by=old["reviewed_by"] if unchanged else principal.actor_id,
                    recorded_at=old["recorded_at"] if unchanged else current_time().isoformat(),
                )
            ids = {p["id"] for p in value[kind]}
            value[kind] += [
                {
                    **old,
                    "status": "withdrawn",
                    "revision": old["revision"] + int(old["status"] != "withdrawn"),
                }
                for old in previous[kind]
                if old["id"] not in ids
            ]
            require(len(value[kind]) <= 120, "research_history_limit", 429)
        identifier = scope_id(business_id, location)
        board = session.get(ResearchBoard, identifier)
        if board:
            changed = session.execute(
                update(ResearchBoard)
                .where(
                    ResearchBoard.id == identifier,
                    ResearchBoard.revision == payload.expected_revision,
                )
                .values(revision=ResearchBoard.revision + 1)
            )
            require(changed.rowcount == 1, "research_revision_conflict")
            session.refresh(board)
        else:
            board = ResearchBoard(
                id=identifier, business_id=business_id, location_id=location, revision=1
            )
            session.add(board)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "research_revision_conflict") from None
        value.update(
            id=f"{identifier}:{board.revision}",
            revision=board.revision,
            business_id=business_id,
            location_id=location,
        )
        session.add(ResearchVersion(id=value["id"], board_id=identifier, document=canonical(value)))
        session.commit()
        return {**value, "analysis": report(session, business_id, location)}

    @app.get(root + "/history", dependencies=[Depends(read)])
    def history(business_id: str, location_id: str | None = None, session=Depends(get_session)):
        scope(business_id, location_id)
        return {
            "versions": [
                json.loads(v.document)
                for v in session.scalars(
                    select(ResearchVersion)
                    .where(ResearchVersion.board_id == scope_id(business_id, location_id))
                    .order_by(ResearchVersion.id)
                    .limit(100)
                )
            ],
            "coverage": "bounded_history",
        }
