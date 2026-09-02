# inventory/pkg/pricing.py

from dataclasses import dataclass

TAX_RATE = 0.08


@dataclass
class Line:
    item: str
    quantity: int
    unit_price: float
    discount_rate: float
    subtotal: float


class Pricer:
    def __init__(self) -> None:
        self.catalog: dict[str, float] = {
            "widget": 2.50,
            "cable": 7.00,
            "case": 12.00,
        }
        # (minimum quantity for the tier, rate taken off that line), lowest first
        self.bulk_tiers: list[tuple[int, float]] = [
            (10, 0.10),
            (50, 0.20),
        ]

    def price_order(self, order: str) -> dict | None:
        if not order or order.isspace():
            return None

        lines = [self._price_line(spec) for spec in order.strip().split(",")]
        subtotal = round(sum(line.subtotal for line in lines), 2)
        tax = round(subtotal * TAX_RATE, 2)

        return {
            "lines": lines,
            "subtotal": subtotal,
            "tax": tax,
            "total": round(subtotal + tax, 2),
        }

    def discount_rate(self, quantity: int) -> float:
        rate = 0.0
        for minimum, tier_rate in self.bulk_tiers:
            if quantity >= minimum:
                rate = tier_rate
        return rate

    def _price_line(self, spec: str) -> Line:
        item, quantity = self._parse_spec(spec)

        if item not in self.catalog:
            raise ValueError(f"unknown item: {item}")

        unit_price = self.catalog[item]
        rate = self.discount_rate(quantity)
        subtotal = round(unit_price * quantity * (1 - rate), 2)

        return Line(
            item=item,
            quantity=quantity,
            unit_price=unit_price,
            discount_rate=rate,
            subtotal=subtotal,
        )

    def _parse_spec(self, spec: str) -> tuple[str, int]:
        parts = spec.strip().split(":")
        if len(parts) != 2:
            raise ValueError(f"invalid item spec: {spec.strip()}")

        item, raw_quantity = parts[0].strip(), parts[1].strip()
        try:
            quantity = int(raw_quantity)
        except ValueError:
            raise ValueError(f"invalid quantity: {raw_quantity}")

        if quantity <= 0:
            raise ValueError(f"quantity must be positive: {raw_quantity}")

        return item, quantity
