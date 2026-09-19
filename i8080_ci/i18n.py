"""Backward-compatible re-export. Actual implementation lives in common.i18n and common.themes."""
from common.i18n import *  # noqa: F401,F403
from common.i18n import LANGS, get_system_language, set_language  # noqa: F401
from common.themes import THEMES  # noqa: F401
