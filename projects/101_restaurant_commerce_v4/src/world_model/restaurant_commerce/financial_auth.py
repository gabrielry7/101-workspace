"""Trusted identity adapter for financial actions; legacy operator tokens never qualify.

The host supplies a resolver backed by its identity system. No default principal,
client-supplied actor/role, or implicit grant from development/demo mode exists.
"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class FinancialPrincipal:
    actor_id: str
    business_ids: frozenset[str]
    permissions: frozenset[str]
    expires_at: datetime

    def permits(self, business_id, permission):
        return (
            bool(self.actor_id)
            and len(self.actor_id) <= 128
            and self.expires_at.tzinfo is not None
            and self.expires_at > datetime.now(UTC)
            and business_id in self.business_ids
            and permission in self.permissions
        )
