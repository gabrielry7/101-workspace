"""Explicit owner choices; onboarding context never creates publishable facts."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .social_production import Strict

GOALS = {
    "discovery": "Que más personas me conozcan",
    "orders": "Recibir más pedidos",
    "bookings": "Conseguir más reservas",
    "repeat": "Que mis clientes vuelvan",
    "promote": "Promover algo específico",
}
CHANNELS = {
    "store": "En el local",
    "whatsapp": "Por WhatsApp",
    "instagram": "Por Instagram",
    "website": "En mi página",
    "platform": "Por una plataforma",
}
FEATURES = {
    "product": "Un producto o servicio",
    "process": "Cómo trabajamos",
    "team": "Nuestro equipo",
    "news": "Una novedad",
    "question": "Responder una pregunta frecuente",
}
CONDITIONS = {
    "advance": "Trabajamos por encargo",
    "limited": "Tenemos cupos limitados",
    "area": "Atendemos ciertas zonas",
    "variable_price": "Los precios varían",
}


class Answer(Strict):
    choice: str = Field(min_length=1, max_length=40)
    detail: str = Field(default="", max_length=2400)


class OnboardingAnswers(Strict):
    goal: Answer
    channels: list[Answer] = Field(min_length=1, max_length=6)
    feature: Answer
    materials: list[Literal["photos", "videos", "logo", "posts", "none", "later", "other"]] = Field(
        min_length=1, max_length=5
    )
    material_detail: str = Field(default="", max_length=2400)
    conditions: list[Answer] = Field(default_factory=list, max_length=5)
    lead_time: Answer | None = None
    locale: str | None = Field(default=None, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")

    @model_validator(mode="after")
    def valid_choices(self):
        def check(answer, options, detailed=()):
            if answer.choice not in options:
                raise ValueError("unknown_onboarding_choice")
            answer.detail = answer.detail.strip()
            if answer.choice in {*detailed, "other"} and not answer.detail:
                raise ValueError("onboarding_detail_required")
            if answer.choice in {"unknown", "later", "none", "help"} and answer.detail:
                raise ValueError("unanswered_choice_has_detail")

        def many(answers, options, exclusive, detailed=()):
            keys = [a.choice for a in answers]
            if len(set(keys)) != len(keys) or (set(keys) & exclusive and len(keys) != 1):
                raise ValueError("conflicting_onboarding_choices")
            for answer in answers:
                check(answer, options, detailed)

        check(self.goal, {*GOALS, "other", "unknown"})
        many(self.channels, {*CHANNELS, "other", "later"}, {"later"})
        check(self.feature, {*FEATURES, "other", "help"}, {"product", "news", "question"})
        if len(set(self.materials)) != len(self.materials) or (
            set(self.materials) & {"none", "later"} and len(self.materials) != 1
        ):
            raise ValueError("conflicting_material_choices")
        if "other" in self.materials and not self.material_detail.strip():
            raise ValueError("onboarding_detail_required")
        if "other" not in self.materials and self.material_detail:
            raise ValueError("unused_material_detail")
        many(self.conditions, {*CONDITIONS, "other", "none", "later"}, {"none", "later"})
        if self.lead_time:
            if "advance" not in [a.choice for a in self.conditions]:
                raise ValueError("unused_lead_time")
            check(
                self.lead_time, {"same_day", "one_day", "two_days", "depends", "other", "unknown"}
            )
        return self

    def brief_fields(self):
        def describe(answer, labels):
            label = labels.get(answer.choice)
            if answer.choice == "other":
                return answer.detail
            return (label + (": " + answer.detail if answer.detail else "")) if label else None

        channels = [describe(a, CHANNELS) for a in self.channels]
        conditions = [describe(a, CONDITIONS) for a in self.conditions]
        if self.lead_time:
            lead = describe(
                self.lead_time,
                {
                    "same_day": "Pedir el mismo día",
                    "one_day": "Pedir un día antes",
                    "two_days": "Pedir dos días antes",
                    "depends": "El plazo depende del producto",
                },
            )
            if lead:
                conditions.append(lead)
        return {
            "objective": describe(self.goal, GOALS),
            "offering": describe(self.feature, FEATURES),
            "buying_destination": "; ".join(filter(None, channels)) or None,
            "constraints": "; ".join(filter(None, conditions)),
            "locale": self.locale,
        }


class OnboardingInput(Strict):
    expected_revision: int = Field(ge=0)
    answers: OnboardingAnswers
    confirmed: Literal[True]
    location_id: UUID | None = None
