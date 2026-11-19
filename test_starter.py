import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def make_fetch(offers, status="success"):
    async def _fetch():
        return {"status": status, "offers": offers}

    return _fetch


class RecommendPriceTest(unittest.IsolatedAsyncioTestCase):
    async def test_sample_offers(self):
        res = await recommend_price(
            sample_fetch_offers,
            current_price=Decimal("4900.00"),
            min_price=Decimal("4500.00"),
        )
        self.assertEqual(res["price"], Decimal("4728.00"))
        self.assertEqual(res["decision"], "APPLY")
        self.assertIsInstance(res["price"], Decimal)

    async def test_round_down(self):
        fetch = make_fetch([
            {"seller": "COMP", "price": Decimal("100.01"), "delivery_days": 1},
        ])
        res = await recommend_price(fetch, Decimal("100.00"), Decimal("50.00"))
        self.assertEqual(res["price"], Decimal("98.50"))
        self.assertEqual(res["decision"], "APPLY")

    async def test_filter_offers(self):
        fetch = make_fetch([
            {"seller": "MyShop", "price": Decimal("100.00"), "delivery_days": 0},
            {"seller": "NO_DAYS", "price": Decimal("150.00"), "delivery_days": None},
            {"seller": "SLOW", "price": Decimal("160.00"), "delivery_days": 7},
            {"seller": "SAME_DAY", "price": Decimal("200.00"), "delivery_days": 0},
            {"seller": "BORDER", "price": Decimal("300.00"), "delivery_days": 6},
        ])
        res = await recommend_price(fetch, Decimal("210.00"), Decimal("100.00"))
        self.assertEqual(res["price"], Decimal("197.00"))
        self.assertEqual(res["decision"], "APPLY")

    async def test_timeout(self):
        async def slow_fetch():
            await asyncio.sleep(0.2)
            return {"status": "success", "offers": []}

        res = await recommend_price(slow_fetch, Decimal("4900.00"), Decimal("4500.00"), timeout_s=0.02)
        self.assertEqual(res["price"], Decimal("4900.00"))
        self.assertEqual(res["decision"], "HOLD")

    async def test_source_exception(self):
        async def broken_fetch():
            raise RuntimeError("network error")

        res = await recommend_price(broken_fetch, Decimal("4900.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4900.00"))
        self.assertEqual(res["decision"], "HOLD")

    async def test_non_success_status(self):
        offers = [{"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 2}]
        for status in ("partial", "error"):
            with self.subTest(status=status):
                res = await recommend_price(
                    make_fetch(offers, status=status),
                    Decimal("4900.00"),
                    Decimal("4500.00"),
                )
                self.assertEqual(res["price"], Decimal("4900.00"))
                self.assertEqual(res["decision"], "HOLD")

    async def test_no_valid_offers_keeps_current_below_min(self):
        fetch = make_fetch([
            {"seller": "MYSHOP", "price": Decimal("5000.00"), "delivery_days": 1},
            {"seller": "NO_DAYS", "price": Decimal("5000.00"), "delivery_days": None},
        ])
        res = await recommend_price(fetch, Decimal("4000.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4000.00"))
        self.assertEqual(res["decision"], "HOLD")

    async def test_min_price_floor(self):
        fetch = make_fetch([
            {"seller": "DUMP", "price": Decimal("4000.00"), "delivery_days": 2},
        ])
        res = await recommend_price(fetch, Decimal("4900.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4500.00"))
        self.assertEqual(res["decision"], "APPLY")

    async def test_deviation_boundaries(self):
        fetch = make_fetch([
            {"seller": "COMP", "price": Decimal("500.00"), "delivery_days": 1},
        ])
        cases = [
            (Decimal("700.00"), "APPLY"),
            (Decimal("699.99"), "REVIEW"),
            (Decimal("1300.00"), "APPLY"),
            (Decimal("1300.01"), "REVIEW"),
        ]
        for min_price, expected_decision in cases:
            with self.subTest(min_price=min_price):
                res = await recommend_price(fetch, Decimal("1000.00"), min_price)
                self.assertEqual(res["price"], min_price)
                self.assertEqual(res["decision"], expected_decision)


if __name__ == "__main__":
    unittest.main()