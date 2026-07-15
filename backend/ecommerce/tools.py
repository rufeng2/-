from backend.ecommerce.metrics import build_dashboard
from backend.ecommerce.schemas import EcommerceDataset, ToolTraceStep
from backend.ecommerce.segmentation import build_product_analysis


class EcommerceTools:
    def __init__(self, dataset: EcommerceDataset):
        self.dataset = dataset

    def get_kpi_snapshot(self):
        dashboard = build_dashboard(self.dataset)
        return dashboard, ToolTraceStep(
            tool_name="get_kpi_snapshot",
            step_title="读取经营指标快照",
            input={"range": "latest_vs_previous"},
            output_summary=f"GMV {dashboard.kpis['gmv'].value} 元，环比 {dashboard.kpis['gmv'].delta_pct}%。",
        )

    def explain_gmv_attribution(self):
        dashboard = build_dashboard(self.dataset)
        strongest = min(dashboard.gmv_attribution, key=lambda item: item.delta_value)
        return dashboard.gmv_attribution, ToolTraceStep(
            tool_name="explain_gmv_attribution",
            step_title="拆解 GMV 变化归因",
            input={"factors": "traffic,conversion,aov"},
            output_summary=f"{strongest.label}贡献 {strongest.delta_value} 元，是本次 GMV 下滑的主要解释项。",
        )

    def detect_anomalies(self):
        dashboard = build_dashboard(self.dataset)
        return dashboard.anomalies, ToolTraceStep(
            tool_name="detect_anomalies",
            step_title="识别经营异常",
            input={"scope": "sales_ads_inventory_reviews"},
            output_summary=f"识别 {len(dashboard.anomalies)} 个经营异常。",
        )

    def rank_products(self):
        products = build_product_analysis(self.dataset)
        return products, ToolTraceStep(
            tool_name="rank_products",
            step_title="商品分层与风险排序",
            input={"sort": "gmv_desc", "signals": "abc,margin,conversion,inventory,review,roi"},
            output_summary=f"完成 {len(products)} 个商品分层，最高 GMV 商品为 {products[0].name}。",
        )

    def generate_campaign_plan(self, goal: str = "大促增长"):
        normalized_goal = goal.strip() or "大促增长"
        products = build_product_analysis(self.dataset)
        hero = [item for item in products if item.segment in {"hero", "profit"} and not item.risk_tags][:3]
        clearance = [item for item in products if item.segment == "clearance" or item.stock > item.safety_stock * 2][:2]
        plan = {
            "theme": _campaign_theme(normalized_goal),
            "hero_products": [item.model_dump() for item in hero],
            "clearance_products": [item.model_dump() for item in clearance],
            "strategy": _campaign_strategy(normalized_goal),
        }
        return plan, ToolTraceStep(
            tool_name="generate_campaign_plan",
            step_title="生成活动选品策略",
            input={"goal": normalized_goal},
            output_summary=f"围绕{normalized_goal}推荐 {len(hero)} 个主推商品和 {len(clearance)} 个补充商品。",
        )


def _campaign_theme(goal: str) -> str:
    if goal.endswith(("策略", "活动", "方案")):
        return goal
    return f"{goal}策略"


def _campaign_strategy(goal: str) -> list[str]:
    if any(keyword in goal for keyword in ("新品", "冷启动", "上新")):
        return ["新品先用低门槛券获取首批转化", "用高意图搜索词承接种草流量", "控制预算验证点击率和收藏加购"]
    if any(keyword in goal for keyword in ("清仓", "库存", "尾货")):
        return ["高库存商品配置阶梯满减", "风险商品先处理评价和售后解释", "清仓预算按库存周转天数排序"]
    if any(keyword in goal for keyword in ("复购", "会员", "老客")):
        return ["利润款绑定会员券提升复购", "主推款做加购提醒和短信召回", "低毛利商品不参与深折扣"]
    return ["主推款承接搜索流量", "利润款配置满减", "风险商品先处理评价和库存"]
