"""Merchant launch context and source-backed catalog editing over existing owners."""

# ruff: noqa: B008
from urllib.parse import urlencode

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .catalog_connection import CatalogConnection
from .catalog_connection import context as catalog_context
from .models import Menu, MenuCategory, MenuItem, RestaurantCommerceProfile


class PriceEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=1)
    price_minor: int = Field(gt=0, le=1_000_000_000)


def catalog_items(session, business):
    return list(
        session.scalars(
            select(MenuItem)
            .join(MenuCategory)
            .join(Menu)
            .where(Menu.business_id == business)
            .order_by(MenuCategory.display_order, MenuItem.display_order, MenuItem.id)
        )
    )


def describe(app, session, business):
    profile = session.get(RestaurantCommerceProfile, business)
    if not profile:
        raise HTTPException(404, "Negocio no encontrado")
    spec = getattr(app.state, "merchant_workspaces", {}).get(business, {})
    demo = bool(getattr(app.state, "offline_demo", False) and spec.get("mode") == "demo")
    source = catalog_context(session, business)

    def link(area, **extra):
        return "/workspace/" + area + "?" + urlencode({"business": business, **extra})

    signup = bool(getattr(app.state, "signup_options", {}).get("adapters"))
    channels = [
        i["adapter"].name
        for i in getattr(app.state, "campaign_options", {}).get("integrations", {}).values()
        if i["business_id"] == business and i["scope"] == "test"
    ]
    return {
        "business_id": business,
        "configured": bool(spec),
        "mode": "demo" if demo else "standard",
        "no_money": demo,
        "external_actions": not bool(getattr(app.state, "offline_demo", False)),
        "store_url": spec.get("store_url") or "/r/" + profile.slug,
        "catalog_url": link("website", section="catalog"),
        "signup_url": "/join/" + business,
        "web_analytics": (
            "demo_samples"
            if getattr(app.state, "demo_mode", False)
            and (
                spec.get("web_analytics") == "demo_samples"
                or getattr(app.state, "monthly_report_demo_business", None) == business
            )
            else "platform"
            if getattr(app.state, "merchant_analytics_available", lambda _: False)(business)
            else "unconfigured"
        ),
        "catalog_count": len(catalog_items(session, business)),
        "source_current": False if source else None,
        "modules": [
            {
                "title": "Tienda y productos",
                "state": "demo" if source and demo else "available",
                "detail": "Carta, precios de prueba, existencias y checkout.",
                "href": link("website"),
            },
            {
                "title": "Pedidos",
                "state": "demo" if demo else "available",
                "detail": "Aceptar, preparar y entregar; pagos simulados en esta demo.",
                "href": link("sales"),
            },
            {
                "title": "Clientes y fidelización",
                "state": "demo" if signup and demo else "needs_setup",
                "detail": "Registro, consentimiento, compras y programa de prueba.",
                "href": link("customers"),
            },
            {
                "title": "Campañas",
                "state": "demo" if channels else "needs_setup",
                "detail": "Correo, WhatsApp y SMS simulados; sin mensajes reales."
                if channels
                else "Configura un canal antes de enviar.",
                "href": link("campaigns"),
            },
            {
                "title": "Contenido",
                "state": "available",
                "detail": "Fotos, propuestas, revisión y exportación. Cuentas por conectar.",
                "href": link("social"),
            },
            {
                "title": "Resultados",
                "state": "available",
                "detail": "Pedidos y pagos de prueba; medición web aún por conectar."
                if demo
                else "Resultados y cobertura disponibles.",
                "href": link("reports"),
            },
        ],
        "activation_gates": [
            "Confirmar precios, disponibilidad y condiciones actuales con el negocio.",
            "Aprobar identidad, material y contenido para publicación real.",
            "Configurar y validar cobros reales; esta demo no permite activarlos.",
            "Conectar cuentas y canales autorizados; la simulación no acredita acceso.",
            "Validar consentimiento, mensajes y operación de entrega antes de activarlos.",
            "Publicar en un dominio estable y verificar medición y recuperación.",
        ]
        if demo
        else [],
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/workspace"

    @app.get(root + "/context")
    def merchant_context(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        scoped_staff(request, session, business_id, "operations.read")
        return describe(app, session, business_id)

    @app.get(root + "/catalog")
    def catalog(business_id: str, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, "operations.read")
        source = catalog_context(session, business_id)
        return {
            "editable": bool(source),
            "revision": source["revision"] if source else 0,
            "currency": session.get(RestaurantCommerceProfile, business_id).currency,
            "archived_source": source,
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price_minor": p.base_price_minor,
                    "sold_out": p.sold_out,
                    "enabled": p.enabled,
                }
                for p in catalog_items(session, business_id)
            ],
        }

    @app.put(root + "/catalog/{item_id}")
    def edit_price(
        business_id: str,
        item_id: str,
        body: PriceEdit,
        request: Request,
        session: Session = Depends(get_session),
    ):
        scoped_staff(request, session, business_id, "settings.write")
        profile = session.get(RestaurantCommerceProfile, business_id)
        if not getattr(app.state, "demo_mode", False) or profile.payment_provider != "simulated":
            raise HTTPException(409, "La edición de este catálogo requiere la tienda de prueba")
        source = catalog_context(session, business_id)
        if not source or item_id not in {p.id for p in catalog_items(session, business_id)}:
            raise HTTPException(404, "Producto no encontrado")
        result = session.execute(
            update(CatalogConnection)
            .where(
                CatalogConnection.business_id == business_id,
                CatalogConnection.revision == body.expected_revision,
            )
            .values(revision=CatalogConnection.revision + 1)
        )
        if result.rowcount != 1:
            raise HTTPException(409, "La carta cambió. Actualiza antes de guardar.")
        item = session.get(MenuItem, item_id)
        item.base_price_minor = body.price_minor
        session.commit()
        app.state.storefront_cache.invalidate(business_id)
        return {
            "id": item.id,
            "price_minor": item.base_price_minor,
            "revision": body.expected_revision + 1,
            "current_price_confirmed": False,
        }
