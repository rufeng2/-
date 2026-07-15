# 简历项目描述：智能电商运营 Agent 平台

## 推荐写法

智能电商运营 Agent 平台：基于 FastAPI、Vue 3 和模拟电商经营数据构建 AI 运营决策系统，实现自然语言经营诊断、GMV 归因、商品分层、广告 ROI 分析、库存风险识别和建议审批闭环。系统通过确定性工具编排返回 Agent 执行轨迹、数据证据、风险等级和策略建议，支持无真实电商平台和无内部系统资料条件下的完整本地演示。

## 简历亮点

- 设计并实现多工具调用 Agent，将“指标快照、GMV 归因、异常检测、商品分层、活动策略”编排为可解释分析链路。
- 构建本地电商模拟数据集，覆盖订单、流量、广告、库存、评价、竞品和运营规则。
- 实现 GMV、转化率、客单价、退款率、广告 ROI、ABC 分层、库存周转天数和差评风险等运营指标。
- 将高风险动作沉淀为建议审批流，模拟企业级人机协同和风控闭环。
- 补充 pytest 与前端构建验证，保证 Agent 输出、指标计算、API 契约和前端页面稳定。

## 面试讲法

1. **为什么做这个项目**：没有真实平台数据时，先用确定性模拟数据构建完整业务闭环，重点展示 Agent 工程和数据分析能力。
2. **Agent 怎么工作**：自然语言问题先做意图识别，再按工具链执行，最后输出证据、结论和建议动作。
3. **数据分析怎么体现**：GMV 下滑不是只给结论，而是拆成流量、转化率、客单价三个因子的贡献。
4. **企业级在哪里**：高风险建议不直接执行，进入审批中心；生产环境仍保留限流、认证和依赖 fail-closed 策略。
5. **怎么保证可演示**：开发环境提供本地 demo 账号库和确定性数据，避免依赖真实 Redis/Postgres 或第三方电商 API。

## 可展示接口

- `GET /api/ecommerce/dashboard`
- `POST /api/ecommerce/agent/analyze`
- `GET /api/ecommerce/products`
- `GET /api/ecommerce/campaigns/plan`
- `GET /api/ecommerce/recommendations`
- `POST /api/ecommerce/recommendations/{id}/approve`
