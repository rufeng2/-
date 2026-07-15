# Ecommerce Operations Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the copied knowledge-base project into a dedicated, resume-ready intelligent ecommerce operations Agent platform that highlights AI Agent orchestration and data analysis.

**Architecture:** Keep the existing FastAPI + Vue 3 + auth + RAG foundation, but replace the product identity and primary workflows with ecommerce operations. Add a deterministic ecommerce analytics domain layer backed by local demo data, then expose it through Agent-style APIs that return intent, tool traces, evidence, recommendations, and approval state. Frontend pages consume those APIs as an operations dashboard, Agent workspace, product analysis, campaign planner, and recommendation approval center.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, Vue 3, TypeScript, Element Plus, Pinia, Vue Router, Vite.

## Global Constraints

- Product identity must be "智能电商运营 Agent 平台".
- Keep FastAPI, Vue 3, login/auth, API client, RAG/LangChain, Docker, test, and production configuration foundations.
- Replace visible "企业知识库问答" identity with ecommerce operations language in README, app metadata, health checks, sidebar, login page, route titles, and export names.
- First version must run without real ecommerce platforms, internal systems, or LLM API keys.
- LLM can enhance wording only; deterministic metrics and tool results remain the source of truth.
- High-risk actions such as price changes, ad budget increases, coupons, and clearance must create approval recommendations instead of executing directly.
- The UI must be an operations tool: dense metrics, tables, status tags, timelines, and task lists; no marketing landing page.
- Every backend response for Agent analysis must include data evidence and tool trace fields so the UI can show why the Agent made a judgment.

---

## File Structure

Create backend ecommerce domain files:

- `backend/ecommerce/__init__.py`: package marker and public exports.
- `backend/ecommerce/schemas.py`: Pydantic models for metrics, anomalies, Agent traces, recommendations, products, campaigns.
- `backend/ecommerce/data_loader.py`: load deterministic CSV/JSON demo data from `data/ecommerce`.
- `backend/ecommerce/metrics.py`: compute KPI snapshots, trends, product metrics, ad ROI, review summaries.
- `backend/ecommerce/anomaly.py`: convert metric deltas and thresholds into explainable anomalies.
- `backend/ecommerce/segmentation.py`: classify products into hero, profit, traffic, clearance, and risk buckets.
- `backend/ecommerce/recommendations.py`: in-memory recommendation store with approve/reject transitions.
- `backend/ecommerce/tools.py`: Agent callable tool registry and typed tool results.
- `backend/ecommerce/agent.py`: intent routing and tool orchestration for built-in operations questions.
- `backend/api/ecommerce.py`: FastAPI router for dashboard, products, Agent analysis, campaigns, recommendations.

Create data files:

- `data/ecommerce/products.csv`
- `data/ecommerce/orders.csv`
- `data/ecommerce/traffic.csv`
- `data/ecommerce/ad_spend.csv`
- `data/ecommerce/inventory.csv`
- `data/ecommerce/reviews.csv`
- `data/ecommerce/competitors.csv`
- `data/ecommerce/operation_rules.json`

Modify backend files:

- `backend/main.py`: register ecommerce router and replace app/root/health product identity.

Create frontend files:

- `frontend/src/views/Ecommerce/Dashboard.vue`
- `frontend/src/views/Ecommerce/AgentWorkspace.vue`
- `frontend/src/views/Ecommerce/Products.vue`
- `frontend/src/views/Ecommerce/Campaigns.vue`
- `frontend/src/views/Ecommerce/Recommendations.vue`

Modify frontend files:

- `frontend/src/api/client.ts`: add `ecommerceAPI`.
- `frontend/src/router/index.ts`: replace default authenticated route with `/dashboard`; add ecommerce routes; retitle legacy knowledge/evaluation routes.
- `frontend/src/App.vue`: replace sidebar brand and navigation.
- `frontend/src/views/Login.vue`: replace login product identity and redirect to `/dashboard`.
- `frontend/src/styles/global.css`: keep existing shell styles; ecommerce pages use scoped CSS in their Vue files.

Modify docs:

- `README.md`: rewrite as ecommerce operations Agent project.

Create tests:

- `tests/test_ecommerce_metrics.py`
- `tests/test_ecommerce_agent.py`
- `tests/test_ecommerce_api_contract.py`
- `tests/test_ecommerce_frontend_contract.py`

---

### Task 1: Product Identity Replacement

**Files:**
- Modify: `backend/main.py`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/Login.vue`
- Modify: `frontend/src/api/client.ts`
- Modify: `README.md`
- Test: `tests/test_ecommerce_frontend_contract.py`
- Test: `tests/test_deployment_contract.py`

**Interfaces:**
- Consumes: Existing FastAPI `app`, Vue router, auth store, `operationsAPI.exportPrivacy()`.
- Produces: Product identity strings and route names that later ecommerce pages rely on: `/dashboard`, `/agent`, `/products`, `/campaigns`, `/recommendations`, `/knowledge`, `/evaluation`, `/admin`.

- [ ] **Step 1: Write failing frontend branding contract**

Create `tests/test_ecommerce_frontend_contract.py` with:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_uses_ecommerce_product_identity():
    app = read("frontend/src/App.vue")
    login = read("frontend/src/views/Login.vue")
    router = read("frontend/src/router/index.ts")

    assert "智能电商运营 Agent 平台" in app
    assert "运营驾驶舱" in app
    assert "运营 Agent" in app
    assert "运营知识库" in app
    assert "智能电商运营 Agent 平台" in login
    assert 'path: "/dashboard"' in router
    assert 'path: "/agent"' in router
    assert 'path: "/recommendations"' in router
    assert "企业知识库问答" not in app + login + router


def test_frontend_api_exports_ecommerce_client():
    client = read("frontend/src/api/client.ts")
    assert "export const ecommerceAPI" in client
    assert 'client.get("/ecommerce/dashboard")' in client
    assert 'client.post("/ecommerce/agent/analyze"' in client
```

- [ ] **Step 2: Run contract test to verify it fails**

Run:

```powershell
pytest tests/test_ecommerce_frontend_contract.py -v
```

Expected: FAIL because the copied frontend still contains old product identity and no ecommerce API client.

- [ ] **Step 3: Replace backend app/root/health identity**

In `backend/main.py`, replace the FastAPI metadata and root/health app names with:

```python
app = FastAPI(
    title="智能电商运营 Agent 平台",
    description="基于模拟电商经营数据、工具调用和审批闭环的 AI 运营决策系统",
    version="1.0.0",
    lifespan=lifespan,
)
```

Replace `health()` app data with:

```python
return {
    "status": "ok",
    "app": "ecommerce-operations-agent",
    "models": {
        "chat": f"{settings.LLM_MODEL} (optional LLM enhancement)",
        "orchestration": "Deterministic ecommerce tools + optional LangChain Runnable",
        "embedding": "text-embedding-v3 + multimodal-embedding-v1 (for operations knowledge base)",
        "reranker": reranker.get_model_info(),
        "vision": "qwen-vl-plus (DashScope, optional)" if settings.DASHSCOPE_API_KEY else "not configured",
    },
    "config": {
        "retrieval_top_k": settings.RETRIEVAL_TOP_K,
        "rerank_top_k": settings.RETRIEVAL_RERANK_TOP_K,
        "use_rerank": settings.RETRIEVAL_USE_RERANK,
    },
}
```

Replace `root()` return value with:

```python
return {
    "app": "智能电商运营 Agent 平台",
    "docs": "/docs",
    "openapi": "/openapi.json",
    "version": "1.0.0",
    "primary_workflow": "/api/ecommerce/dashboard",
}
```

- [ ] **Step 4: Replace frontend router**

Replace `frontend/src/router/index.ts` with:

```ts
import { createRouter, createWebHistory } from "vue-router"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "login", component: () => import("@/views/Login.vue"), meta: { title: "登录", public: true } },
    { path: "/dashboard", name: "dashboard", component: () => import("@/views/Ecommerce/Dashboard.vue"), meta: { title: "运营驾驶舱", requiresAuth: true } },
    { path: "/agent", name: "agent", component: () => import("@/views/Ecommerce/AgentWorkspace.vue"), meta: { title: "运营 Agent", requiresAuth: true } },
    { path: "/products", name: "products", component: () => import("@/views/Ecommerce/Products.vue"), meta: { title: "商品分析", requiresAuth: true } },
    { path: "/campaigns", name: "campaigns", component: () => import("@/views/Ecommerce/Campaigns.vue"), meta: { title: "活动策略", requiresAuth: true } },
    { path: "/recommendations", name: "recommendations", component: () => import("@/views/Ecommerce/Recommendations.vue"), meta: { title: "建议审批", requiresAuth: true } },
    { path: "/knowledge", name: "knowledge", component: () => import("@/views/Documents.vue"), meta: { title: "运营知识库", requiresAuth: true } },
    { path: "/evaluation", name: "evaluation", component: () => import("@/views/Evaluation.vue"), meta: { title: "Agent 分析质量评测", requiresAuth: true, requiresAdmin: true } },
    { path: "/admin", name: "admin", component: () => import("@/views/Admin/Dashboard.vue"), meta: { title: "运营管理后台", requiresAuth: true, requiresAdmin: true } },
    { path: "/:pathMatch(.*)*", redirect: "/dashboard" },
  ],
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || "运营工作台"} - 智能电商运营 Agent 平台`

  const token = localStorage.getItem("token")
  const role = localStorage.getItem("role")

  if (to.meta.requiresAuth && !token) {
    next({ name: "login" })
  } else if (to.meta.requiresAdmin && role !== "admin") {
    next({ name: "dashboard" })
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 5: Replace sidebar shell identity and links**

In `frontend/src/App.vue`, replace brand and navigation copy with:

```vue
<div class="brand">
  <span class="brand-mark">E</span>
  <div class="sidebar-copy"><strong>智能电商运营</strong><small>Agent Workspace</small></div>
</div>
<nav>
  <router-link to="/dashboard" title="运营驾驶舱"><el-icon><DataBoard /></el-icon><span class="sidebar-copy">运营驾驶舱</span></router-link>
  <router-link to="/agent" title="运营 Agent"><el-icon><ChatDotRound /></el-icon><span class="sidebar-copy">运营 Agent</span></router-link>
  <router-link to="/products" title="商品分析"><el-icon><Goods /></el-icon><span class="sidebar-copy">商品分析</span></router-link>
  <router-link to="/campaigns" title="活动策略"><el-icon><Calendar /></el-icon><span class="sidebar-copy">活动策略</span></router-link>
  <router-link to="/recommendations" title="建议审批"><el-icon><Checked /></el-icon><span class="sidebar-copy">建议审批</span></router-link>
  <router-link to="/knowledge" title="运营知识库"><el-icon><Files /></el-icon><span class="sidebar-copy">运营知识库</span></router-link>
  <router-link v-if="auth.isAdmin" to="/evaluation" title="分析质量评测"><el-icon><DataAnalysis /></el-icon><span class="sidebar-copy">质量评测</span></router-link>
  <router-link v-if="auth.isAdmin" to="/admin" title="运营管理后台"><el-icon><Setting /></el-icon><span class="sidebar-copy">运营管理</span></router-link>
</nav>
```

Update the imports:

```ts
import { ArrowLeft, ArrowRight, Calendar, ChatDotRound, Checked, DataAnalysis, DataBoard, Files, Goods, Menu, MoreFilled, Setting } from "@element-plus/icons-vue"
```

Change export filename:

```ts
link.download = "ecommerce-agent-" + auth.username + ".json"
```

- [ ] **Step 6: Replace login page identity and redirects**

In `frontend/src/views/Login.vue`, change visible copy to:

```vue
<div class="product"><span>E</span><div><h1>智能电商运营 Agent 平台</h1><p>经营分析、策略生成与审批闭环</p></div></div>
```

Change token redirect:

```ts
location.href = "/dashboard"
```

Change successful login redirect:

```ts
router.push(result.role === "admin" ? "/dashboard" : "/dashboard")
```

Change footer:

```vue
<footer><span class="status-dot"></span>运营分析服务已连接</footer>
```

- [ ] **Step 7: Add ecommerce API client methods**

In `frontend/src/api/client.ts`, append:

```ts
export const ecommerceAPI = {
  dashboard: () => client.get("/ecommerce/dashboard"),
  products: () => client.get("/ecommerce/products"),
  analyze: (question: string) => client.post("/ecommerce/agent/analyze", { question }),
  campaignPlan: (goal = "大促增长") => client.get("/ecommerce/campaigns/plan", { params: { goal } }),
  recommendations: (status = "") => client.get("/ecommerce/recommendations", { params: { status } }),
  approveRecommendation: (id: string) => client.post(`/ecommerce/recommendations/${id}/approve`),
  rejectRecommendation: (id: string) => client.post(`/ecommerce/recommendations/${id}/reject`),
}
```

- [ ] **Step 8: Rewrite README project opening**

Rewrite `README.md` to start with:

```markdown
# 智能电商运营 Agent 平台

基于 FastAPI、Vue 3、LangChain/RAG 和模拟电商经营数据构建的 AI 运营决策系统。项目聚焦 AI Agent 工程能力和数据分析能力，支持运营驾驶舱、经营异常诊断、商品分层、活动策略生成、广告 ROI 分析、库存风险识别和人工审批闭环。
```

Include these demo bullets in README:

```markdown
## 简历亮点

- 设计确定性电商经营数据集，覆盖订单、流量、广告、库存、评价和竞品数据。
- 实现多工具调用 Agent，返回意图识别、工具轨迹、数据证据、结论和建议动作。
- 实现 GMV、转化率、客单价、广告 ROI、库存风险和差评率等指标分析。
- 通过建议审批中心模拟企业级风控闭环，高风险动作只生成待审批任务。
```

- [ ] **Step 9: Run contract tests**

Run:

```powershell
pytest tests/test_ecommerce_frontend_contract.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

Run:

```powershell
git add backend/main.py frontend/src/router/index.ts frontend/src/App.vue frontend/src/views/Login.vue frontend/src/api/client.ts README.md tests/test_ecommerce_frontend_contract.py
git commit -m "refactor: rebrand as ecommerce operations agent"
```

---

### Task 2: Deterministic Ecommerce Demo Data

**Files:**
- Create: `data/ecommerce/products.csv`
- Create: `data/ecommerce/orders.csv`
- Create: `data/ecommerce/traffic.csv`
- Create: `data/ecommerce/ad_spend.csv`
- Create: `data/ecommerce/inventory.csv`
- Create: `data/ecommerce/reviews.csv`
- Create: `data/ecommerce/competitors.csv`
- Create: `data/ecommerce/operation_rules.json`
- Create: `backend/ecommerce/__init__.py`
- Create: `backend/ecommerce/schemas.py`
- Create: `backend/ecommerce/data_loader.py`
- Test: `tests/test_ecommerce_metrics.py`

**Interfaces:**
- Produces: `EcommerceDataLoader.load() -> EcommerceDataset`.
- Produces: Pydantic models `ProductRecord`, `OrderRecord`, `TrafficRecord`, `AdSpendRecord`, `InventoryRecord`, `ReviewRecord`, `CompetitorRecord`, `OperationRules`, `EcommerceDataset`.
- Later tasks consume `EcommerceDataset` for metrics, Agent tools, API responses, and frontend demo content.

- [ ] **Step 1: Write failing data loader test**

Create `tests/test_ecommerce_metrics.py` with:

```python
from pathlib import Path

from backend.ecommerce.data_loader import EcommerceDataLoader


def test_loader_reads_all_demo_tables():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()

    assert len(dataset.products) == 8
    assert len(dataset.orders) >= 16
    assert len(dataset.traffic) >= 16
    assert len(dataset.ad_spend) >= 8
    assert len(dataset.inventory) == 8
    assert len(dataset.reviews) >= 8
    assert len(dataset.competitors) >= 4
    assert dataset.rules.thresholds["low_roi"] == 1.8
```

- [ ] **Step 2: Run loader test to verify it fails**

Run:

```powershell
pytest tests/test_ecommerce_metrics.py::test_loader_reads_all_demo_tables -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.ecommerce'`.

- [ ] **Step 3: Create demo data directory and product table**

Create `data/ecommerce/products.csv`:

```csv
product_id,name,category,price,cost,launch_date,positioning
P001,云感防晒衣,服饰,199,92,2026-05-01,hero
P002,轻量跑步鞋,鞋包,329,168,2026-04-18,profit
P003,便携榨汁杯,小家电,149,78,2026-03-20,traffic
P004,智能体脂秤,数码健康,129,64,2026-02-10,profit
P005,露营折叠椅,户外,89,48,2026-01-25,clearance
P006,抗菌保温杯,日用,79,35,2026-06-12,new
P007,儿童护眼台灯,家居,259,136,2026-04-03,hero
P008,真无线降噪耳机,数码,399,235,2026-05-28,risk
```

- [ ] **Step 4: Create order table with explainable GMV drop**

Create `data/ecommerce/orders.csv`:

```csv
date,product_id,orders,units,gmv,refund_amount
2026-07-08,P001,42,48,9552,0
2026-07-08,P002,25,26,8554,0
2026-07-08,P003,31,35,5215,149
2026-07-08,P007,18,19,4921,0
2026-07-14,P001,40,45,8955,199
2026-07-14,P002,27,28,9212,0
2026-07-14,P003,34,39,5811,0
2026-07-14,P007,20,21,5439,0
2026-07-15,P001,24,27,5373,398
2026-07-15,P002,18,18,5922,0
2026-07-15,P003,27,27,4023,149
2026-07-15,P004,14,14,1806,0
2026-07-15,P005,9,12,1068,0
2026-07-15,P006,15,15,1185,0
2026-07-15,P007,8,8,2072,259
2026-07-15,P008,6,6,2394,798
```

- [ ] **Step 5: Create traffic table showing conversion pressure**

Create `data/ecommerce/traffic.csv`:

```csv
date,product_id,impressions,visitors,add_to_cart
2026-07-08,P001,16800,2100,188
2026-07-08,P002,9800,1120,104
2026-07-08,P003,12400,1450,116
2026-07-08,P007,7600,820,66
2026-07-14,P001,17100,2140,184
2026-07-14,P002,10100,1165,112
2026-07-14,P003,12800,1490,128
2026-07-14,P007,7900,850,71
2026-07-15,P001,16950,2125,128
2026-07-15,P002,10250,1170,113
2026-07-15,P003,13100,1530,141
2026-07-15,P004,7200,760,62
2026-07-15,P005,5600,590,42
2026-07-15,P006,8400,1180,74
2026-07-15,P007,8050,845,48
2026-07-15,P008,9200,980,53
```

- [ ] **Step 6: Create ad, inventory, review, competitor, and rules data**

Create `data/ecommerce/ad_spend.csv`:

```csv
date,campaign_id,product_id,channel,spend,attributed_gmv,clicks
2026-07-14,C001,P001,搜索广告,1800,7200,620
2026-07-14,C002,P003,信息流,900,4100,430
2026-07-14,C003,P008,搜索广告,1300,3900,360
2026-07-15,C001,P001,搜索广告,2600,5200,710
2026-07-15,C002,P003,信息流,980,4500,455
2026-07-15,C003,P008,搜索广告,1850,3200,420
2026-07-15,C004,P006,达人短视频,760,1800,390
2026-07-15,C005,P007,信息流,1100,2400,330
```

Create `data/ecommerce/inventory.csv`:

```csv
product_id,stock,safety_stock,inbound_units,lead_time_days
P001,62,80,120,3
P002,210,90,0,5
P003,340,120,0,4
P004,160,70,80,6
P005,520,100,0,2
P006,48,60,160,7
P007,38,75,90,4
P008,95,80,0,6
```

Create `data/ecommerce/reviews.csv`:

```csv
date,product_id,rating,topic,comment_count
2026-07-14,P001,4.7,面料轻薄,36
2026-07-14,P007,4.6,光线柔和,18
2026-07-15,P001,3.6,尺码偏小,21
2026-07-15,P001,3.8,物流慢,15
2026-07-15,P007,3.5,包装破损,12
2026-07-15,P008,3.4,降噪不稳定,17
2026-07-15,P003,4.5,便携好清洗,29
2026-07-15,P006,4.4,保温效果好,14
```

Create `data/ecommerce/competitors.csv`:

```csv
date,product_id,competitor_price,competitor_promo
2026-07-15,P001,169,竞品限时直降
2026-07-15,P002,319,竞品满300减30
2026-07-15,P007,239,竞品赠送灯架
2026-07-15,P008,359,竞品平台补贴
```

Create `data/ecommerce/operation_rules.json`:

```json
{
  "thresholds": {
    "low_roi": 1.8,
    "critical_stock_ratio": 1.0,
    "warning_stock_ratio": 1.4,
    "conversion_drop_pct": -20,
    "gmv_drop_pct": -15,
    "bad_rating": 4.0
  },
  "risk_actions": {
    "price_change": "high",
    "ad_budget_increase": "high",
    "coupon": "high",
    "clearance": "high",
    "content_optimization": "low",
    "customer_service_followup": "low",
    "campaign_plan": "medium"
  }
}
```

- [ ] **Step 7: Create ecommerce schemas**

Create `backend/ecommerce/schemas.py`:

```python
from datetime import date
from pydantic import BaseModel


class ProductRecord(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    cost: float
    launch_date: date
    positioning: str


class OrderRecord(BaseModel):
    date: date
    product_id: str
    orders: int
    units: int
    gmv: float
    refund_amount: float


class TrafficRecord(BaseModel):
    date: date
    product_id: str
    impressions: int
    visitors: int
    add_to_cart: int


class AdSpendRecord(BaseModel):
    date: date
    campaign_id: str
    product_id: str
    channel: str
    spend: float
    attributed_gmv: float
    clicks: int


class InventoryRecord(BaseModel):
    product_id: str
    stock: int
    safety_stock: int
    inbound_units: int
    lead_time_days: int


class ReviewRecord(BaseModel):
    date: date
    product_id: str
    rating: float
    topic: str
    comment_count: int


class CompetitorRecord(BaseModel):
    date: date
    product_id: str
    competitor_price: float
    competitor_promo: str


class OperationRules(BaseModel):
    thresholds: dict[str, float]
    risk_actions: dict[str, str]


class EcommerceDataset(BaseModel):
    products: list[ProductRecord]
    orders: list[OrderRecord]
    traffic: list[TrafficRecord]
    ad_spend: list[AdSpendRecord]
    inventory: list[InventoryRecord]
    reviews: list[ReviewRecord]
    competitors: list[CompetitorRecord]
    rules: OperationRules
```

- [ ] **Step 8: Create data loader implementation**

Create `backend/ecommerce/data_loader.py`:

```python
import csv
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from backend.ecommerce.schemas import (
    AdSpendRecord,
    CompetitorRecord,
    EcommerceDataset,
    InventoryRecord,
    OperationRules,
    OrderRecord,
    ProductRecord,
    ReviewRecord,
    TrafficRecord,
)

T = TypeVar("T", bound=BaseModel)


class EcommerceDataLoader:
    def __init__(self, root: Path | str = Path("data/ecommerce")):
        self.root = Path(root)

    def load(self) -> EcommerceDataset:
        missing = [name for name in self.required_files() if not (self.root / name).exists()]
        if missing:
            raise FileNotFoundError(f"Missing ecommerce demo data files in {self.root}: {', '.join(missing)}")

        return EcommerceDataset(
            products=self._read_csv("products.csv", ProductRecord),
            orders=self._read_csv("orders.csv", OrderRecord),
            traffic=self._read_csv("traffic.csv", TrafficRecord),
            ad_spend=self._read_csv("ad_spend.csv", AdSpendRecord),
            inventory=self._read_csv("inventory.csv", InventoryRecord),
            reviews=self._read_csv("reviews.csv", ReviewRecord),
            competitors=self._read_csv("competitors.csv", CompetitorRecord),
            rules=OperationRules.model_validate(json.loads((self.root / "operation_rules.json").read_text(encoding="utf-8"))),
        )

    @staticmethod
    def required_files() -> list[str]:
        return [
            "products.csv",
            "orders.csv",
            "traffic.csv",
            "ad_spend.csv",
            "inventory.csv",
            "reviews.csv",
            "competitors.csv",
            "operation_rules.json",
        ]

    def _read_csv(self, filename: str, model: type[T]) -> list[T]:
        with (self.root / filename).open("r", encoding="utf-8-sig", newline="") as handle:
            return [model.model_validate(row) for row in csv.DictReader(handle)]
```

Create `backend/ecommerce/__init__.py`:

```python
"""Ecommerce operations analytics and Agent orchestration."""
```

- [ ] **Step 9: Run loader test**

Run:

```powershell
pytest tests/test_ecommerce_metrics.py::test_loader_reads_all_demo_tables -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

Run:

```powershell
git add data/ecommerce backend/ecommerce tests/test_ecommerce_metrics.py
git commit -m "feat: add ecommerce demo dataset"
```

---

### Task 3: Metrics, Anomaly Detection, and Product Segmentation

**Files:**
- Modify: `backend/ecommerce/schemas.py`
- Create: `backend/ecommerce/metrics.py`
- Create: `backend/ecommerce/anomaly.py`
- Create: `backend/ecommerce/segmentation.py`
- Modify: `tests/test_ecommerce_metrics.py`

**Interfaces:**
- Consumes: `EcommerceDataset`.
- Produces: `build_dashboard(dataset: EcommerceDataset) -> DashboardSummary`.
- Produces: `build_product_analysis(dataset: EcommerceDataset) -> list[ProductAnalysis]`.
- Produces: `detect_anomalies(dataset: EcommerceDataset) -> list[Anomaly]`.

- [ ] **Step 1: Add failing metrics tests**

Append to `tests/test_ecommerce_metrics.py`:

```python
from backend.ecommerce.anomaly import detect_anomalies
from backend.ecommerce.metrics import build_dashboard, safe_div
from backend.ecommerce.segmentation import build_product_analysis


def test_safe_div_handles_zero_denominator():
    assert safe_div(10, 0) == 0
    assert safe_div(10, 4) == 2.5


def test_dashboard_computes_core_kpis_and_detects_drop():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    dashboard = build_dashboard(dataset)

    assert dashboard.kpis["gmv"]["value"] == 23843
    assert dashboard.kpis["orders"]["value"] == 121
    assert dashboard.kpis["ad_roi"]["value"] < 2.5
    assert dashboard.kpis["gmv"]["delta_pct"] < -15
    assert any(item.metric == "gmv" for item in dashboard.anomalies)


def test_product_analysis_labels_inventory_and_review_risks():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    products = build_product_analysis(dataset)
    by_id = {item.product_id: item for item in products}

    assert by_id["P001"].segment in {"hero", "risk"}
    assert "库存风险" in by_id["P007"].risk_tags
    assert "差评风险" in by_id["P008"].risk_tags


def test_anomaly_detection_returns_evidence():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    anomalies = detect_anomalies(dataset)

    assert anomalies
    assert all(item.evidence for item in anomalies)
    assert any("ROI" in item.title for item in anomalies)
```

- [ ] **Step 2: Run metrics tests to verify they fail**

Run:

```powershell
pytest tests/test_ecommerce_metrics.py -v
```

Expected: FAIL because metric and anomaly modules do not exist.

- [ ] **Step 3: Add analytics response schemas**

Append to `backend/ecommerce/schemas.py`:

```python
class KpiValue(BaseModel):
    label: str
    value: float
    unit: str = ""
    delta_pct: float = 0
    trend: str = "flat"


class Evidence(BaseModel):
    label: str
    value: str
    baseline: str = ""
    rule: str = ""


class Anomaly(BaseModel):
    id: str
    metric: str
    title: str
    severity: str
    summary: str
    evidence: list[Evidence]


class DashboardSummary(BaseModel):
    date: str
    kpis: dict[str, KpiValue]
    anomalies: list[Anomaly]
    trend: list[dict[str, float | str]]


class ProductAnalysis(BaseModel):
    product_id: str
    name: str
    category: str
    segment: str
    gmv: float
    orders: int
    conversion_rate: float
    gross_margin_rate: float
    stock: int
    safety_stock: int
    ad_roi: float
    average_rating: float
    risk_tags: list[str]
```

- [ ] **Step 4: Implement metrics**

Create `backend/ecommerce/metrics.py`:

```python
from collections import defaultdict
from datetime import date

from backend.ecommerce.schemas import DashboardSummary, EcommerceDataset, KpiValue


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0
    return round(numerator / denominator, 4)


def latest_date(dataset: EcommerceDataset) -> date:
    return max(row.date for row in dataset.orders)


def previous_date(dataset: EcommerceDataset) -> date:
    dates = sorted({row.date for row in dataset.orders})
    return dates[-2] if len(dates) >= 2 else dates[-1]


def orders_on(dataset: EcommerceDataset, target: date):
    return [row for row in dataset.orders if row.date == target]


def traffic_on(dataset: EcommerceDataset, target: date):
    return [row for row in dataset.traffic if row.date == target]


def ads_on(dataset: EcommerceDataset, target: date):
    return [row for row in dataset.ad_spend if row.date == target]


def pct_delta(current: float, baseline: float) -> float:
    if baseline == 0:
        return 0
    return round((current - baseline) / baseline * 100, 2)


def trend(delta: float) -> str:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def kpi(label: str, value: float, unit: str, baseline: float) -> KpiValue:
    delta = pct_delta(value, baseline)
    return KpiValue(label=label, value=round(value, 2), unit=unit, delta_pct=delta, trend=trend(delta))


def build_dashboard(dataset: EcommerceDataset) -> DashboardSummary:
    from backend.ecommerce.anomaly import detect_anomalies

    current_day = latest_date(dataset)
    baseline_day = previous_date(dataset)
    current_orders = orders_on(dataset, current_day)
    baseline_orders = orders_on(dataset, baseline_day)
    current_traffic = traffic_on(dataset, current_day)
    baseline_traffic = traffic_on(dataset, baseline_day)
    current_ads = ads_on(dataset, current_day)
    baseline_ads = ads_on(dataset, baseline_day)

    current_gmv = sum(row.gmv for row in current_orders)
    baseline_gmv = sum(row.gmv for row in baseline_orders)
    current_order_count = sum(row.orders for row in current_orders)
    baseline_order_count = sum(row.orders for row in baseline_orders)
    current_visitors = sum(row.visitors for row in current_traffic)
    baseline_visitors = sum(row.visitors for row in baseline_traffic)
    current_refund = sum(row.refund_amount for row in current_orders)
    baseline_refund = sum(row.refund_amount for row in baseline_orders)
    current_spend = sum(row.spend for row in current_ads)
    baseline_spend = sum(row.spend for row in baseline_ads)
    current_ad_gmv = sum(row.attributed_gmv for row in current_ads)
    baseline_ad_gmv = sum(row.attributed_gmv for row in baseline_ads)

    trend_rows = []
    for day in sorted({row.date for row in dataset.orders}):
        rows = orders_on(dataset, day)
        trend_rows.append({"date": day.isoformat(), "gmv": round(sum(row.gmv for row in rows), 2), "orders": sum(row.orders for row in rows)})

    return DashboardSummary(
        date=current_day.isoformat(),
        kpis={
            "gmv": kpi("GMV", current_gmv, "元", baseline_gmv),
            "orders": kpi("订单数", current_order_count, "单", baseline_order_count),
            "conversion_rate": kpi("转化率", safe_div(current_order_count, current_visitors) * 100, "%", safe_div(baseline_order_count, baseline_visitors) * 100),
            "average_order_value": kpi("客单价", safe_div(current_gmv, current_order_count), "元", safe_div(baseline_gmv, baseline_order_count)),
            "refund_rate": kpi("退款率", safe_div(current_refund, current_gmv) * 100, "%", safe_div(baseline_refund, baseline_gmv) * 100),
            "ad_spend": kpi("广告花费", current_spend, "元", baseline_spend),
            "ad_roi": kpi("广告 ROI", safe_div(current_ad_gmv, current_spend), "", safe_div(baseline_ad_gmv, baseline_spend)),
        },
        anomalies=detect_anomalies(dataset),
        trend=trend_rows,
    )


def product_lookup(dataset: EcommerceDataset):
    return {item.product_id: item for item in dataset.products}
```

- [ ] **Step 5: Implement anomaly detection**

Create `backend/ecommerce/anomaly.py`:

```python
from backend.ecommerce.metrics import ads_on, latest_date, orders_on, pct_delta, previous_date, safe_div
from backend.ecommerce.schemas import Anomaly, EcommerceDataset, Evidence


def detect_anomalies(dataset: EcommerceDataset) -> list[Anomaly]:
    current_day = latest_date(dataset)
    baseline_day = previous_date(dataset)
    current_orders = orders_on(dataset, current_day)
    baseline_orders = orders_on(dataset, baseline_day)
    current_ads = ads_on(dataset, current_day)
    current_gmv = sum(row.gmv for row in current_orders)
    baseline_gmv = sum(row.gmv for row in baseline_orders)
    gmv_delta = pct_delta(current_gmv, baseline_gmv)
    anomalies: list[Anomaly] = []

    if gmv_delta <= dataset.rules.thresholds["gmv_drop_pct"]:
        anomalies.append(Anomaly(
            id="gmv-drop",
            metric="gmv",
            title="GMV 环比明显下降",
            severity="high",
            summary=f"{current_day.isoformat()} GMV 较 {baseline_day.isoformat()} 下降 {abs(gmv_delta)}%，需要优先排查主推商品转化和评价问题。",
            evidence=[
                Evidence(label="当日 GMV", value=f"{current_gmv:.0f} 元", baseline=f"{baseline_gmv:.0f} 元", rule="gmv_drop_pct <= -15"),
            ],
        ))

    for ad in current_ads:
        roi = safe_div(ad.attributed_gmv, ad.spend)
        if roi < dataset.rules.thresholds["low_roi"]:
            anomalies.append(Anomaly(
                id=f"low-roi-{ad.campaign_id}",
                metric="ad_roi",
                title=f"{ad.campaign_id} 广告 ROI 低于阈值",
                severity="medium",
                summary=f"{ad.channel} 计划 ROI 为 {roi}，低于 {dataset.rules.thresholds['low_roi']} 的投放阈值。",
                evidence=[
                    Evidence(label="广告花费", value=f"{ad.spend:.0f} 元", rule="attributed_gmv / spend < low_roi"),
                    Evidence(label="归因成交", value=f"{ad.attributed_gmv:.0f} 元", baseline=f"ROI {roi}"),
                ],
            ))

    inventory_by_id = {row.product_id: row for row in dataset.inventory}
    product_by_id = {row.product_id: row for row in dataset.products}
    for product_id, inv in inventory_by_id.items():
        ratio = safe_div(inv.stock, inv.safety_stock)
        if ratio <= dataset.rules.thresholds["critical_stock_ratio"]:
            product = product_by_id[product_id]
            anomalies.append(Anomaly(
                id=f"stock-risk-{product_id}",
                metric="inventory",
                title=f"{product.name} 库存低于安全线",
                severity="high",
                summary=f"当前库存 {inv.stock}，安全库存 {inv.safety_stock}，补货周期 {inv.lead_time_days} 天。",
                evidence=[Evidence(label="库存/安全库存", value=f"{inv.stock}/{inv.safety_stock}", rule="stock / safety_stock <= 1.0")],
            ))

    return anomalies
```

- [ ] **Step 6: Implement product segmentation**

Create `backend/ecommerce/segmentation.py`:

```python
from collections import defaultdict

from backend.ecommerce.metrics import latest_date, orders_on, safe_div, traffic_on
from backend.ecommerce.schemas import EcommerceDataset, ProductAnalysis


def build_product_analysis(dataset: EcommerceDataset) -> list[ProductAnalysis]:
    current_day = latest_date(dataset)
    products = {item.product_id: item for item in dataset.products}
    orders = {row.product_id: row for row in orders_on(dataset, current_day)}
    traffic = {row.product_id: row for row in traffic_on(dataset, current_day)}
    inventory = {row.product_id: row for row in dataset.inventory}
    ad_roi = _ad_roi_by_product(dataset, current_day)
    ratings = _rating_by_product(dataset, current_day)
    results: list[ProductAnalysis] = []

    for product_id, product in products.items():
        order = orders.get(product_id)
        visit = traffic.get(product_id)
        inv = inventory[product_id]
        gmv = order.gmv if order else 0
        order_count = order.orders if order else 0
        conversion = safe_div(order_count, visit.visitors if visit else 0) * 100
        margin = safe_div(product.price - product.cost, product.price) * 100
        average_rating = ratings.get(product_id, 5.0)
        risk_tags: list[str] = []
        if inv.stock <= inv.safety_stock:
            risk_tags.append("库存风险")
        if average_rating < dataset.rules.thresholds["bad_rating"]:
            risk_tags.append("差评风险")
        if ad_roi.get(product_id, 99) < dataset.rules.thresholds["low_roi"]:
            risk_tags.append("投放低效")

        segment = product.positioning
        if risk_tags and product.positioning in {"hero", "risk"}:
            segment = "risk"
        elif gmv >= 5000 and margin >= 40:
            segment = "hero"
        elif margin >= 45:
            segment = "profit"
        elif conversion >= 5:
            segment = "traffic"

        results.append(ProductAnalysis(
            product_id=product_id,
            name=product.name,
            category=product.category,
            segment=segment,
            gmv=round(gmv, 2),
            orders=order_count,
            conversion_rate=round(conversion, 2),
            gross_margin_rate=round(margin, 2),
            stock=inv.stock,
            safety_stock=inv.safety_stock,
            ad_roi=round(ad_roi.get(product_id, 0), 2),
            average_rating=round(average_rating, 2),
            risk_tags=risk_tags,
        ))

    return sorted(results, key=lambda item: item.gmv, reverse=True)


def _ad_roi_by_product(dataset: EcommerceDataset, target_day):
    spend = defaultdict(float)
    gmv = defaultdict(float)
    for row in dataset.ad_spend:
        if row.date == target_day:
            spend[row.product_id] += row.spend
            gmv[row.product_id] += row.attributed_gmv
    return {product_id: safe_div(gmv[product_id], amount) for product_id, amount in spend.items()}


def _rating_by_product(dataset: EcommerceDataset, target_day):
    weighted = defaultdict(float)
    counts = defaultdict(int)
    for row in dataset.reviews:
        if row.date == target_day:
            weighted[row.product_id] += row.rating * row.comment_count
            counts[row.product_id] += row.comment_count
    return {product_id: safe_div(weighted[product_id], counts[product_id]) for product_id in counts}
```

- [ ] **Step 7: Run metrics tests**

Run:

```powershell
pytest tests/test_ecommerce_metrics.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend/ecommerce tests/test_ecommerce_metrics.py
git commit -m "feat: add ecommerce analytics engine"
```

---

### Task 4: Agent Tools, Orchestration, and Recommendation Store

**Files:**
- Modify: `backend/ecommerce/schemas.py`
- Create: `backend/ecommerce/recommendations.py`
- Create: `backend/ecommerce/tools.py`
- Create: `backend/ecommerce/agent.py`
- Test: `tests/test_ecommerce_agent.py`

**Interfaces:**
- Consumes: `build_dashboard`, `build_product_analysis`, `detect_anomalies`.
- Produces: `EcommerceAgent.analyze(question: str) -> AgentAnalysis`.
- Produces: `RecommendationStore.list(status: str = "")`, `approve(id: str)`, `reject(id: str)`, `seed_from_analysis(analysis: AgentAnalysis)`.

- [ ] **Step 1: Write failing Agent tests**

Create `tests/test_ecommerce_agent.py`:

```python
from pathlib import Path

from backend.ecommerce.agent import EcommerceAgent
from backend.ecommerce.data_loader import EcommerceDataLoader
from backend.ecommerce.recommendations import RecommendationStore


def test_agent_returns_tool_trace_for_gmv_question():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    agent = EcommerceAgent(dataset)

    result = agent.analyze("昨天 GMV 为什么下降？")

    assert result.intent == "business_diagnosis"
    assert [step.tool_name for step in result.tool_trace] == ["get_kpi_snapshot", "detect_anomalies", "rank_products"]
    assert result.evidence
    assert any(action.risk_level == "high" for action in result.recommendations)
    assert result.confidence >= 0.7


def test_agent_routes_campaign_question():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    agent = EcommerceAgent(dataset)

    result = agent.analyze("哪些商品适合参加大促？")

    assert result.intent == "campaign_planning"
    assert any(step.tool_name == "generate_campaign_plan" for step in result.tool_trace)
    assert "活动" in result.summary


def test_recommendation_store_status_transition():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    analysis = EcommerceAgent(dataset).analyze("哪些广告计划 ROI 太低？")
    store = RecommendationStore()
    store.seed_from_analysis(analysis)
    pending = store.list(status="pending")

    assert pending
    approved = store.approve(pending[0].id, operator="admin")
    assert approved.status == "approved"
    rejected = store.reject(pending[-1].id, operator="admin")
    assert rejected.status == "rejected"
```

- [ ] **Step 2: Run Agent tests to verify they fail**

Run:

```powershell
pytest tests/test_ecommerce_agent.py -v
```

Expected: FAIL because Agent modules do not exist.

- [ ] **Step 3: Add Agent and recommendation schemas**

Append to `backend/ecommerce/schemas.py`:

```python
from datetime import datetime
from uuid import uuid4


class ToolTraceStep(BaseModel):
    tool_name: str
    input: dict[str, str | int | float | bool]
    output_summary: str


class RecommendedAction(BaseModel):
    id: str
    title: str
    action_type: str
    risk_level: str
    reason: str
    expected_impact: str
    evidence: list[Evidence]
    status: str = "pending"
    operator: str = ""
    updated_at: str = ""

    @staticmethod
    def create(title: str, action_type: str, risk_level: str, reason: str, expected_impact: str, evidence: list[Evidence]) -> "RecommendedAction":
        return RecommendedAction(
            id=str(uuid4()),
            title=title,
            action_type=action_type,
            risk_level=risk_level,
            reason=reason,
            expected_impact=expected_impact,
            evidence=evidence,
            updated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )


class AgentAnalysis(BaseModel):
    question: str
    intent: str
    summary: str
    tool_trace: list[ToolTraceStep]
    evidence: list[Evidence]
    recommendations: list[RecommendedAction]
    risk_level: str
    confidence: float
```

- [ ] **Step 4: Implement recommendation store**

Create `backend/ecommerce/recommendations.py`:

```python
from datetime import datetime

from backend.ecommerce.schemas import AgentAnalysis, RecommendedAction


class RecommendationStore:
    def __init__(self):
        self._items: dict[str, RecommendedAction] = {}

    def seed_from_analysis(self, analysis: AgentAnalysis) -> None:
        for item in analysis.recommendations:
            self._items.setdefault(item.id, item)

    def seed(self, items: list[RecommendedAction]) -> None:
        for item in items:
            self._items.setdefault(item.id, item)

    def list(self, status: str = "") -> list[RecommendedAction]:
        values = list(self._items.values())
        if status:
            values = [item for item in values if item.status == status]
        return sorted(values, key=lambda item: item.updated_at, reverse=True)

    def approve(self, recommendation_id: str, operator: str = "system") -> RecommendedAction:
        return self._transition(recommendation_id, "approved", operator)

    def reject(self, recommendation_id: str, operator: str = "system") -> RecommendedAction:
        return self._transition(recommendation_id, "rejected", operator)

    def _transition(self, recommendation_id: str, status: str, operator: str) -> RecommendedAction:
        if recommendation_id not in self._items:
            raise KeyError(recommendation_id)
        item = self._items[recommendation_id]
        if item.status != "pending":
            raise ValueError(f"Recommendation {recommendation_id} is already {item.status}")
        item.status = status
        item.operator = operator
        item.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return item
```

- [ ] **Step 5: Implement tools**

Create `backend/ecommerce/tools.py`:

```python
from backend.ecommerce.metrics import build_dashboard
from backend.ecommerce.schemas import EcommerceDataset, ToolTraceStep
from backend.ecommerce.segmentation import build_product_analysis


class EcommerceTools:
    def __init__(self, dataset: EcommerceDataset):
        self.dataset = dataset

    def get_kpi_snapshot(self) -> tuple[object, ToolTraceStep]:
        dashboard = build_dashboard(self.dataset)
        return dashboard, ToolTraceStep(tool_name="get_kpi_snapshot", input={"range": "latest_vs_previous"}, output_summary=f"GMV {dashboard.kpis['gmv'].value}，环比 {dashboard.kpis['gmv'].delta_pct}%")

    def detect_anomalies(self) -> tuple[list[object], ToolTraceStep]:
        dashboard = build_dashboard(self.dataset)
        return dashboard.anomalies, ToolTraceStep(tool_name="detect_anomalies", input={"scope": "sales_ads_inventory_reviews"}, output_summary=f"识别 {len(dashboard.anomalies)} 个经营异常")

    def rank_products(self) -> tuple[list[object], ToolTraceStep]:
        products = build_product_analysis(self.dataset)
        return products, ToolTraceStep(tool_name="rank_products", input={"sort": "gmv_desc"}, output_summary=f"完成 {len(products)} 个商品分层")

    def generate_campaign_plan(self) -> tuple[dict, ToolTraceStep]:
        products = build_product_analysis(self.dataset)
        hero = [item for item in products if item.segment in {"hero", "profit"}][:3]
        clearance = [item for item in products if item.segment == "clearance" or "库存风险" not in item.risk_tags][-2:]
        plan = {
            "theme": "周末增长活动",
            "hero_products": [item.model_dump() for item in hero],
            "clearance_products": [item.model_dump() for item in clearance],
            "strategy": ["主推款做搜索承接", "利润款配置满减", "风险商品先处理评价和库存"],
        }
        return plan, ToolTraceStep(tool_name="generate_campaign_plan", input={"goal": "大促增长"}, output_summary=f"推荐 {len(hero)} 个主推商品和 {len(clearance)} 个补充商品")
```

- [ ] **Step 6: Implement Agent orchestration**

Create `backend/ecommerce/agent.py`:

```python
from backend.ecommerce.schemas import AgentAnalysis, EcommerceDataset, Evidence, RecommendedAction, ToolTraceStep
from backend.ecommerce.tools import EcommerceTools


class EcommerceAgent:
    def __init__(self, dataset: EcommerceDataset):
        self.dataset = dataset
        self.tools = EcommerceTools(dataset)

    def analyze(self, question: str) -> AgentAnalysis:
        intent = self._detect_intent(question)
        if intent == "campaign_planning":
            return self._campaign(question)
        if intent == "ad_review":
            return self._ad_review(question)
        if intent == "inventory_risk":
            return self._inventory(question)
        return self._business_diagnosis(question)

    def _detect_intent(self, question: str) -> str:
        if any(word in question for word in ["大促", "活动", "参加"]):
            return "campaign_planning"
        if any(word in question for word in ["广告", "ROI", "投放", "预算"]):
            return "ad_review"
        if any(word in question for word in ["库存", "补货"]):
            return "inventory_risk"
        return "business_diagnosis"

    def _business_diagnosis(self, question: str) -> AgentAnalysis:
        dashboard, kpi_trace = self.tools.get_kpi_snapshot()
        anomalies, anomaly_trace = self.tools.detect_anomalies()
        products, product_trace = self.tools.rank_products()
        evidence = [item for anomaly in anomalies for item in anomaly.evidence][:6]
        recommendations = [
            RecommendedAction.create(
                title="暂停低 ROI 广告计划并复盘素材",
                action_type="ad_budget_increase",
                risk_level="high",
                reason="广告 ROI 异常低于投放阈值，继续加预算会放大损耗。",
                expected_impact="减少低效花费，优先保住整体 ROI。",
                evidence=evidence[:2],
            ),
            RecommendedAction.create(
                title="优化主推商品详情页和评价解释",
                action_type="content_optimization",
                risk_level="low",
                reason="主推商品流量稳定但成交下降，评价和尺码问题影响转化。",
                expected_impact="提升详情页承接和客服解释效率。",
                evidence=evidence[:3],
            ),
        ]
        return AgentAnalysis(
            question=question,
            intent="business_diagnosis",
            summary=f"GMV 下降主要由主推商品转化走弱、低 ROI 广告消耗和部分商品库存/评价风险共同造成。当前 GMV 为 {dashboard.kpis['gmv'].value} 元，环比 {dashboard.kpis['gmv'].delta_pct}%。",
            tool_trace=[kpi_trace, anomaly_trace, product_trace],
            evidence=evidence,
            recommendations=recommendations,
            risk_level="high",
            confidence=0.86,
        )

    def _campaign(self, question: str) -> AgentAnalysis:
        plan, plan_trace = self.tools.generate_campaign_plan()
        products, product_trace = self.tools.rank_products()
        evidence = [
            Evidence(label="主推商品数", value=str(len(plan["hero_products"])), rule="segment in hero/profit"),
            Evidence(label="商品分层样本", value=str(len(products)), rule="gmv + margin + risk tags"),
        ]
        return AgentAnalysis(
            question=question,
            intent="campaign_planning",
            summary="活动建议采用主推款承接搜索流量、利润款承担满减、风险款先处理库存和评价后再放量。",
            tool_trace=[plan_trace, product_trace],
            evidence=evidence,
            recommendations=[
                RecommendedAction.create("创建周末增长活动方案", "campaign_plan", "medium", "商品分层已完成，具备活动编排条件。", "提升活动选品效率。", evidence)
            ],
            risk_level="medium",
            confidence=0.82,
        )

    def _ad_review(self, question: str) -> AgentAnalysis:
        anomalies, anomaly_trace = self.tools.detect_anomalies()
        ad_evidence = [item for anomaly in anomalies if anomaly.metric == "ad_roi" for item in anomaly.evidence]
        return AgentAnalysis(
            question=question,
            intent="ad_review",
            summary="低 ROI 广告计划应先降预算或暂停，保留 ROI 稳定的商品承接计划。",
            tool_trace=[anomaly_trace],
            evidence=ad_evidence,
            recommendations=[
                RecommendedAction.create("暂停低 ROI 广告计划", "ad_budget_increase", "high", "ROI 低于 1.8 阈值。", "降低无效消耗。", ad_evidence[:2])
            ],
            risk_level="high",
            confidence=0.8,
        )

    def _inventory(self, question: str) -> AgentAnalysis:
        anomalies, anomaly_trace = self.tools.detect_anomalies()
        stock_evidence = [item for anomaly in anomalies if anomaly.metric == "inventory" for item in anomaly.evidence]
        return AgentAnalysis(
            question=question,
            intent="inventory_risk",
            summary="库存风险集中在安全库存以下的主推或新品，建议先补货再放量。",
            tool_trace=[anomaly_trace],
            evidence=stock_evidence,
            recommendations=[
                RecommendedAction.create("为低库存商品创建补货任务", "campaign_plan", "medium", "库存低于安全线。", "降低活动断货风险。", stock_evidence[:2])
            ],
            risk_level="medium",
            confidence=0.78,
        )
```

- [ ] **Step 7: Run Agent tests**

Run:

```powershell
pytest tests/test_ecommerce_agent.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add backend/ecommerce tests/test_ecommerce_agent.py
git commit -m "feat: add ecommerce agent orchestration"
```

---

### Task 5: Ecommerce API Routes

**Files:**
- Create: `backend/api/ecommerce.py`
- Modify: `backend/main.py`
- Test: `tests/test_ecommerce_api_contract.py`

**Interfaces:**
- Consumes: `EcommerceDataLoader`, `build_dashboard`, `build_product_analysis`, `EcommerceAgent`, `RecommendationStore`.
- Produces: `/api/ecommerce/dashboard`, `/api/ecommerce/products`, `/api/ecommerce/agent/analyze`, `/api/ecommerce/campaigns/plan`, `/api/ecommerce/recommendations`, approve/reject endpoints.

- [ ] **Step 1: Write failing API contract tests**

Create `tests/test_ecommerce_api_contract.py`:

```python
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_ecommerce_dashboard_endpoint_returns_kpis():
    response = client.get("/api/ecommerce/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert "gmv" in payload["data"]["kpis"]
    assert payload["data"]["anomalies"]


def test_ecommerce_agent_endpoint_returns_trace_and_recommendations():
    response = client.post("/api/ecommerce/agent/analyze", json={"question": "昨天 GMV 为什么下降？"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "business_diagnosis"
    assert data["tool_trace"]
    assert data["recommendations"]


def test_recommendation_approval_flow():
    created = client.post("/api/ecommerce/agent/analyze", json={"question": "哪些广告计划 ROI 太低？"}).json()["data"]
    recommendation_id = created["recommendations"][0]["id"]

    approved = client.post(f"/api/ecommerce/recommendations/{recommendation_id}/approve").json()["data"]

    assert approved["status"] == "approved"
```

- [ ] **Step 2: Run API tests to verify they fail**

Run:

```powershell
pytest tests/test_ecommerce_api_contract.py -v
```

Expected: FAIL with 404 because ecommerce router is not registered.

- [ ] **Step 3: Implement ecommerce router**

Create `backend/api/ecommerce.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.ecommerce.agent import EcommerceAgent
from backend.ecommerce.data_loader import EcommerceDataLoader
from backend.ecommerce.metrics import build_dashboard
from backend.ecommerce.recommendations import RecommendationStore
from backend.ecommerce.segmentation import build_product_analysis
from backend.ecommerce.tools import EcommerceTools
from backend.schemas.common import ApiResponse

router = APIRouter(prefix="/api/ecommerce", tags=["ecommerce-operations-agent"])
_store = RecommendationStore()


class AgentAnalyzeRequest(BaseModel):
    question: str


def _dataset():
    return EcommerceDataLoader().load()


@router.get("/dashboard", response_model=ApiResponse)
async def dashboard():
    dataset = _dataset()
    summary = build_dashboard(dataset)
    return ApiResponse(data=summary.model_dump())


@router.get("/products", response_model=ApiResponse)
async def products():
    dataset = _dataset()
    return ApiResponse(data=[item.model_dump() for item in build_product_analysis(dataset)])


@router.post("/agent/analyze", response_model=ApiResponse)
async def analyze(request: AgentAnalyzeRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    dataset = _dataset()
    analysis = EcommerceAgent(dataset).analyze(question)
    _store.seed_from_analysis(analysis)
    return ApiResponse(data=analysis.model_dump())


@router.get("/campaigns/plan", response_model=ApiResponse)
async def campaign_plan(goal: str = "大促增长"):
    dataset = _dataset()
    plan, trace = EcommerceTools(dataset).generate_campaign_plan()
    plan["goal"] = goal
    plan["tool_trace"] = [trace.model_dump()]
    return ApiResponse(data=plan)


@router.get("/recommendations", response_model=ApiResponse)
async def recommendations(status: str = ""):
    if not _store.list():
        analysis = EcommerceAgent(_dataset()).analyze("昨天 GMV 为什么下降？")
        _store.seed_from_analysis(analysis)
    return ApiResponse(data=[item.model_dump() for item in _store.list(status=status)])


@router.post("/recommendations/{recommendation_id}/approve", response_model=ApiResponse)
async def approve_recommendation(recommendation_id: str):
    try:
        return ApiResponse(data=_store.approve(recommendation_id, operator="demo-user").model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="recommendation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recommendations/{recommendation_id}/reject", response_model=ApiResponse)
async def reject_recommendation(recommendation_id: str):
    try:
        return ApiResponse(data=_store.reject(recommendation_id, operator="demo-user").model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="recommendation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 4: Register ecommerce router**

In `backend/main.py`, update imports:

```python
from backend.api import auth, documents, chat, admin, knowledge_bases, evaluation, enterprise_auth, operations, health, ecommerce
```

Add router registration after `app.include_router(health.router)`:

```python
app.include_router(ecommerce.router)
```

- [ ] **Step 5: Run API tests**

Run:

```powershell
pytest tests/test_ecommerce_api_contract.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add backend/api/ecommerce.py backend/main.py tests/test_ecommerce_api_contract.py
git commit -m "feat: expose ecommerce operations api"
```

---

### Task 6: Frontend Ecommerce Workbench Pages

**Files:**
- Create: `frontend/src/views/Ecommerce/Dashboard.vue`
- Create: `frontend/src/views/Ecommerce/AgentWorkspace.vue`
- Create: `frontend/src/views/Ecommerce/Products.vue`
- Create: `frontend/src/views/Ecommerce/Campaigns.vue`
- Create: `frontend/src/views/Ecommerce/Recommendations.vue`
- Modify: `frontend/src/styles/global.css` if shared grid utilities are needed.
- Test: `tests/test_ecommerce_frontend_contract.py`

**Interfaces:**
- Consumes: `ecommerceAPI.dashboard()`, `products()`, `analyze(question)`, `campaignPlan(goal)`, `recommendations(status)`, `approveRecommendation(id)`, `rejectRecommendation(id)`.
- Produces: User-visible operations workbench that demonstrates metrics, Agent trace, evidence, product segmentation, campaign plan, and approval flow.

- [ ] **Step 1: Extend frontend contract test**

Append to `tests/test_ecommerce_frontend_contract.py`:

```python
def test_ecommerce_pages_render_agent_and_analysis_terms():
    pages = [
        "frontend/src/views/Ecommerce/Dashboard.vue",
        "frontend/src/views/Ecommerce/AgentWorkspace.vue",
        "frontend/src/views/Ecommerce/Products.vue",
        "frontend/src/views/Ecommerce/Campaigns.vue",
        "frontend/src/views/Ecommerce/Recommendations.vue",
    ]
    content = "\n".join(read(path) for path in pages)

    assert "GMV" in content
    assert "工具调用轨迹" in content
    assert "数据证据" in content
    assert "商品分层" in content
    assert "建议审批" in content
```

- [ ] **Step 2: Run frontend contract test to verify it fails**

Run:

```powershell
pytest tests/test_ecommerce_frontend_contract.py -v
```

Expected: FAIL because ecommerce page files do not exist.

- [ ] **Step 3: Create Dashboard page**

Create `frontend/src/views/Ecommerce/Dashboard.vue` with:

```vue
<template>
  <section class="page-surface">
    <div class="page-heading">
      <div><h1>运营驾驶舱</h1><p>实时查看 GMV、转化、广告 ROI、库存和评价异常。</p></div>
      <el-button type="primary" :loading="loading" @click="load">刷新数据</el-button>
    </div>
    <div class="metric-grid">
      <article v-for="(item, key) in dashboard?.kpis" :key="key" class="metric-card">
        <span>{{ item.label }}</span><strong>{{ item.value }}{{ item.unit }}</strong>
        <em :class="item.trend">环比 {{ item.delta_pct }}%</em>
      </article>
    </div>
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :lg="14">
        <div class="panel section-panel"><h2>经营趋势</h2><el-table :data="dashboard?.trend || []"><el-table-column prop="date" label="日期" /><el-table-column prop="gmv" label="GMV" /><el-table-column prop="orders" label="订单数" /></el-table></div>
      </el-col>
      <el-col :xs="24" :lg="10">
        <div class="panel section-panel"><h2>异常提醒</h2><el-empty v-if="!dashboard?.anomalies?.length" description="暂无异常" /><div v-for="item in dashboard?.anomalies || []" :key="item.id" class="alert-item"><el-tag :type="item.severity === 'high' ? 'danger' : 'warning'">{{ item.severity }}</el-tag><strong>{{ item.title }}</strong><p>{{ item.summary }}</p></div></div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { ecommerceAPI } from "@/api/client"

const loading = ref(false)
const dashboard = ref<any>(null)

async function load() {
  loading.value = true
  try { dashboard.value = (await ecommerceAPI.dashboard()).data.data } catch { ElMessage.error("运营数据加载失败") } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.metric-card{background:#fff;border:1px solid var(--border);border-radius:6px;padding:16px}.metric-card span{display:block;color:var(--ink-muted);font-size:12px}.metric-card strong{display:block;margin-top:8px;font-size:24px}.metric-card em{font-style:normal;font-size:12px}.metric-card em.down{color:var(--danger)}.metric-card em.up{color:var(--success)}.section-row{margin-top:16px}.section-panel{padding:16px}.section-panel h2{margin:0 0 12px;font-size:16px}.alert-item{border-top:1px solid var(--border);padding:12px 0}.alert-item:first-of-type{border-top:0}.alert-item strong{display:block;margin:6px 0}.alert-item p{margin:0;color:var(--ink-muted);line-height:1.6}
</style>
```

- [ ] **Step 4: Create Agent workspace page**

Create `frontend/src/views/Ecommerce/AgentWorkspace.vue` with:

```vue
<template>
  <section class="page-surface">
    <div class="page-heading"><div><h1>运营 Agent</h1><p>输入经营问题，查看意图识别、工具调用轨迹、数据证据和建议动作。</p></div></div>
    <div class="panel agent-layout">
      <div class="question-bar">
        <el-input v-model="question" size="large" placeholder="例如：昨天 GMV 为什么下降？" @keyup.enter="analyze" />
        <el-button type="primary" size="large" :loading="loading" @click="analyze">分析</el-button>
      </div>
      <div class="quick-prompts">
        <el-button v-for="item in prompts" :key="item" @click="question = item; analyze()">{{ item }}</el-button>
      </div>
      <el-empty v-if="!analysis" description="选择一个问题开始分析" />
      <template v-else>
        <h2>{{ analysis.summary }}</h2>
        <el-descriptions :column="3" border><el-descriptions-item label="意图">{{ analysis.intent }}</el-descriptions-item><el-descriptions-item label="风险">{{ analysis.risk_level }}</el-descriptions-item><el-descriptions-item label="置信度">{{ analysis.confidence }}</el-descriptions-item></el-descriptions>
        <h3>工具调用轨迹</h3><el-timeline><el-timeline-item v-for="step in analysis.tool_trace" :key="step.tool_name" :timestamp="step.tool_name">{{ step.output_summary }}</el-timeline-item></el-timeline>
        <h3>数据证据</h3><el-table :data="analysis.evidence"><el-table-column prop="label" label="指标" /><el-table-column prop="value" label="当前值" /><el-table-column prop="baseline" label="基准" /><el-table-column prop="rule" label="触发规则" /></el-table>
        <h3>建议动作</h3><el-table :data="analysis.recommendations"><el-table-column prop="title" label="建议" min-width="180" /><el-table-column prop="risk_level" label="风险" width="100" /><el-table-column prop="expected_impact" label="预期影响" /></el-table>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { ElMessage } from "element-plus"
import { ecommerceAPI } from "@/api/client"

const prompts = ["昨天 GMV 为什么下降？", "哪些商品适合参加大促？", "哪些广告计划 ROI 太低？", "哪些商品存在库存风险？"]
const question = ref(prompts[0])
const loading = ref(false)
const analysis = ref<any>(null)

async function analyze() {
  if (!question.value.trim()) return
  loading.value = true
  try { analysis.value = (await ecommerceAPI.analyze(question.value)).data.data } catch { ElMessage.error("Agent 分析失败") } finally { loading.value = false }
}
</script>

<style scoped>
.agent-layout{padding:18px}.question-bar{display:grid;grid-template-columns:1fr auto;gap:10px}.quick-prompts{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 18px}.agent-layout h2{font-size:18px;line-height:1.5}.agent-layout h3{margin:22px 0 10px;font-size:15px}
</style>
```

- [ ] **Step 5: Create Products page**

Create `frontend/src/views/Ecommerce/Products.vue` with a table bound to `ecommerceAPI.products()` and columns `name`, `category`, `segment`, `gmv`, `conversion_rate`, `gross_margin_rate`, `stock`, `ad_roi`, `average_rating`, `risk_tags`. Use the page title "商品分析" and include visible copy "商品分层".

Use this table column pattern:

```vue
<el-table-column prop="segment" label="商品分层" width="110"><template #default="{ row }"><el-tag>{{ row.segment }}</el-tag></template></el-table-column>
<el-table-column label="风险标签" min-width="160"><template #default="{ row }"><el-tag v-for="tag in row.risk_tags" :key="tag" type="danger" style="margin-right:6px">{{ tag }}</el-tag></template></el-table-column>
```

- [ ] **Step 6: Create Campaigns page**

Create `frontend/src/views/Ecommerce/Campaigns.vue` that calls `ecommerceAPI.campaignPlan(goal)` and renders `theme`, `goal`, `hero_products`, `clearance_products`, `strategy`, and `tool_trace`. Include visible copy "活动策略" and "工具调用轨迹".

- [ ] **Step 7: Create Recommendations page**

Create `frontend/src/views/Ecommerce/Recommendations.vue` that calls `ecommerceAPI.recommendations(status)`, displays a status segmented filter, and provides approve/reject buttons for `pending` rows. Include visible copy "建议审批" and "数据证据".

- [ ] **Step 8: Run frontend contract and build**

Run:

```powershell
pytest tests/test_ecommerce_frontend_contract.py -v
cd frontend
npm run build
```

Expected: pytest PASS and `npm run build` exits 0.

- [ ] **Step 9: Commit**

Run:

```powershell
git add frontend/src/views/Ecommerce tests/test_ecommerce_frontend_contract.py
git commit -m "feat: add ecommerce operations workbench"
```

---

### Task 7: Final Verification and Demo Hardening

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/superpowers/specs/2026-07-15-ecommerce-operations-agent-design.md`

**Interfaces:**
- Consumes: Completed backend APIs and frontend pages.
- Produces: A verified demo project with repeatable commands and resume-ready README.

- [ ] **Step 1: Add README demo workflow**

Ensure `README.md` includes:

```markdown
## 演示路径

1. 启动后端和前端。
2. 登录系统后进入 `/dashboard` 查看运营驾驶舱。
3. 进入 `/agent`，提问“昨天 GMV 为什么下降？”。
4. 查看 Agent 的意图识别、工具调用轨迹、数据证据和建议动作。
5. 进入 `/recommendations`，审批一条高风险建议。
6. 进入 `/products` 和 `/campaigns` 展示商品分层与活动策略。
```

- [ ] **Step 2: Run backend targeted tests**

Run:

```powershell
pytest tests/test_ecommerce_metrics.py tests/test_ecommerce_agent.py tests/test_ecommerce_api_contract.py tests/test_ecommerce_frontend_contract.py -v
```

Expected: PASS.

- [ ] **Step 3: Run broader regression tests that do not require external services**

Run:

```powershell
pytest tests/test_business_intent.py tests/test_dependency_health.py tests/test_deployment_contract.py tests/test_production_config.py tests/test_provider_resilience.py -v
```

Expected: PASS. If a test fails because it asserts old product copy, update that test to assert ecommerce operations copy instead.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: TypeScript and Vite build succeed.

- [ ] **Step 5: Run backend import smoke test**

Run:

```powershell
python -c "from backend.main import app; print(app.title)"
```

Expected output contains:

```text
智能电商运营 Agent 平台
```

- [ ] **Step 6: Commit final docs and verification fixes**

Run:

```powershell
git add README.md .env.example docs/superpowers/specs/2026-07-15-ecommerce-operations-agent-design.md tests
git commit -m "docs: document ecommerce agent demo"
```

If only README changed, stage and commit only `README.md`.
