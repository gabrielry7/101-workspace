from __future__ import annotations

from sqlalchemy.orm import Session

from .models import (
    AutomationRule,
    LoyaltyProgram,
    Menu,
    MenuCategory,
    MenuItem,
    ModifierGroup,
    ModifierOption,
    Promotion,
    RestaurantCommerceProfile,
    RewardDefinition,
)

DEMO_BUSINESS_ID = "demo-restaurant-bogota"


def seed_demo(session: Session) -> str:
    existing = session.get(RestaurantCommerceProfile, DEMO_BUSINESS_ID)
    if existing:
        return DEMO_BUSINESS_ID

    profile = RestaurantCommerceProfile(
        business_id=DEMO_BUSINESS_ID,
        slug="casa-101",
        display_name="Casa 101",
        currency="COP",
        timezone="America/Bogota",
        ordering_enabled=True,
        pickup_enabled=True,
        delivery_enabled=True,
        delivery_provider="simulated_delivery",
        delivery_origin_address="Casa 101, Chapinero, Bogotá",
        delivery_origin_latitude=4.6486,
        delivery_origin_longitude=-74.0630,
        delivery_max_distance_meters=12000,
        accepts_reservations=True,
        default_prep_minutes=25,
        reservation_slot_minutes=30,
        max_party_size=12,
        pickup_instructions="Recoge tu pedido en caja. Te avisamos cuando esté listo.",
        loyalty_enabled=True,
        marketing_automation_enabled=True,
        review_requests_enabled=True,
        winback_days=30,
    )
    menu = Menu(business_id=DEMO_BUSINESS_ID, name="Menú", enabled=True, display_order=0)
    session.add_all([profile, menu])
    session.flush()

    burgers = MenuCategory(menu_id=menu.id, name="Hamburguesas", display_order=0)
    sides = MenuCategory(menu_id=menu.id, name="Para acompañar", display_order=1)
    drinks = MenuCategory(menu_id=menu.id, name="Bebidas", display_order=2)
    session.add_all([burgers, sides, drinks])
    session.flush()

    smash = MenuItem(
        category_id=burgers.id,
        name="Smash 101",
        description="Doble carne, queso, cebolla caramelizada y salsa de la casa.",
        base_price_minor=32900,
        currency="COP",
        display_order=0,
    )
    chicken = MenuItem(
        category_id=burgers.id,
        name="Pollo Crispy",
        description="Pollo apanado, coleslaw y salsa picante suave.",
        base_price_minor=29900,
        currency="COP",
        display_order=1,
    )
    fries = MenuItem(
        category_id=sides.id,
        name="Papas de la casa",
        description="Papas crocantes con sal especiada.",
        base_price_minor=11900,
        currency="COP",
    )
    soda = MenuItem(
        category_id=drinks.id,
        name="Gaseosa",
        description="Lata 330 ml.",
        base_price_minor=7000,
        currency="COP",
    )
    session.add_all([smash, chicken, fries, soda])
    session.flush()

    doneness = ModifierGroup(
        item_id=smash.id,
        name="Término",
        required=True,
        min_selections=1,
        max_selections=1,
        display_order=0,
    )
    extras = ModifierGroup(
        item_id=smash.id,
        name="Extras",
        required=False,
        min_selections=0,
        max_selections=2,
        display_order=1,
    )
    chicken_sauce = ModifierGroup(
        item_id=chicken.id,
        name="Salsa",
        required=True,
        min_selections=1,
        max_selections=1,
        display_order=0,
    )
    session.add_all([doneness, extras, chicken_sauce])
    session.flush()

    session.add_all(
        [
            ModifierOption(group_id=doneness.id, name="Medio", price_delta_minor=0, display_order=0),
            ModifierOption(group_id=doneness.id, name="Tres cuartos", price_delta_minor=0, display_order=1),
            ModifierOption(group_id=doneness.id, name="Bien asada", price_delta_minor=0, display_order=2),
            ModifierOption(group_id=extras.id, name="Tocineta", price_delta_minor=5500, display_order=0),
            ModifierOption(group_id=extras.id, name="Queso extra", price_delta_minor=4000, display_order=1),
            ModifierOption(group_id=chicken_sauce.id, name="Picante suave", price_delta_minor=0),
            ModifierOption(group_id=chicken_sauce.id, name="Ajo", price_delta_minor=0, display_order=1),
        ]
    )

    session.add(
        LoyaltyProgram(
            business_id=DEMO_BUSINESS_ID,
            enabled=True,
            spend_minor_per_point=1000,
            minimum_redeem_points=20,
        )
    )
    session.add_all(
        [
            RewardDefinition(
                business_id=DEMO_BUSINESS_ID,
                name="$10.000 de descuento",
                description="Canjea 50 puntos por $10.000 de descuento.",
                points_cost=50,
                discount_minor=10000,
                minimum_order_minor=30000,
            ),
            Promotion(
                business_id=DEMO_BUSINESS_ID,
                code="DIRECTO10",
                name="10% pedido directo",
                discount_type="percent",
                value=1000,
                minimum_order_minor=25000,
                maximum_discount_minor=15000,
                per_customer_limit=2,
                enabled=True,
            ),
            AutomationRule(
                business_id=DEMO_BUSINESS_ID,
                name="Pedir reseña después de completar",
                trigger_kind="order.completed.review_request",
                channel="whatsapp",
                purpose="service_followup",
                delay_minutes=120,
                template_text="Hola {{name}}, gracias por tu pedido #{{order_code}}. ¿Nos cuentas cómo te fue?",
            ),
            AutomationRule(
                business_id=DEMO_BUSINESS_ID,
                name="Win-back 30 días",
                trigger_kind="customer.winback",
                channel="whatsapp",
                purpose="marketing",
                delay_minutes=0,
                template_text="Hola {{name}}, hace rato no te vemos. Tenemos ganas de cocinarte algo otra vez.",
            ),
        ]
    )
    session.commit()
    return DEMO_BUSINESS_ID
