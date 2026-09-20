"""Past categories page: deactivated periods, grouped by the calendar month
each period starts in, each card with its own download/reactivate/delete."""
from datetime import datetime

from nicegui import ui

import storage
from components import confirm_delete_category, open_category_expenses_dialog, toggle_active_and_refresh
from export_service import download_category
from shell import page_footer, page_header, page_shell, section_label
from theme import ACCENT, CRITICAL, INK, MUTED
from utils import fmt_eur, is_active_period, parse_date, status_color


@ui.page("/past-categories")
def past_categories_page():
    content = page_shell("/past-categories")
    with content:
        with ui.column().classes("w-full").style("max-width: 980px; gap: 24px;"):
            page_header("Past categories", "Deactivated periods — no longer shown on the dashboard")

            list_container = ui.column().classes("w-full")

            def refresh():
                list_container.clear()
                past_cats = [c for c in storage.get_categories() if not is_active_period(c)]
                with list_container:
                    if not past_cats:
                        with ui.column().classes("panel w-full items-center").style("padding: 40px 20px; gap: 6px;"):
                            ui.icon("inventory_2", size="28px").style(f"color:{MUTED}")
                            ui.label("No past categories yet").style(f"color:{INK}; font-weight: 600;")
                            ui.label("Deactivate a category from the dashboard to move it here.").style(
                                f"color:{MUTED}; font-size: 13px;"
                            )
                        return

                    # Group by the calendar month each period *starts* in, so a
                    # Sep-Oct card files under September rather than October.
                    months: dict[str, list] = {}
                    for cat in past_cats:
                        start = parse_date(cat.period_start)
                        key = start.strftime("%Y-%m") if start else "No date"
                        months.setdefault(key, []).append(cat)

                    def month_sort_key(k: str):
                        return k if k != "No date" else ""

                    for key in sorted(months.keys(), key=month_sort_key, reverse=True):
                        group = months[key]
                        label = (
                            datetime.strptime(key, "%Y-%m").strftime("%B %Y") if key != "No date" else "No start date"
                        )
                        with ui.column().classes("w-full").style("gap: 10px;"):
                            section_label(label)
                            with ui.grid(columns="repeat(auto-fit, minmax(280px, 1fr))").classes("w-full").style(
                                "gap: 12px;"
                            ):
                                for cat in group:
                                    spent = storage.get_total_spent(cat.id)
                                    budget = cat.budget or 0
                                    pct_used = (spent / budget * 100) if budget > 0 else 0
                                    color = status_color(pct_used)

                                    with ui.column().classes("stripe-card inactive").style(
                                        f"border-left-color: {color}; padding: 16px 18px; gap: 10px;"
                                    ):
                                        with ui.row().classes("w-full items-center justify-between no-wrap").style(
                                            "gap: 8px;"
                                        ):
                                            with ui.column().style("gap: 1px; min-width: 0; cursor: pointer;").on(
                                                "click", lambda c=cat: open_category_expenses_dialog(c, refresh)
                                            ):
                                                ui.label(cat.name).style(
                                                    f"font-weight: 600; font-size: 15px; color: {INK};"
                                                )
                                                ui.label(cat.month_label).style(f"font-size: 11px; color:{MUTED};")

                                            with ui.row().style("gap: 2px; flex: none;"):
                                                ui.button(
                                                    icon="download",
                                                    on_click=lambda c=cat: download_category(c),
                                                ).props("flat round dense size=sm").style(f"color:{ACCENT}").tooltip(
                                                    "Download this category"
                                                )
                                                ui.button(
                                                    icon="toggle_on",
                                                    on_click=lambda c=cat: toggle_active_and_refresh(c, True, refresh),
                                                ).props("flat round dense size=sm").style(f"color:{MUTED}").tooltip(
                                                    "Reactivate"
                                                )
                                                ui.button(
                                                    icon="delete_outline",
                                                    on_click=lambda c=cat: confirm_delete_category(c, refresh),
                                                ).props("flat round dense size=sm").style(f"color:{CRITICAL}").tooltip(
                                                    "Delete"
                                                )

                                        ui.label(f"{fmt_eur(spent)} of {fmt_eur(budget)}").classes("tabular").style(
                                            f"font-size: 13px; color: {MUTED};"
                                        )
                                        ui.label(f"{pct_used:.0f}% utilised").classes("tabular").style(
                                            f"font-size: 12.5px; font-weight: 600; color: {color};"
                                        )

            refresh()
    page_footer()
