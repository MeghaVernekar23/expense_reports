"""Analysis page: month-over-month, year-over-year, and per-recurring-
category spend vs. budget."""
from datetime import datetime

from nicegui import ui

import storage
from components import echart_bar
from shell import page_footer, page_header, page_shell, section_label
from theme import ACCENT, ACCENT_SOFT, BORDER, GOOD, INK, MUTED
from utils import category_groups, fmt_eur, monthly_totals, status_color, yearly_totals


@ui.page("/analysis")
def analysis_page():
    content = page_shell("/analysis")
    with content:
        with ui.column().classes("w-full").style("max-width: 900px; gap: 28px;"):
            page_header("Analysis", "Month-over-month and year-over-year spend")

            all_expenses = storage.get_expenses()

            if not all_expenses:
                with ui.column().classes("panel w-full items-center").style("padding: 40px 20px; gap: 6px;"):
                    ui.icon("insights", size="28px").style(f"color:{MUTED}")
                    ui.label("No spending logged yet").style(f"color:{INK}; font-weight: 600;")
                    ui.label("Charts appear once you log a few expenses.").style(
                        f"color:{MUTED}; font-size: 13px;"
                    )
            else:
                # ---- Month over month ----
                section_label("Month over month (all categories combined)")
                m_totals = monthly_totals(all_expenses)
                m_labels = [datetime.strptime(k, "%Y-%m").strftime("%b %Y") for k, _ in m_totals]
                m_values = [round(v, 2) for _, v in m_totals]
                with ui.column().classes("panel w-full").style("padding: 16px 8px 4px;"):
                    echart_bar(m_labels, m_values)

                # ---- Year over year ----
                section_label("Year over year")
                y_totals = yearly_totals(all_expenses)
                y_labels = [k for k, _ in y_totals]
                y_values = [round(v, 2) for _, v in y_totals]
                with ui.column().classes("panel w-full").style("padding: 16px 8px 4px; margin-top: 4px;"):
                    echart_bar(y_labels, y_values, color=GOOD, height="220px")

                # ---- Per recurring category ----
                section_label("By recurring category")
                groups = category_groups()
                with ui.column().classes("w-full").style("gap: 14px; margin-top: 4px;"):
                    for name, periods in sorted(groups.items()):
                        if len(periods) < 1:
                            continue
                        with ui.column().classes("panel w-full").style("padding: 16px 18px; gap: 10px;"):
                            ui.label(name).style(f"font-weight: 600; font-size: 14.5px; color:{INK};")

                            period_labels = [p.month_label for p in periods]
                            spent_values = [round(storage.get_total_spent(p.id), 2) for p in periods]
                            budget_values = [round(p.budget, 2) for p in periods]

                            if len(periods) > 1:
                                ui.echart(
                                    {
                                        "grid": {"left": 50, "right": 16, "top": 30, "bottom": 40},
                                        "legend": {
                                            "data": ["Budget", "Spent"],
                                            "top": 0,
                                            "textStyle": {"color": MUTED, "fontSize": 11},
                                        },
                                        "xAxis": {
                                            "type": "category",
                                            "data": period_labels,
                                            "axisLabel": {"color": MUTED, "fontSize": 10.5},
                                        },
                                        "yAxis": {
                                            "type": "value",
                                            "axisLine": {"show": False},
                                            "splitLine": {"lineStyle": {"color": BORDER, "type": "dashed"}},
                                            "axisLabel": {"color": MUTED, "fontSize": 11, "formatter": "€{value}"},
                                        },
                                        "tooltip": {"trigger": "axis"},
                                        "series": [
                                            {
                                                "name": "Budget",
                                                "type": "bar",
                                                "data": budget_values,
                                                "itemStyle": {"color": ACCENT_SOFT},
                                                "barMaxWidth": 28,
                                            },
                                            {
                                                "name": "Spent",
                                                "type": "line",
                                                "data": spent_values,
                                                "itemStyle": {"color": ACCENT},
                                                "smooth": True,
                                            },
                                        ],
                                    }
                                ).style("width: 100%; height: 200px;")

                            with ui.row().classes("w-full").style("gap: 0; overflow-x: auto;"):
                                for p, spent, budget in zip(periods, spent_values, budget_values):
                                    pct = (spent / budget * 100) if budget > 0 else 0
                                    color = status_color(pct)
                                    with ui.column().style(
                                        f"padding: 4px 14px; gap: 2px; border-left: 1px solid {BORDER}; min-width: 110px;"
                                    ):
                                        ui.label(p.month_label).style(f"font-size: 10.5px; color:{MUTED};")
                                        ui.label(f"{fmt_eur(spent)}").classes("tabular").style(
                                            f"font-size: 13px; font-weight: 600; color:{color};"
                                        )
                                        ui.label(f"of {fmt_eur(budget)}").classes("tabular").style(
                                            f"font-size: 10.5px; color:{MUTED};"
                                        )
    page_footer()
