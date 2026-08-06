from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Money = Decimal
ZERO = Decimal("0.00")


def money(value: object) -> Money:
    if value is None or value == "":
        return ZERO
    if isinstance(value, Decimal):
        parsed = value
    else:
        text = str(value).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("INR", "")
        try:
            parsed = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid money value: {value!r}") from exc
    return parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_inr(value: Money) -> str:
    sign = "-" if value < 0 else ""
    value = abs(money(value))
    whole, fraction = f"{value:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}₹{whole}.{fraction}"
