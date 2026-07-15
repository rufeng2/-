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
            input={"range": "latest_vs_previous"},
            output_summary=f"GMV {dashboard.kpis['gmv'].value}，环比 {dashboard.kpis['gmv'].delta_pct}%",
        )

    def detect_anomalies(self):
        dashboard = build_dashboard(self.dataset)
        return dashboard.anomalies, ToolTraceStep(
            tool_name="detect_anomalies",
            input={"scope": "sales_ads_inventory_reviews"},
            output_summary=f"识别 {len(dashboard.anomalies)} 个经营异常",
        )

    def rank_products(self):
        products = build_product_analysis(self.dataset)
        return products, ToolTraceStep(
            tool_name="rank_products",
            input={"sort": "gmv_desc"},
            output_summary=f"完成 {len(products)} 个商品分层",
        )

    def generate_campaign_plan(self):
        products = build_product_analysis(self.dataset)
        hero = [item for item in products if item.segment in {"hero", "profit"} and not item.risk_tags][:3]
        clearance = [item for item in products if item.segment == "clearance" or item.stock > item.safety_stock * 2][:2]
        plan = {
            "theme": "周末增长活动",
            "hero_products": [item.model_dump() for item in hero],
            "clearance_products": [item.model_dump() for item in clearance],
            "strategy": ["主推款做搜索承接", "利润款配置满减", "风险商品先处理评价和库存"],
        }
        return plan, ToolTraceStep(
            tool_name="generate_campaign_plan",
            input={"goal": "大促增长"},
            output_summary=f"推荐 {len(hero)} 个主推商品和 {len(clearance)} 个补充商品",
        )
