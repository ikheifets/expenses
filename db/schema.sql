-- PostgreSQL schema for the data in Expenses.csv.
--
-- The spreadsheet is "wide": one row per department, expense type and year with twelve
-- month columns. It is stored "long" - one row per month - because every aggregation
-- of the task is SUM(amount) over a set of months.

CREATE TABLE department (
    id   serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE expense_type (
    id   serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE expense (
    id              bigserial PRIMARY KEY,
    department_id   integer  NOT NULL REFERENCES department (id),
    expense_type_id integer  NOT NULL REFERENCES expense_type (id),
    year            smallint NOT NULL,
    month           smallint NOT NULL CHECK (month BETWEEN 1 AND 12),
    quarter         smallint GENERATED ALWAYS AS ((month - 1) / 3 + 1) STORED,
    currency        char(3)  NOT NULL DEFAULT 'USD',
    amount          numeric(18, 2) NOT NULL          -- signed: "($1,234)" in the file is -1234
);

-- Rows sharing department / type / year / month are additive rather than unique:
-- the sample file itself contains the 2023 block twice and the tool sums them.
CREATE INDEX expense_lookup ON expense (department_id, year, month);


-- The four aggregations of the task (each one mirrors a CLI invocation).

-- a) python3 expenses.py Sales
SELECT sum(e.amount) AS total
FROM expense e JOIN department d ON d.id = e.department_id
WHERE d.name = 'Sales';

-- b) python3 expenses.py "Human Resources" 2021
SELECT sum(e.amount) AS total
FROM expense e JOIN department d ON d.id = e.department_id
WHERE d.name = 'Human Resources' AND e.year = 2021;

-- c) python3 expenses.py Payroll 2022 Q1
SELECT sum(e.amount) AS total
FROM expense e JOIN department d ON d.id = e.department_id
WHERE d.name = 'Payroll' AND e.year = 2022 AND e.quarter = 1;

-- d) python3 expenses.py Marketing 2020 Jan
SELECT sum(e.amount) AS total
FROM expense e JOIN department d ON d.id = e.department_id
WHERE d.name = 'Marketing' AND e.year = 2020 AND e.month = 1;
