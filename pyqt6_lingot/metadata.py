from __future__ import annotations

from pathlib import Path

APP_NAME = "Lingot"
APP_DISPLAY_NAME = "Lingot PyQt6"
APP_VERSION = "1.1.2"
APP_SUMMARY = "Experimental PyQt6 frontend for the Lingot tuner"
APP_WEBSITE = "https://www.nongnu.org/lingot/"
APP_BUGTRACKER = "https://github.com/ibancg/lingot/issues/"
APP_COPYRIGHT = "Copyright (C) 2004-2020 Iban Cereijo<br>Copyright (C) 2004-2019 Jairo Chapela"
APP_AUTHORS = (
    "Iban Cereijo &lt;ibancg@gmail.com&gt;",
    "Jairo Chapela &lt;jairochapela@gmail.com&gt;",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ICON_PATH = REPO_ROOT / "icons" / "org.nongnu.lingot.svg"
