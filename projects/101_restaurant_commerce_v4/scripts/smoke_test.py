from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import init_schema
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from sqlalchemy.orm import Session

engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
init_schema(engine)
with Session(engine) as session:
    seed_demo(session)
client = TestClient(create_app(engine=engine, operator_token="smoke"))
assert client.get("/health").json()["status"] == "ok"
store = client.get(f"/api/restaurants/{DEMO_BUSINESS_ID}/storefront").json()
assert store["display_name"] == "Casa 101"
assert store["ordering_enabled"] is True
assert store["loyalty_enabled"] is True
assert store["delivery_enabled"] is True
quote = client.post(
    f"/api/restaurants/{DEMO_BUSINESS_ID}/delivery/quote",
    json={
        "destination": {
            "address_line": "Calle 85 # 12-34",
            "city": "Bogotá",
            "latitude": 4.6697,
            "longitude": -74.0549,
        }
    },
)
assert quote.status_code == 200
assert quote.json()["fee_minor"] > 0
analytics = client.get(
    f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/analytics",
    headers={"X-101-Operator-Token": "smoke"},
)
assert analytics.status_code == 200
print("RESTAURANT_COMMERCE_V4_SMOKE_PASS")
