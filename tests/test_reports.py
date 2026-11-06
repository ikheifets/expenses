import io
from decimal import Decimal
from pathlib import Path

import pytest

from formats import format_money, read_expenses
from reports import Expense, InvalidData, NotFound, total_expenses


def expenses(department, year, amount, currency="$"):
    """Twelve monthly records with the same amount."""
    return [Expense(department, year, month, Decimal(amount), currency) for month in range(1, 13)]


# Totals are easy to check by hand. Payroll 2020 appears twice: duplicates must be summed.
SMALL = (
    [Expense("Sales", 2020, month, Decimal(10 * month), "$") for month in range(1, 13)]
    + [Expense("Sales", 2020, month, Decimal(month), "$") for month in range(1, 13)]
    + expenses("Sales", 2021, 1000)
    + expenses("Payroll", 2020, -5)
    + expenses("Payroll", 2020, -1)
)
SAMPLE_CSV = (Path(__file__).resolve().parent.parent / "Expenses.csv").read_text()


@pytest.mark.parametrize(
    ("department", "period", "expected"),
    [
        ("Sales", {}, 12858),
        ("sales", {}, 12858),  # case-insensitive
        ("Sales", {"year": 2020}, 858),
        ("Sales", {"year": 2020, "quarter": 1}, 66),
        ("Sales", {"year": 2020, "quarter": 4}, 363),
        ("Sales", {"year": 2020, "month": 1}, 11),
        ("Sales", {"year": 2020, "month": 12}, 132),
        ("Payroll", {"year": 2020}, -72),  # duplicated rows are summed
    ],
)
def test_totals_on_hand_checked_data(department, period, expected):
    assert total_expenses(SMALL, department, **period) == (Decimal(expected), "$")


# Expected values were computed independently with awk over the raw file.
@pytest.mark.parametrize(
    ("department", "period", "expected"),
    [
        ("Sales", {}, "$7,069,662,522"),
        ("Human Resources", {"year": 2021}, "-$620,393,836"),
        ("Payroll", {"year": 2022, "quarter": 1}, "-$37,421,162"),
        ("Marketing", {"year": 2020, "month": 1}, "-$2,438,475"),
        ("Consulting", {"year": 2023}, "-$166,278,271"),  # 2023 appears twice in the file
        ("Travel & Entertainment", {"year": 2023, "quarter": 4}, "-$8,418,705"),
        ("Sales", {"year": 2021, "month": 3}, "$108,872,683"),
    ],
)
def test_totals_on_sample_file(department, period, expected):
    total = total_expenses(read_expenses(io.StringIO(SAMPLE_CSV)), department, **period)
    assert format_money(*total) == expected


@pytest.mark.parametrize(
    ("department", "period"),
    [("Legal", {}), ("Sales", {"year": 2019}), ("Sales", {"year": 2022, "quarter": 1})],
)
def test_nothing_matched(department, period):
    with pytest.raises(NotFound):
        total_expenses(SMALL, department, **period)


@pytest.mark.parametrize(
    ("period", "message"),
    [
        ({"quarter": 1}, "require a year"),
        ({"month": 1}, "require a year"),
        ({"year": 2020, "quarter": 1, "month": 1}, "not both"),
        ({"year": 2020, "quarter": 5}, "quarter must be between 1 and 4"),
        ({"year": 2020, "month": 13}, "month must be between 1 and 12"),
    ],
)
def test_invalid_parameters(period, message):
    with pytest.raises(ValueError, match=message):
        total_expenses(SMALL, "Sales", **period)


def test_blank_department_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        total_expenses(SMALL, "  ")


def test_mixed_currencies_are_rejected():
    with pytest.raises(InvalidData, match="mixed currencies"):
        total_expenses(expenses("Sales", 2020, 1) + expenses("Sales", 2021, 1, "€"), "Sales")
