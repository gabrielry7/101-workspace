"""101-033: operational pause must survive changes to proposed rules."""

import pytest
from test_loyalty_assignment import checkout, enroll, req
from test_loyalty_assignment import cohort as cohort
from test_loyalty_assignment import factory as factory
from test_loyalty_configuration import document, experiment, publish

from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_execution_models import (
    LoyaltyOrderSnapshot,
)
from world_model.restaurant_commerce.loyalty_models import LoyaltyStrategyVersion
from world_model.restaurant_commerce.loyalty_schemas import (
    ExperimentEdit,
    StrategyEdit,
    Transition,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID


@pytest.mark.parametrize("kind", ["programs", "experiments"])
@pytest.mark.parametrize("pause_first", [True, False])
def test_pause_survives_edit_and_publish_for_existing_assignment(
    cohort, kind, pause_first
):
    sessions, vid, ev, eid, cids = cohort
    with sessions() as session:
        assigned = enroll(session, ev, cids["points"])
        session.commit()
        config = LoyaltyConfigurationService(session, "audit-regression")
        rid = (
            session.get(LoyaltyStrategyVersion, vid).strategy_id
            if kind == "programs"
            else eid
        )
        current = config.get(kind, BID, rid)
        if pause_first:
            current = config.transition(
                kind,
                BID,
                rid,
                Transition(state="paused", expected_revision=current["revision"]),
            )
        cls = StrategyEdit if kind == "programs" else ExperimentEdit
        doc = (
            document(name="New proposal")
            if kind == "programs"
            else experiment(vid, name="New proposal")
        )
        current = config.edit(
            kind, BID, rid, cls(expected_revision=current["revision"], document=doc)
        )
        if not pause_first:
            current = config.transition(
                kind,
                BID,
                rid,
                Transition(state="paused", expected_revision=current["revision"]),
            )
        assert current["state"] == "paused"
        publish(config, current, kind)
        assert config.get(kind, BID, rid)["state"] == "paused"
        assert enroll(session, ev, cids["points"]) == assigned
        session.commit()
        svc = checkout(session, eid, cids["points"])
        request = req(svc)
        order = svc.create_order(BID, request)
        assert session.get(LoyaltyOrderSnapshot, order.id) is None
