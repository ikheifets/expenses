#!/usr/bin/env python3
"""Aggregate company expenses from CSV data on standard input.

    cat Expenses.csv | python3 expenses.py <department> [year [quarter|month]]

A quarter is written as Q1..Q4, a month as 1..12 or a name (Jan, January).
Department names are matched case-insensitively; quote names containing spaces.
"""

import argparse
import sys

from formats import format_money, parse_period, read_expenses
from reports import total_expenses


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("department")
    parser.add_argument("year", nargs="?", type=int)
    parser.add_argument("period", nargs="?", metavar="quarter|month")
    args = parser.parse_args()
    if sys.stdin is None or sys.stdin.isatty():
        sys.exit("error: no CSV data on stdin, e.g. cat Expenses.csv | python3 expenses.py Sales")
    sys.stdin.reconfigure(encoding="utf-8-sig")  # tolerate a BOM

    try:
        quarter, month = parse_period(args.period) if args.period else (None, None)
        expenses = read_expenses(sys.stdin)
        amount, currency = total_expenses(expenses, args.department, args.year, quarter, month)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    print(format_money(amount, currency))


if __name__ == "__main__":
    main()
