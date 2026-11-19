"""Customer appearance only; canonical cart, prices, identity and payment remain untouched."""

# ruff: noqa: B008 -- FastAPI dependency declarations
import json
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import ForeignKey, String, Text, Integer, inspect, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .models import Base, RestaurantCommerceProfile

CONTRACT = json.loads((Path(__file__).parent / "web/checkout-contract.json").read_text())
TABLES = frozenset({"restaurant_checkout_designs"})


class CheckoutDesign(Base):
    __tablename__ = "restaurant_checkout_designs"
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


def numeric_model(name, rules):
    return create_model(
        name,
        __base__=Strict,
        **{
            key: (float | None, Field(default=None, ge=bounds[0], le=bounds[1]))
            for key, bounds in rules.items()
        },
    )


Geometry = numeric_model("CheckoutGeometry", CONTRACT["geometry"])
Typography = create_model(
    "CheckoutTypography",
    __base__=numeric_model("CheckoutTypeSizes", CONTRACT["typography"]),
    bodyFont=(Literal["inter", "system"] | None, None),
    headingFont=(Literal["inter", "system"] | None, None),
)
Colors = create_model(
    "CheckoutColors",
    __base__=Strict,
    **{
        key: (str | None, Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$"))
        for key in CONTRACT["colors"]
    },
)


class Surface(Strict):
    radius: float | None = Field(default=None, ge=0, le=999)
    fill: str | None = Field(default=None, pattern=r"^(#[a-fA-F0-9]{6}|transparent)$")
    borderWidth: float | None = Field(default=None, ge=0, le=12)
    borderColor: str | None = Field(default=None, pattern=r"^#[a-fA-F0-9]{6}$")
    padding: float | None = Field(default=None, ge=0, le=96)
    marginTop: float | None = Field(default=None, ge=0, le=128)
    marginBottom: float | None = Field(default=None, ge=0, le=128)
    shadow: Literal["none", "soft"] | None = None


Surfaces = create_model(
    "CheckoutSurfaces",
    __base__=Strict,
    **{key: (Surface | None, None) for key in CONTRACT["surfaces"]},
)


class Bones(Strict):
    surfaces: Surfaces = Field(default_factory=Surfaces)


class Profile(Strict):
    schema_version: Literal["1"]
    layout: Literal["sidebar", "stacked"]
    geometry: Geometry = Field(default_factory=Geometry)
    typography: Typography = Field(default_factory=Typography)
    colors: Colors = Field(default_factory=Colors)
    bones: Bones = Field(default_factory=Bones)


class SaveDesign(Strict):
    expected_revision: int = Field(ge=0)
    profile: Profile


def ready(session):
    return TABLES <= set(inspect(session.get_bind()).get_table_names())


def upgrade_checkout_design(engine):
    """Explicit additive offline migration. Rollback disables writes; retain saved designs."""
    Base.metadata.create_all(engine, tables=[CheckoutDesign.__table__])


def read(session, business):
    if session.get(RestaurantCommerceProfile, business) is None:
        raise HTTPException(404, "Negocio no encontrado")
    installed = ready(session)
    row = session.get(CheckoutDesign, business) if installed else None
    return {
        "business_id": business,
        "revision": row.revision if row else 0,
        "available": installed,
        "profile": json.loads(row.document) if row else CONTRACT["presets"]["source"],
    }


def register(app, get_session, scoped_staff):
    @app.get("/api/restaurants/{business_id}/checkout-design")
    def public_checkout_design(business_id: str, session: Session = Depends(get_session)):
        # No actor, customer, order, credential or unpublished content in this projection.
        result = read(session, business_id)
        return JSONResponse(
            {key: result[key] for key in ["business_id", "revision", "profile"]},
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/operator/restaurants/{business_id}/checkout-design")
    def checkout_design(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        scoped_staff(request, session, business_id, "operations.read")
        return {**read(session, business_id), "contract": CONTRACT}

    @app.put("/api/operator/restaurants/{business_id}/checkout-design")
    def save_checkout_design(
        business_id: str,
        body: SaveDesign,
        request: Request,
        session: Session = Depends(get_session),
    ):
        principal = scoped_staff(request, session, business_id, "settings.write")
        current = read(session, business_id)
        if not current["available"]:
            raise HTTPException(503, "Falta instalar el almacenamiento del diseño")
        document = body.profile.model_dump_json(exclude_none=True)
        actor = str(principal.actor_id)
        if body.expected_revision == 0:
            session.add(
                CheckoutDesign(
                    business_id=business_id, revision=1, document=document, actor_id=actor
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "El diseño cambió. Recarga antes de guardar.") from None
        else:
            changed = session.execute(
                update(CheckoutDesign)
                .where(
                    CheckoutDesign.business_id == business_id,
                    CheckoutDesign.revision == body.expected_revision,
                )
                .values(revision=body.expected_revision + 1, document=document, actor_id=actor)
            )
            if changed.rowcount != 1:
                session.rollback()
                raise HTTPException(409, "El diseño cambió. Recarga antes de guardar.")
            session.commit()
        return read(session, business_id)
