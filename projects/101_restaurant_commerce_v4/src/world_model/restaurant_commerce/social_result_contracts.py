"""Owner-reported observations, never inferred provider verification or causal lift."""

from datetime import UTC
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, model_validator

from .social_production import Strict

METRICS = {
    "reach": ("Alcance", "count", "attention"),
    "views": ("Visualizaciones", "count", "attention"),
    "comments": ("Comentarios", "count", "attention"),
    "shares": ("Compartidos", "count", "attention"),
    "saves": ("Guardados", "count", "attention"),
    "watch_seconds": ("Tiempo de reproducción", "seconds", "attention"),
    "search_views": ("Visualizaciones desde búsquedas", "count", "attention"),
    "qualified_inquiries": ("Consultas de compra", "count", "purchase_interest"),
    "orders": ("Pedidos reportados", "count", "reported_business"),
    "net_revenue_minor": ("Ingresos netos reportados", "minor_currency", "reported_business"),
    "owner_effort_seconds": ("Tiempo del propietario", "seconds", "production"),
}
Metric = Literal[
    "reach",
    "views",
    "comments",
    "shares",
    "saves",
    "watch_seconds",
    "search_views",
    "qualified_inquiries",
    "orders",
    "net_revenue_minor",
    "owner_effort_seconds",
]


class Receipt(Strict):
    request_id: UUID
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    platform: Literal["instagram", "facebook", "tiktok"]
    account: str = Field(min_length=1, max_length=120)
    permalink: str = Field(min_length=10, max_length=500)
    provider_post_id: str = Field(default="", max_length=160)
    published_at: AwareDatetime
    timezone: str = Field(min_length=1, max_length=80)
    timestamp_precision: Literal["minute", "second"] = "minute"
    source_ref: str = Field(min_length=3, max_length=500)
    matches_approved: Literal[True]
    status: Literal["active", "withdrawn"] = "active"
    reason: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def source(self):
        parsed = urlsplit(self.permalink)
        hosts = {"instagram": "instagram.com", "facebook": "facebook.com", "tiktok": "tiktok.com"}
        host = parsed.hostname or ""
        root = hosts[self.platform]
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or not (host == root or host.endswith("." + root))
            or parsed.path in {"", "/"}
        ):
            raise ValueError("supported_publication_permalink_required")
        if not self.account.strip() or not self.source_ref.strip() or not self.reason.strip():
            raise ValueError("publication_source_required")
        try:
            tz = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError("invalid_timezone") from None
        if self.published_at.astimezone(tz).utcoffset() != self.published_at.utcoffset():
            raise ValueError("timestamp_timezone_mismatch")
        if self.timestamp_precision == "minute" and (
            self.published_at.second or self.published_at.microsecond
        ):
            raise ValueError("timestamp_precision_mismatch")
        return self


class ReceiptCorrection(Receipt):
    expected_revision: int = Field(ge=1)


class Observation(Strict):
    request_id: UUID
    supersedes_id: str | None = Field(default=None, max_length=64)
    metric: Metric
    availability: Literal["measured", "unavailable", "not_yet_collected"]
    value: int | None = Field(default=None, strict=True, ge=-(2**53 - 1), le=2**53 - 1)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    definition: str = Field(min_length=3, max_length=500)
    window_kind: Literal["lifetime_snapshot", "period"]
    window_start: AwareDatetime
    window_end: AwareDatetime
    observed_at: AwareDatetime
    source_kind: Literal[
        "owner_report", "owner_entered_provider_export", "owner_entered_first_party_report"
    ] = "owner_report"
    source_ref: str = Field(min_length=3, max_length=500)
    reason: str = Field(default="", max_length=600)
    search_specific: bool = False
    test_data: bool = False

    @model_validator(mode="after")
    def values(self):
        if self.metric != "net_revenue_minor" and self.value is not None and self.value < 0:
            raise ValueError("negative_count_not_supported")
        if (self.availability == "measured") != (self.value is not None):
            raise ValueError("measurement_value_or_null_reason")
        if self.availability != "measured" and not self.reason.strip():
            raise ValueError("missing_measurement_reason")
        if self.supersedes_id and not self.reason.strip():
            raise ValueError("correction_reason_required")
        if not self.source_ref.strip() or not self.definition.strip():
            raise ValueError("observation_source_required")
        if not (self.window_start < self.window_end <= self.observed_at):
            raise ValueError("observation_window_invalid")
        if (self.metric == "net_revenue_minor") != (self.currency is not None):
            raise ValueError("measurement_currency_mismatch")
        if (
            self.metric == "search_views"
            and self.availability == "measured"
            and not self.search_specific
        ):
            raise ValueError("search_specific_evidence_required")
        return self


class Effort(Strict):
    request_id: UUID
    supersedes_id: str | None = Field(default=None, max_length=64)
    role: Literal["owner", "reviewer"]
    seconds: int = Field(strict=True, ge=0, le=86400)
    activity: Literal["capture", "upload", "review", "revision", "reporting"]
    source_ref: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=1, max_length=600)


class Plan(Strict):
    request_id: UUID
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    supersedes_id: str | None = Field(default=None, max_length=64)
    question: str = Field(min_length=3, max_length=500)
    variant_difference: str = Field(min_length=3, max_length=500)
    primary_metric: Literal["qualified_inquiries", "orders", "reach", "owner_effort_seconds"]
    review_at: AwareDatetime
    reason: str = Field(min_length=1, max_length=600)


class NextDecision(Strict):
    request_id: UUID
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    action: Literal["repeat", "modify", "stop", "collect_evidence", "inconclusive"]
    owner_reason: str = Field(min_length=3, max_length=800)
    next_question: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def reasons(self):
        if (
            len(set(self.evidence_ids)) != len(self.evidence_ids)
            or not self.owner_reason.strip()
            or not self.next_question.strip()
        ):
            raise ValueError("decision_evidence_and_reason_required")
        return self


def utc(value):
    return value.astimezone(UTC).isoformat()
