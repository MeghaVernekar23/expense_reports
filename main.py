"""Expense Reports Dashboard — NiceGUI app."""
import csv
import io
import shutil
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path

from nicegui import ui, app

import storage

storage.init_db()

BILLS_DIR = Path(__file__).parent / "bills"
BILLS_DIR.mkdir(exist_ok=True)
app.add_static_files("/bills", str(BILLS_DIR))

# ---- Palette --------------------------------------------------------
# Warm paper ground, ink text, a muted steel-blue accent — a quiet,
# ledger-like palette suited to a finance tool rather than a generic app.
INK = "#1C2333"
PAPER = "#FAFAF7"
SURFACE = "#FFFFFF"
BORDER = "#E4E2DA"
MUTED = "#767A8C"
ACCENT = "#3D5A80"
ACCENT_SOFT = "#EDF1F6"
GOOD = "#2E7D5B"
WARN = "#B8860B"
CRITICAL = "#B0413E"


CURRENCY_SYMBOLS = {"EUR": "€", "INR": "₹"}


def fmt_money(v: float, currency: str = "EUR") -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, "")
    return f"{symbol}{v:,.2f}"


def fmt_eur(v: float) -> str:
    return fmt_money(v, "EUR")


def parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_remaining(end_str: str | None) -> int | None:
    end = parse_date(end_str)
    if end is None:
        return None
    delta = (end - date.today()).days
    return max(delta, 0)


def format_period(start, end):
    if not start and not end:
        return None
    s = parse_date(start)
    e = parse_date(end)
    if s and e:
        return f"{s.strftime('%d %b')} – {e.strftime('%d %b %Y')}"
    if s:
        return f"From {s.strftime('%d %b %Y')}"
    if e:
        return f"Until {e.strftime('%d %b %Y')}"
    return None


def is_active_period(cat) -> bool:
    """A category is 'current' if it has no end date, or its end date
    hasn't passed yet. Past periods (old months) are excluded from the
    main view and totals, but stay visible in the All periods history."""
    end = parse_date(cat.period_end)
    return end is None or end >= date.today()


def status_color(pct_used: float) -> str:
    if pct_used >= 100:
        return CRITICAL
    if pct_used >= 75:
        return WARN
    return GOOD


def build_export_zip() -> bytes:
    """Package every category, every expense, and all uploaded bill files
    into a single zip: categories.csv, expenses.csv, and bills/<file>."""
    cats = storage.get_categories()
    expenses = storage.get_expenses()

    cat_buf = io.StringIO()
    cat_writer = csv.writer(cat_buf)
    cat_writer.writerow(["id", "name", "period", "start_date", "end_date", "budget_eur"])
    for c in cats:
        cat_writer.writerow([c.id, c.name, c.month_label, c.period_start or "", c.period_end or "", f"{c.budget:.2f}"])

    exp_buf = io.StringIO()
    exp_writer = csv.writer(exp_buf)
    exp_writer.writerow(
        ["id", "date", "category", "amount", "currency", "amount_eur", "fx_rate_inr_per_eur", "note", "bill_file"]
    )
    for e in expenses:
        exp_writer.writerow(
            [
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
        )

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


def pace_status(cat, spent: float) -> tuple[str, str]:
    """Compare spend pace against the elapsed share of the category's period,
    so overspending shows red/yellow even while % of budget still looks fine.

    Returns (color, short_label). Falls back to plain % thresholds when the
    category has no dated period to pace against.
    """
    budget = cat.budget or 0
    pct_used = (spent / budget * 100) if budget > 0 else 0

    start = parse_date(cat.period_start)
    end = parse_date(cat.period_end)
    if not (start and end) or budget <= 0:
        if pct_used >= 100:
            return CRITICAL, "Over budget"
        if pct_used >= 75:
            return WARN, "Watch spending"
        return GOOD, "On track"

    total_days = max((end - start).days, 1)
    elapsed_days = min(max((date.today() - start).days, 0), total_days)
    pct_elapsed = elapsed_days / total_days * 100

    # how far ahead of the "fair" pace this category's spend is
    drift = pct_used - pct_elapsed

    if pct_used >= 100 or drift >= 20:
        return CRITICAL, "Spending too fast"
    if drift >= 8:
        return WARN, "Ahead of pace"
    return GOOD, "On track"


# ---------------------------------------------------------------- UI ----

@ui.page("/")
def main_page():
    ui.add_head_html(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --ink: {INK};
                --paper: {PAPER};
                --surface: {SURFACE};
                --border: {BORDER};
                --muted: {MUTED};
                --accent: {ACCENT};
                --accent-soft: {ACCENT_SOFT};
                --good: {GOOD};
                --warn: {WARN};
                --critical: {CRITICAL};
            }}
            html, body {{
                background: var(--paper) !important;
                color: var(--ink);
                font-family: 'Inter', system-ui, sans-serif;
            }}
            .display {{
                font-family: 'Fraunces', Georgia, serif;
                font-optical-sizing: auto;
            }}
            .tabular {{ font-variant-numeric: tabular-nums; }}
            .panel {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                box-shadow: 0 1px 2px rgba(28, 35, 51, 0.04);
            }}
            .stripe-card {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-left-width: 3px;
                border-radius: 8px;
                transition: box-shadow .15s ease;
            }}
            .stripe-card:hover {{ box-shadow: 0 2px 10px rgba(28, 35, 51, 0.07); }}
            .eyebrow {{
                font-size: 11px;
                letter-spacing: .08em;
                text-transform: uppercase;
                color: var(--muted);
                font-weight: 600;
            }}
            .hairline {{ border-color: var(--border) !important; }}
            .q-field__control, .q-field__native {{ color: var(--ink) !important; }}
            .q-field--outlined .q-field__control:before {{ border-color: var(--border) !important; }}
            .q-btn.accent-btn {{ background: var(--accent) !important; color: white !important; }}
            .q-list, .q-item {{ background: transparent !important; }}
            .q-item {{ border-color: var(--border) !important; }}
            ::selection {{ background: var(--accent-soft); }}
        </style>
        """
    )

    with ui.column().classes("w-full items-center").style("padding: 40px 20px 64px; gap: 0;"):
        with ui.column().classes("w-full").style("max-width: 1040px; gap: 28px;"):

            # ---- Masthead ----
            with ui.row().classes("w-full items-baseline justify-between no-wrap"):
                with ui.column().style("gap: 2px;"):
                    ui.label("Nikhil and Megha Ledger").classes("display").style(
                        f"font-size: 30px; font-weight: 600; color: {INK}; line-height: 1.1;"
                    )
                    ui.label("Category budgets & daily spend").classes("eyebrow")
                with ui.column().style("gap: 6px; align-items: flex-end;"):
                    ui.label(date.today().strftime("%A, %d %B %Y")).style(f"color:{MUTED}; font-size: 13px;")
                    with ui.row().style("gap: 4px;"):
                        ui.button("All periods", icon="history", on_click=open_all_periods_dialog).props(
                            "flat no-caps dense"
                        ).style(f"color:{MUTED}; font-size: 12.5px;")
                        ui.button("Download all", icon="download", on_click=download_everything).props(
                            "flat no-caps dense"
                        ).style(f"color:{ACCENT}; font-size: 12.5px;")

            totals_row = ui.column().classes("w-full").style("gap: 10px;")
            summary_container = ui.column().classes("w-full").style("gap: 14px;")

            with ui.row().classes("w-full items-start").style("gap: 24px; flex-wrap: wrap;"):
                with ui.column().style("flex: 1 1 340px; gap: 20px; min-width: 320px;"):
                    category_card = ui.column().classes("w-full")
                    expense_card = ui.column().classes("w-full")

                with ui.column().style("flex: 1.3 1 380px; gap: 12px; min-width: 340px;"):
                    history_container = ui.column().classes("w-full").style("gap: 10px;")

            def refresh_all():
                render_totals(totals_row)
                render_summary(summary_container, refresh_all)
                render_history(history_container, refresh_all)
                render_add_expense_card(expense_card, refresh_all)

            render_add_category_card(category_card, refresh_all)
            refresh_all()


def render_totals(container: ui.column):
    container.clear()
    all_cats = storage.get_categories()
    active_cats = [c for c in all_cats if is_active_period(c)]

    def totals_for(cats):
        budget = sum(c.budget or 0 for c in cats)
        spent = sum(storage.get_total_spent(c.id) for c in cats)
        pct = (spent / budget * 100) if budget > 0 else 0
        return budget, spent, budget - spent, pct

    with container:
        # Current period(s) — what's active right now
        cur_budget, cur_spent, cur_remaining, cur_pct = totals_for(active_cats)
        ui.label("Current period").classes("eyebrow").style("padding-left: 2px;")
        with ui.row().classes("panel w-full items-stretch no-wrap").style(
            "padding: 20px 24px; gap: 0; overflow-x: auto;"
        ):
            stat("Total budget", fmt_eur(cur_budget), INK)
            divider()
            stat("Spent", fmt_eur(cur_spent), status_color(cur_pct))
            divider()
            stat(
                "Remaining" if cur_remaining >= 0 else "Over budget",
                fmt_eur(abs(cur_remaining)),
                GOOD if cur_remaining >= 0 else CRITICAL,
            )
            divider()
            stat("Utilised", f"{cur_pct:.0f}%", status_color(cur_pct))

        # All-time — every category, every period, ever
        all_budget, all_spent, all_remaining, all_pct = totals_for(all_cats)
        ui.label("All-time overall").classes("eyebrow").style("padding-left: 2px; margin-top: 4px;")
        with ui.row().classes("panel w-full items-stretch no-wrap").style(
            "padding: 14px 24px; gap: 0; overflow-x: auto; background: var(--accent-soft);"
        ):
            stat_sm("Total spent", fmt_eur(all_spent), INK)
            divider()
            stat_sm("Total budgeted", fmt_eur(all_budget), INK)
            divider()
            stat_sm("Budget utilised", f"{all_pct:.0f}%", status_color(all_pct))
            divider()
            stat_sm(
                "Remaining" if all_remaining >= 0 else "Over budget",
                fmt_eur(abs(all_remaining)),
                GOOD if all_remaining >= 0 else CRITICAL,
            )


def stat(label: str, value: str, color: str):
    with ui.column().style("gap: 4px; padding: 0 24px; min-width: 130px;"):
        ui.label(label).classes("eyebrow")
        ui.label(value).classes("display tabular").style(f"font-size: 24px; font-weight: 600; color: {color};")


def stat_sm(label: str, value: str, color: str):
    with ui.column().style("gap: 2px; padding: 0 24px; min-width: 120px;"):
        ui.label(label).classes("eyebrow")
        ui.label(value).classes("tabular").style(f"font-size: 16px; font-weight: 600; color: {color};")


def divider():
    ui.element("div").classes("hairline").style("width: 1px; align-self: stretch; border-left: 1px solid;")


def render_summary(container: ui.column, refresh_all):
    container.clear()
    all_cats = storage.get_categories()
    cats = [c for c in all_cats if is_active_period(c)]
    with container:
        if not all_cats:
            with ui.column().classes("panel w-full items-center").style("padding: 40px 20px; gap: 6px;"):
                ui.icon("inbox", size="28px").style(f"color:{MUTED}")
                ui.label("No categories yet").style(f"color:{INK}; font-weight: 600;")
                ui.label("Add one on the left to start tracking spend.").style(f"color:{MUTED}; font-size: 13px;")
            return

        if not cats:
            with ui.column().classes("panel w-full items-center").style("padding: 32px 20px; gap: 6px;"):
                ui.icon("event_busy", size="26px").style(f"color:{MUTED}")
                ui.label("No active period right now").style(f"color:{INK}; font-weight: 600;")
                ui.label("Start a new period on a category, or check All periods.").style(
                    f"color:{MUTED}; font-size: 13px;"
                )
            return

        ui.label("Categories").classes("eyebrow").style("padding-left: 2px;")
        with ui.grid(columns="repeat(auto-fit, minmax(280px, 1fr))").classes("w-full").style("gap: 12px;"):
            for cat in cats:
                spent = storage.get_total_spent(cat.id)
                budget = cat.budget or 0
                remaining = budget - spent
                pct_used = (spent / budget * 100) if budget > 0 else 0
                pct_left = max(0, 100 - pct_used)

                d_left = days_remaining(cat.period_end)
                per_day = None
                if d_left is not None and d_left > 0 and remaining > 0:
                    per_day = remaining / d_left
                elif d_left == 0 and remaining > 0:
                    per_day = remaining

                color, pace_label = pace_status(cat, spent)

                with ui.column().classes("stripe-card").style(
                    f"border-left-color: {color}; padding: 16px 18px; gap: 10px;"
                ):
                    with ui.row().classes("w-full items-center justify-between no-wrap").style("gap: 8px;"):
                        with ui.column().style("gap: 1px; min-width: 0;"):
                            ui.label(cat.name).style(f"font-weight: 600; font-size: 15px; color: {INK};")
                            ui.label(cat.month_label).style(f"font-size: 11px; color:{MUTED};")
                        with ui.row().style("gap: 0; flex: none;"):
                            ui.button(
                                icon="event_repeat",
                                on_click=lambda c=cat: open_new_period_dialog(c, refresh_all),
                            ).props("flat round dense size=sm").style(f"color:{MUTED}").tooltip(
                                "Start next period"
                            )
                            ui.button(
                                icon="edit_outlined", on_click=lambda c=cat: open_edit_dialog(c, refresh_all)
                            ).props("flat round dense size=sm").style(f"color:{MUTED}")
                            ui.button(
                                icon="delete_outline",
                                on_click=lambda c=cat: confirm_delete_category(c, refresh_all),
                            ).props("flat round dense size=sm").style(f"color:{MUTED}")

                    with ui.row().classes("items-center").style("gap: 6px;"):
                        ui.element("div").style(
                            f"width:8px;height:8px;border-radius:50%;background:{color};flex:none;"
                        )
                        ui.label(pace_label).style(f"font-size: 11.5px; font-weight: 600; color:{color};")

                    ui.linear_progress(min(pct_used / 100, 1), show_value=False).props(
                        f'color=none track-color=grey-3 size="6px"'
                    ).style(f"border-radius: 4px; --q-primary: {color};")

                    with ui.row().classes("w-full justify-between items-baseline").style("gap: 8px;"):
                        ui.label(f"{fmt_eur(spent)} of {fmt_eur(budget)}").classes("tabular").style(
                            f"font-size: 13px; color: {MUTED};"
                        )
                        ui.label(f"{pct_used:.0f}%").classes("tabular").style(
                            f"font-size: 13px; font-weight: 600; color: {color};"
                        )

                    remaining_label = (
                        f"{fmt_money(remaining)} left ({pct_left:.0f}%)"
                        if remaining >= 0
                        else f"{fmt_money(-remaining)} over budget"
                    )
                    ui.label(remaining_label).classes("tabular").style(
                        f"font-size: 12.5px; color: {GOOD if remaining >= 0 else CRITICAL}; font-weight: 500;"
                    )

                    if d_left is not None:
                        ui.element("div").classes("hairline").style("width:100%; border-top: 1px solid; margin: 2px 0;")
                        with ui.row().classes("w-full justify-between items-baseline"):
                            ui.label(f"{d_left} day{'s' if d_left != 1 else ''} left").style(
                                f"font-size: 12px; color: {MUTED};"
                            )
                            if per_day is not None:
                                ui.label(f"{fmt_money(per_day)}/day").classes("tabular").style(
                                    f"font-size: 12px; font-weight: 600; color: {ACCENT};"
                                )
                            elif remaining < 0:
                                ui.label("Budget exceeded").style(
                                    f"font-size: 12px; font-weight: 600; color: {CRITICAL};"
                                )


def section_label(text: str):
    ui.label(text).classes("eyebrow").style("padding-left: 2px;")


def render_add_category_card(container: ui.column, on_added):
    with container:
        section_label("Add category")
        with ui.column().classes("panel w-full").style("padding: 18px 20px; gap: 12px;"):
            name_input = ui.input("Category name").props("outlined dense").classes("w-full")
            budget_input = ui.number("Budget amount", min=0, format="%.2f").props("outlined dense").classes("w-full")

            ui.label("Period (optional)").style(f"font-size: 11.5px; color:{MUTED}; margin-top: 2px;")
            with ui.row().classes("w-full no-wrap").style("gap: 10px;"):
                start_input = ui.input("Start date").props("outlined dense readonly").classes("w-full")
                with start_input as si:
                    with ui.menu().props("no-parent-event") as start_menu:
                        with ui.date().bind_value(start_input):
                            with ui.row().classes("justify-end w-full"):
                                ui.button("Close", on_click=start_menu.close).props("flat")
                    with si.add_slot("append"):
                        ui.icon("event", size="18px").on("click", start_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

                end_input = ui.input("End date").props("outlined dense readonly").classes("w-full")
                with end_input as ei:
                    with ui.menu().props("no-parent-event") as end_menu:
                        with ui.date().bind_value(end_input):
                            with ui.row().classes("justify-end w-full"):
                                ui.button("Close", on_click=end_menu.close).props("flat")
                    with ei.add_slot("append"):
                        ui.icon("event", size="18px").on("click", end_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            def submit():
                if not name_input.value or not name_input.value.strip():
                    ui.notify("Category name is required", color="negative")
                    return
                try:
                    budget_val = float(budget_input.value or 0)
                except (TypeError, ValueError):
                    ui.notify("Enter a valid budget", color="negative")
                    return
                try:
                    storage.add_category(
                        name_input.value, budget_val, start_input.value or None, end_input.value or None
                    )
                except Exception as e:
                    ui.notify(f"Could not add category: {e}", color="negative")
                    return
                name_input.value = ""
                budget_input.value = None
                start_input.value = None
                end_input.value = None
                ui.notify("Category added", color="positive")
                on_added()

            ui.button("Add category", icon="add", on_click=submit).props("unelevated no-caps").classes(
                "accent-btn w-full"
            ).style("margin-top: 4px; font-weight: 600;")


def render_add_expense_card(container: ui.column, on_added):
    container.clear()
    with container:
        section_label("Log a spend")
        with ui.column().classes("panel w-full").style("padding: 18px 20px; gap: 12px;"):
            cats = [c for c in storage.get_categories() if is_active_period(c)]
            if not cats:
                ui.label("No active category. Start a new period first.").style(f"color:{MUTED}; font-size: 13px;")
                return

            options = {c.id: f"{c.name} · {c.month_label}" for c in cats}
            category_select = ui.select(options, label="Category *", with_input=True).props(
                "outlined dense"
            ).classes("w-full")

            with ui.row().classes("w-full no-wrap").style("gap: 10px;"):
                amount_input = ui.number("Amount *", min=0, format="%.2f").props("outlined dense").classes("w-full")
                currency_select = ui.select(
                    {"EUR": "€ EUR", "INR": "₹ INR"}, value="EUR", label="Currency"
                ).props("outlined dense").style("width: 130px; flex: none;")

            note_input = ui.input("Note (optional)").props("outlined dense").classes("w-full")

            date_input = ui.input("Date", value=date.today().isoformat()).props("outlined dense readonly").classes("w-full")
            with date_input as di:
                with ui.menu().props("no-parent-event") as date_menu:
                    with ui.date().bind_value(date_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=date_menu.close).props("flat")
                with di.add_slot("append"):
                    ui.icon("event", size="18px").on("click", date_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            ui.label("Bill / receipt (optional)").style(f"font-size: 11.5px; color:{MUTED}; margin-top: 2px;")
            pending_bill: dict = {"path": None, "name": None}
            bill_preview = ui.row().classes("w-full items-center").style("gap: 8px; min-height: 0;")

            def on_upload(e):
                suffix = Path(e.name).suffix
                dest_name = f"{uuid.uuid4().hex}{suffix}"
                dest_path = BILLS_DIR / dest_name
                with dest_path.open("wb") as f:
                    shutil.copyfileobj(e.content, f)
                pending_bill["path"] = dest_name
                pending_bill["name"] = e.name
                bill_preview.clear()
                with bill_preview:
                    ui.icon("attach_file", size="16px").style(f"color:{ACCENT}")
                    ui.label(e.name).style(f"font-size: 12.5px; color:{INK};")
                    ui.button(icon="close", on_click=lambda: clear_pending_bill()).props(
                        "flat round dense size=sm"
                    ).style(f"color:{MUTED}")
                ui.notify("Bill attached", color="positive")

            def clear_pending_bill():
                pending_bill["path"] = None
                pending_bill["name"] = None
                bill_preview.clear()

            ui.upload(
                label="Upload bill image",
                on_upload=on_upload,
                auto_upload=True,
                max_files=1,
            ).props('accept="image/*,.pdf" outlined flat').classes("w-full")

            def submit():
                if not category_select.value:
                    ui.notify("Please select a category", color="negative")
                    return
                try:
                    amount_val = float(amount_input.value or 0)
                except (TypeError, ValueError):
                    amount_val = 0
                if amount_val <= 0:
                    ui.notify("Enter a valid amount", color="negative")
                    return
                storage.add_expense(
                    category_select.value,
                    amount_val,
                    note_input.value or "",
                    date_input.value or date.today().isoformat(),
                    pending_bill["path"],
                    currency_select.value or "EUR",
                )
                ui.notify("Expense saved", color="positive")
                amount_input.value = None
                note_input.value = ""
                clear_pending_bill()
                on_added()

            ui.button("Add expense", icon="add", on_click=submit).props("unelevated no-caps").classes(
                "accent-btn w-full"
            ).style("margin-top: 4px; font-weight: 600;")


def render_history(container: ui.column, on_change):
    container.clear()
    expenses = storage.get_expenses()
    with container:
        section_label("Recent spending")
        with ui.column().classes("panel w-full").style("padding: 4px 0;"):
            if not expenses:
                ui.label("No expenses logged yet.").style(f"color:{MUTED}; padding: 20px;")
            else:
                for i, e in enumerate(expenses[:50]):
                    if i > 0:
                        ui.element("div").classes("hairline").style("border-top: 1px solid; margin: 0 20px;")
                    with ui.row().classes("w-full items-center no-wrap").style("padding: 12px 20px; gap: 12px;"):
                        bill_path = e.bill_path
                        if bill_path:
                            suffix = Path(bill_path).suffix.lower()
                            url = f"/bills/{bill_path}"
                            if suffix == ".pdf":
                                with ui.link(target=url, new_tab=True).style("flex: none;"):
                                    ui.icon("picture_as_pdf", size="28px").style(f"color:{CRITICAL}")
                            else:
                                ui.image(url).style(
                                    "width:40px;height:40px;object-fit:cover;border-radius:6px;flex:none;cursor:pointer;"
                                    f"border:1px solid {BORDER}"
                                ).on("click", lambda u=url: ui.navigate.to(u, new_tab=True))
                        else:
                            with ui.element("div").style(
                                f"width:40px;height:40px;border-radius:6px;flex:none;background:{ACCENT_SOFT};"
                                "display:flex;align-items:center;justify-content:center;"
                            ):
                                ui.icon("receipt_long", size="18px").style(f"color:{ACCENT}")

                        with ui.column().style("gap: 1px; flex: 1; min-width: 0;"):
                            ui.label(e.category_name).style(
                                f"font-size: 13.5px; font-weight: 600; color:{INK};"
                            )
                            sub = e.spent_on
                            if e.note:
                                sub += f"  ·  {e.note}"
                            ui.label(sub).style(
                                f"font-size: 12px; color:{MUTED}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                            )

                        with ui.column().style("gap: 0; align-items: flex-end; flex: none;"):
                            ui.label(fmt_money(e.amount, e.currency)).classes("tabular").style(
                                f"font-size: 14px; font-weight: 600; color:{INK};"
                            )
                            if e.currency != "EUR":
                                ui.label(f"≈ {fmt_eur(e.amount_eur)}").classes("tabular").style(
                                    f"font-size: 11px; color:{MUTED};"
                                )
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda ev, eid=e.id: delete_expense_and_refresh(eid, on_change),
                        ).props("flat round dense size=sm").style(f"color:{MUTED}; flex:none;")


def delete_expense_and_refresh(expense_id: int, on_change):
    expense = storage.get_expense(expense_id)
    storage.delete_expense(expense_id)
    if expense and expense.bill_path:
        bill_file = BILLS_DIR / expense.bill_path
        if bill_file.exists():
            bill_file.unlink()
    ui.notify("Expense removed", color="positive")
    on_change()


def confirm_delete_category(cat, on_change):
    with ui.dialog() as dialog, ui.card().classes("panel").style("padding: 20px; gap: 4px;"):
        ui.label(f'Delete "{cat.name}"?').style(f"font-weight: 600; color:{INK};")
        ui.label("This also removes all logged expenses in this category.").style(
            f"font-size: 13px; color:{MUTED};"
        )
        with ui.row().classes("w-full justify-end").style("gap: 8px; margin-top: 12px;"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps").style(f"color:{MUTED}")

            def do_delete():
                storage.delete_category(cat.id)
                dialog.close()
                ui.notify("Category deleted", color="positive")
                on_change()

            ui.button("Delete", on_click=do_delete).props("unelevated no-caps").style(
                f"background:{CRITICAL}; color:white"
            )
    dialog.open()


def open_all_periods_dialog():
    """Every category ever created, current and past, grouped by name so
    the full history of a recurring category (e.g. all 'Food' months) is
    visible in one place — even though only the active period shows on
    the main dashboard."""
    cats = storage.get_categories()
    by_name: dict[str, list] = {}
    for c in cats:
        by_name.setdefault(c.name, []).append(c)
    for group in by_name.values():
        group.sort(key=lambda c: c.period_start or "", reverse=True)

    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 22px 24px; gap: 16px; min-width: 360px; max-width: 560px; max-height: 80vh; overflow-y: auto;"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("All periods").style(f"font-weight: 600; color:{INK}; font-size: 16px;")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense size=sm").style(f"color:{MUTED}")

        if not cats:
            ui.label("No categories yet.").style(f"color:{MUTED}; font-size: 13px;")
        else:
            for name, group in sorted(by_name.items()):
                with ui.column().style("gap: 6px; width: 100%;"):
                    ui.label(name).style(f"font-size: 12.5px; font-weight: 700; color:{ACCENT};")
                    for c in group:
                        spent = storage.get_total_spent(c.id)
                        active = is_active_period(c)
                        color = status_color((spent / c.budget * 100) if c.budget > 0 else 0)
                        with ui.row().classes("w-full items-center justify-between no-wrap").style(
                            f"padding: 8px 10px; border-radius: 6px; background: {ACCENT_SOFT if active else 'transparent'};"
                            f" border: 1px solid {BORDER};"
                        ):
                            with ui.column().style("gap: 0;"):
                                ui.label(c.month_label).style(f"font-size: 12.5px; color:{INK}; font-weight: 500;")
                                ui.label("Current" if active else "Past").style(
                                    f"font-size: 10.5px; color: {ACCENT if active else MUTED}; font-weight: 600;"
                                )
                            ui.label(f"{fmt_eur(spent)} / {fmt_eur(c.budget)}").classes("tabular").style(
                                f"font-size: 12.5px; color:{color}; font-weight: 600;"
                            )
    dialog.open()


def open_new_period_dialog(cat, on_change):
    """Quick-create the same category for its next billing period: start
    where the previous one ended, same length, same budget — editable
    before saving."""
    prev_start = parse_date(cat.period_start)
    prev_end = parse_date(cat.period_end)
    next_start = prev_end or date.today()
    if prev_start and prev_end:
        next_end = next_start + (prev_end - prev_start)
    else:
        next_end = None

    with ui.dialog() as dialog, ui.card().classes("panel").style("padding: 20px; gap: 12px; min-width:320px"):
        ui.label(f'New period for "{cat.name}"').style(f"font-weight: 600; color:{INK}; font-size: 15px;")
        budget_input = ui.number("Budget amount (€)", value=cat.budget, min=0, format="%.2f").props(
            "outlined dense"
        ).classes("w-full")

        with ui.row().classes("w-full no-wrap").style("gap: 10px;"):
            start_input = ui.input("Start date", value=next_start.isoformat()).props(
                "outlined dense readonly"
            ).classes("w-full")
            with start_input as si:
                with ui.menu().props("no-parent-event") as start_menu:
                    with ui.date().bind_value(start_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=start_menu.close).props("flat")
                with si.add_slot("append"):
                    ui.icon("event", size="18px").on("click", start_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            end_input = ui.input("End date", value=next_end.isoformat() if next_end else None).props(
                "outlined dense readonly"
            ).classes("w-full")
            with end_input as ei:
                with ui.menu().props("no-parent-event") as end_menu:
                    with ui.date().bind_value(end_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=end_menu.close).props("flat")
                with ei.add_slot("append"):
                    ui.icon("event", size="18px").on("click", end_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

        with ui.row().classes("w-full justify-end").style("gap: 8px; margin-top: 4px;"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps").style(f"color:{MUTED}")

            def create():
                storage.add_category(
                    cat.name,
                    float(budget_input.value or 0),
                    start_input.value or None,
                    end_input.value or None,
                )
                dialog.close()
                ui.notify(f'New "{cat.name}" period created', color="positive")
                on_change()

            ui.button("Create period", on_click=create).props("unelevated no-caps").classes("accent-btn")
    dialog.open()


def open_edit_dialog(cat, on_change):
    with ui.dialog() as dialog, ui.card().classes("panel").style("padding: 20px; gap: 12px; min-width:320px"):
        ui.label("Edit category").style(f"font-weight: 600; color:{INK}; font-size: 15px;")
        name_input = ui.input("Category name", value=cat.name).props("outlined dense").classes("w-full")
        budget_input = ui.number("Budget amount", value=cat.budget, min=0, format="%.2f").props(
            "outlined dense"
        ).classes("w-full")

        with ui.row().classes("w-full no-wrap").style("gap: 10px;"):
            start_input = ui.input("Start date", value=cat.period_start).props("outlined dense readonly").classes("w-full")
            with start_input as si:
                with ui.menu().props("no-parent-event") as start_menu:
                    with ui.date().bind_value(start_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=start_menu.close).props("flat")
                with si.add_slot("append"):
                    ui.icon("event", size="18px").on("click", start_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            end_input = ui.input("End date", value=cat.period_end).props("outlined dense readonly").classes("w-full")
            with end_input as ei:
                with ui.menu().props("no-parent-event") as end_menu:
                    with ui.date().bind_value(end_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=end_menu.close).props("flat")
                with ei.add_slot("append"):
                    ui.icon("event", size="18px").on("click", end_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

        with ui.row().classes("w-full justify-end").style("gap: 8px; margin-top: 4px;"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps").style(f"color:{MUTED}")

            def save():
                if not name_input.value or not name_input.value.strip():
                    ui.notify("Name required", color="negative")
                    return
                storage.update_category(
                    cat.id,
                    name_input.value,
                    float(budget_input.value or 0),
                    start_input.value or None,
                    end_input.value or None,
                )
                dialog.close()
                ui.notify("Category updated", color="positive")
                on_change()

            ui.button("Save", on_click=save).props("unelevated no-caps").classes("accent-btn")
    dialog.open()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Nikhil and Megha Ledger", favicon="📒", port=9000, reload=False)
