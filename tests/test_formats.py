import io
from decimal import Decimal
from pathlib import Path

import pytest

from formats import format_money, parse_money, parse_period, read_expenses
from reports import InvalidData

HEADER = "Department;Expense Type;Year;Jan;Feb;Mar;Apr;May;Jun;Jul;Aug;Sep;Oct;Nov;Dec"
ROW = "Sales;Software;2020;$1;$2;$3;$4;$5;$6;$7;$8;$9;$10;$11;$12"
SAMPLE_CSV = (Path(__file__).resolve().parent.parent / "Expenses.csv").read_text()


@pytest.mark.parametrize(
    ("text", "amount", "currency"),
    [
        ("$71,093,649", Decimal("71093649"), "$"),
        ("($34,103,526)", Decimal("-34103526"), "$"),
        ("-$5", Decimal("-5"), "$"),
        ("$-5", Decimal("-5"), "$"),
        ("USD 100", Decimal("100"), "USD"),
        ("$12.50", Decimal("12.50"), "$"),
        ("€7", Decimal("7"), "€"),
        ("1234", Decimal("1234"), ""),
    ],
)
def test_parse_money(text, amount, currency):
    assert parse_money(text) == (amount, currency)


@pytest.mark.parametrize(
    "text", ["", "$", "abc", "$1.2.3", "$1,00", "$1,234,56", "$5-", "(5", "1e5", "5$"]
)
def test_parse_money_rejects_garbage(text):
    with pytest.raises(InvalidData):
        parse_money(text)


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (Decimal("7069662522"), "$", "$7,069,662,522"),
        (Decimal("-620393836"), "$", "-$620,393,836"),
        (Decimal("12.50"), "€", "€12.50"),
        (Decimal("0"), "$", "$0"),
    ],
)
def test_format_money(amount, currency, expected):
    assert format_money(amount, currency) == expected


def test_read_expenses_yields_one_record_per_month():
    expenses = list(read_expenses(io.StringIO(f"{HEADER}\n{ROW}\n\n")))
    assert [(e.department, e.year, e.month, e.amount, e.currency) for e in expenses] == [
        ("Sales", 2020, month, Decimal(month), "$") for month in range(1, 13)
    ]


def test_read_expenses_on_sample_file():
    expenses = list(read_expenses(io.StringIO(SAMPLE_CSV)))
    assert len(expenses) == 120 * 12
    assert (expenses[0].department, expenses[0].year, expenses[0].month) == ("Sales", 2020, 1)
    assert (expenses[0].amount, expenses[0].currency) == (Decimal("71093649"), "$")


@pytest.mark.parametrize(
    ("csv_text", "message"),
    [
        ("", "expected header"),
        ("Department,Expense Type,Year\n", "expected header"),
        (f"{HEADER}\nSales;Software;2020;$1\n", "line 2: expected 15 columns, got 4"),
        (f"{HEADER}\n{ROW.replace('2020', '20x0')}\n", "line 2: invalid literal"),
        (f"{HEADER}\n{ROW.replace('$3', 'x')}\n", "line 2: cannot parse amount 'x'"),
        (f"{HEADER}\n{ROW.replace('Software', 'x' * 200_000)}\n", "line 2: field larger"),
    ],
)
def test_read_expenses_rejects_invalid_csv(csv_text, message):
    with pytest.raises(InvalidData, match=message):
        list(read_expenses(io.StringIO(csv_text)))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Q1", (1, None)),
        ("q4", (4, None)),
        ("3", (None, 3)),
        ("Mar", (None, 3)),
        ("Sept", (None, 9)),
    ],
)
def test_parse_period(text, expected):
    assert parse_period(text) == expected


@pytest.mark.parametrize("text", ["", "Q", "Foo", "Ma", "1.5", "Marvelous"])
def test_parse_period_rejects_garbage(text):
    with pytest.raises(ValueError, match="expected a quarter"):
        parse_period(text)
