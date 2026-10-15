"""Add category page: name (dropdown of common categories, or free text via
"Others"), budget, optional billing period, active switch."""
from datetime import date

from nicegui import ui

import fx
import storage
from shell import page_footer, page_header, page_shell
from theme import CATEGORY_NAME_OPTIONS, MUTED


@ui.page("/add-category")
def add_category_page():
    content = page_shell("/add-category")
    with content:
        with ui.column().classes("w-full").style("max-width: 520px; gap: 24px;"):
            page_header("Add category", "Set a budget and, optionally, a billing period")

            with ui.column().classes("panel w-full").style("padding: 22px 24px; gap: 14px;"):
                name_select = ui.select(
                    CATEGORY_NAME_OPTIONS, label="Category name", value=CATEGORY_NAME_OPTIONS[0]
                ).props("outlined dense").classes("w-full")
                other_name_input = ui.input("Custom category name").props("outlined dense").classes("w-full")
                other_name_input.bind_visibility_from(name_select, "value", value="Others")

                with ui.row().classes("w-full").style("gap: 10px;"):
                    budget_input = ui.number("Budget amount", min=0, format="%.2f").props(
                        "outlined dense"
                    ).style("flex: 1 1 auto;")
                    currency_select = ui.select(["EUR", "INR"], value="EUR").props(
                        "outlined dense"
                    ).style("width: 100px;")

                ui.label("Period (optional)").style(f"font-size: 11.5px; color:{MUTED}; margin-top: 2px;")
                with ui.row().classes("w-full").style("gap: 10px; flex-wrap: wrap;"):
                    start_input = ui.input("Start date").props("outlined dense readonly").style(
                        "flex: 1 1 140px; min-width: 0;"
                    )
                    with start_input as si:
                        with ui.menu().props("no-parent-event") as start_menu:
                            with ui.date().bind_value(start_input):
                                with ui.row().classes("justify-end w-full"):
                                    ui.button("Close", on_click=start_menu.close).props("flat")
                        with si.add_slot("append"):
                            ui.icon("event", size="18px").on("click", start_menu.open).classes(
                                "cursor-pointer"
                            ).style(f"color:{MUTED}")

                    end_input = ui.input("End date").props("outlined dense readonly").style(
                        "flex: 1 1 140px; min-width: 0;"
                    )
                    with end_input as ei:
                        with ui.menu().props("no-parent-event") as end_menu:
                            with ui.date().bind_value(end_input):
                                with ui.row().classes("justify-end w-full"):
                                    ui.button("Close", on_click=end_menu.close).props("flat")
                        with ei.add_slot("append"):
                            ui.icon("event", size="18px").on("click", end_menu.open).classes(
                                "cursor-pointer"
                            ).style(f"color:{MUTED}")

                active_switch = ui.switch("Active immediately", value=True).props("dense color=primary").style(
                    "margin-top: 4px;"
                )

                def submit():
                    chosen_name = (
                        other_name_input.value if name_select.value == "Others" else name_select.value
                    )
                    if not chosen_name or not chosen_name.strip():
                        ui.notify("Category name is required", color="negative")
                        return
                    try:
                        budget_val = float(budget_input.value or 0)
                    except (TypeError, ValueError):
                        ui.notify("Enter a valid budget", color="negative")
                        return
                    budget_eur, _ = fx.convert_to_eur(
                        budget_val, currency_select.value, date.today().isoformat()
                    )
                    storage.add_category(
                        chosen_name,
                        budget_eur,
                        start_input.value or None,
                        end_input.value or None,
                        active_switch.value,
                        currency_select.value,
                        budget_val,
                    )
                    name_select.value = CATEGORY_NAME_OPTIONS[0]
                    other_name_input.value = ""
                    budget_input.value = None
                    currency_select.value = "EUR"
                    start_input.value = None
                    end_input.value = None
                    active_switch.value = True
                    ui.notify("Category added", color="positive")

                ui.button("Add category", icon="add", on_click=submit).props("unelevated no-caps").classes(
                    "accent-btn w-full"
                ).style("margin-top: 4px; font-weight: 600;")
    page_footer()
