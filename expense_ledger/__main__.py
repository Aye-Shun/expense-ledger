"""Command-line interface: python -m expense_ledger --help."""

import argparse
from datetime import date
import sqlite3

from .ledger import add_expense, connect, format_amount, list_expenses, summarize


def print_table(headers, rows):
    strings = [list(map(str, row)) for row in rows]
    widths = [
        max(len(header), *(len(row[index]) for row in strings))
        for index, header in enumerate(headers)
    ]
    print("  ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("  ".join("-" * width for width in widths))
    for row in strings:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track local expenses in SQLite.")
    parser.add_argument("--db", default="expenses.db", help="database path (default: expenses.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record an expense")
    add.add_argument("amount", help="positive amount, e.g. 12.50")
    add.add_argument("category", help="category, e.g. food")
    add.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (default: today)")
    add.add_argument("--note", default="", help="optional description, at most 200 characters")

    listing = commands.add_parser("list", help="list expenses ordered by date")
    listing.add_argument("--month", help="filter by YYYY-MM")
    listing.add_argument("--category", help="filter by category")

    summary = commands.add_parser("summary", help="totals grouped by month and category")
    summary.add_argument("--month", help="filter by YYYY-MM")

    args = parser.parse_args(argv)
    try:
        with connect(args.db) as connection:
            if args.command == "add":
                expense_id = add_expense(connection, args.amount, args.category, args.date, args.note)
                print(f"Added expense #{expense_id}.")
            elif args.command == "list":
                rows = list_expenses(connection, args.month, args.category)
                if not rows:
                    print("No expenses found.")
                else:
                    print_table(
                        ["ID", "Date", "Category", "Amount", "Note"],
                        [(r["id"], r["spent_on"], r["category"], format_amount(r["amount_cents"]), r["note"]) for r in rows],
                    )
            else:
                rows = summarize(connection, args.month)
                if not rows:
                    print("No expenses found.")
                else:
                    print_table(
                        ["Month", "Category", "Count", "Total"],
                        [(r["month"], r["category"], r["count"], format_amount(r["total_cents"])) for r in rows],
                    )
                    print(f"Total: {format_amount(sum(r['total_cents'] for r in rows))}")
    except (ValueError, sqlite3.Error) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
