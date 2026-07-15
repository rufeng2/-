# 智能电商运营 Agent 平台

基于 FastAPI、Vue 3、LangChain/RAG 和模拟电商经营数据构建的 AI 运营决策系统。项目聚焦 AI Agent 工程能力和数据分析能力，支持运营驾驶舱、经营异常诊断、商品分层、活动策略生成、广告 ROI 分析、库存风险识别和人工审批闭环。

## 简历亮点

- 设计确定性电商经营数据集，覆盖订单、流量、广告、库存、评价和竞品数据。
- 实现多工具调用 Agent，返回意图识别、工具轨迹、数据证据、结论和建议动作。
- 实现 GMV、转化率、客单价、广告 ROI、库存风险和差评率等指标分析。
- 通过建议审批中心模拟企业级风控闭环，高风险动作只生成待审批任务。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.12+、FastAPI、Pydantic |
| Agent | 规则工具编排 + 可选 LangChain/LLM 增强 |
| 数据 | 本地模拟 CSV/JSON 数据集，保留 PostgreSQL/pgvector 底座 |
| 前端 | Vue 3、TypeScript、Element Plus、Pinia |
| 部署 | Docker Compose、Nginx |
| 测试 | pytest、vue-tsc、Vite build |

## 核心模块

- 运营驾驶舱：展示 GMV、订单数、转化率、客单价、广告 ROI、库存风险和异常提醒。
- 运营 Agent：根据经营问题调用指标、异常、商品分层、广告 ROI、库存风险等工具，输出可解释分析。
- 商品分析：展示商品分层、销售贡献、转化效率、毛利、库存和评价风险。
- 活动策略：根据商品分层生成主推款、利润款、清仓款和活动打法。
- 建议审批：对改价、加预算、发券、清仓等高风险建议进行审批闭环。
- 运营知识库：复用原 RAG 能力，用于商品资料、品牌规则、活动复盘和客服 SOP。

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 演示路径

1. 登录系统后进入 `/dashboard` 查看运营驾驶舱。
2. 进入 `/agent`，提问“昨天 GMV 为什么下降？”。
3. 查看 Agent 的意图识别、工具调用轨迹、数据证据和建议动作。
4. 进入 `/recommendations`，审批一条高风险建议。
5. 进入 `/products` 和 `/campaigns` 展示商品分层与活动策略。

## 默认定位

本项目不依赖真实淘宝、天猫、抖店、京东或 Shopify API。第一版使用本地确定性模拟数据，保证没有真实平台、没有内部系统资料、没有大模型 API Key 时也能完整演示；配置大模型后只增强自然语言表达，不改变底层指标计算结果。
