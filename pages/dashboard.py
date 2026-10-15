"""Dashboard page: active-category totals, charts, category cards, recent
spending — the app's landing page."""
from datetime import date

from nicegui import ui

import fx
import storage
from components import (
    confirm_delete_category,
    open_all_periods_dialog,
    open_category_expenses_dialog,
    open_edit_dialog,
    open_new_period_dialog,
    open_quick_log_dialog,
    render_expense_list,
    stat,
    stat_sm,
    toggle_active_and_refresh,
)
from export_service import download_everything
from shell import page_footer, page_header, page_shell, section_label
from theme import ACCENT, ACCENT_SOFT, BORDER, CRITICAL, GOOD, INK, MUTED, SURFACE, WARN
from utils import days_remaining, fmt_eur, fmt_money, is_active_period, monthly_daily_totals, pace_status, status_color


@ui.page("/")
def dashboard_page():
    content = page_shell("/")
    with content:
        with ui.column().classes("w-full").style("max-width: 980px; gap: 24px;"):
            def header_actions():
                ui.button("All periods", icon="history", on_click=open_all_periods_dialog).props(
                    "flat no-caps dense"
                ).style(f"color:{MUTED}; font-size: 12.5px;")
                ui.button("Download all", icon="download", on_click=download_everything).props(
                    "flat no-caps dense"
                ).style(f"color:{ACCENT}; font-size: 12.5px;")

            page_header("Dashboard", "Active categories & overall totals", header_actions)

            totals_container = ui.column().classes("w-full").style("gap: 10px;")
            charts_container = ui.column().classes("w-full").style("gap: 14px; margin-top: 24px;")
            summary_container = ui.column().classes("w-full").style("gap: 14px; margin-top: 24px;")
            history_container = ui.column().classes("w-full").style("gap: 10px; margin-top: 24px;")

            def refresh_all():
                render_totals(totals_container)
                render_dashboard_charts(charts_container)
                render_summary(summary_container, refresh_all)
                render_history(history_container, refresh_all)

            refresh_all()
    page_footer()


def render_dashboard_charts(container: ui.column):
    container.clear()
    active_cats = [c for c in storage.get_categories() if is_active_period(c)]
    if not active_cats:
        return

    donut_data = [
        {"name": c.name, "value": round(storage.get_total_spent(c.id), 2)}
        for c in active_cats
        if storage.get_total_spent(c.id) > 0
    ]

    active_expenses = [e for c in active_cats for e in storage.get_expenses(c.id)]
    daily = monthly_daily_totals(active_expenses)

    with container:
        section_label("Active period at a glance")
        with ui.row().classes("w-full items-start").style("gap: 14px; flex-wrap: wrap;"):
            with ui.column().classes("panel").style("flex: 1 1 280px; min-width: 260px; padding: 16px;"):
                ui.label("Spend by category").style(f"font-size: 12.5px; font-weight: 600; color:{INK};")
                if donut_data:
                    ui.echart(
                        {
                            "tooltip": {"trigger": "item", "valueFormatter": "value => '€' + value.toFixed(2)"},
                            "legend": {
                                "orient": "vertical",
                                "right": 4,
                                "top": "middle",
                                "textStyle": {"color": MUTED, "fontSize": 11},
                            },
                            "series": [
                                {
                                    "type": "pie",
                                    "radius": ["45%", "72%"],
                                    "center": ["38%", "50%"],
                                    "data": donut_data,
                                    "label": {"show": False},
                                    "itemStyle": {"borderColor": SURFACE, "borderWidth": 2},
                                }
                            ],
                            "color": [ACCENT, GOOD, WARN, CRITICAL, "#8AA9C9", "#C9A26A"],
                        }
                    ).style("width: 100%; height: 220px;")
                else:
                    ui.label("No spend logged in the active period yet.").style(
                        f"color:{MUTED}; font-size: 12.5px; padding: 40px 0;"
                    )

            with ui.column().classes("panel").style("flex: 1.4 1 320px; min-width: 280px; padding: 16px;"):
                ui.label("Spend over time").style(f"font-size: 12.5px; font-weight: 600; color:{INK};")
                if daily:
                    labels = [d.strftime("%d %b") for d, _ in daily]
                    values = [round(v, 2) for _, v in daily]
                    ui.echart(
                        {
                            "grid": {"left": 46, "right": 12, "top": 20, "bottom": 30},
                            "xAxis": {
                                "type": "category",
                                "data": labels,
                                "axisLabel": {"color": MUTED, "fontSize": 10},
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
                                    "type": "line",
                                    "data": values,
                                    "smooth": True,
                                    "areaStyle": {"color": ACCENT_SOFT},
                                    "itemStyle": {"color": ACCENT},
                                    "showSymbol": len(values) <= 20,
                                }
                            ],
                        }
                    ).style("width: 100%; height: 220px;")
                else:
                    ui.label("No spend logged in the active period yet.").style(
                        f"color:{MUTED}; font-size: 12.5px; padding: 40px 0;"
                    )


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
        # Active categories — what's switched on right now
        cur_budget, cur_spent, cur_remaining, cur_pct = totals_for(active_cats)
        ui.label("Active categories").classes("eyebrow").style("padding-left: 2px;")
        with ui.element("div").classes("panel stat-grid w-full").style("padding: 20px 24px;"):
            stat("Total budget", fmt_eur(cur_budget), INK)
            stat("Spent", fmt_eur(cur_spent), status_color(cur_pct))
            stat(
                "Remaining" if cur_remaining >= 0 else "Over budget",
                fmt_eur(abs(cur_remaining)),
                GOOD if cur_remaining >= 0 else CRITICAL,
            )
            stat("Utilised", f"{cur_pct:.0f}%", status_color(cur_pct))

        # All-time — every category, active or not, ever
        all_budget, all_spent, all_remaining, all_pct = totals_for(all_cats)
        ui.label("All-time overall").classes("eyebrow").style("padding-left: 2px; margin-top: 4px;")
        with ui.element("div").classes("panel stat-grid w-full").style(
            "padding: 14px 24px; background: var(--accent-soft);"
        ):
            stat_sm("Total spent", fmt_eur(all_spent), INK)
            stat_sm("Total budgeted", fmt_eur(all_budget), INK)
            stat_sm("Budget utilised", f"{all_pct:.0f}%", status_color(all_pct))
            stat_sm(
                "Remaining" if all_remaining >= 0 else "Over budget",
                fmt_eur(abs(all_remaining)),
                GOOD if all_remaining >= 0 else CRITICAL,
            )


def render_summary(container: ui.column, refresh_all):
    container.clear()
    all_cats = storage.get_categories()
    cats = [c for c in all_cats if is_active_period(c)]
    with container:
        if not all_cats:
            with ui.column().classes("panel w-full items-center").style("padding: 40px 20px; gap: 6px;"):
                ui.icon("inbox", size="28px").style(f"color:{MUTED}")
                ui.label("No categories yet").style(f"color:{INK}; font-weight: 600;")
                ui.label("Add one from the sidebar to start tracking spend.").style(
                    f"color:{MUTED}; font-size: 13px;"
                )
            return

        if not cats:
            with ui.column().classes("panel w-full items-center").style("padding: 32px 20px; gap: 6px;"):
                ui.icon("event_busy", size="26px").style(f"color:{MUTED}")
                ui.label("No active categories right now").style(f"color:{INK}; font-weight: 600;")
                ui.label("Reactivate one from All periods, or add a new one.").style(
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
                    f"border-left-color: {color}; padding: 16px 18px; gap: 10px; cursor: pointer;"
                ).on("click", lambda c=cat: open_category_expenses_dialog(c, refresh_all)):
                    with ui.row().classes("w-full items-center justify-between no-wrap").style("gap: 8px;"):
                        with ui.column().style("gap: 1px; min-width: 0;"):
                            ui.label(cat.name).style(f"font-weight: 600; font-size: 15px; color: {INK};")
                            ui.label(cat.month_label).style(f"font-size: 11px; color:{MUTED};")

                        with ui.row().style("gap: 2px; flex: none;"):
                            # Log a spend is the primary quick action, so it gets
                            # its own always-visible button (pre-filled with this
                            # category) rather than living inside the ⋮ menu.
                            ui.button(icon="add_card").props("flat round dense size=sm").style(
                                f"color:{ACCENT}"
                            ).tooltip("Log a spend").on(
                                "click.stop", lambda c=cat: open_quick_log_dialog(c, refresh_all)
                            )

                            # A single menu button for the remaining, less-frequent
                            # actions — putting them behind one click target (rather
                            # than loose icons inside the card's own click area)
                            # avoids fighting the card's "open expenses" handler.
                            with ui.button(icon="more_vert").props("flat round dense size=sm").style(
                                f"color:{MUTED}; flex: none;"
                            ).on("click.stop", lambda: None):
                                with ui.menu() as menu:
                                    with ui.menu_item(
                                        on_click=lambda c=cat: (menu.close(), open_new_period_dialog(c, refresh_all))
                                    ):
                                        with ui.row().classes("items-center").style("gap: 8px;"):
                                            ui.icon("event_repeat", size="18px")
                                            ui.label("Start next period")
                                    with ui.menu_item(
                                        on_click=lambda c=cat: (
                                            menu.close(),
                                            toggle_active_and_refresh(c, False, refresh_all),
                                        )
                                    ):
                                        with ui.row().classes("items-center").style("gap: 8px;"):
                                            ui.icon("toggle_off", size="18px")
                                            ui.label("Deactivate")
                                    with ui.menu_item(
                                        on_click=lambda c=cat: (menu.close(), open_edit_dialog(c, refresh_all))
                                    ):
                                        with ui.row().classes("items-center").style("gap: 8px;"):
                                            ui.icon("edit_outlined", size="18px")
                                            ui.label("Edit")
                                    ui.separator()
                                    with ui.menu_item(
                                        on_click=lambda c=cat: (menu.close(), confirm_delete_category(c, refresh_all))
                                    ):
                                        with ui.row().classes("items-center").style(f"gap: 8px; color:{CRITICAL};"):
                                            ui.icon("delete_outline", size="18px")
                                            ui.label("Delete")

                    with ui.row().classes("items-center").style("gap: 6px;"):
                        ui.element("div").style(
                            f"width:8px;height:8px;border-radius:50%;background:{color};flex:none;"
                        )
                        ui.label(pace_label).style(f"font-size: 11.5px; font-weight: 600; color:{color};")

                    ui.linear_progress(min(pct_used / 100, 1), show_value=False).props(
                        'color=none track-color=grey-3 size="6px"'
                    ).style(f"border-radius: 4px; --q-primary: {color};")

                    with ui.row().classes("w-full justify-between items-baseline").style("gap: 8px;"):
                        ui.label(f"{fmt_eur(spent)} of {fmt_eur(budget)}").classes("tabular").style(
                            f"font-size: 13px; color: {MUTED};"
                        )
                        ui.label(f"{pct_used:.0f}%").classes("tabular").style(
                            f"font-size: 13px; font-weight: 600; color: {color};"
                        )

                    if cat.currency == "INR":
                        spent_inr = fx.convert_from_eur(spent, date.today().isoformat())
                        ui.label(f"{spent_inr:,.0f} of {cat.amount_native:,.0f} INR used").classes("tabular").style(
                            f"font-size: 11.5px; color: {MUTED};"
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


def render_history(container: ui.column, on_change):
    container.clear()
    expenses = storage.get_expenses()
    with container:
        with ui.row().classes("w-full items-baseline justify-between"):
            section_label("Recent spending")
            ui.link("View all →", "/spending").style(f"font-size: 12px; color:{ACCENT}; font-weight: 500;")
        render_expense_list(expenses[:15], on_change)
