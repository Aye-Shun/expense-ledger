# Expense Ledger

A small Python command-line app for recording expenses in a local SQLite database. Add a purchase, find past entries, and see totals by month and category without setting up a server or installing dependencies.

## Features

- Records an amount, category, date, and optional note.
- Stores money as **integer cents**, using `Decimal` to parse input exactly.
- Lists expenses in date order, with optional month and category filters.
- Groups totals by month and category using SQL.
- Validates real calendar dates and rejects amounts that would require rounding.
- Uses parameterized queries for all user-provided values.

## Quick start

Requires **Python 3.11 or newer**. The app and tests use only the Python standard library.

```bash
git clone https://github.com/Aye-Shun/expense-ledger.git
cd expense-ledger
python -m expense_ledger --help
```

On systems that use `python3`, replace `python` with `python3`. There is no package installation step; run the commands from this folder.

## Example

Use a separate demo database to keep sample entries separate from your own records:

```bash
python -m expense_ledger --db demo.db add 12.50 food --date 2026-10-01 --note "Lunch"
python -m expense_ledger --db demo.db add 3.25 food --date 2026-10-02 --note "Coffee"
python -m expense_ledger --db demo.db add 8.00 transport --date 2026-10-03 --note "Train ticket"
python -m expense_ledger --db demo.db summary --month 2026-10
```

Output after adding those three entries to an empty database:

```text
Month    Category   Count  Total
-------  ---------  -----  -----
2026-10  food       2      15.75
2026-10  transport  1      8.00
Total: 23.75
```

Running the `add` commands again creates additional entries. The app does not deduplicate purchases.

## Commands

The default database is `expenses.db` in your current directory. Put `--db PATH` **before** the command when choosing a different file.

```bash
# Record an expense; omitting --date uses today's local calendar date.
python -m expense_ledger add 19.99 supplies --note "Notebook"

# List all recorded expenses.
python -m expense_ledger list

# Find food expenses in a particular month.
python -m expense_ledger list --month 2026-10 --category food

# Summarize all months and categories, or one month.
python -m expense_ledger summary
python -m expense_ledger summary --month 2026-10
```

Amounts must be positive and have at most two decimal places: `12`, `12.5`, and `12.50` are accepted; `12.501`, `-5`, and `1e2` are rejected. Dates use `YYYY-MM-DD` and months use `YYYY-MM`. Categories are trimmed and made lowercase, so `Food` and `food` belong to the same group. Categories allow 1–40 printable characters; notes allow up to 200.

## How it works

`expense_ledger/ledger.py` contains validation and SQLite operations. `expense_ledger/__main__.py` handles command-line arguments and prints tables. The database has one `expenses` table:

| Column | Purpose |
| --- | --- |
| `id` | Entry identifier |
| `amount_cents` | Positive integer amount |
| `category` | Normalized category |
| `spent_on` | ISO calendar date |
| `note` | Optional description |

For example, `12.50` is stored as `1250`. Summaries use SQLite `GROUP BY` and `SUM`; the display converts integer cents back to two decimal places. The ledger total is capped at SQLite's signed integer limit so those sums remain exact. Adding entries locks the database while checking that limit.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover exact cents, invalid inputs, leap dates, persistence, filters, grouped totals, SQL-like strings treated as data, the integer limit, and command-line output. GitHub Actions runs the same suite on Python 3.11 and 3.14.

## Scope

This is a local learning project for Python and SQL. It supports one currency with two decimal places; it does not perform currency conversion. There are no accounts, cloud sync, bank connections, income records, refunds, edit/delete commands, or encryption. Database files are ignored by Git; back up the file yourself if you use it for personal records. Choose a database path in an existing directory.

## License

MIT — see [LICENSE](LICENSE).
