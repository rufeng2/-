"""Business intent classification and executable routing decisions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re

from backend.config import settings
from backend.services.llm_gateway import llm_gateway
from backend.services.cache_service import cache_service
from backend.utils.logger import logger


INTENTS = {"knowledge_qa", "document_search", "memory_update", "greeting", "capability", "clarification", "sensitive_action", "out_of_scope"}
DOMAINS = {"human_resources", "finance", "procurement", "it_security", "customer_service", "project_management", "data_governance", "administration", "general"}


@dataclass(frozen=True)
class IntentDecision:
    intent: str
    domain: str
    action: str
    confidence: float
    reason: str
    source: str

    def public_payload(self) -> dict:
        return asdict(self)


class BusinessIntentRouter:
    _greeting = re.compile(r"^(你好|您好|嗨|hi|hello|早上好|下午好|晚上好)[!！。\s]*$", re.I)
    _capability = re.compile(r"(你能做什么|有什么功能|怎么使用|如何使用这个系统|你是谁|帮助中心)")
    _document_search = re.compile(r"(查找|找出|搜索|有哪些).{0,12}(文档|文件|制度|原文)|(文档|文件|制度|原文).{0,12}(在哪|有哪些|给我|打开)")
    _dangerous = re.compile(
        r"(删除|修改|覆盖|绕过|导出|泄露|停用|批准|执行).{0,16}"
        r"(全部文档|数据库|权限|密钥|审计日志|安全策略|审批记录)"
        r"|(导出|泄露|获取).{0,12}(全部|所有).{0,8}(密码|账号)"
    )
    _vague = re.compile(r"^(这个|那个|怎么办|为什么|还有呢|继续|详细说说|帮我看看)[？?。\s]*$")
    _memory_update = re.compile(r"(请记住|记住|以后请|我偏好|我习惯|我的部门是|我的岗位是)")
    _domain_patterns = {
        "human_resources": re.compile(r"(员工|入职|离职|转正|绩效|薪酬|年假|人事|招聘)"),
        "finance": re.compile(r"(财务|报销|发票|预算|付款|差旅|费用)"),
        "procurement": re.compile(r"(采购|供应商|合同|用印|报价|招标)"),
        "it_security": re.compile(r"(IT|系统|账号|权限|资产|故障|信息安全|网络)", re.I),
        "customer_service": re.compile(r"(客户|工单|投诉|SLA|服务台|响应时限)", re.I),
        "project_management": re.compile(r"(项目|立项|变更|验收|延期|里程碑)"),
        "data_governance": re.compile(r"(数据|个人信息|隐私|身份证|分类分级)"),
        "administration": re.compile(r"(行政|门禁|访客|办公场所|应急)"),
    }

    @staticmethod
    def _decision(intent: str, domain: str, action: str, confidence: float, reason: str, source: str) -> IntentDecision:
        return IntentDecision(intent, domain, action, max(0.0, min(1.0, confidence)), reason[:160], source)

    def detect_domain(self, query: str) -> str:
        scores = {domain: len(pattern.findall(query)) for domain, pattern in self._domain_patterns.items()}
        domain, score = max(scores.items(), key=lambda item: item[1])
        return domain if score else "general"

    def fast_route(self, query: str, has_images: bool = False) -> IntentDecision | None:
        compact = query.strip()
        domain = self.detect_domain(compact)
        if has_images:
            return self._decision("knowledge_qa", domain, "rag", 0.99, "image input requires multimodal retrieval", "rule")
        if self._dangerous.search(compact):
            return self._decision("sensitive_action", domain, "deny", 0.99, "privileged or destructive action", "rule")
        if self._greeting.fullmatch(compact):
            return self._decision("greeting", "general", "direct", 0.99, "standalone greeting", "rule")
        if self._capability.search(compact):
            return self._decision("capability", "general", "direct", 0.98, "assistant capability question", "rule")
        if self._document_search.search(compact):
            return self._decision("document_search", domain, "search", 0.95, "source document lookup", "rule")
        if self._memory_update.search(compact):
            return self._decision("memory_update", domain, "direct", 0.98, "explicit long-term memory request", "rule")
        if len(compact) <= 2 or self._vague.fullmatch(compact):
            return self._decision("clarification", domain, "clarify", 0.96, "missing searchable business subject", "rule")
        return None

    @staticmethod
    def _extract_json(value: str) -> dict:
        match = re.search(r"\{[\s\S]*\}", value or "")
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    async def route(self, query: str, history: list[dict] | None = None, has_images: bool = False) -> IntentDecision:
        fast = self.fast_route(query, has_images)
        if fast:
            return fast
        fallback_domain = self.detect_domain(query)
        if not settings.INTENT_ROUTER_USE_LLM:
            return self._decision("knowledge_qa", fallback_domain, "rag", 0.60, "LLM routing disabled", "fallback")
        history_text = "\n".join(f"{item.get('role', '')}: {item.get('content', '')[:200]}" for item in (history or [])[-4:])
        intent_cache_key = await cache_service.build_key("intent", {"query": query.strip(), "history": history_text})
        cached = await cache_service.get_json("intent", intent_cache_key)
        if isinstance(cached, dict) and cached.get("intent") in INTENTS and cached.get("domain") in DOMAINS:
            intent = str(cached["intent"])
            action = {"knowledge_qa": "rag", "document_search": "search", "memory_update": "direct", "greeting": "direct", "capability": "direct", "clarification": "clarify", "sensitive_action": "deny", "out_of_scope": "direct"}[intent]
            return self._decision(intent, str(cached["domain"]), action, float(cached.get("confidence", 0.8)), str(cached.get("reason", "cached classification")), "cache")
        prompt = f"""Classify an enterprise knowledge assistant request. Return one JSON object only:
{{"intent":"knowledge_qa|document_search|memory_update|greeting|capability|clarification|sensitive_action|out_of_scope","domain":"human_resources|finance|procurement|it_security|customer_service|project_management|data_governance|administration|general","confidence":0.0,"reason":"short reason"}}
knowledge_qa asks for enterprise facts, policies, processes or explanations. document_search asks to locate source documents. clarification lacks a concrete subject. sensitive_action asks to execute privileged, destructive or data-exfiltration operations; questions about those policies are knowledge_qa. out_of_scope is unrelated to enterprise knowledge.
History: {history_text or '(none)'}
Request: {query}"""
        try:
            raw = await llm_gateway.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=180)
            parsed = self._extract_json(raw)
            intent = str(parsed.get("intent", ""))
            domain = str(parsed.get("domain", fallback_domain))
            confidence = float(parsed.get("confidence", 0.0))
            if intent not in INTENTS or domain not in DOMAINS or confidence < settings.INTENT_ROUTER_CONFIDENCE_THRESHOLD:
                raise ValueError("invalid or low-confidence intent response")
            action = {"knowledge_qa": "rag", "document_search": "search", "memory_update": "direct", "greeting": "direct", "capability": "direct", "clarification": "clarify", "sensitive_action": "deny", "out_of_scope": "direct"}[intent]
            decision = self._decision(intent, domain, action, confidence, str(parsed.get("reason", "semantic classification")), "llm")
            await cache_service.set_json("intent", intent_cache_key, decision.public_payload(), settings.INTENT_CACHE_TTL_SECONDS)
            return decision
        except Exception as exc:
            logger.warning("Intent routing failed, using knowledge QA fallback: %s", exc)
            return self._decision("knowledge_qa", fallback_domain, "rag", 0.50, "classifier unavailable; safe retrieval fallback", "fallback")

    @staticmethod
    def direct_answer(decision: IntentDecision) -> str:
        answers = {
            "greeting": "你好，我是企业知识库助手。你可以询问公司制度、业务流程、项目规范，或让我查找相关原文。",
            "capability": "我可以基于你有权限访问的知识库回答制度和流程问题、查找原文与引用，并分析上传的图片或图表。",
            "clarification": "请补充具体的业务对象或问题，例如制度名称、流程环节、项目或文档主题。",
            "sensitive_action": "我不能执行删除、修改权限、导出敏感数据等高风险操作。你可以询问相关制度或申请流程。",
            "out_of_scope": "这个问题不属于当前企业知识库的服务范围。请改为询问公司制度、流程、项目或文档内容。",
            "memory_update": "我已记住这项偏好，后续对话会在相关问题中参考。",
        }
        return answers.get(decision.intent, "请补充你希望查询的具体内容。")


business_intent_router = BusinessIntentRouter()
