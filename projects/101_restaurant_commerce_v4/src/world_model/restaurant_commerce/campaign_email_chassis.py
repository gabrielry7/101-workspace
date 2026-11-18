"""Email-safe projection of 101 bones; never campaign content or action destinations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Surface(Strict):
    radius: float | None = Field(default=None, ge=0, le=96)
    fill: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    borderWidth: float | None = Field(default=None, ge=0, le=4)
    borderColor: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    padding: float | None = Field(default=None, ge=0, le=64)
    marginTop: float | None = Field(default=None, ge=0, le=96)
    marginBottom: float | None = Field(default=None, ge=0, le=96)
    shadow: Literal["none", "soft"] | None = None


class Surfaces(Strict):
    card: Surface | None = None
    stage: Surface | None = None
    panel: Surface | None = None
    brand: Surface | None = None
    intro: Surface | None = None
    content: Surface | None = None
    photo: Surface | None = None
    controls: Surface | None = None
    footer: Surface | None = None


class Colors(Strict):
    heading: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    intro: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    action: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    date: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    brand: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")


class Bones(Strict):
    shape: Literal["recipe", "square", "soft", "round"] = "recipe"
    surfaces: Surfaces = Field(default_factory=Surfaces)
    colors: Colors = Field(default_factory=Colors)


class TextStyle(Strict):
    fontFamily: (
        Literal[
            "Inter",
            "Arial",
            "Georgia",
            "Instrument Serif",
            "IBM Plex Sans Condensed",
            "IBM Plex Mono",
            "Geist",
        ]
        | None
    ) = None
    fontSize: float | None = Field(default=None, ge=12, le=72)
    fontWeight: Literal[400, 500, 600] | None = None
    lineHeight: float | None = Field(default=None, ge=1, le=2)
    letterSpacing: float | None = Field(default=None, ge=-1, le=4)
    textTransform: Literal["none", "uppercase"] | None = None
    color: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")


class Typography(Strict):
    heading: TextStyle | None = None
    body: TextStyle | None = None
    label: TextStyle | None = None
    action: TextStyle | None = None
    meta: TextStyle | None = None


class Geometry(Strict):
    maxWidth: int | None = Field(default=None, ge=320, le=800)
    logoWidth: int | None = Field(default=None, ge=48, le=240)


class EmailChassis(Strict):
    schema_version: Literal["1"]
    coat: Literal["source", "neutral"] = "source"
    geometry: Geometry = Field(default_factory=Geometry)
    bones: Bones = Field(default_factory=Bones)
    typography: Typography = Field(default_factory=Typography)
