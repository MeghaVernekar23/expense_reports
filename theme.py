"""Visual identity: palette, page head styles, and static nav config."""

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

CATEGORY_NAME_OPTIONS = [
    "Credit Card",
    "General",
    "Outside Food",
    "Personal-Nikhil",
    "Personal-Megha",
    "Others",
]

NAV_ITEMS = [
    ("/", "space_dashboard", "Dashboard"),
    ("/spending", "receipt_long", "Spending"),
    ("/analysis", "insights", "Analysis"),
    ("/past-categories", "inventory_2", "Past categories"),
    ("/add-category", "add_box", "Add category"),
    ("/log-spend", "add_card", "Log a spend"),
]

HEAD_HTML = f"""
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
        box-sizing: border-box;
    }}
    .stripe-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-left-width: 3px;
        border-radius: 8px;
        transition: box-shadow .15s ease;
    }}
    .stripe-card:hover {{ box-shadow: 0 2px 10px rgba(28, 35, 51, 0.07); }}
    .stripe-card.inactive {{ opacity: 0.55; }}
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
    .side-link {{
        display: flex; align-items: center; gap: 10px; width: 100%;
        padding: 9px 14px; border-radius: 8px; box-sizing: border-box;
        color: var(--muted); font-size: 13.5px; font-weight: 500;
        text-decoration: none; transition: background .12s ease, color .12s ease;
    }}
    .side-link:hover {{ background: var(--accent-soft); color: var(--ink); }}
    .side-link.active {{ background: var(--accent); color: white; font-weight: 600; }}
    .app-header {{
        background: var(--surface) !important;
        border-bottom: 1px solid var(--border);
        color: var(--ink) !important;
        height: 56px;
        padding: 0 20px;
    }}
    .app-sidebar {{ background: var(--surface) !important; }}
    .header-brand {{ display: flex; align-items: center; gap: 8px; }}
    .header-menu-btn {{ display: none; }}
    .header-date {{ display: none; }}
    @media (min-width: 901px) {{
        .header-date {{ display: block; }}
    }}
    .page-content {{ width: 100%; padding: 28px 28px 64px; }}
    .app-footer {{
        background: var(--surface) !important;
        border-top: 1px solid var(--border);
        color: var(--muted) !important;
        padding: 14px 20px;
        width: 100%;
        box-sizing: border-box;
    }}
    /* Stat rows (totals bar): a responsive grid instead of a fixed-width
       flex row, so numbers reflow to 2 then 1 column on narrow screens
       instead of clipping or squeezing against each other. Cells get a
       divider via border rather than a separate element, since a column
       layout has no meaningful "vertical" divider to draw. */
    .stat-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 4px 0;
    }}
    .stat-cell {{
        padding: 0 20px;
        border-left: 1px solid var(--border);
        min-width: 0;
    }}
    .stat-cell:first-child {{ border-left: none; padding-left: 0; }}
    @media (max-width: 900px) {{
        .header-menu-btn {{ display: inline-flex; }}
        .app-header {{ padding: 0 14px; }}
        .app-footer {{ padding: 14px; }}
        .page-content {{ padding: 20px 14px 48px; }}
    }}
    @media (max-width: 560px) {{
        .stat-grid {{ grid-template-columns: repeat(2, 1fr); gap: 14px 0; }}
        .stat-cell:nth-child(2n+1) {{ border-left: none; padding-left: 0; }}
        .stat-cell:nth-child(n+3) {{ border-left: none; padding-left: 0; border-top: 1px solid var(--border); padding-top: 12px; }}
    }}
    ::selection {{ background: var(--accent-soft); }}
</style>
"""
