"""Expense Report — a multi-page NiceGUI expense dashboard.

Entrypoint only: initializes the database, patches ui.notify, imports
every page module (registering their @ui.page routes as a side effect),
and starts the server. Page bodies live in pages/, shared chrome in
shell.py, reusable widgets/dialogs in components.py, data export in
export_service.py, formatting/date helpers in utils.py, and the visual
theme in theme.py.
"""
from nicegui import app, ui

import storage
from export_service import BILLS_DIR

storage.init_db()

_original_notify = ui.notify


def notify(message: str, **kwargs):
    """ui.notify wrapper defaulting toasts to the top-center of the screen
    instead of NiceGUI's bottom default, which gets lost below the fold."""
    kwargs.setdefault("position", "top")
    return _original_notify(message, **kwargs)


ui.notify = notify

app.add_static_files("/bills", str(BILLS_DIR))

# Import order doesn't matter for routing — each module registers its own
# @ui.page route on import — but every page is needed for the app to expose
# its full nav.
import pages.dashboard  # noqa: E402,F401
import pages.spending  # noqa: E402,F401
import pages.analysis  # noqa: E402,F401
import pages.past_categories  # noqa: E402,F401
import pages.add_category  # noqa: E402,F401
import pages.log_spend  # noqa: E402,F401

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Expense Report", favicon="📒", port=9000, reload=True)
