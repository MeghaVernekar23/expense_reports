"""Zip export of ledger data (all categories, or a single one) plus their
uploaded bill files, and the ui.download triggers that hand them to the browser."""
import csv
import io
import zipfile
from datetime import date
from pathlib import Path

from nicegui import ui

import storage

BILLS_DIR = Path(__file__).parent / "bills"
BILLS_DIR.mkdir(exist_ok=True)

_EXPENSE_HEADER = ["id", "date", "category", "amount", "currency", "amount_eur", "fx_rate_inr_per_eur", "note", "bill_file"]


def _expense_row(e) -> list:
    return [
        e.id,
        e.spent_on,
        e.category_name,
        f"{e.amount:.2f}",
        e.currency,
        f"{e.amount_eur:.2f}",
        f"{e.fx_rate:.4f}" if e.fx_rate else "",
        e.note or "",
        e.bill_path or "",
    ]


def build_export_zip() -> bytes:
    """Package every category, every expense, and all uploaded bill files
    into a single zip: categories.csv, expenses.csv, and bills/<file>."""
    cats = storage.get_categories()
    expenses = storage.get_expenses()

    cat_buf = io.StringIO()
    cat_writer = csv.writer(cat_buf)
    cat_writer.writerow(["id", "name", "period", "start_date", "end_date", "budget_eur", "active"])
    for c in cats:
        cat_writer.writerow(
            [c.id, c.name, c.month_label, c.period_start or "", c.period_end or "", f"{c.budget:.2f}", c.is_active]
        )

    exp_buf = io.StringIO()
    exp_writer = csv.writer(exp_buf)
    exp_writer.writerow(_EXPENSE_HEADER)
    for e in expenses:
        exp_writer.writerow(_expense_row(e))

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("categories.csv", cat_buf.getvalue())
        zf.writestr("expenses.csv", exp_buf.getvalue())
        for e in expenses:
            if e.bill_path:
                bill_file = BILLS_DIR / e.bill_path
                if bill_file.exists():
                    zf.write(bill_file, f"bills/{e.bill_path}")
    return zip_buf.getvalue()


def download_everything():
    data = build_export_zip()
    ui.download(data, filename=f"ledger-export-{date.today().isoformat()}.zip")


def build_category_export_zip(cat) -> bytes:
    """Package one category's expenses + its bill files into a zip:
    expenses.csv and bills/<file>. Mirrors build_export_zip but scoped
    to a single category, for the per-card download on Past categories."""
    expenses = storage.get_expenses(cat.id)

    exp_buf = io.StringIO()
    exp_writer = csv.writer(exp_buf)
    exp_writer.writerow(_EXPENSE_HEADER)
    for e in expenses:
        exp_writer.writerow(_expense_row(e))

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("expenses.csv", exp_buf.getvalue())
        for e in expenses:
            if e.bill_path:
                bill_file = BILLS_DIR / e.bill_path
                if bill_file.exists():
                    zf.write(bill_file, f"bills/{e.bill_path}")
    return zip_buf.getvalue()


def download_category(cat):
    data = build_category_export_zip(cat)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in cat.name)
    ui.download(data, filename=f"{safe_name}-{cat.month_label}-{cat.id}.zip".replace(" ", "_"))
