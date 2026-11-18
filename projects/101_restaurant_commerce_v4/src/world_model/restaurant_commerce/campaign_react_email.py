"""Versioned React Email JSON subprocess boundary; orchestration and SES stay in Python."""

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .campaign_email_chassis import EmailChassis

TemplateId = Literal["legacy", "classic", "barebone", "matte", "protocol", "arcane", "studio"]
RUNTIME = Path(__file__).parent / "email_runtime"
NAMES = {
    "legacy": "Clásico anterior",
    "classic": "Clásico",
    "barebone": "Barebone",
    "matte": "Matte",
    "protocol": "Protocol",
    "arcane": "Arcane",
    "studio": "Studio",
}


def absolute_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20]", value):
        raise ValueError("email_url_invalid")
    parsed = urlsplit(value)
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("email_url_invalid")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("email_url_https_required")
    return value


class EmailDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: TemplateId = "legacy"
    image_url: str | None = Field(default=None, max_length=2048)
    image_alt: str = Field(default="", max_length=200)
    cta_label: str = Field(default="Ver la carta y pedir →", min_length=1, max_length=80)
    chassis: EmailChassis | None = None

    @field_validator("image_url")
    @classmethod
    def image(cls, v):
        if v is not None:
            absolute_url(v)
            if not urlsplit(v).path.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                raise ValueError("email_image_format_unsupported")
        return v

    @model_validator(mode="after")
    def image_description(self):
        if self.template_id == "legacy" and self.chassis is not None:
            raise ValueError("legacy_has_no_chassis")
        if self.image_url and not self.image_alt.strip():
            raise ValueError("email_image_description_required")
        for value in (self.image_alt, self.cta_label):
            if re.search(r"[\x00-\x1f]", value):
                raise ValueError("email_text_invalid")
        return self


def runtime_manifest(version=2):
    try:
        manifest = json.loads(
            (RUNTIME / ("manifest.json" if version == 1 else "manifest-v2.json")).read_text()
        )
        bundle_hash = hashlib.sha256(
            (RUNTIME / ("renderer.cjs" if version == 1 else "renderer-v2.cjs.gz")).read_bytes()
        ).hexdigest()
        if bundle_hash != manifest["bundle_sha256"]:
            raise ValueError("artifact_changed")
        for name, digest in manifest["assets"].items():
            if (
                Path(name).name != name
                or hashlib.sha256((RUNTIME / "fonts" / name).read_bytes()).hexdigest() != digest
            ):
                raise ValueError("font_asset_changed")
        joined = "|".join(k + ":" + v for k, v in manifest["assets"].items())
        metadata = manifest.get("metadata", {})
        for name, digest in metadata.items():
            if (
                Path(name).name != name
                or hashlib.sha256((RUNTIME / name).read_bytes()).hexdigest() != digest
            ):
                raise ValueError("metadata_changed")
        joined += "|".join(k + ":" + v for k, v in metadata.items())
        if (
            hashlib.sha256((bundle_hash + joined).encode()).hexdigest()
            != manifest["renderer_sha256"]
        ):
            raise ValueError("renderer_manifest_changed")
        return manifest
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "email_renderer_unavailable") from None


def node_command(version=2):
    executable = os.environ.get("CAMPAIGN_EMAIL_NODE") or shutil.which("node")
    if not executable or not Path(executable).is_file() or not os.access(executable, os.X_OK):
        raise HTTPException(503, "email_renderer_unavailable")
    return [
        executable,
        "--max-old-space-size=192",
        str(RUNTIME / ("renderer.cjs" if version == 1 else "renderer-v2-loader.cjs")),
    ]


def renderer_version(version=2):
    node_command(version)
    return "react-email-v" + str(version) + ":" + runtime_manifest(version)["renderer_sha256"]


def bind(design):
    value = EmailDesign.model_validate(design).model_dump()
    if value["chassis"] is None:
        value.pop("chassis")
    else:
        value["chassis"] = EmailChassis.model_validate(value["chassis"]).model_dump(
            exclude_none=True
        )
    if value["template_id"] == "legacy":
        return None
    return {**value, "template_version": "2"}


def compatible(document):
    from .campaign_email import VERSION

    if not document.get("email_design"):
        return document.get("renderer") == VERSION
    try:
        design = document["email_design"]
        version = int(design.get("template_version", "0"))
        return (
            version in {1, 2}
            and design.get("template_id") in runtime_manifest(version)["templates"]
            and document.get("renderer") == renderer_version(version)
        )
    except (HTTPException, ValueError, TypeError):
        return False


def catalog():
    try:
        version = renderer_version()
    except HTTPException:
        version = None
    return {
        "templates": [
            {"id": k, "name": v, "available": k == "legacy" or version is not None}
            for k, v in NAMES.items()
        ],
        "renderer": version,
        "chassis": json.loads((RUNTIME / "chassis.json").read_text()) if version else None,
    }


def render(document, recipient, ordering_url, unsubscribe_url):
    if not compatible(document):
        raise HTTPException(409, "renderer_revision_changed")
    design = document["email_design"]
    version = int(design["template_version"])
    origin = document.get("email_origin", "http://127.0.0.1:8799")
    try:
        absolute_url(origin)
        ordering_url = absolute_url(urljoin(origin + "/", ordering_url))
        unsubscribe_url = absolute_url(urljoin(origin + "/", unsubscribe_url))
        brand = document["brand"]
        logo = brand.get("logo_url")
        if not logo and re.fullmatch(r"/assets/[a-z0-9-]+\.png", brand.get("logo_path") or ""):
            logo = urljoin(origin, brand["logo_path"])
        if logo:
            absolute_url(logo)
        inputs = {
            "schema_version": "1",
            "font_base_url": origin.rstrip("/") + "/assets/email-fonts/",
            "template_id": design["template_id"],
            "content": {
                **document["content"],
                "cta_label": design["cta_label"],
                "expiry": datetime.fromisoformat(document["expires_at"].replace("Z", "+00:00"))
                .astimezone(ZoneInfo("America/Bogota"))
                .strftime("%d/%m/%Y %H:%M · Bogotá"),
                "label": "DEMOSTRACIÓN · SIN ENVÍO REAL"
                if document["scope"] == "test"
                else "NOVEDADES DE LA CASA",
            },
            "brand": {
                "name": brand["name"],
                "logo_url": logo,
                "accent": brand.get("accent"),
                "font": brand.get("font"),
            },
            "media": {"url": design["image_url"], "alt": design["image_alt"]}
            if design.get("image_url")
            else None,
            "personalization": {
                "name": recipient.get("name") or "amigo de la casa",
                "ordering_url": ordering_url,
                "unsubscribe_url": unsubscribe_url,
            },
        }
        if version == 2:
            inputs["chassis"] = design.get("chassis")
        raw = json.dumps(inputs, ensure_ascii=False).encode()
        if len(raw) > 131072:
            raise ValueError("input_limit")
        result = subprocess.run(
            node_command(version),
            input=raw,
            capture_output=True,
            timeout=12,
            check=False,
            cwd=RUNTIME,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        )
        if result.returncode or len(result.stdout) > 2_000_000:
            raise ValueError("renderer_failed")
        output = json.loads(result.stdout)
        if (
            output.get("schema_version") != "1"
            or output.get("template_id") != design["template_id"]
            or output.get("subject") != document["content"]["subject"]
            or not all(isinstance(output.get(k), str) and output[k] for k in ("html", "text"))
        ):
            raise ValueError("renderer_contract")
        return {key: output[key] for key in ("html", "text", "subject")}
    except HTTPException:
        raise
    except (OSError, ValueError, subprocess.SubprocessError, KeyError, TypeError):
        # Never log submitted content, personalize outside the service, or silently swap a design.
        raise HTTPException(503, "email_render_failed") from None


def preview_selected(
    session, business, campaign_id, template_id, *, origin="http://127.0.0.1:8799"
):
    from . import campaigns as c
    from .campaign_email import VERSION
    from .campaign_email import render as render_any
    from .campaign_models import CampaignRevision

    campaign = c.scoped_campaign(session, business, campaign_id)
    revision = session.get(CampaignRevision, campaign.revision_id)
    document = json.loads(revision.document)
    if document["channel"] != "email":
        raise HTTPException(422, "email_design_requires_email_channel")
    document.setdefault("email_origin", origin)
    original = document.get("email_design", {})
    value = EmailDesign.model_validate(
        {
            **{k: v for k, v in original.items() if k != "template_version"},
            "template_id": template_id,
        }
    )
    selected = bind(value.model_dump())
    if selected:
        document.update(email_design=selected, renderer=renderer_version())
    else:
        document.pop("email_design", None)
        document["renderer"] = VERSION
    recipient = next(
        (r for r in document["recipients"] if r.get("snapshot_eligible")), document["recipients"][0]
    )
    email = render_any(document, recipient, "#preview-ordering-link", "#preview-unsubscribe")
    return {**email, "template_id": template_id, "saved": False, "campaign_digest": revision.digest}
