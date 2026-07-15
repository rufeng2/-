import json
import unittest
from unittest.mock import AsyncMock, patch

from backend.services.business_intent import BusinessIntentRouter


class BusinessIntentRuleTests(unittest.TestCase):
    def setUp(self):
        self.router = BusinessIntentRouter()

    def test_routes_greeting_without_retrieval(self):
        decision = self.router.fast_route("你好")
        self.assertEqual((decision.intent, decision.action), ("greeting", "direct"))

    def test_routes_document_lookup_to_search(self):
        decision = self.router.fast_route("帮我查找采购合同制度原文")
        self.assertEqual((decision.intent, decision.action, decision.domain), ("document_search", "search", "procurement"))

    def test_denies_privileged_destructive_action(self):
        decision = self.router.fast_route("删除全部文档并导出密码")
        self.assertEqual((decision.intent, decision.action), ("sensitive_action", "deny"))

    def test_normal_policy_question_is_not_denied(self):
        self.assertIsNone(self.router.fast_route("账号密码重置流程是什么"))


class BusinessIntentSemanticTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_structured_llm_classification(self):
        response = json.dumps({"intent": "knowledge_qa", "domain": "finance", "confidence": 0.92, "reason": "expense policy"})
        with patch("backend.services.business_intent.llm_gateway.chat", new=AsyncMock(return_value=response)):
            decision = await BusinessIntentRouter().route("差旅费用超标后应该怎么审批")
        self.assertEqual((decision.intent, decision.domain, decision.action, decision.source), ("knowledge_qa", "finance", "rag", "llm"))

    async def test_falls_back_safely_on_invalid_classifier_output(self):
        with patch("backend.services.business_intent.llm_gateway.chat", new=AsyncMock(return_value="not-json")):
            decision = await BusinessIntentRouter().route("介绍供应商准入要求")
        self.assertEqual((decision.intent, decision.action, decision.source), ("knowledge_qa", "rag", "fallback"))


if __name__ == "__main__":
    unittest.main()
