from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
from api import app

SAMPLE = (Path(__file__).resolve().parent.parent / "Expenses.csv").read_bytes()
client = TestClient(app)


def post(csv=SAMPLE, **params):
    return client.post("/expenses", params=params, content=csv)


@pytest.mark.parametrize(
    ("params", "amount", "formatted"),
    [
        ({"department": "Sales"}, "7069662522", "$7,069,662,522"),
        (
            {"department": "Human Resources", "year": 2021},
            "-620393836",
            "-$620,393,836",
        ),
        (
            {"department": "Payroll", "year": 2022, "quarter": 1},
            "-37421162",
            "-$37,421,162",
        ),
        (
            {"department": "Marketing", "year": 2020, "month": 1},
            "-2438475",
            "-$2,438,475",
        ),
    ],
)
def test_aggregates(params, amount, formatted):
    response = post(**params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["amount"], body["currency"], body["formatted"]) == (
        amount,
        "$",
        formatted,
    )
    assert body["department"] == params["department"]


@pytest.mark.parametrize(
    ("params", "csv", "status"),
    [
        ({"department": "Legal"}, SAMPLE, 404),
        ({"department": "Sales", "year": 2019}, SAMPLE, 404),
        ({}, SAMPLE, 422),  # department is required
        ({"department": "Sales", "year": "abc"}, SAMPLE, 422),
        ({"department": "Sales", "quarter": 1}, SAMPLE, 422),  # quarter requires a year
        ({"department": "Sales", "year": 2020, "quarter": 1, "month": 1}, SAMPLE, 422),
        ({"department": "Sales", "year": 2020, "quarter": 5}, SAMPLE, 422),
        ({"department": "Sales"}, b"", 400),
        ({"department": "Sales"}, b"not;a;csv", 400),
        ({"department": "Sales"}, b"\xff\xfe", 400),  # not UTF-8
        ({"department": "Sales"}, SAMPLE + b"\r\nSales;" + b"x" * 200_000, 400),  # csv.Error
        ({"department": ""}, SAMPLE, 422),
        ({"department": "  "}, SAMPLE, 422),
    ],
)
def test_errors(params, csv, status):
    response = post(csv, **params)
    assert response.status_code == status, response.text
    assert "detail" in response.json()


def test_accepts_utf8_bom():
    response = post(b"\xef\xbb\xbf" + SAMPLE, department="Sales")
    assert response.json()["formatted"] == "$7,069,662,522"


def test_oversized_body_is_413(monkeypatch):
    monkeypatch.setattr(api, "MAX_BODY", 1000)
    assert post(SAMPLE, department="Sales").status_code == 413


def test_is_stateless():
    changed = SAMPLE.replace(b"Sales;Software;2020;$71,093,649", b"Sales;Software;2020;$71,093,650")
    first = post(SAMPLE, department="Sales", year=2020).json()["amount"]
    second = post(changed, department="Sales", year=2020).json()["amount"]
    assert int(second) == int(first) + 1
