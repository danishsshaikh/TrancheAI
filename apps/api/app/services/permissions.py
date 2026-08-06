from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import Role


@dataclass(frozen=True)
class Actor:
    id: str
    roles: set[Role]


READ_ROLES = {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER}
WRITE_ROLES = {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR}
APPROVE_ROLES = {Role.ADMINISTRATOR, Role.FUND_REVIEWER}
EXPORT_ROLES = {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER}


def can(actor: Actor, action: str) -> bool:
    if action == "read":
        return bool(actor.roles & READ_ROLES)
    if action == "write":
        return bool(actor.roles & WRITE_ROLES)
    if action == "approve":
        return bool(actor.roles & APPROVE_ROLES)
    if action == "export":
        return bool(actor.roles & EXPORT_ROLES)
    if action == "audit_read":
        return bool(actor.roles & {Role.ADMINISTRATOR, Role.AUDITOR})
    return False


def require(actor: Actor, action: str) -> None:
    if not can(actor, action):
        raise PermissionError(f"Actor {actor.id} is not allowed to {action}.")

