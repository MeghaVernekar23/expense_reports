"""Spending page: every expense across every category/period, filterable
by category and currency."""
from nicegui import ui

import storage
from components import render_expense_list
from export_service import download_everything
from shell import page_footer, page_header, page_shell
from theme import ACCENT, INK, MUTED
from utils import fmt_eur


@ui.page("/spending")
def spending_page():
    content = page_shell("/spending")
    with content:
        with ui.column().classes("w-full").style("max-width: 900px; gap: 20px;"):
            def header_actions():
                ui.button("Download all", icon="download", on_click=download_everything).props(
                    "flat no-caps dense"
                ).style(f"color:{ACCENT}; font-size: 12.5px;")

            page_header("Spending", "Every expense, every category, every period", header_actions)

            all_cats = storage.get_categories()
            cat_options = {"": "All categories"} | {c.id: f"{c.name} · {c.month_label}" for c in all_cats}

            with ui.row().classes("w-full").style("gap: 10px; margin-bottom: 4px; flex-wrap: wrap;"):
                category_filter = ui.select(cat_options, value="", label="Filter by category").props(
                    "outlined dense"
                ).style("flex: 1 1 180px; min-width: 0;")
                currency_filter = ui.select(
                    {"": "All currencies", "EUR": "€ EUR", "INR": "₹ INR"}, value="", label="Currency"
                ).props("outlined dense").style("flex: 1 1 140px; min-width: 0;")

            list_container = ui.column().classes("w-full")

            def refresh():
                list_container.clear()
                expenses = storage.get_expenses(category_filter.value or None)
                if currency_filter.value:
                    expenses = [e for e in expenses if e.currency == currency_filter.value]
                total_eur = sum(e.amount_eur for e in expenses)
                with list_container:
                    with ui.row().classes("w-full items-baseline justify-between").style("margin-bottom: 4px;"):
                        ui.label(f"{len(expenses)} expense{'s' if len(expenses) != 1 else ''}").style(
                            f"font-size: 12.5px; color:{MUTED};"
                        )
                        ui.label(f"Total: {fmt_eur(total_eur)}").classes("tabular").style(
                            f"font-size: 13px; font-weight: 600; color:{INK};"
                        )
                    render_expense_list(expenses, refresh, empty_message="No expenses match this filter.")

            category_filter.on_value_change(refresh)
            currency_filter.on_value_change(refresh)
            refresh()
    page_footer()
