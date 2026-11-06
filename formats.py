"""Parsers and formatters: the Expenses.csv layout, monetary values and periods.

The CSV is semicolon-separated with the header ``Department;Expense Type;Year;Jan;...;Dec``.
Amounts look like ``$1,234`` or, when negative, ``($1,234)``.
"""

import csv
import re
from collections.abc import Iterable, Iterator
from decimal import Decimal
from typing import Optional

from reports import Expense, InvalidData

MONTH_NAMES = ("January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December")
MONTHS = tuple(name[:3] for name in MONTH_NAMES)
HEADER = ("Department", "Expense Type", "Year", *MONTHS)

# Parentheses or a minus before/after the currency symbol mark a negative amount;
# thousands, when separated, must come in groups of three.
MONEY = re.compile(
    r"^(?P<open>\()?\s*(?P<neg>-)?\s*(?P<currency>[^\d\s.,()-]*)\s*(?P<neg2>-)?\s*"
    r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?P<close>\))?$"
)


def parse_money(text: str) -> tuple[Decimal, str]:
    """'$1,234' -> (1234, '$'); '($1,234)', '-$1,234' or '$-1,234' -> (-1234, '$')."""
    match = MONEY.match(text.strip())
    if match is None or bool(match["open"]) != bool(match["close"]):
        raise InvalidData(f"cannot parse amount {text!r}")
    amount = Decimal(match["number"].replace(",", ""))
    negative = match["open"] or match["neg"] or match["neg2"]
    return (-amount if negative else amount), match["currency"]


def read_expenses(lines: Iterable[str]) -> Iterator[Expense]:
    """Parse CSV lines into one Expense per department, year and month."""
    reader = csv.reader(lines, delimiter=";")
    rows = _rows(reader)
    header = next(rows, None)
    if header is None or tuple(cell.strip() for cell in header) != HEADER:
        received = ";".join(header or [])[:60]
        raise InvalidData(f"expected header {';'.join(HEADER)!r}, got {received!r}")
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue  # blank line
        if len(row) != len(HEADER):
            raise InvalidData(
                f"line {reader.line_num}: expected {len(HEADER)} columns, got {len(row)}"
            )
        department, _expense_type, year, *cells = row
        try:
            year_number = int(year)
            amounts = [parse_money(cell) for cell in cells]
        except ValueError as exc:
            raise InvalidData(f"line {reader.line_num}: {exc}") from None
        for month, (amount, currency) in enumerate(amounts, start=1):
            yield Expense(department.strip(), year_number, month, amount, currency)


def _rows(reader) -> Iterator[list]:
    """Iterate a csv.reader, reporting csv.Error (NUL bytes, oversized fields) as InvalidData."""
    try:
        yield from reader
    except csv.Error as exc:
        raise InvalidData(f"line {reader.line_num}: {exc}") from None


def parse_period(text: str) -> tuple[Optional[int], Optional[int]]:
    """'Q1' -> (1, None); '3', 'Mar' or 'March' -> (None, 3)."""
    if text[:1].upper() == "Q" and text[1:].isdigit():
        return int(text[1:]), None
    if text.isdigit():
        return None, int(text)
    months = [n for n, name in enumerate(MONTH_NAMES, 1) if name.lower().startswith(text.lower())]
    if len(text) >= 3 and len(months) == 1:
        return None, months[0]
    raise ValueError(f"expected a quarter (Q1..Q4) or a month (1..12, Jan, January), got {text!r}")


def format_money(amount: Decimal, currency: str) -> str:
    """-1234 with '$' -> '-$1,234'."""
    sign = "-" if amount < 0 else ""
    return f"{sign}{currency}{abs(amount):,f}"
