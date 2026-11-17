"""Bounded literal text; optional source ranges apply only to owner-entered captions."""

import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .social_video_contracts import Strict


class Word(Strict):
    index: int = Field(ge=0, le=249)
    start: int = Field(ge=0, le=30000)
    end: int = Field(ge=1, le=30100)
    text: str = Field(min_length=1, max_length=64)
    probability: float = Field(ge=0, le=1)
    uncertain: bool = True

    @model_validator(mode="after")
    def literal(self):
        self.text = unicodedata.normalize("NFC", self.text.strip())
        if (
            self.end <= self.start
            or not self.text
            or any(unicodedata.category(c).startswith("C") for c in self.text)
        ):
            raise ValueError("speech_word_invalid")
        return self


class Machine(Strict):
    schema_version: Literal["1"] = "1"
    language: Literal["es"] = "es"
    words: list[Word] = Field(min_length=1, max_length=250)
    uncertainty: Literal["automatic_unverified"] = "automatic_unverified"


class Correction(Strict):
    start: int | None = Field(default=None, ge=0, le=30000, strict=True)
    end: int | None = Field(default=None, ge=1, le=30100, strict=True)
    index: int = Field(ge=0, le=249)
    text: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def literal(self):
        self.text = unicodedata.normalize("NFC", self.text.strip())
        if not self.text or any(unicodedata.category(c).startswith("C") for c in self.text):
            raise ValueError("speech_word_invalid")
        return self


class EditInput(Strict):
    request_id: UUID
    expected_revision: int = Field(ge=0, le=100)
    changes: list[Correction] = Field(min_length=1, max_length=250)
    reason: str = Field(min_length=3, max_length=500)
    meaning_confirmed: Literal[True]

    @model_validator(mode="after")
    def unique(self):
        if len({c.index for c in self.changes}) != len(self.changes):
            raise ValueError("duplicate_word_correction")
        return self
