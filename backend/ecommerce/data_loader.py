import csv
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from backend.ecommerce.schemas import (
    AdSpendRecord,
    CompetitorRecord,
    EcommerceDataset,
    InventoryRecord,
    OperationRules,
    OrderRecord,
    ProductRecord,
    ReviewRecord,
    TrafficRecord,
)

T = TypeVar("T", bound=BaseModel)


class EcommerceDataLoader:
    def __init__(self, root: Path | str = Path("data/ecommerce")):
        self.root = Path(root)

    def load(self) -> EcommerceDataset:
        missing = [name for name in self.required_files() if not (self.root / name).exists()]
        if missing:
            raise FileNotFoundError(f"Missing ecommerce demo data files in {self.root}: {', '.join(missing)}")

        return EcommerceDataset(
            products=self._read_csv("products.csv", ProductRecord),
            orders=self._read_csv("orders.csv", OrderRecord),
            traffic=self._read_csv("traffic.csv", TrafficRecord),
            ad_spend=self._read_csv("ad_spend.csv", AdSpendRecord),
            inventory=self._read_csv("inventory.csv", InventoryRecord),
            reviews=self._read_csv("reviews.csv", ReviewRecord),
            competitors=self._read_csv("competitors.csv", CompetitorRecord),
            rules=OperationRules.model_validate(json.loads((self.root / "operation_rules.json").read_text(encoding="utf-8"))),
        )

    @staticmethod
    def required_files() -> list[str]:
        return [
            "products.csv",
            "orders.csv",
            "traffic.csv",
            "ad_spend.csv",
            "inventory.csv",
            "reviews.csv",
            "competitors.csv",
            "operation_rules.json",
        ]

    def _read_csv(self, filename: str, model: type[T]) -> list[T]:
        with (self.root / filename).open("r", encoding="utf-8-sig", newline="") as handle:
            return [model.model_validate(row) for row in csv.DictReader(handle)]
