from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.core.money import money

NULL_VALUES = {"", "na", "n/a", "-", "none", "null"}
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%d %B %Y")


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    if text.lower() in NULL_VALUES:
        return None
    return text


def normalize_code(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    return re.sub(r"\s*/\s*", "/", text).upper()


def normalize_enum(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def normalize_money(value: object) -> Decimal:
    text = normalize_text(value)
    if text is None:
        return money("0")
    return money(text)


def normalize_date(value: object) -> date | None:
    text = normalize_text(value)
    if text is None:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value!r}")


def fingerprint(values: dict[str, Any]) -> str:
    normalized = "|".join(f"{key}={normalize_text(values.get(key)) or ''}" for key in sorted(values))
    return sha256(normalized.encode("utf-8")).hexdigest()

