# inventory/tests.py

import unittest
from pkg.pricing import Pricer


class TestPricer(unittest.TestCase):
    def setUp(self) -> None:
        self.pricer = Pricer()

    def test_single_item_no_discount(self) -> None:
        invoice = self.pricer.price_order("widget:4")
        self.assertEqual(invoice["subtotal"], 10.00)
        self.assertEqual(invoice["tax"], 0.80)
        self.assertEqual(invoice["total"], 10.80)

    def test_bulk_discount(self) -> None:
        invoice = self.pricer.price_order("widget:25")
        self.assertEqual(invoice["lines"][0].discount_rate, 0.10)
        self.assertEqual(invoice["subtotal"], 56.25)
        self.assertEqual(invoice["total"], 60.75)

    def test_deep_bulk_discount(self) -> None:
        invoice = self.pricer.price_order("widget:60")
        self.assertEqual(invoice["lines"][0].discount_rate, 0.20)
        self.assertEqual(invoice["subtotal"], 120.00)
        self.assertEqual(invoice["total"], 129.60)

    def test_multiple_items(self) -> None:
        invoice = self.pricer.price_order("cable:2,case:1")
        self.assertEqual(len(invoice["lines"]), 2)
        self.assertEqual(invoice["subtotal"], 26.00)
        self.assertEqual(invoice["tax"], 2.08)
        self.assertEqual(invoice["total"], 28.08)

    def test_empty_order(self) -> None:
        invoice = self.pricer.price_order("")
        self.assertIsNone(invoice)

    def test_unknown_item(self) -> None:
        with self.assertRaises(ValueError):
            self.pricer.price_order("sprocket:3")

    def test_malformed_spec(self) -> None:
        with self.assertRaises(ValueError):
            self.pricer.price_order("widget")

    def test_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            self.pricer.price_order("widget:0")


if __name__ == "__main__":
    unittest.main()
