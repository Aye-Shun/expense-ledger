from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

from expense_ledger.__main__ import main
from expense_ledger.ledger import (
    MAX_CENTS, add_expense, connect, format_amount, list_expenses,
    normalize_category, parse_amount, parse_date, parse_month, summarize,
)


class ValidationTests(unittest.TestCase):
    def test_amounts_are_exact_integer_cents(self):
        for value, expected in [("0.01", 1), ("12.5", 1250), ("19", 1900), (" 0.29 ", 29)]:
            with self.subTest(value=value):
                self.assertEqual(parse_amount(value), expected)
        self.assertEqual(parse_amount("92233720368547758.07"), MAX_CENTS)
        self.assertEqual(format_amount(MAX_CENTS), "92233720368547758.07")

    def test_invalid_amounts_are_rejected_without_rounding(self):
        for value in ["0", "0.00", "-1", "+1", "1.001", "1e2", "NaN", "Infinity", "1,000", "", "92233720368547758.08", "9" * 1000]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_amount(value)

    def test_real_dates_and_months(self):
        self.assertEqual(parse_date("2024-02-29"), "2024-02-29")
        self.assertEqual(parse_month("2026-10"), "2026-10")
        for value in ["2025-02-29", "2026-04-31", "20261010", "2026-1-01", "0000-01-01"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_date(value)
        for value in ["2026-00", "2026-13", "2026-1", "0000-01"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_month(value)

    def test_category_normalization_and_invalid_input(self):
        self.assertEqual(normalize_category(" Food "), "food")
        for value in ["", "   ", "a" * 41, "food\ntravel"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_category(value)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = Path(self.directory.name) / "ledger.db"

    def tearDown(self):
        self.directory.cleanup()

    def test_storage_filters_and_persistence(self):
        with connect(self.db) as connection:
            add_expense(connection, "0.10", "Food", "2026-10-01", "Coffee")
            add_expense(connection, "0.20", "food", "2026-10-02")
            add_expense(connection, "2.50", "Travel", "2026-09-30")
        with connect(self.db) as connection:
            self.assertEqual([r["spent_on"] for r in list_expenses(connection)], ["2026-09-30", "2026-10-01", "2026-10-02"])
            rows = list_expenses(connection, month="2026-10", category=" FOOD ")
            self.assertEqual([r["amount_cents"] for r in rows], [10, 20])
            self.assertEqual(connection.execute("SELECT typeof(amount_cents) FROM expenses").fetchone()[0], "integer")
            summary = summarize(connection, month="2026-10")
            self.assertEqual([(r["month"], r["category"], r["count"], r["total_cents"]) for r in summary], [("2026-10", "food", 2, 30)])
            self.assertEqual(len(summarize(connection)), 2)

    def test_user_strings_are_bound_as_data(self):
        category = "food'; drop table expenses;--"
        note = "a'); DROP TABLE expenses; --"
        with connect(self.db) as connection:
            add_expense(connection, "3.00", category, "2026-10-10", note)
            row = list_expenses(connection, category=category)[0]
            self.assertEqual(row["note"], note)
            self.assertEqual(row["category"], category)
            self.assertEqual(len(list_expenses(connection)), 1)

    def test_validation_failures_do_not_insert(self):
        with connect(self.db) as connection:
            for args in [("1.001", "food", "2026-10-10", ""), ("1", "food", "2026-02-30", ""), ("1", "food", "2026-10-10", "x" * 201)]:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    add_expense(connection, *args)
            self.assertEqual(list_expenses(connection), [])

    def test_total_cap_prevents_sqlite_sum_overflow(self):
        with connect(self.db) as connection:
            add_expense(connection, "92233720368547758.07", "test", "2026-10-10")
            with self.assertRaises(ValueError):
                add_expense(connection, "0.01", "test", "2026-10-10")
            self.assertEqual(summarize(connection)[0]["total_cents"], MAX_CENTS)

    def test_cli_output_and_errors(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--db", str(self.db), "list"])
            main(["--db", str(self.db), "add", "12.50", "food", "--date", "2026-10-10"])
            main(["--db", str(self.db), "summary", "--month", "2026-10"])
            main(["--db", str(self.db), "list", "--category", "food"])
        self.assertIn("No expenses found.", output.getvalue())
        self.assertIn("Added expense #1.", output.getvalue())
        self.assertIn("Total: 12.50", output.getvalue())
        self.assertIn("2026-10-10", output.getvalue())
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as caught:
            main(["--db", str(self.db), "add", "1.001", "food"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("at most two decimal places", error.getvalue())


if __name__ == "__main__":
    unittest.main()
