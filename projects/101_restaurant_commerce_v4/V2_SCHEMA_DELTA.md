# V2 schema delta

V2 adds growth/retention state to the V1 operational schema.

## Existing tables extended

`restaurant_commerce_profiles`
- `loyalty_enabled`
- `marketing_automation_enabled`
- `review_requests_enabled`
- `winback_days`

`restaurant_customers`
- `whatsapp_opt_in`
- `whatsapp_opt_in_at`
- `marketing_opt_in`
- `marketing_opt_in_at`
- `marketing_opt_in_source`

`restaurant_orders`
- `promotion_discount_minor`
- `reward_discount_minor`
- `discount_minor`
- `promotion_code_snapshot`
- `reward_name_snapshot`

## New tables

- `restaurant_loyalty_programs`
- `restaurant_loyalty_accounts`
- `restaurant_loyalty_ledger`
- `restaurant_rewards`
- `restaurant_reward_redemptions`
- `restaurant_promotions`
- `restaurant_promotion_redemptions`
- `restaurant_automation_rules`
- `restaurant_outbound_messages`

For the live 101 integration, generate the migration from the actual live ORM state and verify it with Alembic drift checks rather than copying SQL from this document.
