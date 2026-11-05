"""Optional staff configuration API; does not enable experimental incentives."""

# FastAPI resolves these dependency defaults per request.
# ruff: noqa: B008
from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from .loyalty_config import LoyaltyConfigurationService
from .loyalty_preview import PublishedRulePreview, preview_published_rules
from .loyalty_rules import CALCULATION_VERSION, PreviewScenario
from .loyalty_schemas import (
    ExperimentCreate,
    ExperimentEdit,
    Publish,
    StrategyCreate,
    StrategyEdit,
    Transition,
)
from .loyalty_simulator import (
    SIMULATION_VERSION,
    SimulationResult,
    SimulationScenario,
    simulate,
)


def register(app, get_session, scoped_staff, *, analytics_enabled=False):
    def read(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "growth.read")

    def write(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "growth.write")

    root = "/api/operator/restaurants/{business_id}/loyalty-config"
    if analytics_enabled:
        from .loyalty_analytics_routes import register as register_analytics
        register_analytics(app, get_session, scoped_staff)

    @app.get(root + "/overview", dependencies=[Depends(read)])
    def loyalty_overview(business_id: str, session: Session = Depends(get_session)):
        from .loyalty_workspace import overview

        return overview(session, business_id)

    @app.get(root + "/capabilities", dependencies=[Depends(read)])
    def loyalty_capabilities(business_id: str, session: Session = Depends(get_session)):
        from .models import RestaurantCommerceProfile

        return {
            "currency": session.get(RestaurantCommerceProfile, business_id).currency,
            "configuration_enabled": True,
            "execution_enabled": False,
            "assignment_enabled": False,
            "analytics_enabled": analytics_enabled,
            "stage": "profit_analytics" if analytics_enabled else "administration_console",
            "simulator_enabled": True,
            "simulation_version": SIMULATION_VERSION,
            "controlled_assignment_available": True,
            "controlled_execution_available": True,
            "preview_enabled": True,
            "calculation_version": CALCULATION_VERSION,
            "preview_rule_types": ["points_earning", "fixed_value_redemption"],
        }

    @app.post(
        root + "/simulator",
        response_model=SimulationResult,
        dependencies=[Depends(read)],
    )
    def loyalty_simulator(business_id: str, payload: SimulationScenario):
        # Scoped staff permission is resolved before this pure, nonpersistent calculation.
        return simulate(payload)

    @app.get(
        root + "/experiments/{resource_id}/enrollment", dependencies=[Depends(read)]
    )
    def loyalty_enrollment_summary(
        business_id: str, resource_id: str, session: Session = Depends(get_session)
    ):
        from .loyalty_assignment import assignment_summary

        return assignment_summary(session, business_id, resource_id)

    @app.post(
        root + "/programs/{resource_id}/versions/{version_id}/preview",
        response_model=PublishedRulePreview,
        dependencies=[Depends(read)],
    )
    def loyalty_preview_program(
        business_id: str,
        resource_id: str,
        version_id: str,
        payload: PreviewScenario,
        session: Session = Depends(get_session),
    ):
        return preview_published_rules(
            session, business_id, resource_id, version_id, payload
        )

    # Explicit request models keep OpenAPI and validation contracts inspectable.
    @app.post(root + "/programs")
    def loyalty_create_program(
        business_id: str,
        payload: StrategyCreate,
        principal=Depends(write),
        session: Session = Depends(get_session),
    ):
        return LoyaltyConfigurationService(session, principal.actor_id).create(
            "programs", business_id, payload
        )

    @app.put(root + "/programs/{resource_id}")
    def loyalty_edit_program(
        business_id: str,
        resource_id: str,
        payload: StrategyEdit,
        principal=Depends(write),
        session: Session = Depends(get_session),
    ):
        return LoyaltyConfigurationService(session, principal.actor_id).edit(
            "programs", business_id, resource_id, payload
        )

    @app.post(root + "/experiments")
    def loyalty_create_experiment(
        business_id: str,
        payload: ExperimentCreate,
        principal=Depends(write),
        session: Session = Depends(get_session),
    ):
        return LoyaltyConfigurationService(session, principal.actor_id).create(
            "experiments", business_id, payload
        )

    @app.put(root + "/experiments/{resource_id}")
    def loyalty_edit_experiment(
        business_id: str,
        resource_id: str,
        payload: ExperimentEdit,
        principal=Depends(write),
        session: Session = Depends(get_session),
    ):
        return LoyaltyConfigurationService(session, principal.actor_id).edit(
            "experiments", business_id, resource_id, payload
        )

    # Register shared operations through a factory, avoiding late-bound loop variables.
    def common(kind):
        @app.get(root + "/" + kind, name="loyalty_list_" + kind)
        def listing(
            business_id: str,
            principal=Depends(read),
            session: Session = Depends(get_session),
        ):
            return LoyaltyConfigurationService(session, principal.actor_id).list(
                kind, business_id
            )

        @app.get(
            root + "/" + kind + "/{resource_id}/eligibility",
            name="loyalty_labels_" + kind,
        )
        def labels(
            business_id: str,
            resource_id: str,
            version_id: str | None = None,
            expected_revision: int | None = Query(default=None, ge=1),
            principal=Depends(read),
            session: Session = Depends(get_session),
        ):
            from .loyalty_workspace import eligibility_labels

            return eligibility_labels(
                session, business_id, kind, resource_id, version_id, expected_revision
            )

        @app.get(root + "/" + kind + "/{resource_id}", name="loyalty_get_" + kind)
        def detail(
            business_id: str,
            resource_id: str,
            principal=Depends(read),
            session: Session = Depends(get_session),
        ):
            return LoyaltyConfigurationService(session, principal.actor_id).get(
                kind, business_id, resource_id
            )

        @app.post(
            root + "/" + kind + "/{resource_id}/publish", name="loyalty_publish_" + kind
        )
        def publish(
            business_id: str,
            resource_id: str,
            payload: Publish,
            principal=Depends(write),
            session: Session = Depends(get_session),
        ):
            return LoyaltyConfigurationService(session, principal.actor_id).publish(
                kind, business_id, resource_id, payload
            )

        @app.post(
            root + "/" + kind + "/{resource_id}/state", name="loyalty_state_" + kind
        )
        def state(
            business_id: str,
            resource_id: str,
            payload: Transition,
            principal=Depends(write),
            session: Session = Depends(get_session),
        ):
            return LoyaltyConfigurationService(session, principal.actor_id).transition(
                kind, business_id, resource_id, payload
            )

    common("programs")
    common("experiments")
