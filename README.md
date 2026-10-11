# Expense Ledger

Record expenses in SQLite and total them by month and category. Small practice project for Python command-line tools and SQL.

Python 3.11+, using only the standard library. Run from this folder:

```sh
python3 -m expense_ledger --db demo.db add 12.50 food --date 2026-10-01 --note "Lunch"
python3 -m expense_ledger --db demo.db add 3.25 food --date 2026-10-02
python3 -m expense_ledger --db demo.db list --category food
python3 -m expense_ledger --db demo.db summary --month 2026-10
```

An empty demo database will now have two entries totaling **15.75**. Running the add commands again adds them again.

## Notes

Without `--db`, the file is `expenses.db`. Put `--db` before the command and choose a path in an existing directory. Omit `--date` to use today. `list` also accepts `--month`; omit filters to see everything.

Amounts must be positive with at most two decimal places. `12.50` is stored as 1250 cents, using `Decimal` to parse it without rounding. Dates must be real `YYYY-MM-DD` dates. Categories are trimmed and made lowercase; notes are optional.

The validation and queries live in `expense_ledger/ledger.py`. Summaries use SQL grouping. This handles one currency with two decimal places, without conversion, refunds, edit/delete, accounts, or sync. Database files are ignored by Git; back them up separately.

```sh
python3 -m unittest discover -s tests -v
```

[MIT](LICENSE)
