"""Constrained editable portrait scenes. No HTML, commands, remote fonts or code."""

from __future__ import annotations

import hashlib
import io
import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, ConfigDict, Field, model_validator
from reportlab.pdfbase.ttfonts import TTFont

VERSION = "social-canvas-v1"
WIDTH, HEIGHT, SAFE = 1080, 1350, 48
FONT_ID = "inter-regular-v1"
FONT_PATH = Path(__file__).parent / "web" / "report-inter.ttf"
FONT_HASH = "b9cf0ffbbdc5fc5181d61649bdafc12a0c367eea4959a1e97bab4513324b80bd"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rect(Strict):
    x: int = Field(ge=0, le=1080)
    y: int = Field(ge=0, le=1350)
    width: int = Field(ge=32, le=1080)
    height: int = Field(ge=32, le=1350)


class TextLayer(Rect):
    id: Literal["headline", "detail", "price"]
    fact_id: str = Field(min_length=1, max_length=64)
    size: int = Field(ge=24, le=100)
    line_height: float = Field(default=1.2, ge=1.05, le=1.6)
    tracking: int = Field(default=0, ge=0, le=3)
    align: Literal["left", "center", "right"] = "left"


class Styles(Strict):
    background: str = Field(default="#F5F1E9", pattern=r"^#[0-9a-fA-F]{6}$")
    foreground: str = Field(default="#27272B", pattern=r"^#[0-9a-fA-F]{6}$")
    font_id: Literal["inter-regular-v1"] = FONT_ID


class Canvas(Strict):
    width: Literal[1080] = WIDTH
    height: Literal[1350] = HEIGHT


class Design(Strict):
    schema_version: Literal["1"] = "1"
    preset_version: Literal["1"] = "1"
    layout: Literal["photo_only", "photo_first", "information"]
    canvas: Canvas = Field(default_factory=Canvas)
    styles: Styles = Field(default_factory=Styles)
    photo: Rect
    layers: list[TextLayer] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def unique_roles(self):
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_text_layer")
        if self.layout == "photo_only" and self.layers:
            raise ValueError("photo_only_has_no_text")
        if self.layout != "photo_only" and "headline" not in ids:
            raise ValueError("headline_required")
        return self


def violation(code, role="canvas"):
    raise HTTPException(422, "design:" + role + ":" + code)


def presets():
    """One shared server preset definition; editor loads these instead of duplicating geometry."""

    def text(role, x, y, w, h, size):
        return dict(
            id=role,
            fact_id="",
            x=x,
            y=y,
            width=w,
            height=h,
            size=size,
            line_height=1.2,
            tracking=0,
            align="left",
        )

    common = dict(
        schema_version="1",
        preset_version="1",
        canvas=dict(width=WIDTH, height=HEIGHT),
        styles=Styles().model_dump(),
    )
    return {
        "photo_only": {
            **common,
            "layout": "photo_only",
            "photo": dict(x=0, y=0, width=1080, height=1350),
            "layers": [],
        },
        "photo_first": {
            **common,
            "layout": "photo_first",
            "photo": dict(x=0, y=0, width=1080, height=860),
            "layers": [
                text("headline", 64, 912, 952, 144, 56),
                text("detail", 64, 1078, 952, 116, 30),
                text("price", 64, 1230, 952, 64, 44),
            ],
        },
        "information": {
            **common,
            "layout": "information",
            "photo": dict(x=72, y=548, width=936, height=528),
            "layers": [
                text("headline", 72, 80, 936, 192, 72),
                text("detail", 72, 320, 936, 176, 34),
                text("price", 72, 1168, 936, 104, 48),
            ],
        },
    }


def font_record():
    if not FONT_PATH.is_file() or hashlib.sha256(FONT_PATH.read_bytes()).hexdigest() != FONT_HASH:
        violation("font_missing_or_changed")
    return {
        "id": FONT_ID,
        "family": "Inter",
        "style": "Regular",
        "weight": 400,
        "sha256": FONT_HASH,
        "source": "existing monthly_report_pdf.py bundled report-inter.ttf",
        "license": "SIL-OFL-1.1",
        "license_reference": "INTER-LICENSE.txt",
        "file_reference": "urn:101:font:" + FONT_HASH,
        "included_in_export": False,
    }


@lru_cache(maxsize=1)
def glyphs():
    font_record()
    return frozenset(TTFont("SocialInter", str(FONT_PATH)).face.charToGlyph)


@lru_cache(maxsize=50)
def font(size):
    font_record()
    return ImageFont.truetype(str(FONT_PATH), size)


def contrast(foreground, background):
    def luminance(color):
        rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    a, b = sorted([luminance(foreground), luminance(background)])
    return (b + 0.05) / (a + 0.05)


def intersects(a, b):
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def measure(value, face, tracking):
    if not value:
        return 0
    if tracking:
        pen = 0
        left = 0
        right = 0
        for char in value:
            box = face.getbbox(char)
            left = min(left, pen + box[0])
            right = max(right, pen + box[2])
            pen += face.getlength(char) + tracking
        return max(right, pen - tracking) - left
    box = face.getbbox(value)
    return max(face.getlength(value), box[2]) - min(0, box[0])


def wrap(value, spec):
    value = unicodedata.normalize("NFC", value)
    if not value.strip() or any(
        (ord(c) < 32 and c not in "\n\t") or (not c.isspace() and ord(c) not in glyphs())
        for c in value
    ):
        violation("unsupported_character", spec.id)
    face = font(spec.size)
    lines = []
    for paragraph in value.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = (current + " " + word).strip()
            if measure(candidate, face, spec.tracking) <= spec.width:
                current = candidate
            else:
                if not current or measure(word, face, spec.tracking) > spec.width:
                    violation("text_overflow", spec.id)
                lines.append(current)
                current = word
        lines.append(current)
    step = round(spec.size * spec.line_height)
    # Anchor at the glyph's visible top rather than the font's baseline offset.
    height = max(face.getbbox(line or "A")[3] - face.getbbox(line or "A")[1] for line in lines)
    if (len(lines) - 1) * step + height > spec.height:
        violation("text_overflow", spec.id)
    return [
        {"text": line, "width": round(measure(line, face, spec.tracking), 3), "top": index * step}
        for index, line in enumerate(lines)
    ]


def compile_scene(brief, original):
    spec = brief.design
    if spec is None:
        return None
    spec = Design.model_validate(spec)
    photo = spec.photo.model_dump()
    if photo["x"] + photo["width"] > WIDTH or photo["y"] + photo["height"] > HEIGHT:
        violation("out_of_bounds", "photo")
    if spec.layout == "photo_only" and photo != presets()["photo_only"]["photo"]:
        violation("photo_only_full_canvas", "photo")
    with Image.open(io.BytesIO(original)) as source:
        if source.width * source.height > 24_000_000:
            violation("pixel_limit", "photo")
        image = ImageOps.exif_transpose(source)
        w, h = image.size
    scale = max(photo["width"] / w, photo["height"] / h)
    if scale > 1:
        violation("source_resolution", "photo")
    crop_w, crop_h = photo["width"] / scale, photo["height"] / scale
    crop = [(w - crop_w) * brief.focal_x, (h - crop_h) * brief.focal_y]
    crop += [crop[0] + crop_w, crop[1] + crop_h]
    texts = []
    boxes = []
    facts = {f.id: f for f in brief.facts}
    if spec.layers and contrast(spec.styles.foreground, spec.styles.background) < 4.5:
        violation("contrast")
    for layer in spec.layers:
        box = {k: getattr(layer, k) for k in ("x", "y", "width", "height")}
        if (
            min(layer.x, layer.y) < SAFE
            or layer.x + layer.width > WIDTH - SAFE
            or layer.y + layer.height > HEIGHT - SAFE
        ):
            violation("safe_region", layer.id)
        if intersects(box, photo) or any(intersects(box, b) for b in boxes):
            violation("overlap", layer.id)
        fact = facts.get(layer.fact_id)
        if fact is None:
            violation("unresolved_fact", layer.id)
        # Content is derived from the exact confirmed fact, not separately editable pixels.
        lines = wrap(fact.text, layer)
        texts.append(
            {
                **layer.model_dump(),
                "type": "text",
                "text": unicodedata.normalize("NFC", fact.text),
                "font_id": spec.styles.font_id,
                "color": spec.styles.foreground,
                "lines": lines,
            }
        )
        boxes.append(box)
    record = font_record() if texts else None
    scene = {
        "schema_version": "1",
        "renderer": VERSION,
        "pillow_version": Image.__version__,
        "canvas": spec.canvas.model_dump(),
        "layout": spec.layout,
        "preset_version": spec.preset_version,
        "styles": spec.styles.model_dump(),
        "safe_inset": SAFE,
        "fonts": [record] if record else [],
        "layers": [
            {"id": "background", "type": "solid", "color": spec.styles.background},
            {
                "id": "photo",
                "type": "photo",
                **photo,
                "asset_id": brief.asset_id,
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "source_dimensions": [w, h],
                "crop": crop,
                "focal_point": [brief.focal_x, brief.focal_y],
                "orientation": "exif_transposed",
                "alpha_policy": "composite_over_background",
            },
            *texts,
        ],
    }
    scene["sha256"] = hashlib.sha256(
        json.dumps(scene, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return scene


def draw_scene(original, scene):
    # Only compiled, source-bound scenes enter here; no caller strings become code.
    canvas = Image.new("RGB", (WIDTH, HEIGHT), scene["styles"]["background"])
    photo = scene["layers"][1]
    if hashlib.sha256(original).hexdigest() != photo["source_sha256"]:
        violation("source_changed", "photo")
    with Image.open(io.BytesIO(original)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image = image.resize(
            (photo["width"], photo["height"]), Image.Resampling.LANCZOS, box=tuple(photo["crop"])
        )
        canvas.paste(image, (photo["x"], photo["y"]), image.getchannel("A"))
    painter = ImageDraw.Draw(canvas)
    for layer in scene["layers"][2:]:
        face = font(layer["size"])
        for line in layer["lines"]:
            x = (
                layer["x"]
                + (
                    {
                        "left": 0,
                        "center": (layer["width"] - line["width"]) / 2,
                        "right": layer["width"] - line["width"],
                    }[layer["align"]]
                )
            )
            y = layer["y"] + line["top"]
            if not line["text"]:
                continue
            bbox = face.getbbox(line["text"])
            x -= min(0, bbox[0])
            # Glyph bearings are included in overflow checks; keep all visible ink in its box.
            if layer["tracking"]:
                for char in line["text"]:
                    painter.text((x, y - bbox[1]), char, font=face, fill=layer["color"])
                    x += face.getlength(char) + layer["tracking"]
            else:
                painter.text((x, y - bbox[1]), line["text"], font=face, fill=layer["color"])
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=94, subsampling=0)
    with Image.open(io.BytesIO(out.getvalue())) as decoded:
        decoded.load()
        if decoded.size != (WIDTH, HEIGHT):
            violation("export_dimensions")
    return out.getvalue()


def changes(previous, current):
    """Readable semantic differences; version/history stays in the existing revision table."""
    changed = []
    if previous is None:
        return ["initial"]
    if previous["caption"] != current["caption"]:
        changed.append("caption")
    a, b = previous.get("design"), current.get("design")
    for field in ("asset_id", "focal_x", "focal_y"):
        if previous["brief"].get(field) != current["brief"].get(field):
            changed.append("photo." + field)
    if bool(a) != bool(b):
        changed.append("composition")
    if a and b:
        for key in ("layout", "styles", "canvas"):
            if a[key] != b[key]:
                changed.append(key)
        before = {layer["id"]: layer for layer in a["layers"]}
        for layer in b["layers"]:
            old = before.pop(layer["id"], None)
            if old != layer:
                if layer["type"] == "text":
                    if not old or old.get("text") != layer["text"]:
                        changed.append("text." + layer["id"])
                    if not old or any(
                        old.get(k) != layer.get(k)
                        for k in [
                            "x",
                            "y",
                            "width",
                            "height",
                            "size",
                            "tracking",
                            "align",
                            "line_height",
                        ]
                    ):
                        changed.append("layout." + layer["id"])
                elif layer["type"] == "photo":
                    changed.append("photo.frame_or_source")
        changed.extend("removed." + key for key in before)
    return list(dict.fromkeys(changed)) or ["brief_or_review"]
