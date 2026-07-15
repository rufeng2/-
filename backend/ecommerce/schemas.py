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
