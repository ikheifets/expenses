"""Runs the command-line tool as a subprocess, exactly as described in the task."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = (ROOT / "Expenses.csv").read_bytes()


def run(*args, stdin=SAMPLE):
    command = [sys.executable, "cli.py", *args]
    return subprocess.run(command, input=stdin, capture_output=True, cwd=ROOT, timeout=30)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["Sales"], "$7,069,662,522"),
        (["Human Resources", "2021"], "-$620,393,836"),
        (["Payroll", "2022", "Q1"], "-$37,421,162"),
        (["Payroll", "2022", "q1"], "-$37,421,162"),
        (["Marketing", "2020", "Jan"], "-$2,438,475"),
        (["Marketing", "2020", "january"], "-$2,438,475"),
        (["marketing", "2020", "1"], "-$2,438,475"),
    ],
)
def test_prints_total_with_currency(args, expected):
    result = run(*args)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode() == expected + "\n"


@pytest.mark.parametrize(
    ("args", "stdin", "message"),
    [
        (["Legal"], SAMPLE, "no expenses found"),
        (["Sales", "2019"], SAMPLE, "no expenses found"),
        (["Sales", "2020", "Q5"], SAMPLE, "quarter must be between 1 and 4"),
        (["Sales", "2020", "Foo"], SAMPLE, "expected a quarter"),
        (["Sales"], b"garbage", "expected header"),
        (["Sales"], b"", "expected header"),
        (["Sales"], SAMPLE + b"\r\nSales;" + b"x" * 200_000, "field larger"),  # csv.Error
    ],
)
def test_errors_go_to_stderr_with_exit_code_1(args, stdin, message):
    result = run(*args, stdin=stdin)
    assert result.returncode == 1
    assert result.stdout == b""
    assert message in result.stderr.decode()


def test_expenses_py_entry_point_from_the_task_statement():
    command = [sys.executable, "expenses.py", "Payroll", "2022", "Q1"]
    result = subprocess.run(command, input=SAMPLE, capture_output=True, cwd=ROOT, timeout=30)
    assert result.stdout.decode() == "-$37,421,162\n"


@pytest.mark.parametrize("args", [[], ["Sales", "20x1"], ["Sales", "2020", "Q1", "extra"]])
def test_bad_arguments_exit_with_2(args):
    assert run(*args).returncode == 2


def test_accepts_utf8_bom():
    assert run("Sales", stdin=b"\xef\xbb\xbf" + SAMPLE).stdout.decode() == "$7,069,662,522\n"
