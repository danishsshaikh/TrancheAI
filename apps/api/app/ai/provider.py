from __future__ import annotations

from typing import Protocol

from app.ai.schemas import AIProposal


class AIProvider(Protocol):
    def propose(self, user_request: str) -> AIProposal:
        """Return a structured proposal. Providers must not mutate application data."""


class FakeAIProvider:
    def __init__(self, proposal: AIProposal | None = None) -> None:
        self.proposal = proposal or AIProposal(action="search_projects", payload={"query": ""}, requires_confirmation=False)

    def propose(self, user_request: str) -> AIProposal:
        if self.proposal.payload.get("query") == "":
            return AIProposal(action=self.proposal.action, payload={"query": user_request}, requires_confirmation=self.proposal.requires_confirmation)
        return self.proposal

