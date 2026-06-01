from __future__ import annotations

import argparse
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from .bindings import LingotBindings, LingotContext, LingotLibraryError
from .i18n import install as install_i18n
from .main_window import MainWindow
from .metadata import APP_NAME


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="lingot-pyqt6")
    parser.add_argument("-c", "--config", help="configuration name under ~/.config/lingot")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    install_i18n()

    args = parse_args(sys.argv[1:] if argv is None else argv)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("org.lingot.lingot")

    context = None
    config_filename = ""
    bindings = None
    ui_settings = None
    startup_error = ""

    try:
        bindings = LingotBindings()
        bindings.initialize(args.config)
        config_filename = bindings.config_filename()
        ui_settings = bindings.ui_settings()
        context = LingotContext(bindings)
        context.start()
    except LingotLibraryError as exc:
        startup_error = str(exc)

    window = MainWindow(
        context=context,
        config_filename=config_filename,
        bindings=bindings,
        ui_settings=ui_settings,
    )
    window.show()

    if startup_error:
        QMessageBox.warning(window, "Lingot", startup_error)

    result = app.exec()
    if context is not None:
        context.close()
    return result
