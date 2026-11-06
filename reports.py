"""Business logic: aggregating expenses into report totals."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class InvalidData(ValueError):
    """The input data is malformed or inconsistent."""


class NotFound(ValueError):
    """No expenses match the requested department and period."""


@dataclass
class Expense:
    """The expenses of one department in one calendar month."""

    department: str
    year: int
    month: int
    amount: Decimal
    currency: str


def total_expenses(
    expenses: Iterable[Expense],
    department: str,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
) -> tuple[Decimal, str]:
    """Sum the expenses of a department, optionally within a year and a quarter or a month.

    Returns the total and its currency. Raises ValueError for inconsistent parameters,
    NotFound when nothing matches and InvalidData when the matched amounts mix currencies.
    """
    if not department.strip():
        raise ValueError("department must not be empty")
    if (quarter is not None or month is not None) and year is None:
        raise ValueError("quarter and month require a year")
    if quarter is not None and month is not None:
        raise ValueError("specify either a quarter or a month, not both")
    if quarter is not None and not 1 <= quarter <= 4:
        raise ValueError(f"quarter must be between 1 and 4, got {quarter}")
    if month is not None and not 1 <= month <= 12:
        raise ValueError(f"month must be between 1 and 12, got {month}")

    if month is not None:
        months = range(month, month + 1)
    elif quarter is not None:
        months = range(3 * quarter - 2, 3 * quarter + 1)
    else:
        months = range(1, 13)

    matched = [
        e
        for e in expenses
        if e.department.casefold() == department.strip().casefold()
        and (year is None or e.year == year)
        and e.month in months
    ]
    if not matched:
        raise NotFound(
            f"no expenses found for {department!r} (year={year}, quarter={quarter}, month={month})"
        )
    currencies = {e.currency for e in matched}
    if len(currencies) > 1:
        raise InvalidData(f"mixed currencies: {', '.join(sorted(currencies))}")
    return sum(e.amount for e in matched), currencies.pop()
