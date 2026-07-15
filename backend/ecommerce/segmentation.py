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
    abc = _abc_segments(orders)
    results: list[ProductAnalysis] = []

    for product_id, product in products.items():
        order = orders.get(product_id)
        visit = traffic.get(product_id)
        inv = inventory[product_id]
        gmv = order.gmv if order else 0
        order_count = order.orders if order else 0
        units = order.units if order else 0
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

        inventory_turnover_days = safe_div(inv.stock, units)

        results.append(ProductAnalysis(
            product_id=product_id,
            name=product.name,
            category=product.category,
            segment=segment,
            abc_segment=abc.get(product_id, "C"),
            gmv=round(gmv, 2),
            orders=order_count,
            conversion_rate=round(conversion, 2),
            gross_margin_rate=round(margin, 2),
            stock=inv.stock,
            safety_stock=inv.safety_stock,
            inventory_turnover_days=round(inventory_turnover_days, 1),
            ad_roi=round(ad_roi.get(product_id, 0), 2),
            average_rating=round(average_rating, 2),
            risk_tags=risk_tags,
        ))

    return sorted(results, key=lambda item: item.gmv, reverse=True)


def _abc_segments(orders: dict) -> dict[str, str]:
    total_gmv = sum(row.gmv for row in orders.values())
    if total_gmv <= 0:
        return {product_id: "C" for product_id in orders}

    cumulative = 0.0
    segments: dict[str, str] = {}
    for product_id, row in sorted(orders.items(), key=lambda item: item[1].gmv, reverse=True):
        cumulative += row.gmv
        share = cumulative / total_gmv
        if share <= 0.7:
            segment = "A"
        elif share <= 0.9:
            segment = "B"
        else:
            segment = "C"
        segments[product_id] = segment
    return segments


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
