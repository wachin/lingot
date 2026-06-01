"""Internationalization support for the Lingot PyQt6 frontend.

Uses Python gettext to load translations from the existing .po files
in the repository's po/ directory.  Falls back to identity
translations when catalogs are not found, so the application always
runs regardless of locale availability.
"""
from __future__ import annotations

import builtins
import gettext
import os
from pathlib import Path

_DOMAIN = "lingot"
_LOCALE_DIR = Path(__file__).resolve().parent.parent / "po"

_installed = False


def install() -> None:
    """Install the ``_`` builtin for the application domain.

    This should be called once at application startup, before any
    user-visible strings are created.
    """
    global _installed  # noqa: PLW0603
    if _installed:
        return
    _installed = True

    locale_dir = str(_LOCALE_DIR) if _LOCALE_DIR.is_dir() else None

    try:
        t = gettext.translation(
            _DOMAIN,
            localedir=locale_dir,
            fallback=True,
        )
    except Exception:
        t = gettext.NullTranslation()

    t.install()