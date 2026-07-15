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
