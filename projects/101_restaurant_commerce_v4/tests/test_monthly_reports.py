from datetime import datetime, timezone
from io import BytesIO
import json
import pytest
from sqlalchemy import select
from pypdf import PdfReader
from test_sales_workspace import env, factory, BUSINESS, OTHER
from world_model.restaurant_commerce.monthly_reports import month_period, previous, MonthlyReport
from world_model.restaurant_commerce.models import Order, Payment, StaffMembership
from world_model.restaurant_commerce.refunds import PaymentRefund

ROOT = f"/api/operator/restaurants/{BUSINESS}/reports"


def generate(env, **kw):
    csrf = env.client.get("/api/staff/me").json()["csrf"]
    return env.client.post(ROOT, params={"month": "2026-10", **kw}, headers={"X-101-CSRF": csrf})


def test_month_boundaries():
    now = datetime(2027, 1, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(Exception):
        month_period("2026-12", "America/Bogota", now)
    assert previous("2026-01") == "2025-12"
    p = month_period("2024-02", "America/Bogota", datetime(2024, 3, 2, tzinfo=timezone.utc))
    assert p["end"].isoformat() == "2024-03-01T05:00:00+00:00"
    p = month_period("2026-03", "America/New_York", datetime(2026, 4, 2, tzinfo=timezone.utc))
    assert p["start"].hour == 5 and p["end"].hour == 4


def test_saved_pdf_refunds_scopes_and_authority(env, tmp_path):
    # Disposable fixture, never alter retained runtime data.
    with env.factory() as s:
        orders = list(s.scalars(select(Order).where(Order.business_id == BUSINESS)))
        for order in orders:
            order.created_at = datetime(2026, 10, 15, tzinfo=timezone.utc)
        payments = list(
            s.scalars(
                select(Payment)
                .join(Order)
                .where(Order.business_id == BUSINESS, Payment.status.in_(["paid", "refunded"]))
            )
        )
        for payment in payments:
            if payment.provider == "simulated":
                payment.provider = "fixture_online"
        s.commit()
        confirmed = [p for p in payments if p.provider not in {"simulated", "cash_at_pickup"}]
        expected_captured = sum(p.amount_minor for p in confirmed)
        expected_refunds = sum(
            p.amount_minor
            if p.status == "refunded"
            else sum(
                s.scalars(
                    select(PaymentRefund.amount_minor).where(PaymentRefund.payment_id == p.id)
                )
            )
            for p in confirmed
        )
        expected_count = len({p.order_id for p in confirmed})
    r = generate(env)
    assert r.status_code == 200, r.text
    d = r.json()
    v = d["periods"][0]["sales"]
    assert v["net"] == expected_captured - expected_refunds
    assert v["paid_orders"] == expected_count
    assert d["periods"][1]["sales"]["net"] is None
    assert d["periods"][0]["website"]["status"] == "disconnected"
    assert generate(env).json()["id"] == d["id"]
    sales = env.client.get(
        f"/api/operator/restaurants/{BUSINESS}/sales",
        params={"status": "all", "date_from": "2026-10-01", "date_to": "2026-10-31"},
    ).json()
    assert next(x for x in sales["money"] if x["scope"] == "provider")["net"] == v["net"]
    pdf = env.client.get(ROOT + "/" + d["id"] + "/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["cache-control"] == "no-store"
    reader = PdfReader(BytesIO(pdf.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "2026-10" in text and "2026-09" in text and "Ventas en línea" in text
    (tmp_path / "report.pdf").write_bytes(pdf.content)
    with env.factory() as s:
        p = s.get(Payment, confirmed[0].id)
        p.status = "refunded"
        s.commit()
    newer = generate(env).json()
    assert newer["id"] != d["id"]
    assert env.client.get(ROOT + "/" + d["id"]).json()["periods"][0]["sales"] == v
    assert env.client.get(ROOT.replace(BUSINESS, OTHER) + "/" + d["id"] + "/pdf").status_code == 403
    assert env.client.get(ROOT + "/unknown/pdf").status_code == 404
    assert env.client.post(ROOT, params={"month": "2026-10"}).status_code == 403
    with env.factory() as s:
        membership = s.scalar(
            select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
        )
        s.delete(membership)
        s.commit()
    assert env.client.get(ROOT + "/" + d["id"] + "/pdf").status_code == 403


def test_missing_zero_partial_and_failure(env):
    env.app.state.monthly_website_reader = lambda request, business, span: {
        "status": "partial",
        "values": {"visitors": 0, "visits": 0, "pageviews": 0},
        "note": "El seguimiento empezó el 12 de octubre.",
    }
    d = generate(env).json()
    assert d["periods"][0]["website"]["values"]["visitors"] == 0

    def fail(*args):
        raise TimeoutError()

    env.app.state.monthly_website_reader = fail
    d = generate(env).json()
    assert d["periods"][0]["website"]["status"] == "unavailable"
    assert d["periods"][0]["website"]["values"] == {}


@pytest.mark.parametrize("month", ["bad", "2026-99", "0001-01", "2026-11", "2027-01"])
def test_reject_invalid_or_unfinished_month(env, month):
    assert generate(env, month=month).status_code == 422


def test_campaign_paid_credit_and_cross_business_id(env):
    from world_model.restaurant_commerce.campaign_models import (
        Campaign,
        CampaignRevision,
        CampaignOrderCredit,
    )

    with env.factory() as s:
        order = s.scalar(select(Order).where(Order.business_id == BUSINESS))
        order.created_at = datetime(2026, 10, 12, tzinfo=timezone.utc)
        payment = Payment(
            order_id=order.id,
            provider="fixture_online",
            provider_reference="monthly-online",
            status="paid",
            currency="COP",
            amount_minor=10000,
        )
        s.add(payment)
        campaign = Campaign(id="monthly-campaign", business_id=BUSINESS, state="approved")
        s.add(campaign)
        s.flush()
        rev = CampaignRevision(
            id="monthly-revision",
            campaign_id=campaign.id,
            document=json.dumps({"scope": "live", "content": {"subject": "Campaña mensual"}}),
            digest="fixture",
        )
        s.add(rev)
        s.flush()
        campaign.revision_id = rev.id
        s.add(
            CampaignOrderCredit(order_id=order.id, revision_id=rev.id, scope="live", rule="fixture")
        )
        owner = s.scalar(select(StaffMembership).where(StaffMembership.business_id == BUSINESS))
        s.add(StaffMembership(account_id=owner.account_id, business_id=OTHER, role="viewer"))
        s.commit()
    d = generate(env).json()
    assert d["campaigns"][0]["current"]["net"] == 10000
    assert d["campaigns"][0]["current"]["paid_orders"] == 1
    assert d["campaigns"][0]["previous"]["net"] is None
    assert env.client.get(ROOT.replace(BUSINESS, OTHER) + "/" + d["id"] + "/pdf").status_code == 404
    with env.factory() as s:
        p = s.scalar(select(Payment).where(Payment.provider_reference == "monthly-online"))
        p.status = "pending"
        s.commit()
    assert generate(env).json()["campaigns"] == []


def test_dense_pdf_one_page(env):
    from world_model.restaurant_commerce.monthly_report_pdf import render

    d = generate(env).json()
    d["business_name"] = "Nombre muy largo del negocio con acentos áéíóú " * 5
    d["campaigns"] = [
        {
            "name": "Una campaña extensa con nombre verificable " * 3,
            "current": {"net": 50000, "paid_orders": 2},
            "previous": {"net": 10000, "paid_orders": 1},
        }
        for _ in range(6)
    ]
    assert len(PdfReader(BytesIO(render(d))).pages) == 1
