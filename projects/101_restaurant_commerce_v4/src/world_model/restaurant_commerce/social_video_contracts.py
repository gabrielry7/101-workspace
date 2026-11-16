"""First constrained recipe: real, vertical, natural-sound product/process footage."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "social-montage-v1"
SPEECH_VERSION = "social-spoken-answer-v1"
SHOTS = (
    {
        "id": "detail",
        "title": "El producto",
        "instruction": (
            "Muestra el producto real de cerca. Deja espacio alrededor y mantén el teléfono quieto."
        ),
        "purpose": "Presentar lo que se va a mostrar.",
    },
    {
        "id": "process",
        "title": "Un paso real",
        "instruction": (
            "Graba un paso real de preparación o de tu servicio. "
            "No hace falta hablar ni recrear una acción que no realizas."
        ),
        "purpose": "Mostrar cómo se hace.",
    },
    {
        "id": "finish",
        "title": "El resultado",
        "instruction": (
            "Muestra el resultado real con un plano algo más abierto. "
            "Evita datos de clientes y personas sin permiso."
        ),
        "purpose": "Cerrar la secuencia con el resultado.",
    },
)
MAX_CLIP_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
SPOKEN_SHOTS = (
    SHOTS[0],
    {"id": "process", "title": "Tu respuesta", "instruction": "Responde la pregunta con los datos confirmados de la guía. Graba en un lugar tranquilo, sin música y con la voz clara. No recortes una condición ni una negación.", "purpose": "Dar una respuesta breve y completa, de hasta 20 segundos."},
    SHOTS[2],
)


def shots_for(recipe):
    return SPOKEN_SHOTS if recipe == "spoken_answer" else SHOTS


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ShootInput(Strict):
    request_id: UUID
    pack_id: str = Field(min_length=1, max_length=64)
    expected_revision: int = Field(ge=1)
    recipe: Literal["product_process_montage", "spoken_answer"] = "product_process_montage"


class Segment(Strict):
    shot_id: Literal["detail", "process", "finish"]
    asset_id: str = Field(min_length=1, max_length=64)
    source_in: int = Field(ge=0, le=30000)
    source_out: int = Field(ge=1, le=30000)
    timeline_start: int = Field(ge=0, le=32000)
    focal_x: float = Field(default=0.5, ge=0, le=1)
    focal_y: float = Field(default=0.5, ge=0, le=1)
    audio_mode: Literal["preserve_natural_sound", "mute"] = "preserve_natural_sound"


class SpeechBinding(Strict):
    transcript_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(ge=0, le=100)
    reviewed: Literal[True]
    size: Literal[40, 48, 56] = 48


class Timeline(Strict):
    schema_version: Literal["1"] = "1"
    recipe: Literal["product_process_montage", "spoken_answer"] = "product_process_montage"
    time_unit: Literal["milliseconds"] = "milliseconds"
    shoot_id: str = Field(min_length=1, max_length=64)
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    fps: Literal[30] = 30
    clips: list[Segment] = Field(min_length=3, max_length=3)
    music_asset_id: None = None
    captions: list = Field(default_factory=list, max_length=0)
    speech: SpeechBinding | None = None

    @model_validator(mode="after")
    def sequence(self):
        if [c.shot_id for c in self.clips] != [s["id"] for s in SHOTS]:
            raise ValueError("all_three_shots_in_recipe_order_required")
        end = 0
        for c in self.clips:
            maximum = 20000 if self.recipe == "spoken_answer" and c.shot_id == "process" else 6000
            if c.timeline_start != end or not 500 <= c.source_out - c.source_in <= maximum:
                raise ValueError("invalid_edit_range_or_gap")
            end += c.source_out - c.source_in
        if end > (32000 if self.recipe == "spoken_answer" else 18000):
            raise ValueError("montage_duration_limit")
        if len({c.asset_id for c in self.clips}) != 3:
            raise ValueError("three_distinct_takes_required")
        if (self.recipe == "spoken_answer") != (self.speech is not None):
            raise ValueError("spoken_answer_requires_reviewed_transcript")
        if self.speech and self.clips[1].audio_mode != "preserve_natural_sound":
            raise ValueError("spoken_answer_audio_required")
        return self


class VideoRenderInput(Strict):
    request_id: UUID
    expected_revision: int = Field(ge=1)
    timeline: Timeline
    confirmed: Literal[True]
