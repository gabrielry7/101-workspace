"""Read-only, tenant-scoped adapter from published configuration to pure calculation."""

from sqlalchemy import select

from .errors import NotFoundError, ValidationError
from .loyalty_config import canonical, digest
from .loyalty_models import LoyaltyStrategyVersion
from .loyalty_rules import PreviewScenario, RulePreview, evaluate_rules
from .loyalty_schemas import StrategyDocument, Strict
from .models import Customer, Menu, MenuCategory, MenuItem


class PublishedRulePreview(Strict):
    business_id: str
    program_id: str
    version_id: str
    version_digest: str
    version_revision: int
    scenario_digest: str
    result: RulePreview


def preview_published_rules(
    session, business_id: str, program_id: str, version_id: str, scenario: PreviewScenario
) -> PublishedRulePreview:
    version = session.scalar(
        select(LoyaltyStrategyVersion).where(
            LoyaltyStrategyVersion.id == version_id,
            LoyaltyStrategyVersion.strategy_id == program_id,
            LoyaltyStrategyVersion.business_id == business_id,
        )
    )
    if version is None:
        raise NotFoundError("Published program version not found")
    if digest(version.document) != version.digest:
        raise ValidationError("Published configuration digest mismatch")
    products = {line.product_id for line in scenario.lines}
    owned_products = (
        set(
            session.scalars(
                select(MenuItem.id)
                .join(MenuCategory)
                .join(Menu)
                .where(Menu.business_id == business_id, MenuItem.id.in_(products))
            )
        )
        if products
        else set()
    )
    if owned_products != products:
        raise ValidationError("Scenario products must belong to this business")
    if (
        scenario.customer_id is not None
        and session.scalar(
            select(Customer.id).where(
                Customer.id == scenario.customer_id,
                Customer.business_id == business_id,
            )
        )
        is None
    ):
        raise ValidationError("Scenario customer must belong to this business")
    # Stored prices, customer contact matches and current wallet balances are not
    # substituted into an explicitly hypothetical scenario. No identity is granted.
    document = StrategyDocument.model_validate_json(version.document)
    return PublishedRulePreview(
        business_id=business_id,
        program_id=program_id,
        version_id=version.id,
        version_digest=version.digest,
        version_revision=version.revision,
        scenario_digest=digest(canonical(scenario)),
        result=evaluate_rules(document, scenario),
    )
