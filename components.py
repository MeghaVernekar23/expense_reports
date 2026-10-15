"""Reusable UI pieces shared across pages: expense rows/lists, stat cells,
bar chart helper, category action handlers, dialogs, and the log-a-spend
form (used standalone on its own page and inline in dashboard quick-log)."""
import shutil
import uuid
from datetime import date
from pathlib import Path

from nicegui import ui

import fx
import storage
from export_service import BILLS_DIR
from theme import ACCENT, ACCENT_SOFT, BORDER, CRITICAL, INK, MUTED
from utils import fmt_eur, fmt_money, is_active_period, parse_date, status_color


# ---------------------------------------------------------------- expense rows/lists ----

def render_expense_row(e, on_change, show_category: bool = True):
    """One expense line: bill thumbnail, category+note+date, amount, delete.
    Shared by the dashboard recent-list, the Spending page, and the
    per-category dialog."""
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
            if show_category:
                ui.label(e.category_name).style(f"font-size: 13.5px; font-weight: 600; color:{INK};")
            sub = e.spent_on
            if e.note:
                sub += f"  ·  {e.note}"
            ui.label(sub).style(
                f"font-size: {'12px' if show_category else '13px'}; color:{MUTED if show_category else INK};"
                " white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                f"{'font-weight: 500;' if not show_category else ''}"
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


def render_expense_list(expenses, on_change, empty_message: str = "No expenses logged yet.", show_category: bool = True):
    """Panel wrapping a list of expense rows, or an empty-state message."""
    with ui.column().classes("panel w-full").style("padding: 4px 0;"):
        if not expenses:
            ui.label(empty_message).style(f"color:{MUTED}; padding: 20px;")
        else:
            for i, e in enumerate(expenses):
                if i > 0:
                    ui.element("div").classes("hairline").style("border-top: 1px solid; margin: 0 20px;")
                render_expense_row(e, on_change, show_category=show_category)


# ---------------------------------------------------------------- stat cells ----

def stat(label: str, value: str, color: str):
    with ui.column().classes("stat-cell").style("gap: 4px;"):
        ui.label(label).classes("eyebrow")
        ui.label(value).classes("display tabular").style(
            f"font-size: 24px; font-weight: 600; color: {color}; overflow-wrap: anywhere;"
        )


def stat_sm(label: str, value: str, color: str):
    with ui.column().classes("stat-cell").style("gap: 2px;"):
        ui.label(label).classes("eyebrow")
        ui.label(value).classes("tabular").style(
            f"font-size: 16px; font-weight: 600; color: {color}; overflow-wrap: anywhere;"
        )


# ---------------------------------------------------------------- charts ----

def echart_bar(labels: list[str], values: list[float], color: str = ACCENT, height: str = "260px"):
    return ui.echart(
        {
            "grid": {"left": 50, "right": 16, "top": 20, "bottom": 32},
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLine": {"lineStyle": {"color": BORDER}},
                "axisLabel": {"color": MUTED, "fontSize": 11},
            },
            "yAxis": {
                "type": "value",
                "axisLine": {"show": False},
                "splitLine": {"lineStyle": {"color": BORDER, "type": "dashed"}},
                "axisLabel": {"color": MUTED, "fontSize": 11, "formatter": "€{value}"},
            },
            "tooltip": {"trigger": "axis", "valueFormatter": "value => '€' + value.toFixed(2)"},
            "series": [
                {
                    "type": "bar",
                    "data": values,
                    "itemStyle": {"color": color, "borderRadius": [4, 4, 0, 0]},
                    "barMaxWidth": 36,
                }
            ],
        }
    ).style(f"width: 100%; height: {height};")


# ---------------------------------------------------------------- category/expense actions ----

def toggle_active_and_refresh(cat, active: bool, on_change):
    storage.set_category_active(cat.id, active)
    ui.notify(f'"{cat.name}" {"activated" if active else "deactivated"}', color="positive")
    on_change()


def delete_expense_and_refresh(expense_id: int, on_change):
    expense = storage.get_expense(expense_id)
    storage.delete_expense(expense_id)
    if expense and expense.bill_path:
        bill_file = BILLS_DIR / expense.bill_path
        if bill_file.exists():
            bill_file.unlink()
    ui.notify("Expense removed", color="positive")
    on_change()


# ---------------------------------------------------------------- dialogs ----

def open_category_expenses_dialog(cat, on_change):
    """Clicking a category card shows just that category's spending,
    without leaving the dashboard."""
    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 20px 0; gap: 0; width: min(380px, 92vw); max-width: 560px; max-height: 80vh; overflow-y: auto;"
    ):
        with ui.row().classes("w-full items-center justify-between").style("padding: 0 20px 12px;"):
            with ui.column().style("gap: 1px;"):
                ui.label(cat.name).style(f"font-weight: 600; color:{INK}; font-size: 15px;")
                ui.label(cat.month_label).style(f"font-size: 11.5px; color:{MUTED};")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense size=sm").style(f"color:{MUTED}")

        def on_row_change():
            dialog.close()
            on_change()

        expenses = storage.get_expenses(cat.id)
        render_expense_list(
            expenses, on_row_change, empty_message="No spending logged in this category yet.", show_category=False
        )
    dialog.open()


def open_quick_log_dialog(cat, on_change):
    """Log a spend straight from a category card, with that category
    pre-filled — no need to leave the dashboard or re-pick it."""
    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 20px 20px 4px; gap: 0; width: min(340px, 92vw); max-width: 460px;"
    ):
        with ui.row().classes("w-full items-center justify-between").style("margin-bottom: 8px;"):
            ui.label(f'Log a spend · {cat.name}').style(f"font-weight: 600; color:{INK}; font-size: 15px;")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense size=sm").style(f"color:{MUTED}")

        form_container = ui.column().classes("w-full")

        def on_saved():
            dialog.close()
            on_change()

        render_log_spend_form(form_container, preselect_category_id=cat.id, on_saved=on_saved)
    dialog.open()


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
    """Every category ever created, active and inactive, grouped by name so
    the full history of a recurring category (e.g. all 'Food' months) is
    visible in one place — even though only active categories show on
    the main dashboard. Each row can be toggled on/off directly here."""
    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 22px 24px; gap: 16px; width: min(380px, 92vw); max-width: 580px; max-height: 80vh; overflow-y: auto;"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("All periods").style(f"font-weight: 600; color:{INK}; font-size: 16px;")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense size=sm").style(f"color:{MUTED}")

        list_container = ui.column().style("gap: 16px; width: 100%;")

        def render_list():
            list_container.clear()
            fresh_cats = storage.get_categories()
            groups: dict[str, list] = {}
            for c in fresh_cats:
                groups.setdefault(c.name, []).append(c)
            for group in groups.values():
                group.sort(key=lambda c: c.period_start or "", reverse=True)

            with list_container:
                if not fresh_cats:
                    ui.label("No categories yet.").style(f"color:{MUTED}; font-size: 13px;")
                    return
                for name, group in sorted(groups.items()):
                    with ui.column().style("gap: 6px; width: 100%;"):
                        ui.label(name).style(f"font-size: 12.5px; font-weight: 700; color:{ACCENT};")
                        for c in group:
                            spent = storage.get_total_spent(c.id)
                            active = is_active_period(c)
                            color = status_color((spent / c.budget * 100) if c.budget > 0 else 0)
                            with ui.row().classes("w-full items-center justify-between no-wrap").style(
                                f"padding: 8px 10px; border-radius: 6px;"
                                f" background: {ACCENT_SOFT if active else 'transparent'};"
                                f" border: 1px solid {BORDER};"
                            ):
                                with ui.column().style("gap: 0;"):
                                    ui.label(c.month_label).style(
                                        f"font-size: 12.5px; color:{INK}; font-weight: 500;"
                                    )
                                    ui.label("Active" if active else "Inactive").style(
                                        f"font-size: 10.5px; color: {ACCENT if active else MUTED}; font-weight: 600;"
                                    )
                                with ui.row().classes("items-center").style("gap: 10px;"):
                                    ui.label(f"{fmt_eur(spent)} / {fmt_eur(c.budget)}").classes("tabular").style(
                                        f"font-size: 12.5px; color:{color}; font-weight: 600;"
                                    )
                                    ui.switch(
                                        value=active,
                                        on_change=lambda e, cid=c.id: (
                                            storage.set_category_active(cid, e.value),
                                            render_list(),
                                        ),
                                    ).props("dense color=primary")

        render_list()
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

    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 20px; gap: 12px; width: min(320px, 92vw);"
    ):
        ui.label(f'New period for "{cat.name}"').style(f"font-weight: 600; color:{INK}; font-size: 15px;")
        with ui.row().classes("w-full").style("gap: 10px;"):
            budget_input = ui.number("Budget amount", value=cat.budget, min=0, format="%.2f").props(
                "outlined dense"
            ).style("flex: 1 1 auto;")
            currency_select = ui.select(["EUR", "INR"], value="EUR").props("outlined dense").style("width: 100px;")

        with ui.row().classes("w-full").style("gap: 10px; flex-wrap: wrap;"):
            start_input = ui.input("Start date", value=next_start.isoformat()).props(
                "outlined dense readonly"
            ).style("flex: 1 1 120px; min-width: 0;")
            with start_input as si:
                with ui.menu().props("no-parent-event") as start_menu:
                    with ui.date().bind_value(start_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=start_menu.close).props("flat")
                with si.add_slot("append"):
                    ui.icon("event", size="18px").on("click", start_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            end_input = ui.input("End date", value=next_end.isoformat() if next_end else None).props(
                "outlined dense readonly"
            ).style("flex: 1 1 120px; min-width: 0;")
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
                budget_eur, _ = fx.convert_to_eur(
                    float(budget_input.value or 0), currency_select.value, date.today().isoformat()
                )
                storage.add_category(
                    cat.name,
                    budget_eur,
                    start_input.value or None,
                    end_input.value or None,
                )
                dialog.close()
                ui.notify(f'New "{cat.name}" period created', color="positive")
                on_change()

            ui.button("Create period", on_click=create).props("unelevated no-caps").classes("accent-btn")
    dialog.open()


def open_edit_dialog(cat, on_change):
    with ui.dialog() as dialog, ui.card().classes("panel").style(
        "padding: 20px; gap: 12px; width: min(320px, 92vw);"
    ):
        ui.label("Edit category").style(f"font-weight: 600; color:{INK}; font-size: 15px;")
        name_input = ui.input("Category name", value=cat.name).props("outlined dense").classes("w-full")
        with ui.row().classes("w-full").style("gap: 10px;"):
            budget_input = ui.number("Budget amount", value=cat.budget, min=0, format="%.2f").props(
                "outlined dense"
            ).style("flex: 1 1 auto;")
            currency_select = ui.select(["EUR", "INR"], value="EUR").props("outlined dense").style("width: 100px;")

        with ui.row().classes("w-full").style("gap: 10px; flex-wrap: wrap;"):
            start_input = ui.input("Start date", value=cat.period_start).props("outlined dense readonly").style(
                "flex: 1 1 120px; min-width: 0;"
            )
            with start_input as si:
                with ui.menu().props("no-parent-event") as start_menu:
                    with ui.date().bind_value(start_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=start_menu.close).props("flat")
                with si.add_slot("append"):
                    ui.icon("event", size="18px").on("click", start_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

            end_input = ui.input("End date", value=cat.period_end).props("outlined dense readonly").style(
                "flex: 1 1 120px; min-width: 0;"
            )
            with end_input as ei:
                with ui.menu().props("no-parent-event") as end_menu:
                    with ui.date().bind_value(end_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=end_menu.close).props("flat")
                with ei.add_slot("append"):
                    ui.icon("event", size="18px").on("click", end_menu.open).classes("cursor-pointer").style(f"color:{MUTED}")

        with ui.row().classes("items-center").style("gap: 8px; margin-top: 2px;"):
            active_switch = ui.switch("Active", value=cat.is_active).props("dense color=primary")

        with ui.row().classes("w-full justify-end").style("gap: 8px; margin-top: 4px;"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps").style(f"color:{MUTED}")

            def save():
                if not name_input.value or not name_input.value.strip():
                    ui.notify("Name required", color="negative")
                    return
                budget_eur, _ = fx.convert_to_eur(
                    float(budget_input.value or 0), currency_select.value, date.today().isoformat()
                )
                storage.update_category(
                    cat.id,
                    name_input.value,
                    budget_eur,
                    start_input.value or None,
                    end_input.value or None,
                    active_switch.value,
                )
                dialog.close()
                ui.notify("Category updated", color="positive")
                on_change()

            ui.button("Save", on_click=save).props("unelevated no-caps").classes("accent-btn")
    dialog.open()


# ---------------------------------------------------------------- log-a-spend form ----

def render_log_spend_form(container: ui.column, preselect_category_id: int | None = None, on_saved=None):
    """Shared by the standalone Log a spend page and the dashboard's
    per-category quick-log dialog."""
    container.clear()
    with container:
        with ui.column().classes("panel w-full").style("padding: 22px 24px; gap: 14px;"):
            cats = [c for c in storage.get_categories() if is_active_period(c)]
            if not cats:
                ui.icon("event_busy", size="26px").style(f"color:{MUTED}")
                ui.label("No active category").style(f"color:{INK}; font-weight: 600;")
                ui.label("Add one, or reactivate an existing category, before logging a spend.").style(
                    f"color:{MUTED}; font-size: 13px;"
                )
                ui.link("Add a category", "/add-category").style(f"color:{ACCENT}; font-size: 13px;")
                return

            options = {c.id: f"{c.name} · {c.month_label}" for c in cats}
            default_category = preselect_category_id if preselect_category_id in options else None
            category_select = ui.select(options, label="Category *", value=default_category, with_input=True).props(
                "outlined dense"
            ).classes("w-full")

            with ui.row().classes("w-full").style("gap: 10px; flex-wrap: wrap;"):
                amount_input = ui.number("Amount *", min=0, format="%.2f").props("outlined dense").style(
                    "flex: 1 1 140px; min-width: 0;"
                )
                currency_select = ui.select(
                    {"EUR": "€ EUR", "INR": "₹ INR"}, value="EUR", label="Currency"
                ).props("outlined dense").style("flex: 0 1 130px; min-width: 100px;")

            note_input = ui.input("Note (optional)").props("outlined dense").classes("w-full")

            date_input = ui.input("Date", value=date.today().isoformat()).props(
                "outlined dense readonly"
            ).classes("w-full")
            with date_input as di:
                with ui.menu().props("no-parent-event") as date_menu:
                    with ui.date().bind_value(date_input):
                        with ui.row().classes("justify-end w-full"):
                            ui.button("Close", on_click=date_menu.close).props("flat")
                with di.add_slot("append"):
                    ui.icon("event", size="18px").on("click", date_menu.open).classes("cursor-pointer").style(
                        f"color:{MUTED}"
                    )

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
                if on_saved:
                    on_saved()

            ui.button("Add expense", icon="add", on_click=submit).props("unelevated no-caps").classes(
                "accent-btn w-full"
            ).style("margin-top: 4px; font-weight: 600;")
