"""Stateless REST service over reports.py (FastAPI, run with ``uvicorn api:app``).

    curl --data-binary @Expenses.csv \\
         "http://127.0.0.1:8000/expenses?department=Payroll&year=2022&quarter=1"

The CSV travels in the body of a POST request, the aggregation parameters in the query
string; nothing is stored between requests.
"""

import io
from typing import Optional

from fastapi import FastAPI, HTTPException, Request

from formats import format_money, read_expenses
from reports import InvalidData, NotFound, total_expenses

app = FastAPI(title="Expenses aggregation")

# HTTP status for each error the aggregation can raise; any other ValueError is a bad parameter.
STATUS = {NotFound: 404, InvalidData: 400}
MAX_BODY = 10 * 1024 * 1024  # bytes of CSV accepted in one request
CSV_BODY = {  # lets Swagger UI send the CSV as the request body
    "requestBody": {"required": True, "content": {"text/csv": {"schema": {"type": "string"}}}}
}


@app.post("/expenses", openapi_extra=CSV_BODY)
async def expenses(
    request: Request,
    department: str,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Aggregate the CSV in the request body for a department and an optional period."""
    body = bytearray()
    async for chunk in request.stream():  # incremental, so an oversized body is cut off early
        body.extend(chunk)
        if len(body) > MAX_BODY:
            raise HTTPException(413, f"request body exceeds {MAX_BODY} bytes")
    try:
        lines = io.StringIO(body.decode("utf-8-sig"))  # tolerate a BOM
    except UnicodeDecodeError:
        raise HTTPException(400, "request body must be UTF-8 text") from None
    try:
        amount, currency = total_expenses(read_expenses(lines), department, year, quarter, month)
    except ValueError as exc:
        raise HTTPException(STATUS.get(type(exc), 422), str(exc)) from None
    return {
        "department": department,
        "year": year,
        "quarter": quarter,
        "month": month,
        "amount": str(amount),  # exact decimal; JSON numbers are floats
        "currency": currency,
        "formatted": format_money(amount, currency),
    }
