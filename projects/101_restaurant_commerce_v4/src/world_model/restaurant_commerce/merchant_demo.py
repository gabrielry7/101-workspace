"""Explicit money-free merchant composition over the ordinary workspace/services.

No provider credentials are loaded. Existing customer/operator edits are never
reseeded. Example contacts/permissions/orders are labeled and scoped test records.
"""

import json
from datetime import timedelta
from hashlib import sha256
from urllib.parse import urlsplit

from sqlalchemy import select

from .api import create_app
from .campaign_delivery import FakeTransport
from .campaign_models import Campaign, CampaignSettings, SmsSender, WhatsAppSender
from .campaigns import Draft, canonical, save_draft, set_permission
from .catalog_connection import context as catalog_context
from .catalog_connection import stable_id
from .customer_signup_delivery import FakePhoneVerifier
from .models import Customer, Order, RestaurantCommerceProfile, StaffAccount, utcnow
from .sms_delivery import FakeSmsTransport
from .staff import provision
from .whatsapp_delivery import FakeWhatsAppTransport

DEMO_PASSWORD = "explicit-local-merchant-demonstration-only"


def demo_time():
    # Explicit test clock, not a claim about merchant hours or a live calendar.
    value = utcnow().replace(hour=17, minute=0, second=0, microsecond=0)
    return value + timedelta(days=1) if value.weekday() == 6 else value


def seed(session, business, name, *, username, origin):
    from . import sms, whatsapp

    profile = session.get(RestaurantCommerceProfile, business)
    if (
        not profile
        or profile.payment_provider != "simulated"
        or not catalog_context(session, business)
    ):
        raise RuntimeError("Enroll a source-backed simulated catalog before opening this workspace")
    cfg = session.get(CampaignSettings, business)
    if cfg and cfg.scope != "test":
        raise RuntimeError("The selected merchant is not configured for simulated campaigns")
    now = demo_time()
    if cfg is not None:
        from .campaigns import date

        now = date(json.loads(cfg.config_json).get("simulation_clock", now.isoformat()))
    if cfg is None:
        profile.display_name = name
        profile.cash_at_pickup_enabled = False
        profile.loyalty_enabled = True
        profile.marketing_automation_enabled = False
        profile.review_requests_enabled = False
        session.add(
            CampaignSettings(
                business_id=business,
                scope="test",
                config_json=canonical(
                    {
                        "sender": "demo@example.test",
                        "frequency_hours": 24,
                        "brand": {
                            "name": name,
                            "tone": "Claro y cercano; dirección de prueba por revisar.",
                            "examples": [],
                            "facts": [],
                            "images": [],
                            "provenance": "Local rehearsal; no approved offers or current claims.",
                        },
                        "simulation_clock": now.isoformat(),
                        "holidays": {str(now.year): []},
                        "holiday_source": "Synthetic calendar; not activation evidence.",
                    }
                ),
            )
        )
        session.flush()
    # Deterministic IDs, explicit fake contacts and test-only permission evidence.
    customers = []
    for index, label in enumerate(
        ["Ana · cliente de prueba", "Luis · cliente de prueba", "Sin permiso · cliente de prueba"]
    ):
        identifier = stable_id(business, "demo-customer", str(index))
        customer = session.get(Customer, identifier)
        if customer is None:
            customer = Customer(
                id=identifier,
                business_id=business,
                name=label,
                phone=f"+5730055599{index:02d}",
                email=f"demo{index}@example.test",
            )
            session.add(customer)
            session.flush()
            for channel in ["email", "whatsapp", "sms"]:
                set_permission(
                    session,
                    business,
                    identifier,
                    channel=channel,
                    scope="test",
                    state="granted" if index < 2 else "unknown",
                    source="synthetic:merchant-demo",
                    registry={
                        "state": "clear",
                        "scope": "test",
                        "source": "synthetic registry; not a real consent/registry check",
                        "expires_at": (now + timedelta(days=30)).isoformat(),
                    },
                    now=now,
                )
        customers.append(customer)
    suffix = str(int(sha256(business.encode()).hexdigest()[:12], 16))
    expires = (now + timedelta(days=30)).isoformat()
    if not session.get(WhatsAppSender, business):
        whatsapp.configure(
            session,
            business,
            whatsapp.SenderInput(
                phone_id="101" + suffix,
                waba_id="202" + suffix,
                version="v23.0",
                display_phone="+573005550199",
                support_owner=username,
                link_origin=origin,
                status="READY",
                quality="GREEN",
                allowance=1000,
                source="Synthetic sender; not Meta verification",
                expires_at=expires,
                unit_cost_microusd=0,
            ),
            now,
        )
        whatsapp.put_template(
            session,
            business,
            whatsapp.TemplateInput(
                provider_id="303" + suffix,
                name="prueba_de_campana",
                language="es",
                category="MARKETING",
                status="APPROVED",
                body="Hola {{1}}. {{2}}",
                footer="Responde BAJA para retirar tu permiso.",
                source="Synthetic template; not Meta approval",
                expires_at=expires,
            ),
            now,
        )
    if not session.get(SmsSender, business):
        sms.configure(
            session,
            business,
            sms.SenderInput(
                account_sid="AC" + "1" * 32,
                sender="+15555550199",
                route="international_long_code",
                link_origin=origin,
                status="READY",
                inbound_supported=True,
                delivery_receipts="available",
                max_segments=10,
                unit_cost_microusd=0,
                source="Synthetic route; no Twilio activation",
                expires_at=expires,
            ),
            now,
        )
    if not session.scalar(select(Campaign.id).where(Campaign.business_id == business)):
        save_draft(
            session,
            business,
            Draft(
                channel="email",
                sender="demo@example.test",
                content={
                    "subject": "Una campaña de prueba",
                    "title": "Un saludo de " + name,
                    "body": "Revisa el mensaje y destinatarios. No se enviará fuera de la demo.",
                    "terms": "Demostración: no hay una oferta vigente ni un envío real.",
                },
                customer_ids=[c.id for c in customers],
                scheduled_at=now,
                expires_at=now + timedelta(days=7),
                scope="test",
                budget_microusd=0,
            ),
            now,
        )
    session.commit()
    if not session.scalar(select(StaffAccount).where(StaffAccount.username == username)):
        provision(
            session, username, DEMO_PASSWORD, business, "manager", actor="explicit-merchant-demo"
        )
    return customers


def app_for_demo(
    database_url,
    *,
    business,
    name,
    store_url,
    origin="http://localhost:8831",
    username="merchant.demo",
    examples=True,
):
    address = urlsplit(store_url)
    if (
        address.scheme != "http"
        or address.hostname not in {"localhost", "127.0.0.1"}
        or address.username
        or address.password
    ):
        raise ValueError("The local demo store must use a loopback HTTP address")
    suffix = str(int(sha256(business.encode()).hexdigest()[:12], 16))
    integrations = {
        business + "-email": {"business_id": business, "scope": "test", "adapter": FakeTransport()},
        business + "-whatsapp": {
            "business_id": business,
            "scope": "test",
            "adapter": FakeWhatsAppTransport(phone_id="101" + suffix, waba_id="202" + suffix),
        },
        business + "-sms": {
            "business_id": business,
            "scope": "test",
            "adapter": FakeSmsTransport(origin=origin),
        },
    }
    clock = {"now": demo_time()}
    options = {"integrations": integrations, "clock": lambda: clock["now"], "base_url": origin}
    app = create_app(
        database_url=database_url,
        demo_mode=True,
        offline_demo=True,
        environment="development",
        campaign_options=options,
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
        loyalty_configuration_enabled=True,
        loyalty_analytics_enabled=True,
        signup_options={
            "mode": "test",
            "public_origin": origin,
            "adapters": {
                "phone": FakePhoneVerifier(),
                "email": FakePhoneVerifier("email-demo-only"),
            },
            "allowed_regions": ["CO", "US", "MX", "ES"],
        },
    )
    app.state.campaign_options = options
    app.state.merchant_workspaces[business] = {"mode": "demo", "store_url": store_url}
    with app.state.session_factory() as session:
        customers = seed(session, business, name, username=username, origin=origin)
        from .campaigns import date

        clock["now"] = date(
            json.loads(session.get(CampaignSettings, business).config_json).get(
                "simulation_clock", demo_time().isoformat()
            )
        )
        if examples:
            seed_orders(session, business, customers)
            seed_loyalty(session, business)
    app.state.workspace_demo_login = (username, DEMO_PASSWORD)
    return app


def seed_orders(session, business, customers):
    from .schemas import CreateOrderRequest
    from .service import RestaurantCommerceService

    item = catalog_context(session, business)["products"][0]["menu_item_id"]
    service = RestaurantCommerceService(session)
    for index, customer in enumerate(customers[:2]):
        key = "merchant-demo-order-v1-" + str(index)
        if session.scalar(
            select(Order.id).where(Order.business_id == business, Order.idempotency_key == key)
        ):
            continue
        order = service.create_order(
            business,
            CreateOrderRequest.model_validate(
                {
                    "customer": {"name": customer.name, "phone": customer.phone},
                    "items": [{"menu_item_id": item, "quantity": 1}],
                    "payment_provider": "simulated",
                    "idempotency_key": key,
                    "source_channel": "merchant_demo",
                }
            ),
        )
        service.apply_payment_status(order.payments[0].provider_reference, "paid")
        if index == 0:
            for state in ["accepted", "preparing", "ready", "completed"]:
                service.transition_order(order.id, state)


def seed_loyalty(session, business):
    from .loyalty_config import LoyaltyConfigurationService
    from .loyalty_models import LoyaltyStrategy
    from .loyalty_schemas import StrategyCreate

    if session.scalar(select(LoyaltyStrategy.id).where(LoyaltyStrategy.business_id == business)):
        return
    config = LoyaltyConfigurationService(session, "explicit-local-demo")
    config.create(
        "programs",
        business,
        StrategyCreate.model_validate(
            {
                "request_key": "merchant-demo-program-v1",
                "document": {
                    "name": "Puntos · programa de prueba",
                    "description": "Borrador de prueba; no es un beneficio vigente.",
                    "currency": "COP",
                    "earning": {
                        "type": "points",
                        "spend_minor_per_point": 1000,
                        "points_per_unit": 1,
                    },
                    "reward": {"type": "fixed_value", "points_cost": 20, "discount_minor": 1000},
                    "maximum_reward_minor": 1000,
                    "per_customer_budget_minor": 10000,
                    "campaign_budget_minor": 100000,
                    "estimated_cost_per_point_minor": 10,
                    "expiration_days": 30,
                },
            }
        ),
    )


def prepare_social_example(app, business, photo, *, source):
    """Use ordinary authorized API contracts; keep archive/demo material explicitly fixture-only.

    This confirms only the running demo's no-charge behavior, never current merchant
    products, prices, availability or media publication rights. No approval is seeded.
    """
    import asyncio
    import base64

    import httpx

    from .social_design import presets
    from .social_production import Asset, Pack

    with app.state.session_factory() as session:
        profile = session.get(RestaurantCommerceProfile, business)
        if profile is None:
            raise RuntimeError("Demo sample needs an enrolled merchant")
        name = profile.display_name
        if session.scalar(select(Pack.id).where(Pack.business_id == business)):
            return "existing_work"
        assets = list(session.scalars(select(Asset).where(Asset.business_id == business)))
        own = [
            asset
            for asset in assets
            if not asset.revoked
            and json.loads(asset.metadata_json).get("fixture") is True
            and json.loads(asset.metadata_json).get("sha256") == sha256(photo).hexdigest()
            and json.loads(asset.metadata_json)
            .get("rights_statement", "")
            .startswith("User-authorized local test from archive.")
        ]
        if assets and not own:
            # Never recreate deleted/revoked material or replace owner work.
            return "existing_material"
        existing_asset = own[0].id if own else None

    async def prepare():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://merchant-demo.local"
        ) as client:
            response = await client.post(
                "/api/staff/login",
                headers={"X-101-Login": "1"},
                json={"username": "101", "password": "101"},
            )
            response.raise_for_status()
            me = (await client.get("/api/staff/me")).json()
            headers = {"X-101-CSRF": me["csrf"]}
            root = "/api/operator/restaurants/" + business + "/social"
            asset = existing_asset
            if asset is None:
                response = await client.post(
                    root + "/uploads",
                    headers=headers,
                    json={
                        "total": len(photo),
                        "sha256": sha256(photo).hexdigest(),
                        "media_kind": "photo",
                        "permitted_use": "production",
                        "rights_statement": (
                            "User-authorized local test from archive. "
                            "No commercial publication rights asserted. " + source
                        ),
                        "expires_at": (utcnow() + timedelta(days=30)).isoformat(),
                        "fixture": True,
                    },
                )
                response.raise_for_status()
                upload = response.json()["id"]
                for offset in range(0, len(photo), 192 * 1024):
                    response = await client.put(
                        root + "/uploads/" + upload,
                        headers=headers,
                        json={
                            "offset": offset,
                            "data_base64": base64.b64encode(
                                photo[offset : offset + 192 * 1024]
                            ).decode(),
                        },
                    )
                    response.raise_for_status()
                response = await client.post(
                    root + "/uploads/" + upload + "/complete", headers=headers
                )
                response.raise_for_status()
                asset = response.json()["id"]
            expiry = (utcnow() + timedelta(days=30)).isoformat()
            design = presets()["photo_first"]
            design["layers"] = design["layers"][:2]
            for layer in design["layers"]:
                layer["fact_id"] = layer["id"]
            facts = [
                {
                    "id": key,
                    "text": text,
                    "source": "Running offline demo; not a commercial claim.",
                    "valid_until": expiry,
                }
                for key, text in [
                    ("headline", name + " en demo."),
                    ("detail", "Sin cobros ni envíos reales."),
                ]
            ]
            response = await client.post(
                root + "/packs",
                headers=headers,
                json={
                    "request_id": stable_id(business, "demo-social-pack"),
                    "asset_id": asset,
                    "objective": "Practicar revisión y exportación de contenido.",
                    "hypothesis": "Ejemplo de prueba; no demuestra rendimiento comercial.",
                    "question": "¿Cómo funciona esta demostración?",
                    "question_source": "owner_suggestion",
                    "question_evidence": "User requested a connected demo without real money.",
                    "facts": facts,
                    "caption_fact_ids": ["headline", "detail"],
                    "design": design,
                    "brand_direction": "Foto real y texto legible; ejemplo interno por revisar.",
                    "reference_reason": "Local archive prototype; no merchant approval.",
                    "primary_measure": "owner_effort",
                    "confirmed": True,
                },
            )
            if response.status_code >= 400:
                raise RuntimeError("Demo content preparation blocked: " + response.text[:350])
            await client.post("/api/staff/logout", headers=headers)

    asyncio.run(prepare())
