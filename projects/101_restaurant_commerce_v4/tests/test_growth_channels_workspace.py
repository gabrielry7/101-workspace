"""U07–U09 native reads/actions, canonical records and fake transports only."""

# ruff: noqa: F811 -- pytest fixtures
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select
from staff_helpers import staff_headers
from test_campaigns import approved  # noqa: F401
from test_campaigns import env as env
from test_campaigns import factory as factory
from world_model.restaurant_commerce import campaigns as c
from world_model.restaurant_commerce.campaign_demo import BUSINESS as BID
from world_model.restaurant_commerce.campaign_demo import (
    CLOCK,
    OTHER,
    app_for_demo,
    enable_sms_demo,
    enable_whatsapp_demo,
)
from world_model.restaurant_commerce.campaign_models import (
    CampaignJob,
    ContactPermission,
    ProviderTestReview,
    WhatsAppConversation,
    WhatsAppEvidence,
    WhatsAppReply,
)
from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.models import Customer, OutboundMessage, utcnow
from world_model.restaurant_commerce.schemas import (
    AutomationRuleCreateIn,
    PromotionCreateIn,
    RewardCreateIn,
)

ROOT = f"/api/operator/restaurants/{BID}"


@pytest.fixture(autouse=True)
def forbid_real_provider_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Real provider HTTP forbidden in fixture checks")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def seed_growth(session):
    growth = RestaurantGrowthService(session)
    if not growth.list_promotions(BID):
        growth.create_promotion(
            BID,
            PromotionCreateIn(
                code="SYNTHETIC10", name="Solo prueba", discount_type="percent", value=1000
            ),
        )
        growth.create_reward(
            BID, RewardCreateIn(name="Recompensa ficticia", points_cost=20, discount_minor=1000)
        )
        growth.create_rule(
            BID,
            AutomationRuleCreateIn(
                name="Regreso ficticio",
                trigger_kind="customer.winback",
                purpose="marketing",
                template_text="Hola {{name}}, invitación de prueba.",
            ),
        )
    for customer in session.scalars(select(Customer).where(Customer.business_id == BID)):
        customer.last_order_at = utcnow() - timedelta(days=90)
        customer.whatsapp_opt_in = customer.marketing_opt_in = True
        customer.whatsapp_verified_at = customer.marketing_verified_at = utcnow()
    session.commit()


def browser_app(database_url, base_url):
    app = app_for_demo(database_url, base_url=base_url)
    with app.state.session_factory() as session:
        for channel, enable in [("whatsapp", enable_whatsapp_demo), ("sms", enable_sms_demo)]:
            app.state.campaign_options["integrations"][channel] = enable(session, origin=base_url)
        seed_growth(session)
    return app


@pytest.fixture
def channels(env):
    with env.factory() as session:
        for channel, enable in [("whatsapp", enable_whatsapp_demo), ("sms", enable_sms_demo)]:
            env.options["integrations"][channel] = enable(session)
        seed_growth(session)
    return env


def customer_id(e):
    return next(
        p["id"]
        for p in e.client.get(ROOT + "/campaigns").json()["customers"]
        if p["email"] == "persona0@example.test"
    )


def inbound(e, text="Hola de prueba", key="native-inbound-one"):
    r = e.client.post(
        ROOT + "/whatsapp/simulate-inbound",
        json={"customer_id": customer_id(e), "text": text, "request_key": key},
        headers=e.headers,
    )
    assert r.status_code == 200, r.text
    return e.client.get(ROOT + "/channel-workspace/inbox").json()["items"][0]


def test_native_reads_are_scoped_and_never_plan_probe_or_send(channels):
    e = channels
    with e.factory() as session:

        def counts():
            return [
                session.scalar(select(func.count()).select_from(m))
                for m in [CampaignJob, WhatsAppReply, OutboundMessage, ProviderTestReview]
            ]

        before = counts()
        for path in [
            "/growth-workspace",
            "/growth-workspace/outbox",
            "/channel-workspace/inbox",
            "/whatsapp",
            "/sms",
            "/campaigns/provider-readiness",
            "/promotions",
            "/rewards",
        ]:
            r = e.client.get(ROOT + path)
            assert r.status_code == 200, r.text
            assert e.client.get(ROOT.replace(BID, OTHER) + path).status_code == 403
        assert counts() == before
    assert e.client.get(ROOT + "/channel-workspace/conversations/missing").status_code == 404
    assert e.client.get(ROOT + "/channel-workspace/inbox?limit=1000").status_code == 422


@pytest.mark.parametrize("channel", ["whatsapp", "sms"])
def test_sender_digest_blocks_stale_edits_without_saving_etag(channels, channel):
    e = channels
    value = e.client.get(ROOT + "/" + channel).json()
    body = {
        **value["sender"],
        "expected_digest": value["sender_digest"],
        "source": "Synthetic updated source",
    }
    r = e.client.put(ROOT + "/" + channel + "/sender", json=body, headers=e.headers)
    assert r.status_code == 200, r.text
    assert (
        "expected_digest" not in r.json()["sender"]
        and r.json()["sender_digest"] != value["sender_digest"]
    )
    assert (
        e.client.put(ROOT + "/" + channel + "/sender", json=body, headers=e.headers).status_code
        == 409
    )
    body.pop("expected_digest")
    assert (
        e.client.put(ROOT + "/" + channel + "/sender", json=body, headers=e.headers).status_code
        == 200
    )


def test_manual_plan_withdrawal_duplicate_and_handoff_are_distinct(channels):
    e = channels
    first = e.client.post(ROOT + "/winback/plan", json={"limit": 100}, headers=e.headers)
    assert first.status_code == 200, first.text
    rows = first.json()
    assert rows and any(r["status"] == "suppressed" for r in rows)
    again = e.client.post(ROOT + "/winback/plan", json={"limit": 100}, headers=e.headers)
    assert {r["id"] for r in again.json()} == {r["id"] for r in rows}
    ready = next(r for r in rows if r["customer_id"] == customer_id(e))
    path = "/api/operator/outbox/" + ready["id"] + "/handoff"
    r = e.client.post(path, headers=e.headers)
    assert (
        r.status_code == 200 and r.json()["status"] == "handed_off" and r.json()["sent_at"] is None
    )
    with e.factory() as session:
        c.set_permission(
            session,
            BID,
            ready["customer_id"],
            channel="whatsapp",
            scope="test",
            state="withdrawn",
            source="synthetic newer withdrawal",
            now=CLOCK,
        )
        session.commit()
    assert e.client.post(path, headers=e.headers).status_code == 422
    found = e.client.get(ROOT + "/growth-workspace/outbox").json()["items"]
    assert next(r for r in found if r["id"] == ready["id"])["status"] == "suppressed"
    assert (
        e.client.patch(
            "/api/operator/outbox/" + ready["id"] + "/sent", json={}, headers=e.headers
        ).status_code
        == 409
    )


def test_campaign_reply_dispatch_are_separate_and_replies_assign_actor(channels):
    e = channels
    convo = inbound(e)
    approved(e)
    with e.factory() as s:
        before_jobs = dict(s.execute(select(CampaignJob.id, CampaignJob.state)).all())
    target = ROOT + "/whatsapp/conversations/" + convo["id"] + "/reply"
    body = {"body": "Respuesta ficticia", "request_key": "native-reply-one"}
    r = e.client.post(target, json=body, headers=e.headers)
    assert r.status_code == 200, r.text
    assert e.client.post(target, json=body, headers=e.headers).json()["id"] == r.json()["id"]
    assert (
        e.client.post(ROOT + "/channel-workspace/simulate-replies", headers=e.headers).status_code
        == 200
    )
    d = e.client.get(ROOT + "/channel-workspace/conversations/" + convo["id"]).json()
    assert d["assigned_name"] == "campaign.manager" and d["replies"][0]["state"] == "accepted"
    with e.factory() as s:
        assert dict(s.execute(select(CampaignJob.id, CampaignJob.state)).all()) == before_jobs
    r = e.client.post(
        target,
        json={"body": "Segunda respuesta ficticia", "request_key": "native-reply-two"},
        headers=e.headers,
    )
    assert r.status_code == 200
    result = e.client.post(ROOT + "/campaigns/simulate/dispatch", headers=e.headers)
    assert result.status_code == 200 and result.json()["replies_processed"] == 0
    with e.factory() as s:
        assert s.get(WhatsAppReply, r.json()["id"]).state == "queued"


def test_window_stop_sms_help_and_readonly_permissions(channels):
    e = channels
    convo = inbound(e)
    target = ROOT + "/whatsapp/conversations/" + convo["id"] + "/reply"
    inbound(e, "BAJA", "native-stop-one")
    detail = e.client.get(ROOT + "/channel-workspace/conversations/" + convo["id"]).json()
    assert detail["opted_out"] and not detail["reply_allowed"]
    assert (
        e.client.post(
            target,
            json={"body": "No se puede", "request_key": "native-block-one"},
            headers=e.headers,
        ).status_code
        == 409
    )
    for text in ["STOP", "HELP", "Hola"]:
        assert (
            e.client.post(
                ROOT + "/sms/simulate-inbound",
                json={"customer_id": customer_id(e), "text": text},
                headers=e.headers,
            ).status_code
            == 200
        )
    result = e.client.get(ROOT + "/channel-workspace/inbox?channel=sms").json()
    assert result["count"] == 3 and all(
        r["document"]["provider_timestamp"] is None for r in result["items"]
    )
    with e.factory() as s:
        p = s.scalar(
            select(ContactPermission).where(
                ContactPermission.customer_id == customer_id(e), ContactPermission.channel == "sms"
            )
        )
        assert p.state == "withdrawn"
    viewer = staff_headers(e.client, name="channel.viewer", business_id=BID, role="viewer")
    assert e.client.get(ROOT + "/channel-workspace/inbox").status_code == 200
    assert (
        e.client.post(ROOT + "/channel-workspace/simulate-replies", headers=viewer).status_code
        == 403
    )
    assert (
        e.client.post(
            target, json={"body": "Denied", "request_key": "native-denied-one"}, headers=viewer
        ).status_code
        == 403
    )


def test_pagination_includes_old_conversations_and_provenance(channels):
    e = channels
    with e.factory() as s:
        for i in range(105):
            s.add(
                WhatsAppConversation(
                    id=f"native-conversation-{i:03}",
                    business_id=BID,
                    scope="test",
                    phone_id="123456789",
                    destination=f"+57300000{i:04}",
                    last_inbound_at=CLOCK - timedelta(minutes=i),
                )
            )
        s.flush()
        for i in range(30):
            s.add(
                WhatsAppEvidence(
                    id=f"{i:064x}",
                    business_id=BID,
                    scope="test",
                    conversation_id="native-conversation-104",
                    kind="inbound",
                    document=json.dumps({"text": f"Synthetic message {i}"}),
                    raw_sha256="0" * 64,
                    provider_at=CLOCK - timedelta(minutes=i),
                    received_at=CLOCK,
                )
            )
        s.commit()
    page = e.client.get(ROOT + "/channel-workspace/inbox?offset=100").json()
    assert page["count"] == 105 and len(page["items"]) == 5
    d = e.client.get(
        ROOT + "/channel-workspace/conversations/native-conversation-104?offset=25"
    ).json()
    assert (
        d["message_count"] == 30
        and len(d["messages"]) == 5
        and d["messages"][0]["received_at"]
        and d["messages"][0]["provider_at"]
    )


def test_reply_cleanup_does_not_modify_another_business(channels):
    e = channels
    with e.factory() as s:
        row = WhatsAppConversation(
            id="other-conversation",
            business_id=OTHER,
            scope="test",
            phone_id="999999999",
            destination="+573005551000",
        )
        s.add(row)
        s.flush()
        s.add(
            WhatsAppReply(
                id="f" * 64,
                business_id=OTHER,
                conversation_id=row.id,
                body="Other fixture",
                actor="fixture",
                sender_digest="e" * 64,
                state="sending",
                claimed_at=CLOCK - timedelta(hours=2),
            )
        )
        s.commit()
    assert (
        e.client.post(ROOT + "/channel-workspace/simulate-replies", headers=e.headers).status_code
        == 200
    )
    with e.factory() as s:
        assert s.get(WhatsAppReply, "f" * 64).state == "sending"


def test_expired_window_and_scope_change_block_reply_at_read_and_write(channels):
    e = channels
    convo = inbound(e)
    path = ROOT + "/channel-workspace/conversations/" + convo["id"]
    target = ROOT + "/whatsapp/conversations/" + convo["id"] + "/reply"
    with e.factory() as s:
        s.get(WhatsAppConversation, convo["id"]).last_inbound_at = CLOCK - timedelta(hours=25)
        s.commit()
    assert not e.client.get(path).json()["reply_allowed"]
    r = e.client.post(
        target,
        json={"body": "Expired fixture", "request_key": "expired-native-reply"},
        headers=e.headers,
    )
    assert r.status_code == 409
    with e.factory() as s:
        s.get(WhatsAppConversation, convo["id"]).last_inbound_at = CLOCK
        c.settings(s, BID).scope = "provider_test"
        s.commit()
    assert not e.client.get(path).json()["reply_allowed"]
    assert (
        e.client.post(ROOT + "/channel-workspace/simulate-replies", headers=e.headers).status_code
        == 409
    )


def test_existing_catalogue_creation_apis_remain_scoped_and_readonly_denied(channels):
    e = channels
    payloads = {
        "promotions": {
            "code": "SECOND_SYNTHETIC",
            "name": "Synthetic only",
            "discount_type": "percent",
            "value": 500,
        },
        "rewards": {"name": "Second fixture reward", "points_cost": 100, "discount_minor": 500},
    }
    for route, body in payloads.items():
        response = e.client.post(ROOT + "/" + route, json=body, headers=e.headers)
        assert response.status_code == 200, response.text
        assert response.json()["id"] in {r["id"] for r in e.client.get(ROOT + "/" + route).json()}
        assert (
            e.client.post(
                ROOT.replace(BID, OTHER) + "/" + route, json=body, headers=e.headers
            ).status_code
            == 403
        )
    viewer = staff_headers(e.client, name="catalogue.viewer", business_id=BID, role="viewer")
    for route, body in payloads.items():
        assert e.client.post(ROOT + "/" + route, json=body, headers=viewer).status_code == 403
