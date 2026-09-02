from __future__ import annotations

import json
import unittest
from decimal import Decimal
from typing import Any, cast

from sqlalchemy.orm import Session

from app.ai.assistant_service import AIAssistantService, _amount
from app.ai.provider import (
    AIProviderConfigurationError,
    AIProviderMalformedResponse,
    AIProviderUnavailable,
    FakeAIAssistantProvider,
    OpenAICompatibleProvider,
    ProviderHTTPResult,
)
from app.ai.schemas import AIProviderEnvelope
from app.core.enums import Role
from app.models.domain import UserModel


class AIAssistantUnitTests(unittest.TestCase):
    def test_openai_compatible_provider_posts_chat_payload_and_preserves_unicode(self) -> None:
        captured: dict[str, Any] = {}

        def transport(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_seconds: float) -> ProviderHTTPResult:
            captured.update({"url": url, "payload": payload, "headers": headers, "timeout": timeout_seconds})
            content = json.dumps({"kind": "answer", "message": "ठीक आहे", "arguments": {}})
            return ProviderHTTPResult(200, json.dumps({"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}))

        provider = OpenAICompatibleProvider(
            base_url="http://ai-provider.test/v1",
            model="server-configured-model",
            api_key="local-key",
            timeout_seconds=15,
            max_tokens=256,
            temperature=0.2,
            transport=transport,
        )

        envelope = provider.complete(system_prompt="system", user_text="माझा प्रकल्प दाखवा", context={"current_project_code": "SP-001"})

        self.assertEqual(envelope.kind, "answer")
        self.assertEqual(captured["url"], "http://ai-provider.test/v1/chat/completions")
        self.assertEqual(captured["payload"]["model"], "server-configured-model")
        self.assertEqual(captured["payload"]["max_tokens"], 256)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer local-key")
        self.assertIn("माझा प्रकल्प दाखवा", captured["payload"]["messages"][1]["content"])

    def test_openai_compatible_provider_rejects_bad_provider_responses(self) -> None:
        provider = OpenAICompatibleProvider(
            base_url="http://ai-provider.test/v1",
            model="server-configured-model",
            transport=lambda _url, _payload, _headers, _timeout: ProviderHTTPResult(200, json.dumps({"choices": [{"message": {"content": "plain prose"}, "finish_reason": "stop"}]})),
        )
        with self.assertRaises(AIProviderMalformedResponse):
            provider.complete(system_prompt="system", user_text="bad")

        truncated = OpenAICompatibleProvider(
            base_url="http://ai-provider.test/v1",
            model="server-configured-model",
            transport=lambda _url, _payload, _headers, _timeout: ProviderHTTPResult(200, json.dumps({"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]})),
        )
        with self.assertRaises(AIProviderMalformedResponse):
            truncated.complete(system_prompt="system", user_text="bad")

        refused = OpenAICompatibleProvider(
            base_url="http://ai-provider.test/v1",
            model="server-configured-model",
            transport=lambda _url, _payload, _headers, _timeout: ProviderHTTPResult(200, json.dumps({"choices": [{"message": {"refusal": "no", "content": "{}"}, "finish_reason": "stop"}]})),
        )
        with self.assertRaises(AIProviderMalformedResponse):
            refused.complete(system_prompt="system", user_text="bad")

    def test_openai_compatible_provider_rejects_unavailable_or_missing_configuration(self) -> None:
        unavailable = OpenAICompatibleProvider(
            base_url="http://ai-provider.test/v1",
            model="server-configured-model",
            transport=lambda _url, _payload, _headers, _timeout: ProviderHTTPResult(503, "{}"),
        )
        with self.assertRaises(AIProviderUnavailable):
            unavailable.complete(system_prompt="system", user_text="bad")

        with self.assertRaises(AIProviderConfigurationError):
            OpenAICompatibleProvider(base_url="", model="model").complete(system_prompt="system", user_text="bad")
        with self.assertRaises(AIProviderConfigurationError):
            OpenAICompatibleProvider(base_url="http://ai-provider.test/v1", model="").complete(system_prompt="system", user_text="bad")

    def test_service_returns_safe_errors_without_database_access_for_disabled_or_malicious_actions(self) -> None:
        actor = UserModel(id="00000000-0000-0000-0000-000000000001", email="admin@example.test", full_name="Admin", password_hash="x", role=Role.ADMINISTRATOR.value)
        disabled = AIAssistantService(
            session=cast(Session, object()),
            provider=FakeAIAssistantProvider(AIProviderEnvelope(kind="answer", message="unused")),
            ai_enabled=False,
            provider_base_url="http://ai-provider.test/v1",
            provider_model="server-configured-model",
        )
        self.assertEqual(disabled.request(actor=actor, text="hello")["kind"], "error")

        forbidden = AIAssistantService(
            session=cast(Session, object()),
            provider=FakeAIAssistantProvider(AIProviderEnvelope(kind="proposal", message="bad", action="create_project", arguments={"project_code": "X", "title": "X", "sql": "drop table users"})),
            ai_enabled=True,
            provider_base_url="http://ai-provider.test/v1",
            provider_model="server-configured-model",
        )
        result = forbidden.request(actor=actor, text="bad")
        self.assertEqual(result["kind"], "error")
        self.assertIn("forbidden field", str(result["message"]))

        unsupported = AIAssistantService(
            session=cast(Session, object()),
            provider=FakeAIAssistantProvider(AIProviderEnvelope(kind="proposal", message="bad", action="drop_database", arguments={})),
            ai_enabled=True,
            provider_base_url="http://ai-provider.test/v1",
            provider_model="server-configured-model",
        )
        self.assertEqual(unsupported.request(actor=actor, text="bad")["kind"], "error")

    def test_amount_parser_accepts_inr_shortcuts(self) -> None:
        self.assertEqual(_amount("1.5 lakh"), Decimal("150000.00"))
        self.assertEqual(_amount("2 cr"), Decimal("20000000.00"))
        self.assertEqual(_amount("₹12,345.5"), Decimal("12345.50"))


if __name__ == "__main__":
    unittest.main()
