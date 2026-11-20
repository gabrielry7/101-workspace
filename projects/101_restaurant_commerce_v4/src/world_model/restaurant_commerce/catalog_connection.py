"""Source-backed local test catalog -> existing Menu/MenuItem and checkout owners."""

# ruff: noqa: B008
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, Integer, String, Text, inspect, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .models import Base, Menu, MenuCategory, MenuItem, RestaurantCommerceProfile

TABLES = frozenset({"restaurant_catalog_connections"})


class CatalogConnection(Base):
    __tablename__ = "restaurant_catalog_connections"
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Product(Strict):
    ref: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    price_minor: int = Field(gt=0, le=1000000000)
    source_ref: str = Field(min_length=1, max_length=500)
    source_price: str = Field(pattern=r"^\d{1,7}(,\d{1,2})?$")


class Catalog(Strict):
    schema_version: Literal["1"] = "1"
    scope: Literal["test"] = "test"
    currency: Literal["COP"] = "COP"
    location_id: str = Field(min_length=1, max_length=64)
    source_url: str = Field(pattern=r"^https://[^\s]{1,1000}$")
    source_published_at: str = Field(min_length=10, max_length=40)
    observed_at: str = Field(min_length=10, max_length=40)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    unit_multiplier: Literal[1000] = 1000
    unit_confirmation: str = Field(min_length=1, max_length=300)
    current_price_confirmed: Literal[False] = False
    current_availability_confirmed: Literal[False] = False
    products: list[Product] = Field(min_length=1, max_length=250)


class Import(Strict):
    expected_revision: int = Field(ge=0)
    catalog: Catalog


def stable_id(business, kind, ref=""):
    return str(uuid5(NAMESPACE_URL, f"101:source-catalog:{business}:{kind}:{ref}"))


def installed(session):
    return TABLES <= set(inspect(session.get_bind()).get_table_names())


def upgrade_catalog_connection(engine):
    Base.metadata.create_all(engine, tables=[CatalogConnection.__table__])


def context(session, business):
    if not installed(session):
        return None
    row = session.get(CatalogConnection, business)
    if row is None:
        return None
    data = json.loads(row.document)
    return {
        "schema_version": "1",
        "scope": "test",
        "revision": row.revision,
        "source_sha256": data["source_sha256"],
        "source_published_at": data["source_published_at"],
        "price_basis": "archived_menu_with_user_confirmed_COP_thousands",
        "current_price_confirmed": False,
        "current_availability_confirmed": False,
        "products": [
            {"ref": p["ref"], "menu_item_id": stable_id(business, "product", p["ref"])}
            for p in data["products"]
        ],
    }


def import_catalog(session, business, body: Import, *, actor="operator"):
    if not installed(session):
        raise HTTPException(503, "Falta instalar la conexión de catálogo")
    profile = session.get(RestaurantCommerceProfile, business)
    if profile is None:
        raise HTTPException(404, "Negocio no encontrado")
    if profile.payment_provider != "simulated" or profile.currency != "COP":
        raise HTTPException(
            409, "Este importador solo prepara catálogos de prueba con pagos simulados"
        )
    catalog = body.catalog
    if len({p.ref for p in catalog.products}) != len(catalog.products):
        raise HTTPException(422, "Referencias duplicadas")
    # A price interpretation is explicit data, not an LLM guess or a confirmed current price.
    from decimal import Decimal, InvalidOperation

    for product in catalog.products:
        try:
            observed = Decimal(product.source_price.replace(",", ".")) * catalog.unit_multiplier
        except InvalidOperation:
            raise HTTPException(422, "Precio de origen no interpretable") from None
        if observed != product.price_minor:
            raise HTTPException(422, "El precio no coincide con la escala confirmada")
    row = session.scalar(
        select(CatalogConnection).where(CatalogConnection.business_id == business).with_for_update()
    )
    if row and row.source_sha256 == catalog.source_sha256:
        if json.loads(row.document)["products"] != catalog.model_dump()["products"]:
            raise HTTPException(409, "La misma fuente tiene un mapeo diferente")
        return context(session, business)  # Never reset operator stock/price corrections on replay.
    if (row.revision if row else 0) != body.expected_revision:
        raise HTTPException(409, "El catálogo cambió")
    if row is not None:
        raise HTTPException(
            409,
            "Una nueva fuente requiere revisión de conciliación; no se sobrescribe automáticamente",
        )
    menu_id = stable_id(business, "menu")
    if session.get(Menu, menu_id):
        raise HTTPException(409, "El catálogo existente necesita revisión")
    session.add(Menu(id=menu_id, business_id=business, name="Carta de prueba · fuente archivada"))
    session.flush()
    categories = {}
    for index, product in enumerate(catalog.products):
        if product.category not in categories:
            category = MenuCategory(
                id=stable_id(business, "category", product.category),
                menu_id=menu_id,
                name=product.category,
                display_order=len(categories),
            )
            session.add(category)
            session.flush()
            categories[product.category] = category.id
        session.add(
            MenuItem(
                id=stable_id(business, "product", product.ref),
                category_id=categories[product.category],
                name=product.name,
                description=(
                    "Producto del catálogo archivado. "
                    "Precio y disponibilidad actuales por confirmar."
                ),
                base_price_minor=product.price_minor,
                currency="COP",
                image_url=None,
                display_order=index,
            )
        )
    document = catalog.model_dump()
    document["imported_by"] = actor
    document["imported_at"] = datetime.now(UTC).isoformat()
    session.add(
        CatalogConnection(
            business_id=business,
            revision=1,
            document=json.dumps(document, ensure_ascii=False, sort_keys=True),
            source_sha256=catalog.source_sha256,
        )
    )
    session.commit()
    return context(session, business)


def register(app, get_session, scoped_staff):
    @app.get("/api/restaurants/{business_id}/catalog-connection")
    def public_catalog_connection(business_id: str, session: Session = Depends(get_session)):
        profile = session.get(RestaurantCommerceProfile, business_id)
        if profile is None:
            raise HTTPException(404, "Negocio no encontrado")
        value = context(session, business_id)
        return {"connected": bool(value), "business_id": business_id, "context": value}

    @app.put("/api/operator/restaurants/{business_id}/catalog-connection")
    def save_catalog_connection(
        business_id: str, body: Import, request: Request, session: Session = Depends(get_session)
    ):
        principal = scoped_staff(request, session, business_id, "settings.write")
        if not app.state.demo_mode:
            raise HTTPException(409, "La conexión de catálogo de prueba está desactivada")
        from sqlalchemy.exc import IntegrityError

        try:
            result = import_catalog(session, business_id, body, actor=principal.actor_id)
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "El catálogo cambió; revisa la conexión actual") from None
        app.state.storefront_cache.invalidate(business_id)
        return result
