from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import ConcurrencyConflictError, NotFoundError, ValidationError
from .enums import PaymentStatus
from .models import (
    AutomationRule,
    Customer,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    LoyaltyProgram,
    Order,
    OutboundMessage,
    Promotion,
    PromotionRedemption,
    RestaurantCommerceProfile,
    RewardDefinition,
    RewardRedemption,
    utcnow,
)
from .schemas import (
    AutomationRuleCreateIn,
    AutomationRuleOut,
    DiscountOut,
    GrowthAnalyticsOut,
    LoyaltyAccountOut,
    OutboundMessageOut,
    PromotionCreateIn,
    PromotionOut,
    RewardCreateIn,
    RewardOut,
)


def _utc(value: datetime | None = None) -> datetime:
    value = value or utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _render(template: str, values: dict[str, object]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


class RestaurantGrowthService:
    """V2 loyalty, promotions, retention automation and analytics.

    Messages are queued into an outbox. This service never sends WhatsApp,
    email or SMS network traffic itself.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Loyalty / rewards
    # ------------------------------------------------------------------
    def ensure_program(self, business_id: str) -> LoyaltyProgram:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError("Restaurant commerce profile not found")
        program = self.session.get(LoyaltyProgram, business_id)
        if program:
            return program
        candidate = LoyaltyProgram(business_id=business_id, enabled=profile.loyalty_enabled)
        try:
            with self.session.begin_nested():
                self.session.add(candidate)
                self.session.flush()
            return candidate
        except IntegrityError:
            program = self.session.get(LoyaltyProgram, business_id)
            if not program:
                raise ConcurrencyConflictError("Concurrent loyalty program creation could not be reconciled")
            return program

    def ensure_account(self, business_id: str, customer_id: str, *, for_update: bool = False) -> LoyaltyAccount:
        stmt = select(LoyaltyAccount).where(
            LoyaltyAccount.business_id == business_id,
            LoyaltyAccount.customer_id == customer_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        account = self.session.scalar(stmt)
        if account:
            return account
        candidate = LoyaltyAccount(business_id=business_id, customer_id=customer_id)
        try:
            with self.session.begin_nested():
                self.session.add(candidate)
                self.session.flush()
            return candidate
        except IntegrityError:
            account = self.session.scalar(stmt)
            if not account:
                raise ConcurrencyConflictError("Concurrent loyalty account creation could not be reconciled")
            return account

    def loyalty_account(self, business_id: str, customer_id: str) -> LoyaltyAccountOut:
        customer = self.session.get(Customer, customer_id)
        if not customer or customer.business_id != business_id:
            raise NotFoundError("Customer not found")
        account = self.ensure_account(business_id, customer_id)
        rewards = self.session.scalars(
            select(RewardDefinition)
            .where(RewardDefinition.business_id == business_id, RewardDefinition.enabled.is_(True))
            .order_by(RewardDefinition.points_cost.asc())
        ).all()
        return LoyaltyAccountOut(
            customer_id=customer_id,
            business_id=business_id,
            available_points=account.available_points,
            lifetime_earned_points=account.lifetime_earned_points,
            lifetime_redeemed_points=account.lifetime_redeemed_points,
            rewards=[self._reward_out(r) for r in rewards],
        )

    def create_reward(self, business_id: str, request: RewardCreateIn) -> RewardOut:
        self.ensure_program(business_id)
        reward = RewardDefinition(
            business_id=business_id,
            name=request.name,
            description=request.description,
            points_cost=request.points_cost,
            discount_minor=request.discount_minor,
            minimum_order_minor=request.minimum_order_minor,
        )
        self.session.add(reward)
        self.session.commit()
        return self._reward_out(reward)

    def list_rewards(self, business_id: str) -> list[RewardOut]:
        return [
            self._reward_out(r)
            for r in self.session.scalars(
                select(RewardDefinition)
                .where(RewardDefinition.business_id == business_id)
                .order_by(RewardDefinition.points_cost.asc())
            ).all()
        ]

    def _reward_out(self, reward: RewardDefinition) -> RewardOut:
        return RewardOut(
            id=reward.id,
            name=reward.name,
            description=reward.description,
            points_cost=reward.points_cost,
            discount_minor=reward.discount_minor,
            minimum_order_minor=reward.minimum_order_minor,
            enabled=reward.enabled,
        )

    def preview_reward(self, business_id: str, customer_id: str | None, reward_id: str | None, subtotal: int) -> tuple[int, str | None]:
        if not reward_id:
            return 0, None
        if not customer_id:
            raise ValidationError("Customer identity is required to redeem a loyalty reward")
        program = self.ensure_program(business_id)
        if not program.enabled:
            raise ValidationError("Loyalty is disabled")
        reward = self.session.get(RewardDefinition, reward_id)
        if not reward or reward.business_id != business_id or not reward.enabled:
            raise ValidationError("Reward is unavailable")
        if subtotal < reward.minimum_order_minor:
            raise ValidationError("Order does not meet the reward minimum")
        account = self.ensure_account(business_id, customer_id)
        if account.available_points < reward.points_cost:
            raise ValidationError("Not enough loyalty points")
        return min(reward.discount_minor, subtotal), reward.name

    def reserve_reward(self, *, business_id: str, customer_id: str, reward_id: str | None, order: Order) -> RewardRedemption | None:
        if not reward_id:
            return None
        reward = self.session.get(RewardDefinition, reward_id)
        if not reward or reward.business_id != business_id or not reward.enabled:
            raise ValidationError("Reward is unavailable")
        account = self.ensure_account(business_id, customer_id, for_update=True)
        if account.available_points < reward.points_cost:
            raise ValidationError("Not enough loyalty points")
        if order.subtotal_minor < reward.minimum_order_minor:
            raise ValidationError("Order does not meet the reward minimum")

        redemption = RewardRedemption(
            business_id=business_id,
            customer_id=customer_id,
            reward_id=reward.id,
            order_id=order.id,
            points_spent=reward.points_cost,
            discount_minor=order.reward_discount_minor,
            status="reserved",
        )
        self.session.add(redemption)
        self.session.flush()
        account.available_points -= reward.points_cost
        account.lifetime_redeemed_points += reward.points_cost
        self.session.add(
            LoyaltyLedgerEntry(
                account_id=account.id,
                order_id=order.id,
                redemption_id=redemption.id,
                delta_points=-reward.points_cost,
                reason="reward.reserved",
                idempotency_key=f"reward-reserve:{redemption.id}",
            )
        )
        return redemption

    def finalize_reward(self, order_id: str) -> None:
        redemption = self.session.scalar(select(RewardRedemption).where(RewardRedemption.order_id == order_id))
        if redemption and redemption.status == "reserved":
            redemption.status = "applied"
            redemption.applied_at = utcnow()

    def release_reward(self, order_id: str) -> None:
        redemption = self.session.scalar(select(RewardRedemption).where(RewardRedemption.order_id == order_id))
        if not redemption or redemption.status != "reserved":
            return
        account = self.ensure_account(redemption.business_id, redemption.customer_id, for_update=True)
        account.available_points += redemption.points_spent
        account.lifetime_redeemed_points -= redemption.points_spent
        redemption.status = "released"
        redemption.released_at = utcnow()
        self.session.add(
            LoyaltyLedgerEntry(
                account_id=account.id,
                order_id=order_id,
                redemption_id=redemption.id,
                delta_points=redemption.points_spent,
                reason="reward.released",
                idempotency_key=f"reward-release:{redemption.id}",
            )
        )

    def award_completed_order(self, order: Order) -> int:
        program = self.ensure_program(order.business_id)
        if not program.enabled or program.spend_minor_per_point <= 0:
            return 0
        existing = self.session.scalar(
            select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.idempotency_key == f"order-complete:{order.id}")
        )
        if existing:
            return existing.delta_points
        loyalty_eligible_minor = max(0, order.total_minor - getattr(order, "delivery_fee_minor", 0))
        points = loyalty_eligible_minor // program.spend_minor_per_point
        if points <= 0:
            return 0
        account = self.ensure_account(order.business_id, order.customer_id, for_update=True)
        account.available_points += points
        account.lifetime_earned_points += points
        self.session.add(
            LoyaltyLedgerEntry(
                account_id=account.id,
                order_id=order.id,
                delta_points=points,
                reason="order.completed",
                idempotency_key=f"order-complete:{order.id}",
            )
        )
        return points

    # ------------------------------------------------------------------
    # Promotions
    # ------------------------------------------------------------------
    def create_promotion(self, business_id: str, request: PromotionCreateIn) -> PromotionOut:
        if not self.session.get(RestaurantCommerceProfile, business_id):
            raise NotFoundError("Restaurant commerce profile not found")
        code = request.code.strip().upper()
        if self.session.scalar(select(Promotion).where(Promotion.business_id == business_id, Promotion.code == code)):
            raise ValidationError("Promotion code already exists")
        if request.discount_type == "percent" and request.value > 10000:
            raise ValidationError("Percent promotion value uses basis points and cannot exceed 10000")
        promotion = Promotion(business_id=business_id, code=code, **request.model_dump(exclude={"code"}))
        self.session.add(promotion)
        self.session.commit()
        return self._promotion_out(promotion)

    def list_promotions(self, business_id: str) -> list[PromotionOut]:
        return [self._promotion_out(p) for p in self.session.scalars(select(Promotion).where(Promotion.business_id == business_id)).all()]

    def _promotion_out(self, p: Promotion) -> PromotionOut:
        return PromotionOut(
            id=p.id, business_id=p.business_id, code=p.code, name=p.name,
            discount_type=p.discount_type, value=p.value, minimum_order_minor=p.minimum_order_minor,
            maximum_discount_minor=p.maximum_discount_minor, starts_at=p.starts_at, ends_at=p.ends_at,
            per_customer_limit=p.per_customer_limit, total_redemption_limit=p.total_redemption_limit, enabled=p.enabled,
        )

    def preview_promotion(self, business_id: str, code: str | None, subtotal: int, customer_id: str | None) -> tuple[int, Promotion | None]:
        if not code:
            return 0, None
        normalized = code.strip().upper()
        promotion = self.session.scalar(select(Promotion).where(Promotion.business_id == business_id, Promotion.code == normalized))
        if not promotion or not promotion.enabled:
            raise ValidationError("Promotion code is invalid or inactive")
        now = utcnow()
        if promotion.starts_at and _utc(promotion.starts_at) > now:
            raise ValidationError("Promotion has not started")
        if promotion.ends_at and _utc(promotion.ends_at) < now:
            raise ValidationError("Promotion has expired")
        if subtotal < promotion.minimum_order_minor:
            raise ValidationError("Order does not meet the promotion minimum")
        total_uses = self.session.scalar(
            select(func.count(PromotionRedemption.id)).where(
                PromotionRedemption.promotion_id == promotion.id,
                PromotionRedemption.status != "released",
            )
        ) or 0
        if promotion.total_redemption_limit is not None and total_uses >= promotion.total_redemption_limit:
            raise ValidationError("Promotion redemption limit reached")
        if customer_id and promotion.per_customer_limit is not None:
            uses = self.session.scalar(
                select(func.count(PromotionRedemption.id)).where(
                    PromotionRedemption.promotion_id == promotion.id,
                    PromotionRedemption.customer_id == customer_id,
                    PromotionRedemption.status != "released",
                )
            ) or 0
            if uses >= promotion.per_customer_limit:
                raise ValidationError("Customer promotion limit reached")
        if promotion.discount_type == "fixed":
            discount = promotion.value
        elif promotion.discount_type == "percent":
            discount = subtotal * promotion.value // 10000
        else:
            raise ValidationError("Unsupported promotion discount type")
        if promotion.maximum_discount_minor is not None:
            discount = min(discount, promotion.maximum_discount_minor)
        return min(discount, subtotal), promotion

    def record_promotion(self, promotion: Promotion | None, order: Order, customer_id: str, discount_minor: int) -> None:
        if not promotion or discount_minor <= 0:
            return
        # Lock the promotion while enforcing redemption caps. Preview is for UX;
        # this is the authoritative concurrency-safe check at order creation.
        locked = self.session.scalar(
            select(Promotion).where(Promotion.id == promotion.id).with_for_update()
        )
        if not locked or not locked.enabled:
            raise ValidationError("Promotion code is invalid or inactive")
        total_uses = self.session.scalar(
            select(func.count(PromotionRedemption.id)).where(
                PromotionRedemption.promotion_id == locked.id,
                PromotionRedemption.status != "released",
            )
        ) or 0
        if locked.total_redemption_limit is not None and total_uses >= locked.total_redemption_limit:
            raise ValidationError("Promotion redemption limit reached")
        if locked.per_customer_limit is not None:
            uses = self.session.scalar(
                select(func.count(PromotionRedemption.id)).where(
                    PromotionRedemption.promotion_id == locked.id,
                    PromotionRedemption.customer_id == customer_id,
                    PromotionRedemption.status != "released",
                )
            ) or 0
            if uses >= locked.per_customer_limit:
                raise ValidationError("Customer promotion limit reached")
        self.session.add(PromotionRedemption(
            business_id=order.business_id,
            promotion_id=locked.id,
            customer_id=customer_id,
            order_id=order.id,
            discount_minor=discount_minor,
            status="reserved",
        ))

    def finalize_promotion(self, order_id: str) -> None:
        redemption = self.session.scalar(select(PromotionRedemption).where(PromotionRedemption.order_id == order_id))
        if redemption and redemption.status == "reserved":
            redemption.status = "applied"
            redemption.applied_at = utcnow()

    def release_promotion(self, order_id: str) -> None:
        redemption = self.session.scalar(select(PromotionRedemption).where(PromotionRedemption.order_id == order_id))
        if redemption and redemption.status == "reserved":
            redemption.status = "released"
            redemption.released_at = utcnow()

    # ------------------------------------------------------------------
    # Automation / WhatsApp outbox
    # ------------------------------------------------------------------
    def create_rule(self, business_id: str, request: AutomationRuleCreateIn) -> AutomationRuleOut:
        if not self.session.get(RestaurantCommerceProfile, business_id):
            raise NotFoundError("Restaurant commerce profile not found")
        rule = AutomationRule(business_id=business_id, **request.model_dump())
        self.session.add(rule)
        self.session.commit()
        return self._rule_out(rule)

    def list_rules(self, business_id: str) -> list[AutomationRuleOut]:
        return [self._rule_out(r) for r in self.session.scalars(select(AutomationRule).where(AutomationRule.business_id == business_id)).all()]

    def _rule_out(self, r: AutomationRule) -> AutomationRuleOut:
        return AutomationRuleOut(
            id=r.id, business_id=r.business_id, name=r.name, trigger_kind=r.trigger_kind,
            channel=r.channel, purpose=r.purpose, delay_minutes=r.delay_minutes,
            template_text=r.template_text, enabled=r.enabled,
        )

    def queue_order_completed_automations(self, order: Order) -> list[OutboundMessage]:
        profile = self.session.get(RestaurantCommerceProfile, order.business_id)
        if not profile or not profile.marketing_automation_enabled or not profile.review_requests_enabled:
            return []
        customer = self.session.get(Customer, order.customer_id)
        if not customer:
            return []
        rules = self.session.scalars(
            select(AutomationRule).where(
                AutomationRule.business_id == order.business_id,
                AutomationRule.trigger_kind == "order.completed.review_request",
                AutomationRule.enabled.is_(True),
            )
        ).all()
        created: list[OutboundMessage] = []
        for rule in rules:
            created.append(self._queue_message(
                rule=rule, customer=customer, order=order,
                message_kind="review_request",
                values={"name": customer.name or "", "order_code": order.public_code},
                dedupe_key=f"review:{order.id}:{rule.id}",
            ))
        return created

    def plan_winback(self, business_id: str, *, as_of: datetime | None = None, dormant_days: int | None = None, limit: int = 100) -> list[OutboundMessage]:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError("Restaurant commerce profile not found")
        now = _utc(as_of)
        days = dormant_days or profile.winback_days
        cutoff = now - timedelta(days=days)
        rule = self.session.scalar(
            select(AutomationRule).where(
                AutomationRule.business_id == business_id,
                AutomationRule.trigger_kind == "customer.winback",
                AutomationRule.enabled.is_(True),
            ).order_by(AutomationRule.created_at.asc())
        )
        if not rule:
            return []
        customers = self.session.scalars(
            select(Customer).where(
                Customer.business_id == business_id,
                Customer.last_order_at.is_not(None),
                Customer.last_order_at <= cutoff,
            ).order_by(Customer.last_order_at.asc()).limit(limit)
        ).all()
        created: list[OutboundMessage] = []
        bucket = now.date().isoformat()
        for customer in customers:
            created.append(self._queue_message(
                rule=rule, customer=customer, order=None,
                message_kind="winback",
                values={"name": customer.name or "", "days": days},
                dedupe_key=f"winback:{business_id}:{customer.id}:{bucket}:{rule.id}",
                now=now,
            ))
        return created

    def _queue_message(
        self, *, rule: AutomationRule, customer: Customer, order: Order | None,
        message_kind: str, values: dict[str, object], dedupe_key: str, now: datetime | None = None,
    ) -> OutboundMessage:
        existing = self.session.scalar(select(OutboundMessage).where(OutboundMessage.dedupe_key == dedupe_key))
        if existing:
            return existing
        now = _utc(now)
        status = "queued"
        suppression = None
        if rule.channel == "whatsapp" and not customer.whatsapp_opt_in:
            status, suppression = "suppressed", "WHATSAPP_OPT_IN_REQUIRED"
        elif rule.purpose == "marketing" and not customer.marketing_opt_in:
            status, suppression = "suppressed", "MARKETING_OPT_IN_REQUIRED"
        candidate = OutboundMessage(
            business_id=rule.business_id,
            customer_id=customer.id,
            order_id=order.id if order else None,
            rule_id=rule.id,
            channel=rule.channel,
            purpose=rule.purpose,
            message_kind=message_kind,
            destination=customer.phone,
            body=_render(rule.template_text, values),
            scheduled_at=now + timedelta(minutes=rule.delay_minutes),
            status=status,
            suppression_reason=suppression,
            dedupe_key=dedupe_key,
            metadata_json=json.dumps(values, sort_keys=True),
        )
        try:
            with self.session.begin_nested():
                self.session.add(candidate)
                self.session.flush()
            return candidate
        except IntegrityError:
            existing = self.session.scalar(
                select(OutboundMessage).where(OutboundMessage.dedupe_key == dedupe_key)
            )
            if not existing:
                raise ConcurrencyConflictError("Concurrent message dedupe could not be reconciled")
            return existing

    def list_outbox(self, business_id: str, *, status: str | None = None, limit: int = 200) -> list[OutboundMessageOut]:
        stmt = select(OutboundMessage).where(OutboundMessage.business_id == business_id)
        if status:
            stmt = stmt.where(OutboundMessage.status == status)
        rows = self.session.scalars(stmt.order_by(OutboundMessage.scheduled_at.asc()).limit(limit)).all()
        return [self._message_out(m) for m in rows]

    def mark_sent(self, message_id: str, *, sent_at: datetime | None = None) -> OutboundMessageOut:
        message = self.session.get(OutboundMessage, message_id)
        if not message:
            raise NotFoundError("Outbound message not found")
        if message.status == "suppressed":
            raise ValidationError("Suppressed message cannot be marked sent")
        message.status = "sent"
        message.sent_at = _utc(sent_at)
        self.session.commit()
        return self._message_out(message)

    def _message_out(self, m: OutboundMessage) -> OutboundMessageOut:
        return OutboundMessageOut(
            id=m.id, business_id=m.business_id, customer_id=m.customer_id, order_id=m.order_id,
            channel=m.channel, purpose=m.purpose, message_kind=m.message_kind, destination=m.destination,
            body=m.body, scheduled_at=m.scheduled_at, status=m.status,
            suppression_reason=m.suppression_reason, created_at=m.created_at, sent_at=m.sent_at,
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def analytics(self, business_id: str, *, as_of: datetime | None = None) -> GrowthAnalyticsOut:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError("Restaurant commerce profile not found")
        now = _utc(as_of)
        paid_completed = [
            Order.business_id == business_id,
            Order.status == "completed",
            Order.payment_status == PaymentStatus.PAID.value,
        ]
        row = self.session.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.subtotal_minor), 0),
                func.coalesce(func.sum(Order.discount_minor), 0),
                func.coalesce(func.sum(Order.delivery_fee_minor), 0),
                func.coalesce(func.sum(Order.total_minor), 0),
                func.count(func.distinct(Order.customer_id)),
            ).where(*paid_completed)
        ).one()
        completed_orders, gross, discounts, delivery_fees, net, unique_customers = map(int, row)

        repeat_subq = (
            select(Order.customer_id.label("customer_id"))
            .where(*paid_completed)
            .group_by(Order.customer_id)
            .having(func.count(Order.id) >= 2)
            .subquery()
        )
        repeat_customers = int(
            self.session.scalar(select(func.count()).select_from(repeat_subq)) or 0
        )
        channel_rows = self.session.execute(
            select(Order.source_channel, func.count(Order.id))
            .where(*paid_completed)
            .group_by(Order.source_channel)
        ).all()
        channel_counts = {str(channel): int(count) for channel, count in channel_rows}

        loyalty_members, outstanding = self.session.execute(
            select(
                func.count(LoyaltyAccount.id),
                func.coalesce(func.sum(LoyaltyAccount.available_points), 0),
            ).where(LoyaltyAccount.business_id == business_id)
        ).one()
        redemptions = self.session.scalar(
            select(func.count(PromotionRedemption.id)).where(
                PromotionRedemption.business_id == business_id,
                PromotionRedemption.status == "applied",
            )
        ) or 0
        queued = self.session.scalar(
            select(func.count(OutboundMessage.id)).where(
                OutboundMessage.business_id == business_id, OutboundMessage.status == "queued"
            )
        ) or 0
        suppressed = self.session.scalar(
            select(func.count(OutboundMessage.id)).where(
                OutboundMessage.business_id == business_id, OutboundMessage.status == "suppressed"
            )
        ) or 0
        cutoff = now - timedelta(days=profile.winback_days)
        dormant = self.session.scalar(
            select(func.count(Customer.id)).where(
                Customer.business_id == business_id,
                Customer.last_order_at.is_not(None),
                Customer.last_order_at <= cutoff,
            )
        ) or 0
        net = int(net)
        delivery_fees = int(delivery_fees)
        return GrowthAnalyticsOut(
            business_id=business_id,
            as_of=now,
            completed_orders=completed_orders,
            gross_revenue_minor=int(gross),
            discount_minor=int(discounts),
            net_revenue_minor=net,
            food_net_revenue_minor=net - delivery_fees,
            delivery_fees_minor=delivery_fees,
            unique_customers=unique_customers,
            repeat_customers=repeat_customers,
            repeat_customer_rate=(repeat_customers / unique_customers if unique_customers else 0.0),
            average_order_value_minor=(net // completed_orders if completed_orders else 0),
            loyalty_members=int(loyalty_members or 0),
            loyalty_points_outstanding=int(outstanding or 0),
            promotion_redemptions=int(redemptions),
            queued_messages=int(queued),
            suppressed_messages=int(suppressed),
            dormant_customers=int(dormant),
            channel_order_counts=channel_counts,
        )

    def preview_discounts(self, business_id: str, *, subtotal: int, promo_code: str | None, customer_id: str | None, reward_id: str | None) -> DiscountOut:
        promo_discount, promotion = self.preview_promotion(business_id, promo_code, subtotal, customer_id)
        remaining = max(0, subtotal - promo_discount)
        reward_discount, reward_name = self.preview_reward(business_id, customer_id, reward_id, remaining)
        total = min(subtotal, promo_discount + reward_discount)
        return DiscountOut(
            promotion_code=promotion.code if promotion else None,
            promotion_discount_minor=promo_discount,
            reward_id=reward_id,
            reward_name=reward_name,
            reward_discount_minor=reward_discount,
            total_discount_minor=total,
        )
