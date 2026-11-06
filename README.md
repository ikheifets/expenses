# Expenses aggregation

Command-line tool and REST service that aggregate company expenses from CSV data in the
`Expenses.csv` format. Python 3.9+.

| File | Purpose |
|---|---|
| `reports.py` | business logic: the `Expense` model and the aggregation of totals |
| `formats.py` | parsers and formatters: the CSV layout, money values, periods |
| `cli.py` | command-line tool, reads the CSV from stdin |
| `expenses.py` | entry point named as in the task; just calls `cli.main` |
| `api.py` | FastAPI service, receives the CSV in a POST body |
| `tests/` | pytest suite, one file per module |
| `db/schema.sql` | proposed database schema with the equivalent SQL queries |

```bash
pip install -r requirements.txt   # fastapi, uvicorn, pytest, httpx; the CLI needs none of them
```

## Command-line tool

```
cat Expenses.csv | python3 expenses.py <department> [year [quarter|month]]
```

| Invocation | Output |
|---|---|
| `cat Expenses.csv \| python3 expenses.py Sales` | `$7,069,662,522` |
| `cat Expenses.csv \| python3 expenses.py "Human Resources" 2021` | `-$620,393,836` |
| `cat Expenses.csv \| python3 expenses.py Payroll 2022 Q1` | `-$37,421,162` |
| `cat Expenses.csv \| python3 expenses.py Marketing 2020 Jan` | `-$2,438,475` |

A quarter is written as `Q1`..`Q4`; a month as `1`..`12` or a name (`Jan`, `January`).
Department names are matched case-insensitively. Errors are printed to stderr with exit
code 1 (bad data, nothing matched) or 2 (bad arguments).

## REST service

```bash
uvicorn api:app --reload        # interactive docs at http://127.0.0.1:8000/docs
curl --data-binary @Expenses.csv \
     "http://127.0.0.1:8000/expenses?department=Payroll&year=2022&quarter=1"
```

```json
{"department": "Payroll", "year": 2022, "quarter": 1, "month": null,
 "amount": "-37421162", "currency": "$", "formatted": "-$37,421,162"}
```

`POST /expenses` takes the CSV in the request body and `department` (required), `year`,
`quarter` (1-4) and `month` (1-12) as query parameters; `quarter` and `month` need a `year`
and exclude each other. `amount` is a decimal string so no precision is lost in JSON.

| Status | Meaning |
|---|---|
| 400 | body is not valid CSV in the expected format, is empty or not UTF-8, or mixes currencies |
| 404 | the department has no expenses in the requested period |
| 413 | the body is larger than 10 MiB (`MAX_BODY` in `api.py`) |
| 422 | missing, malformed or inconsistent query parameters |

The service is stateless: every request carries its own data.

## Tests

```bash
python3 -m pytest
```

The expected totals for `Expenses.csv` were computed independently with `awk` over the raw
file, so the tests check the code against a second opinion rather than its own output.

## Database schema

`db/schema.sql` stores the file in a normalised "long" form: one row per department,
expense type, year and month, with lookup tables for departments and expense types. Every
aggregation of the task becomes `SUM(amount)` over a filtered set of months; the queries
are at the bottom of the file.

## Notes

* Amounts are `Decimal`, so sums are exact. Signs are kept as in the data: `Sales` rows are
  positive, the other departments negative (written as `($1,234)` in the file).
* The sample lists 2023 twice; rows with the same department and year are summed, never
  overwritten.
* The currency symbol is taken from the data; a selection that mixes currencies is an error.
* A department or period with no data is an error rather than `$0`, so typos are not hidden.
