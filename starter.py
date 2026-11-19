import asyncio
from decimal import Decimal, ROUND_DOWN


async def recommend_price(fetch_offers, current_price, min_price, timeout_s=2.0):
    try:
        result = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except asyncio.TimeoutError:
        return {"price": current_price, "decision": "HOLD", "reason": "Тайм-аут источника"}
    except Exception as err:
        return {
            "price": current_price,
            "decision": "HOLD",
            "reason": f"Ошибка источника: {type(err).__name__}",
        }

    status = result.get("status")
    if status != "success":
        return {"price": current_price, "decision": "HOLD", "reason": f"Статус источника: {status}"}

    prices = [
        offer["price"]
        for offer in result["offers"]
        if offer["delivery_days"] is not None
        and offer["delivery_days"] <= 6
        and offer["seller"].strip().lower() != "myshop"
    ]
    if not prices:
        return {"price": current_price, "decision": "HOLD", "reason": "Нет подходящих предложений"}

    discounted = (min(prices) * Decimal("0.985")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    recommended = max(discounted, min_price)

    if abs(recommended - current_price) > current_price * Decimal("0.30"):
        return {
            "price": recommended,
            "decision": "REVIEW",
            "reason": "Отклонение от текущей цены больше 30%",
        }

    reason = (
        "Цена ограничена min_price"
        if recommended == min_price and discounted < min_price
        else "Цена конкурента со скидкой 1.5%"
    )
    return {"price": recommended, "decision": "APPLY", "reason": reason}


async def sample_fetch_offers():
    return {
        "status": "success",
        "offers": [
            {"seller": "myshop", "price": Decimal("4300.00"), "delivery_days": 2},
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
            {"seller": "SLOW", "price": Decimal("4700.00"), "delivery_days": 8},
        ],
    }


if __name__ == "__main__":
    print(asyncio.run(recommend_price(
        sample_fetch_offers,
        current_price=Decimal("4900.00"),
        min_price=Decimal("4500.00"),
    )))