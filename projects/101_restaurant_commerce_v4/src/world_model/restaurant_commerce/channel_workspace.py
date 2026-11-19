"""Bounded, source-aware channel inbox; writes keep existing channel authority."""

# ruff: noqa: B008 -- FastAPI dependency convention
import json
from datetime import timedelta
from typing import Literal

from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import campaigns as c
from . import whatsapp as w
from .campaign_models import SmsEvidence, WhatsAppConversation, WhatsAppEvidence, WhatsAppReply
from .models import StaffAccount
from .staff import aware


def register(app, get_session, read, write, integrations, now, demo_mode):
    root = "/api/operator/restaurants/{business_id}/channel-workspace"

    @app.get(root + "/inbox", dependencies=[Depends(read)])
    def inbox(
        business_id: str,
        channel: Literal["whatsapp", "sms"] = "whatsapp",
        scope: Literal["all", "test", "provider_test", "live"] = "all",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
        session: Session = Depends(get_session),
    ):
        model = WhatsAppConversation if channel == "whatsapp" else SmsEvidence
        stmt = select(model).where(model.business_id == business_id)
        if scope != "all":
            stmt = stmt.where(model.scope == scope)
        if channel == "sms":
            stmt = stmt.where(SmsEvidence.kind == "inbound").order_by(
                SmsEvidence.received_at.desc(), SmsEvidence.id
            )
        else:
            stmt = stmt.order_by(
                WhatsAppConversation.last_inbound_at.desc().nullslast(), WhatsAppConversation.id
            )
        count = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        rows = session.scalars(stmt.offset(offset).limit(limit))
        if channel == "whatsapp":
            items = [describe(session, row, now(), demo_mode) for row in rows]
        else:
            items = [
                {
                    "id": row.id,
                    "scope": row.scope,
                    "received_at": row.received_at,
                    "source": "sms_inbound",
                    "document": json.loads(row.document),
                }
                for row in rows
            ]
        return {"items": items, "count": count, "channel": channel, "scope": scope}

    @app.get(root + "/conversations/{conversation_id}", dependencies=[Depends(read)])
    def conversation(
        business_id: str,
        conversation_id: str,
        offset: int = Query(0, ge=0, le=100000),
        reply_offset: int = Query(0, ge=0, le=100000),
        session: Session = Depends(get_session),
    ):
        row = session.get(WhatsAppConversation, conversation_id)
        if not row or row.business_id != business_id:
            raise HTTPException(404, "Conversation not found")
        message_query = select(WhatsAppEvidence).where(
            WhatsAppEvidence.conversation_id == row.id,
            WhatsAppEvidence.business_id == business_id,
            WhatsAppEvidence.kind == "inbound",
        )
        reply_query = select(WhatsAppReply).where(
            WhatsAppReply.conversation_id == row.id, WhatsAppReply.business_id == business_id
        )
        return {
            **describe(session, row, now(), demo_mode),
            "message_count": session.scalar(
                select(func.count()).select_from(message_query.subquery())
            ),
            "reply_count": session.scalar(select(func.count()).select_from(reply_query.subquery())),
            "messages": [
                {
                    "id": item.id,
                    "scope": item.scope,
                    "provider_at": item.provider_at,
                    "received_at": item.received_at,
                    "document": json.loads(item.document),
                }
                for item in session.scalars(
                    message_query.order_by(WhatsAppEvidence.provider_at.desc(), WhatsAppEvidence.id)
                    .offset(offset)
                    .limit(25)
                )
            ],
            "replies": [
                {
                    "id": item.id,
                    "body": item.body,
                    "state": item.state,
                    "reason": item.reason,
                    "actor": item.actor,
                    "provider_id": item.provider_id,
                    "created_at": item.created_at,
                }
                for item in session.scalars(
                    reply_query.order_by(WhatsAppReply.created_at.desc(), WhatsAppReply.id)
                    .offset(reply_offset)
                    .limit(25)
                )
            ],
        }

    if demo_mode:

        @app.post(root + "/simulate-replies", dependencies=[Depends(write)])
        def simulate_replies(business_id: str, session: Session = Depends(get_session)):
            if c.settings(session, business_id).scope != "test":
                raise HTTPException(409, "Test scope required")
            session.commit()
            return {
                "processed": w.dispatch_replies(
                    app.state.session_factory, integrations, now(), business=business_id
                )
            }


def describe(session, row, now, demo_mode):
    opened = bool(
        row.last_inbound_at
        and aware(row.last_inbound_at) <= now < aware(row.last_inbound_at) + timedelta(hours=24)
    )
    actor = session.get(StaffAccount, row.assigned_to) if row.assigned_to else None
    sender = w.sender_document(session, row.business_id)
    return {
        "id": row.id,
        "destination": row.destination,
        "scope": row.scope,
        "state": row.state,
        "assigned_to": row.assigned_to,
        "assigned_name": actor.username if actor else None,
        "opted_out": row.opted_out,
        "last_inbound_at": row.last_inbound_at,
        "service_window_open": opened,
        "reply_allowed": bool(
            demo_mode
            and row.scope == "test"
            and opened
            and not row.opted_out
            and sender
            and sender["phone_id"] == row.phone_id
            and c.settings(session, row.business_id).scope == row.scope
        ),
    }
