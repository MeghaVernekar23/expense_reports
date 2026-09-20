"""Page chrome shared by every page: head styles, top bar, sidebar, footer,
and the small header/section label helpers pages use inside their content."""
from datetime import date

from nicegui import ui

from theme import HEAD_HTML, INK, MUTED, NAV_ITEMS


def page_shell(active_path: str):
    """Renders the head styles, a full-width top navigation bar (brand,
    today's date) that stays visible on every screen size, and a left
    sidebar docked directly beneath it — permanent on desktop, a
    toggleable overlay drawer on narrow screens, opened via the menu
    button that appears in the top bar there. Caller fills the content
    column via a `with` block after calling this, or simply continues
    writing widgets — this function opens the wrapping column context
    and returns it."""
    ui.add_head_html(HEAD_HTML)
    ui.page_title("Expense Report")

    with ui.header().classes("app-header").props("elevated=false"):
        with ui.row().classes("w-full h-full items-center justify-between no-wrap"):
            with ui.row().classes("items-center no-wrap").style("gap: 4px;"):
                ui.button(icon="menu", on_click=lambda: drawer.toggle()).props(
                    "flat round dense"
                ).classes("header-menu-btn").style(f"color:{INK};")
                with ui.row().classes("header-brand").style("cursor: pointer;").on(
                    "click", lambda: ui.navigate.to("/")
                ):
                    ui.label("📒").style("font-size: 20px;")
                    ui.label("Expense Report").style(f"font-weight: 700; font-size: 15px; color:{INK};")

            ui.label(date.today().strftime("%A, %d %B %Y")).classes("header-date").style(
                f"color:{MUTED}; font-size: 12.5px; font-weight: 500;"
            )

    with ui.left_drawer(fixed=True, bordered=True).classes("app-sidebar").props(
        "width=220 breakpoint=900 show-if-above"
    ) as drawer:
        with ui.column().style("gap: 2px; padding: 16px 12px; height: 100%;"):
            for path, icon, label in NAV_ITEMS:
                cls = "side-link active" if path == active_path else "side-link"
                with ui.link(target=path).classes(cls):
                    ui.icon(icon, size="18px")
                    ui.label(label)

    with ui.column().classes("items-center").style("width: 100%; gap: 0;"):
        content = ui.column().classes("items-center page-content")
        return content


def page_footer():
    """Called by each page after its own content — a clean bottom bar
    matching the top header's styling (brand + copyright only, no nav),
    docked beside the sidebar rather than under it so it never overlaps."""
    with ui.footer().classes("app-footer").props("elevated=false"):
        with ui.row().classes("w-full items-center justify-center").style("gap: 8px;"):
            ui.label("📒").style("font-size: 15px;")
            ui.label(f"Expense Report · © {date.today().year}").style(
                f"font-size: 12.5px; font-weight: 500; color:{MUTED};"
            )


def page_header(title: str, subtitle: str, extra_actions=None):
    with ui.row().classes("w-full items-baseline justify-between").style("margin-bottom: 22px; gap: 10px; flex-wrap: wrap;"):
        with ui.column().style("gap: 2px;"):
            ui.label(title).classes("display").style(
                f"font-size: 26px; font-weight: 600; color: {INK}; line-height: 1.1;"
            )
            ui.label(subtitle).classes("eyebrow")
        if extra_actions:
            with ui.row().style("gap: 6px; flex-wrap: wrap;"):
                extra_actions()


def section_label(text: str):
    ui.label(text).classes("eyebrow").style("padding-left: 2px;")
