"""Log a spend page: standalone wrapper around the shared log-spend form."""
from nicegui import ui

from components import render_log_spend_form
from shell import page_footer, page_header, page_shell


@ui.page("/log-spend")
def log_spend_page():
    content = page_shell("/log-spend")
    with content:
        with ui.column().classes("w-full").style("max-width: 560px; gap: 24px;"):
            page_header("Log a spend", "Every expense needs an active category")
            form_container = ui.column().classes("w-full")
            render_log_spend_form(form_container)
    page_footer()
