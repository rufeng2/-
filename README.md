# 智能电商运营 Agent 平台

基于 FastAPI、Vue 3、确定性电商经营数据和工具编排构建的 AI 运营决策系统。项目用于展示 AI Agent 工程能力和数据分析能力，不依赖真实淘宝、天猫、抖店、京东或 Shopify API，也不需要真实企业内部系统资料。

## 项目亮点

- **AI Agent 编排**：根据经营问题识别意图，按步骤调用指标快照、GMV 归因、异常检测、商品分层和活动策略工具。
- **数据分析能力**：覆盖 GMV、订单、转化率、客单价、退款率、广告 ROI、GMV 归因、ABC 分层、库存周转和评价风险。
- **可解释输出**：每次分析返回 Agent 执行轨迹、输入参数、工具输出摘要、证据列表、风险等级和建议动作。
- **审批闭环**：高风险建议先进入建议审批中心，支持通过、拒绝和状态筛选，模拟企业级风控流程。
- **本地可演示**：开发环境下没有 Redis/Postgres 也可以注册账号并体验电商 demo；生产环境仍保持依赖和安全策略。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12+、FastAPI、Pydantic、SQLAlchemy |
| Agent | 确定性工具编排 + 可选 LLM 增强 |
| 数据 | 本地 CSV/JSON 模拟电商经营数据 |
| 前端 | Vue 3、TypeScript、Element Plus、Pinia |
| 工程 | Docker Compose、Nginx、pytest、vue-tsc、Vite |

## 核心模块

- **运营驾驶舱**：展示核心 KPI、经营趋势、异常提醒和 GMV 归因。
- **运营 Agent**：输入自然语言问题，展示意图识别、工具调用轨迹、数据证据和建议动作。
- **商品分析**：展示商品分层、ABC 分层、GMV、转化率、毛利率、库存周转、广告 ROI 和风险标签。
- **活动策略**：基于商品分层生成主推款、利润款、清仓款和活动打法。
- **建议审批**：对调预算、暂停投放、内容优化、补货等建议进行人工审批。
- **运营知识库**：保留 RAG 项目底座，可承接商品资料、品牌规则、活动复盘和客服 SOP。

## 演示路径

1. 打开 `http://127.0.0.1:5173/` 注册一个本地 demo 账号。
2. 进入 `/dashboard` 查看 GMV、转化、广告 ROI 和 GMV 归因。
3. 进入 `/agent`，输入“昨天 GMV 为什么下降？”。
4. 查看 Agent 执行轨迹：指标快照 -> GMV 归因 -> 异常检测 -> 商品分层。
5. 进入 `/recommendations` 审批一条高风险建议。
6. 进入 `/products` 和 `/campaigns` 展示商品分析与活动策略。

## 本地运行

后端默认运行在 `8001`，前端默认运行在 `5173`。

```powershell
# 后端
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

# 前端
cd frontend
$env:VITE_API_TARGET="http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5173
```

## 验证

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

## Demo 与生产边界

- `development`：允许电商 demo API 在 Redis 不可用时继续运行；认证可回落到本地 demo 用户库 `data/local_auth_users.json`。
- `production`：仍按生产策略 fail-closed，写操作需要限流依赖可用，认证走数据库和企业安全策略。

这让项目既能本地完整演示，也能在架构说明中体现生产安全意识。
