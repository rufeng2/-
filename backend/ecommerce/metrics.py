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
