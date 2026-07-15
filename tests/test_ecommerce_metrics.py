from pathlib import Path

from backend.ecommerce.data_loader import EcommerceDataLoader


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
