"""Common shared utilities (i18n, themes)."""
__all__ = ['LANGS', 'get_system_language', 'set_language', 'THEMES', 'get_editor_style', 'get_syntax_colors', 'ARROW_COLORS', 'STATUS_COLORS']

from .i18n import LANGS, get_system_language, set_language  # noqa: F401
from .themes import THEMES, get_editor_style, get_syntax_colors, ARROW_COLORS, STATUS_COLORS  # noqa: F401
