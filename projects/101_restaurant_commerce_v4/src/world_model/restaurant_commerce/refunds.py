"""Canonical confirmed partial-refund observations, shared by finance and campaigns.

Only the authenticated payment notification path calls record_refund. No public
campaign action can establish money. Provider refund submission remains unchanged.
"""
from sqlalchemy import ForeignKey, String, Integer, Text, UniqueConstraint, CheckConstraint, select, func
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, Payment, new_id
from .errors import PaymentError, NotFoundError, IdempotencyConflictError


class PaymentRefund(Base):
    __tablename__ = 'restaurant_payment_refunds'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    payment_id: Mapped[str] = mapped_column(ForeignKey('restaurant_payments.id'), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(String(200))
    amount_minor: Mapped[int] = mapped_column(Integer)
    evidence_json: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('provider','reference'), CheckConstraint('amount_minor > 0'))


def refunded_total(session, payment):
    if payment.status == 'refunded': return payment.amount_minor
    return session.scalar(select(func.coalesce(func.sum(PaymentRefund.amount_minor),0))
        .where(PaymentRefund.payment_id == payment.id))


def record_refund(service, provider, body, evidence):
    session = service.session
    # No unqualified real-provider partial-refund interpretation. Simulator contract
    # is explicit; a real provider needs its own authenticated normalization tests.
    if provider != 'simulated': raise PaymentError('Partial refund adapter not qualified')
    payment = session.scalar(select(Payment).where(Payment.provider_reference == body['provider_reference'])
        .with_for_update().execution_options(populate_existing=True))
    if not payment: raise NotFoundError('Payment not bound yet')
    if payment.provider != provider or payment.amount_minor != body['amount_minor'] or payment.currency != body['currency'].upper():
        raise PaymentError('Refund does not match canonical payment')
    reference, amount = body.get('refund_reference'), body.get('refund_amount_minor')
    if not reference or type(amount) is not int or amount <= 0:
        raise PaymentError('Confirmed refund reference and amount required')
    existing = session.scalar(select(PaymentRefund).where(PaymentRefund.provider == provider, PaymentRefund.reference == reference))
    if existing:
        if existing.payment_id != payment.id or existing.amount_minor != amount:
            raise IdempotencyConflictError('Refund reference reused with different values')
        return service.order_out(payment.order_id)
    if payment.status not in {'paid','refunded'}: raise NotFoundError('Refund awaits confirmed payment')
    total = refunded_total(session, payment)
    if total + amount > payment.amount_minor: raise PaymentError('Refund exceeds captured payment')
    # Payment optimistic version fences concurrent SQLite writers as well as PG lock.
    payment.version += 1
    session.add(PaymentRefund(payment_id=payment.id, provider=provider, reference=reference,
        amount_minor=amount, evidence_json=evidence))
    session.flush()
    if total + amount == payment.amount_minor:
        return service.apply_payment_status(payment.provider_reference, 'refunded', provider=provider,
            event_id=body['event_id'], amount_minor=payment.amount_minor, currency=payment.currency, raw_event_json=evidence)
    service._commit_event(kind='payment.partially_refunded', business_id=service.order_out(payment.order_id).business_id,
        entity_id=payment.id, payload={'order_id':payment.order_id,'refund_reference':reference,'amount_minor':amount},
        dedupe_key=f'partial-refund:{provider}:{reference}')
    return service.order_out(payment.order_id)
