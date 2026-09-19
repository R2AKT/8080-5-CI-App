"""
Theme definitions: application stylesheets and syntax highlighting colors.

All color constants and QSS stylesheets are centralized here.
Import from this module instead of hardcoding colors in widgets.
"""

# ============================================================
# APPLICATION STYLESHEETS (QSS)
# ============================================================

THEMES = {
    "Light": "",
    "Dark": """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #d4d4d4; }
        QTabWidget::pane { border: 1px solid #555; }
        QTabBar::tab { background: #3c3c3c; padding: 5px 10px; }
        QTabBar::tab:selected { background: #0078d4; color: white; }
        QPushButton { background-color: #3c3c3c; border: 1px solid #555; padding: 5px; border-radius: 3px; }
        QPushButton:hover { background-color: #505050; }
        QLineEdit, QComboBox, QSpinBox { background-color: #3c3c3c; border: 1px solid #555; padding: 3px; border-radius: 3px; }
        QTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #555; }
        QTableView { background-color: #1e1e1e; color: #d4d4d4; gridline-color: #555; border: 1px solid #555; }
        QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 10px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; }
        QProgressBar::chunk { background-color: #0078d4; }
    """
}

# ============================================================
# EDITOR COLORS (assembler / disassembler code editor)
# ============================================================

EDITOR_DARK = {
    "background": "#1c1c1c",
    "foreground": "#f4f4f4",
    "line_number_bg": "#2b2b2b",
    "line_number_fg": "#808080",
    "current_line_bg": "#264f78",
    "error_line_bg": "#5a1e1e",
}

EDITOR_LIGHT = {
    "background": "#f0f0f0",
    "foreground": "#000000",
    "line_number_bg": "#d0d0d0",
    "line_number_fg": "#141414",
    "current_line_bg": "#f5f5f5",
    "error_line_bg": "#c80000",
}

# ============================================================
# SYNTAX HIGHLIGHTING COLORS (assembler)
# ============================================================

SYNTAX_DARK = {
    "comment": "#6A9955",
    "mnemonic": "#569CD6",
    "directive": "#C586C0",
    "number": "#B5CEA8",
    "label": "#DCDCAA",
    "register": "#9CDCFE",
}

SYNTAX_LIGHT = {
    "comment": "#008000",
    "mnemonic": "#0000FF",
    "directive": "#AF00DB",
    "number": "#098658",
    "label": "#795E26",
    "register": "#001080",
}

# ============================================================
# ARROW COLORS (jump/branch visualization)
# ============================================================

ARROW_COLORS = [
    "#ff6b6b",  # red
    "#4ecdc4",  # teal
    "#ffe66d",  # yellow
    "#a8e6cf",  # mint
    "#ffd93d",  # gold
    "#6bcf7f",  # green
]

# ============================================================
# STATUS / INDICATOR COLORS
# ============================================================

STATUS_COLORS = {
    "warning_bg": "#fff3cd",
    "success_bg": "#d4edda",
    "error_bg": "#f8d7da",
    "error_fg": "#cc0000",
    "normal_fg": "#000000",
    "flag_active": "red",
    "flag_inactive": "black",
    "hint_fg": "#666",
    "trace_active_bg": "#ffcccc",
    "bus_active_bg": "#ffcccc",
    "bus_free_bg": "#f0f0f0",
}


def get_editor_style(is_dark: bool) -> str:
    """Return QSS for code editor based on theme."""
    c = EDITOR_DARK if is_dark else EDITOR_LIGHT
    return f"QTextEdit {{ background-color: {c['background']}; color: {c['foreground']}; }}"


def get_syntax_colors(is_dark: bool) -> dict:
    """Return syntax highlighting color dict for the given theme."""
    return SYNTAX_DARK if is_dark else SYNTAX_LIGHT
