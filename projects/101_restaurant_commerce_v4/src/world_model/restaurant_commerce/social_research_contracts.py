"""Manually reviewed observations; no crawler, volume or private competitor metrics."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, HttpUrl, model_validator

from .social_creative import Sourced
from .social_production import Strict

WINDOWS = {"24h": (20, 28), "72h": (64, 80), "7d": (144, 192)}


class PublicMetric(Strict):
    metric: Literal["likes", "comments", "views"]
    definition: str = Field(min_length=3, max_length=300)
    value: int | None = Field(default=None, strict=True, ge=0, le=2**53 - 1)
    availability: Literal["measured", "unavailable"]
    reason: str = Field(default="", max_length=300)
    window: Literal["24h", "72h", "7d", "lifetime"] = "lifetime"
    observed_at: AwareDatetime
    source_ref: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def values(self):
        if (self.availability == "measured") != (self.value is not None):
            raise ValueError("metric_value_or_unavailable_required")
        if self.availability == "unavailable" and not self.reason.strip():
            raise ValueError("unavailable_metric_reason_required")
        if self.observed_at > datetime.now(UTC):
            raise ValueError("future_observation")
        return self


class ResearchSource(Sourced):
    source_url: HttpUrl | None = None
    permission: str = Field(min_length=8, max_length=600)
    allowed_use: Literal["internal_reference_only"] = "internal_reference_only"
    model_processing_allowed: bool = False
    fixture: bool = False

    @model_validator(mode="after")
    def url(self):
        if self.source_url and (
            self.source_url.scheme != "https"
            or self.source_url.username
            or self.source_url.password
        ):
            raise ValueError("https_source_without_credentials_required")
        return self


class ResearchPost(ResearchSource):
    reference_id: str = Field(min_length=1, max_length=64)
    account_key: str = Field(min_length=1, max_length=100)
    platform: Literal["instagram", "facebook", "tiktok"]
    format: Literal["photo", "carousel", "video"]
    subject: str = Field(min_length=1, max_length=300)
    opening: str = Field(default="", max_length=500)
    sequence: str = Field(default="", max_length=800)
    visible_text: str = Field(default="", max_length=800)
    caption_excerpt: str = Field(default="", max_length=1200)
    visual_treatment: str = Field(default="", max_length=500)
    customer_action: str = Field(default="", max_length=400)
    duration_ms: int | None = Field(default=None, strict=True, ge=1, le=3600000)
    sound: Literal["natural", "speech", "music", "silent", "unknown"] = "unknown"
    paid_support: Literal["unknown", "organic_reported", "paid_reported"] = "unknown"
    distribution_evidence: str = Field(default="", max_length=500)
    published_at: AwareDatetime | None = None
    publication_day: date | None = None
    timestamp_precision: Literal["second", "minute", "day", "unknown"] = "unknown"
    timezone: str | None = Field(default=None, max_length=80)
    observation: str = Field(min_length=1, max_length=600)
    hypothesis: str = Field(min_length=1, max_length=600)
    alternatives: str = Field(min_length=1, max_length=600)
    adaptation: str = Field(min_length=1, max_length=600)
    metrics: list[PublicMetric] = Field(default_factory=list, max_length=9)

    @model_validator(mode="after")
    def publication(self):
        self.account_key = self.account_key.strip().casefold()
        if not self.account_key:
            raise ValueError("account_key_required")
        if self.paid_support != "unknown" and not self.distribution_evidence.strip():
            raise ValueError("distribution_evidence_required")
        precision = self.timestamp_precision
        if precision in {"minute", "second"}:
            if self.published_at is None or self.publication_day is not None or not self.timezone:
                raise ValueError("native_timestamp_timezone_required")
            try:
                zone = ZoneInfo(self.timezone)
            except ZoneInfoNotFoundError:
                raise ValueError("invalid_timezone") from None
            if self.published_at.astimezone(zone).utcoffset() != self.published_at.utcoffset():
                raise ValueError("timestamp_timezone_mismatch")
            if precision == "minute" and (
                self.published_at.second or self.published_at.microsecond
            ):
                raise ValueError("timestamp_precision_mismatch")
            if self.published_at > self.observed_at:
                raise ValueError("publication_after_source_observation")
        elif precision == "day":
            if (
                self.publication_day is None
                or self.published_at is not None
                or self.publication_day > self.observed_at.date()
            ):
                raise ValueError("day_only_timestamp_required")
            if self.timezone:
                try:
                    ZoneInfo(self.timezone)
                except ZoneInfoNotFoundError:
                    raise ValueError("invalid_timezone") from None
        elif (
            self.published_at is not None
            or self.publication_day is not None
            or self.timezone is not None
        ):
            raise ValueError("unknown_publication_time_has_no_invented_timestamp")
        if len({(m.metric, m.window) for m in self.metrics}) != len(self.metrics):
            raise ValueError("duplicate_post_metric_window")
        for metric in self.metrics:
            if metric.observed_at > self.observed_at:
                raise ValueError("metric_after_source_observation")
            if self.published_at and metric.observed_at < self.published_at:
                raise ValueError("metric_before_publication")
            if metric.window != "lifetime":
                if self.published_at is None:
                    raise ValueError("age_comparison_requires_native_timestamp")
                age = (metric.observed_at - self.published_at).total_seconds() / 3600
                low, high = WINDOWS[metric.window]
                if not low <= age <= high:
                    raise ValueError("metric_not_observed_at_declared_post_age")
        return self


class SearchObservation(ResearchSource):
    question_id: str = Field(min_length=1, max_length=64)
    platform: Literal["instagram", "facebook", "tiktok", "other"]
    locale: str = Field(min_length=2, max_length=30)
    geography: str = Field(default="", max_length=160)
    source_kind: Literal[
        "sampled_search", "owner_export", "customer_question", "manual_research", "hypothesis"
    ]
    observation_context: str = Field(min_length=3, max_length=600)
    observation: str = Field(min_length=1, max_length=600)
    sampled_position: int | None = Field(default=None, strict=True, ge=1, le=200)

    @model_validator(mode="after")
    def sample(self):
        if self.sampled_position is not None and self.source_kind != "sampled_search":
            raise ValueError("rank_requires_sampled_search_context")
        if self.source_kind == "hypothesis" and self.source_url:
            raise ValueError("hypothesis_is_not_a_measured_search_result")
        return self


class ResearchInput(Strict):
    expected_revision: int = Field(ge=0)
    location_id: UUID | None = None
    posts: list[ResearchPost] = Field(default_factory=list, max_length=60)
    searches: list[SearchObservation] = Field(default_factory=list, max_length=60)
    reason: str = Field(min_length=1, max_length=600)
    confirmed: Literal[True]

    @model_validator(mode="after")
    def unique(self):
        for rows in (self.posts, self.searches):
            if len({r.id for r in rows}) != len(rows):
                raise ValueError("duplicate_research_id")
        return self
