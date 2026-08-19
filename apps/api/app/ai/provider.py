from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.ai.schemas import AIProposal, AIProviderEnvelope


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


class AIAssistantProvider(Protocol):
    provider_name: str
    model: str

    def complete(self, *, system_prompt: str, user_text: str, context: dict[str, Any] | None = None) -> AIProviderEnvelope:
        """Return a strict structured assistant envelope without mutating application data."""


class AIProviderError(RuntimeError):
    pass


class AIProviderUnavailable(AIProviderError):
    pass


class AIProviderConfigurationError(AIProviderError):
    pass


class AIProviderMalformedResponse(AIProviderError):
    pass


@dataclass(frozen=True)
class ProviderHTTPResult:
    status_code: int
    body: str


ProviderTransport = Callable[[str, dict[str, Any], dict[str, str], float], ProviderHTTPResult]


class OpenAICompatibleProvider:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 60,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        transport: ProviderTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.transport = transport or _urllib_transport

    def complete(self, *, system_prompt: str, user_text: str, context: dict[str, Any] | None = None) -> AIProviderEnvelope:
        if not self.base_url:
            raise AIProviderConfigurationError("AI_BASE_URL is not configured.")
        if not self.model:
            raise AIProviderConfigurationError("AI_MODEL is not configured.")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"request": user_text, "context": context or {}}, ensure_ascii=False)},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        result = self.transport(f"{self.base_url}/chat/completions", payload, headers, self.timeout_seconds)
        if result.status_code < 200 or result.status_code >= 300:
            raise AIProviderUnavailable(f"AI provider returned HTTP {result.status_code}.")
        try:
            data = json.loads(result.body)
            choice = data["choices"][0]
            if choice.get("finish_reason") == "length":
                raise AIProviderMalformedResponse("AI provider response was truncated.")
            message = choice.get("message") or {}
            if message.get("refusal"):
                raise AIProviderMalformedResponse("AI provider refused the request.")
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise AIProviderMalformedResponse("AI provider returned an empty response.")
            envelope = AIProviderEnvelope.model_validate_json(content)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderMalformedResponse("AI provider returned malformed structured output.") from exc
        return envelope


class FakeAIAssistantProvider:
    provider_name = "fake"

    def __init__(self, envelope: AIProviderEnvelope | Exception) -> None:
        self.envelope = envelope
        self.model = "fake-model"

    def complete(self, *, system_prompt: str, user_text: str, context: dict[str, Any] | None = None) -> AIProviderEnvelope:
        if isinstance(self.envelope, Exception):
            raise self.envelope
        return self.envelope


def _urllib_transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_seconds: float) -> ProviderHTTPResult:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return ProviderHTTPResult(response.status, response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise AIProviderUnavailable("AI provider request timed out.") from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return ProviderHTTPResult(exc.code, body)
    except urllib.error.URLError as exc:
        raise AIProviderUnavailable("AI provider is unavailable.") from exc
