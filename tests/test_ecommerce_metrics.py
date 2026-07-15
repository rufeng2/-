from pathlib import Path

from backend.ecommerce.anomaly import detect_anomalies
from backend.ecommerce.data_loader import EcommerceDataLoader
from backend.ecommerce.metrics import build_dashboard, safe_div
from backend.ecommerce.segmentation import build_product_analysis


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


def test_safe_div_handles_zero_denominator():
    assert safe_div(10, 0) == 0
    assert safe_div(10, 4) == 2.5


def test_dashboard_computes_core_kpis_and_detects_drop():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    dashboard = build_dashboard(dataset)

    assert dashboard.kpis["gmv"].value == 23843
    assert dashboard.kpis["orders"].value == 121
    assert dashboard.kpis["ad_roi"].value < 2.5
    assert dashboard.kpis["gmv"].delta_pct < -15
    assert any(item.metric == "gmv" for item in dashboard.anomalies)


def test_dashboard_explains_gmv_change_with_attribution():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    dashboard = build_dashboard(dataset)

    factors = {item.factor: item for item in dashboard.gmv_attribution}

    assert set(factors) == {"traffic", "conversion", "aov"}
    assert factors["conversion"].delta_value < 0
    assert factors["conversion"].contribution_pct < 0
    assert "转化率" in factors["conversion"].insight


def test_product_analysis_labels_inventory_and_review_risks():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    products = build_product_analysis(dataset)
    by_id = {item.product_id: item for item in products}

    assert by_id["P001"].segment in {"hero", "risk"}
    assert "库存风险" in by_id["P007"].risk_tags
    assert "差评风险" in by_id["P008"].risk_tags


def test_product_analysis_adds_abc_and_turnover_indicators():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    products = build_product_analysis(dataset)

    assert {item.abc_segment for item in products} >= {"A", "B", "C"}
    assert all(item.inventory_turnover_days >= 0 for item in products)
    assert products[0].abc_segment == "A"


def test_anomaly_detection_returns_evidence():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    anomalies = detect_anomalies(dataset)

    assert anomalies
    assert all(item.evidence for item in anomalies)
    assert any("ROI" in item.title for item in anomalies)
