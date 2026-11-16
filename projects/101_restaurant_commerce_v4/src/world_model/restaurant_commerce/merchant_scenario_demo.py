"""Explicit, additive local demo scenario. Never called during normal app startup."""

import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from .campaign_demo import BUSINESS
from .campaign_email import VERSION
from .campaign_models import (
    Campaign,
    CampaignApproval,
    CampaignEvent,
    CampaignJob,
    CampaignOrderCredit,
    CampaignRevision,
    CampaignSettings,
    CampaignVisit,
)
from .campaigns import Draft, canonical, digest
from .customer_signup_models import CustomerAccount, CustomerMembership
from .models import Customer, Order, OrderItem, Payment
from .refunds import PaymentRefund

PREFIX = "merchant-scenario-v1"
SOURCE = canonical({"source": PREFIX, "synthetic": True})


def key(value):
    return str(uuid5(NAMESPACE_URL, PREFIX + ":" + str(value)))


def enrich(app, *, as_of=None):
    """Add once; retries never shift history or overwrite user-edited demo records."""
    if not app.state.demo_mode or app.state.environment not in {
        "development",
        "internal",
    }:
        raise ValueError("Only an explicitly local demo can receive this scenario")
    anchor = as_of or datetime.now(UTC)
    if anchor.tzinfo is None:
        raise ValueError("as_of requires a timezone")
    anchor = anchor.astimezone(ZoneInfo("America/Bogota"))
    with app.state.session_factory() as s:
        settings = s.get(CampaignSettings, BUSINESS)
        if (
            not settings
            or settings.scope != "test"
            or not s.get(Customer, "workspace-demo-00000")
        ):
            raise ValueError("Expected the existing synthetic workspace fixture")
        if s.get(Customer, key("customer-0")):
            return {"added": False, "source": PREFIX}
        first = [
            "Laura",
            "Juan",
            "Daniela",
            "Manuel",
            "Sara",
            "Diego",
            "Natalia",
            "Felipe",
            "Juliana",
            "Carlos",
            "Andrea",
            "Pablo",
            "María",
            "Julián",
            "Ana",
            "Esteban",
            "Clara",
            "Simón",
            "Luisa",
            "Gabriel",
        ]
        last = ["Mendoza", "Cárdenas", "Salcedo", "Ospina", "Vélez", "Pardo"]
        customers = []
        for i in range(120):
            created = anchor - timedelta(days=100 - i * 99 / 119)
            c = Customer(
                id=key(f"customer-{i}"),
                business_id=BUSINESS,
                name=f"{first[i % 20]} {last[i // 20]}",
                email=f"visita{i + 1}@example.test",
                created_at=created,
                updated_at=created,
            )
            s.add(c)
            s.flush()
            if i % 4 != 3:
                account = CustomerAccount(
                    id=key(f"account-{i}"),
                    channel="email",
                    identifier=c.email,
                    scope="test",
                    verified_at=created,
                )
                s.add(account)
                s.flush()
                s.add(
                    CustomerMembership(
                        account_id=account.id,
                        business_id=BUSINESS,
                        customer_id=c.id,
                        source=["qr", "website", "direct"][i % 3],
                        created_at=created,
                    )
                )
            customers.append(c)
        menu = [
            ("Hamburguesa clásica", 26900),
            ("Sándwich de pollo", 23900),
            ("Hamburguesa de champiñones", 28900),
            ("Papas rústicas", 8900),
            ("Limonada natural", 6500),
        ]
        orders = []
        counter = 0
        for day in range(90, -1, -1):
            count = 6 if day == 0 else 3 + (day % 4)
            for j in range(count):
                at = (
                    (anchor - timedelta(minutes=8 + (5 - j) * 7))
                    if day == 0
                    else (anchor - timedelta(days=day)).replace(
                        hour=12 + j, minute=13 + (j * 7) % 40, second=0, microsecond=0
                    )
                )
                eligible = [c for c in customers if c.created_at <= at]
                c = eligible[(counter * 7 + j) % len(eligible)]
                state = (
                    [
                        "placed",
                        "accepted",
                        "preparing",
                        "ready",
                        "awaiting_payment",
                        "placed",
                    ][j]
                    if day == 0
                    else ("cancelled" if counter % 23 == 0 else "completed")
                )
                paid = state not in {"cancelled", "awaiting_payment"}
                items = [menu[counter % 3], menu[3], menu[4]]
                qty = 2 if counter % 3 == 0 else 1
                subtotal = sum(price * qty for _, price in items)
                discount = 4000 if counter % 9 == 0 else 0
                full_refund = paid and day > 0 and counter % 37 == 0
                order = Order(
                    id=key(f"order-{counter}"),
                    public_code=f"D-{4101 + counter}",
                    business_id=BUSINESS,
                    customer_id=c.id,
                    customer_snapshot_json=canonical(
                        {
                            "name": c.name,
                            "email": c.email,
                            "identity_verified": False,
                            "synthetic": True,
                        }
                    ),
                    status=state,
                    payment_status="refunded"
                    if full_refund
                    else "paid"
                    if paid
                    else "unpaid",
                    subtotal_minor=subtotal,
                    discount_minor=discount,
                    promotion_discount_minor=discount,
                    total_minor=subtotal - discount,
                    currency="COP",
                    prep_minutes=20,
                    source_channel="web",
                    external_source_ref=PREFIX,
                    notes="Sin cebolla, por favor."
                    if counter % 13 == 0
                    else "Empacar las bebidas por separado."
                    if counter % 17 == 0
                    else None,
                    created_at=at,
                    accepted_at=at + timedelta(minutes=2)
                    if state in {"accepted", "preparing", "ready", "completed"}
                    else None,
                    ready_at=at + timedelta(minutes=18)
                    if state in {"ready", "completed"}
                    else None,
                    completed_at=at + timedelta(minutes=26)
                    if state == "completed"
                    else None,
                )
                s.add(order)
                s.flush()
                for name, price in items:
                    s.add(
                        OrderItem(
                            order_id=order.id,
                            name_snapshot=name,
                            quantity=qty,
                            unit_base_price_minor=price,
                            line_total_minor=price * qty,
                        )
                    )
                payment = Payment(
                    id=key(f"payment-{counter}"),
                    order_id=order.id,
                    provider="simulated",
                    provider_reference=key(f"payment-{counter}"),
                    status="refunded" if full_refund else "paid" if paid else "pending",
                    amount_minor=order.total_minor,
                    currency="COP",
                    raw_status_json=SOURCE,
                    created_at=at,
                    updated_at=at,
                )
                s.add(payment)
                s.flush()
                if paid and not full_refund and counter % 19 == 0:
                    s.add(
                        PaymentRefund(
                            payment_id=payment.id,
                            provider="simulated",
                            reference=key(f"refund-{counter}"),
                            amount_minor=6500,
                            evidence_json=SOURCE,
                        )
                    )
                c.last_order_at = at
                orders.append(order)
                counter += 1
        config = json.loads(settings.config_json)
        campaigns = [
            (
                65,
                "Tu próxima cena, lista para recoger",
                "Elige tu hamburguesa, acompáñala con papas y pasa a recoger tu pedido.",
                "scheduled",
            ),
            (
                35,
                "Una cena para compartir",
                "Dos hamburguesas, papas y limonada. Haz tu pedido para recogerlo a la hora que prefieras.",
                "scheduled",
            ),
            (
                5,
                "¿Cena en casa este fin de semana?",
                "Pide tus favoritos y recógelos recién preparados.",
                "scheduled",
            ),
            (
                2,
                "Vuelve por tus favoritos",
                "Estamos preparando la próxima invitación para quienes ya nos visitaron.",
                "draft",
            ),
            (
                1,
                "El almuerzo del viernes",
                "Hamburguesa clásica, papas y limonada para tu pausa del viernes.",
                "approved",
            ),
        ]
        for n, (days, subject, body, state) in enumerate(campaigns):
            at = (anchor - timedelta(days=days)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            audience = [c for c in customers if c.created_at <= at][:60]
            due = at if state == "scheduled" else anchor + timedelta(days=2 + n)
            doc = Draft(
                sender="demostracion@example.test",
                content={
                    "subject": subject,
                    "title": subject,
                    "body": body,
                    "terms": "Contenido y productos ficticios para esta demostración.",
                },
                customer_ids=[c.id for c in audience],
                scheduled_at=due,
                expires_at=due + timedelta(days=7),
                scope="test",
                budget_microusd=0,
            ).model_dump(mode="json")
            doc.update(
                recipients=[
                    {
                        "id": c.id,
                        "name": c.name,
                        "destination": c.email,
                        "duplicate_destination": False,
                        "snapshot_eligible": False,
                        "snapshot_reasons": ["synthetic_history_only"],
                    }
                    for c in audience
                ],
                brand=config["brand"],
                renderer=VERSION,
                provider="simulated_email",
                unit_cost_microusd=0,
                attribution_window_days=7,
                policy_version="co-marketing-v1",
                audience_rule="explicit-existing-customers-v1",
            )
            campaign = Campaign(
                id=key(f"campaign-{n}"),
                business_id=BUSINESS,
                state=state,
                created_at=at,
            )
            s.add(campaign)
            s.flush()
            revision = CampaignRevision(
                id=key(f"revision-{n}"),
                campaign_id=campaign.id,
                document=canonical(doc),
                digest=digest(canonical(doc)),
                created_at=at,
            )
            s.add(revision)
            s.flush()
            campaign.revision_id = revision.id
            if state != "draft":
                s.add(
                    CampaignApproval(
                        revision_id=revision.id,
                        actor_id=PREFIX,
                        digest=revision.digest,
                        scope="test",
                        approved_at=at,
                    )
                )
            if state != "scheduled":
                continue
            for i, c in enumerate(audience):
                job = CampaignJob(
                    id=key(f"job-{n}-{i}"),
                    business_id=BUSINESS,
                    revision_id=revision.id,
                    customer_id=c.id,
                    destination=c.email,
                    channel="email",
                    scope="test",
                    state="accepted",
                    provider="simulated_email",
                    provider_id=key(f"provider-{n}-{i}"),
                    attempts=1,
                    due_at=at,
                    submitted_at=at,
                    tracking_token=key(f"track-{n}-{i}"),
                    unsubscribe_token=key(f"unsubscribe-{n}-{i}"),
                )
                s.add(job)
                s.flush()
                if i % 11:
                    s.add(
                        CampaignEvent(
                            id=key(f"event-{n}-{i}"),
                            job_id=job.id,
                            kind="delivered",
                            provider_at=at + timedelta(minutes=1),
                            received_at=at + timedelta(minutes=1),
                            evidence_json=SOURCE,
                        )
                    )
                matching = next(
                    (
                        o
                        for o in orders
                        if o.customer_id == c.id
                        and o.payment_status == "paid"
                        and at + timedelta(hours=1)
                        < o.created_at
                        < at + timedelta(days=7)
                    ),
                    None,
                )
                if i % 7 != 0:
                    matching = None
                if matching or i % 5 == 0:
                    visit = CampaignVisit(
                        id=key(f"visit-{n}-{i}"),
                        token_hash=key(f"token-{n}-{i}"),
                        job_id=job.id,
                        at=matching.created_at - timedelta(minutes=4)
                        if matching
                        else at + timedelta(hours=1),
                        scanner=False,
                        evidence_json=SOURCE,
                    )
                    s.add(visit)
                    s.flush()
                    if matching:
                        s.add(
                            CampaignOrderCredit(
                                order_id=matching.id,
                                revision_id=revision.id,
                                visit_id=visit.id,
                                rule="last-eligible-visit-7d-v1",
                                scope="test",
                            )
                        )
        s.commit()
        return {
            "added": True,
            "source": PREFIX,
            "as_of": anchor.isoformat(),
            "customers": len(customers),
            "orders": len(orders),
            "campaigns": len(campaigns),
        }
