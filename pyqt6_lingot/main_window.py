from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .bindings import LingotBindings, LingotContext, LingotLibraryError, Snapshot, UiSettings
from .config_dialog import ConfigDialog
from .metadata import (
    APP_AUTHORS,
    APP_BUGTRACKER,
    APP_COPYRIGHT,
    APP_DISPLAY_NAME,
    APP_ICON_PATH,
    APP_SUMMARY,
    APP_VERSION,
    APP_WEBSITE,
)
from .widgets.gauge import GaugeWidget
from .widgets.spectrum import SpectrumWidget
from .widgets.strobe_disc import StrobeDiscWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        context: LingotContext | None,
        config_filename: str = "",
        bindings: LingotBindings | None = None,
        ui_settings: UiSettings | None = None,
    ) -> None:
        super().__init__()
        self.context = context
        self.bindings = bindings
        self.ui_settings = ui_settings
        self.config_filename = config_filename
        self.current_snapshot = Snapshot()
        self.show_gauge = True
        self._last_status = ""
        self._temporary_status_until = 0.0

        self.setWindowTitle("Lingot")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(760, 520)

        self.gauge = GaugeWidget()
        self.strobe = StrobeDiscWidget()
        self.spectrum = SpectrumWidget()

        self.frequency_label = QLabel("-- Hz")
        self.tone_label = QLabel("--")
        self.error_label = QLabel("-- cents")

        self._build_actions()
        self._build_layout()
        self._restore_ui_settings()
        self._update_engine_status()
        self._build_timers()

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open Configuration...", self)
        self.save_action = QAction("&Save Configuration...", self)
        self.quit_action = QAction("&Quit", self)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.preferences_action = QAction("&Preferences...", self)
        edit_menu.addAction(self.preferences_action)

        view_menu = self.menuBar().addMenu("&View")
        mode_group = QActionGroup(self)
        self.gauge_action = QAction("&Gauge", self, checkable=True)
        self.strobe_action = QAction("&Strobe Disc", self, checkable=True)
        self.gauge_action.setChecked(True)
        mode_group.addAction(self.gauge_action)
        mode_group.addAction(self.strobe_action)
        self.spectrum_action = QAction("&Spectrum", self, checkable=True)
        self.spectrum_action.setChecked(True)
        view_menu.addAction(self.gauge_action)
        view_menu.addAction(self.strobe_action)
        view_menu.addSeparator()
        view_menu.addAction(self.spectrum_action)

        help_menu = self.menuBar().addMenu("&Help")
        self.about_action = QAction("&About", self)
        help_menu.addAction(self.about_action)

        self.quit_action.triggered.connect(self.close)
        self.open_action.triggered.connect(self._open_config)
        self.save_action.triggered.connect(self._save_config)
        self.preferences_action.triggered.connect(self._preferences)
        self.gauge_action.triggered.connect(self._set_gauge_mode)
        self.strobe_action.triggered.connect(self._set_strobe_mode)
        self.spectrum_action.toggled.connect(self.spectrum.setVisible)
        self.about_action.triggered.connect(self._about)

    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.top_splitter = QSplitter()

        self.visual_frame = QFrame()
        visual_layout = QVBoxLayout(self.visual_frame)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        visual_layout.addWidget(self.gauge)
        visual_layout.addWidget(self.strobe)
        self.strobe.hide()

        label_frame = QFrame()
        label_frame.setFrameShape(QFrame.Shape.StyledPanel)
        label_layout = QVBoxLayout(label_frame)
        for label in (self.frequency_label, self.tone_label, self.error_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            label_layout.addWidget(label)

        self.top_splitter.addWidget(self.visual_frame)
        self.top_splitter.addWidget(label_frame)
        self.top_splitter.setSizes([460, 220])

        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.spectrum)
        self.main_splitter.setSizes([310, 190])

        root.addWidget(self.main_splitter)
        self.setCentralWidget(central)

    def _restore_ui_settings(self) -> None:
        if self.ui_settings is None:
            return
        if self.ui_settings.win_width > 0 and self.ui_settings.win_height > 0:
            self.resize(self.ui_settings.win_width, self.ui_settings.win_height)
        self.spectrum_action.setChecked(bool(self.ui_settings.spectrum_visible))
        self.spectrum.setVisible(bool(self.ui_settings.spectrum_visible))
        if self.ui_settings.gauge_visible:
            self.gauge_action.setChecked(True)
            self._set_gauge_mode()
        else:
            self.strobe_action.setChecked(True)
            self._set_strobe_mode()
        if self.ui_settings.horizontal_paned_pos > 0:
            self.top_splitter.setSizes([
                self.ui_settings.horizontal_paned_pos,
                max(120, self.width() - self.ui_settings.horizontal_paned_pos),
            ])
        if self.ui_settings.vertical_paned_pos > 0:
            self.main_splitter.setSizes([
                self.ui_settings.vertical_paned_pos,
                max(120, self.height() - self.ui_settings.vertical_paned_pos),
            ])

    def _build_timers(self) -> None:
        self.snapshot_timer = QTimer(self)
        visualization_rate = (
            self.ui_settings.visualization_rate
            if self.ui_settings is not None and self.ui_settings.visualization_rate > 0
            else 30.0
        )
        self.snapshot_timer.setInterval(max(1, int(1000 / visualization_rate)))
        self.snapshot_timer.timeout.connect(self._refresh_snapshot)
        self.snapshot_timer.start()

        self.message_timer = QTimer(self)
        error_dispatch_rate = (
            self.ui_settings.error_dispatch_rate
            if self.ui_settings is not None and self.ui_settings.error_dispatch_rate > 0
            else 5.0
        )
        self.message_timer.setInterval(max(1, int(1000 / error_dispatch_rate)))
        self.message_timer.timeout.connect(self._dispatch_messages)
        self.message_timer.start()

    def _refresh_snapshot(self) -> None:
        if self.context is None:
            self.frequency_label.setText("engine offline")
            self.tone_label.setText("--")
            self.error_label.setText("-- cents")
            self._set_status("Engine offline")
            return

        self.current_snapshot = self.context.snapshot()
        self.gauge.set_error(self.current_snapshot.error_cents)
        self.strobe.set_error(self.current_snapshot.error_cents)

        if self.current_snapshot.running and self.current_snapshot.spectrum_size:
            self.spectrum.set_samples(self.context.spectrum(self.current_snapshot.spectrum_size))

        if not self.current_snapshot.running:
            self.frequency_label.setText("not running")
            self.tone_label.setText("--")
            self.error_label.setText("-- cents")
            self._set_status(f"Engine stopped - {self._config_status_text()}")
        elif self.current_snapshot.has_pitch:
            self.frequency_label.setText(f"{self.current_snapshot.frequency:.2f} Hz")
            self.tone_label.setText(self.current_snapshot.note_name or "--")
            self.error_label.setText(f"{self.current_snapshot.error_cents:+.2f} cents")
            self._set_status(f"Listening - {self._config_status_text()}")
        else:
            self.frequency_label.setText("-- Hz")
            self.tone_label.setText("--")
            self.error_label.setText("-- cents")
            self._set_status(f"Listening - {self._config_status_text()}")

    def _dispatch_messages(self) -> None:
        if self.context is None:
            return
        while True:
            message = self.context.pop_message()
            if message is None:
                return
            msg_type, _error_code, text = message
            if msg_type == 0:
                QMessageBox.critical(self, "Error", text)
            elif msg_type == 1:
                QMessageBox.warning(self, "Warning", text)
            elif msg_type == 2:
                QMessageBox.information(self, "Info", text)

    def _set_gauge_mode(self) -> None:
        self.show_gauge = True
        self.gauge.show()
        self.strobe.hide()

    def _set_strobe_mode(self) -> None:
        self.show_gauge = False
        self.strobe.show()
        self.gauge.hide()

    def _open_config(self) -> None:
        if self.context is None:
            QMessageBox.warning(self, "Lingot", "The Lingot engine is not available.")
            return

        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open Configuration File",
            self.config_filename or "",
            "Lingot configuration files (*.conf)",
        )
        if not filename:
            return

        try:
            self.context.load_config(filename)
            self.context.restart()
            self.config_filename = filename
            self._update_engine_status()
            self._show_temporary_status(f"Loaded configuration: {self._config_display_name()}")
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    def _save_config(self) -> None:
        if self.context is None:
            QMessageBox.warning(self, "Lingot", "The Lingot engine is not available.")
            return

        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Configuration File",
            self.config_filename or "",
            "Lingot configuration files (*.conf)",
        )
        if not filename:
            return
        if not filename.endswith(".conf"):
            filename = f"{filename}.conf"

        try:
            self.context.save_config(filename)
            self.config_filename = filename
            self._update_engine_status()
            self._show_temporary_status(f"Saved configuration: {self._config_display_name()}")
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    def _preferences(self) -> None:
        if self.context is None:
            QMessageBox.warning(self, "Lingot", "The Lingot engine is not available.")
            return
        dialog = ConfigDialog(self.context, self, ui_settings=self.ui_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_engine_status()
            self._show_temporary_status("Preferences applied")

    def _about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_DISPLAY_NAME}",
            (
                f"<h3>{APP_DISPLAY_NAME} {APP_VERSION}</h3>"
                f"<p>{APP_SUMMARY}.</p>"
                "<p>Lingot is an accurate and easy to use musical instrument tuner. "
                "This frontend reuses the existing C engine for audio capture, "
                "pitch detection, FFT analysis, configuration files, UI settings, "
                "and Scala scale support.</p>"
                f"<p>{APP_COPYRIGHT}</p>"
                f"<p>Authors:<br>{'<br>'.join(APP_AUTHORS)}</p>"
                f"<p><a href=\"{APP_WEBSITE}\">{APP_WEBSITE}</a><br>"
                f"<a href=\"{APP_BUGTRACKER}\">{APP_BUGTRACKER}</a></p>"
                "<p>License: GPL-2.0-or-later</p>"
            ),
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override name
        self.snapshot_timer.stop()
        self.message_timer.stop()
        self._save_ui_settings()
        if self.context is not None:
            self.context.stop()
        super().closeEvent(event)

    def _save_ui_settings(self) -> None:
        if self.bindings is None or self.ui_settings is None:
            return
        self.ui_settings.spectrum_visible = int(self.spectrum_action.isChecked())
        self.ui_settings.gauge_visible = int(self.gauge_action.isChecked())
        self.ui_settings.win_width = self.width()
        self.ui_settings.win_height = self.height()
        self.ui_settings.horizontal_paned_pos = self.top_splitter.sizes()[0]
        self.ui_settings.vertical_paned_pos = self.main_splitter.sizes()[0]
        try:
            self.bindings.set_ui_settings(self.ui_settings)
            self.bindings.save_ui_settings()
        except LingotLibraryError:
            pass

    def _config_display_name(self) -> str:
        if not self.config_filename:
            return "default"
        return Path(self.config_filename).name

    def _config_status_text(self) -> str:
        return f"Config: {self._config_display_name()}"

    def _set_status(self, message: str) -> None:
        if time.monotonic() < self._temporary_status_until:
            return
        if message == self._last_status:
            return
        self._last_status = message
        self.statusBar().showMessage(message)

    def _show_temporary_status(self, message: str, timeout_ms: int = 5000) -> None:
        self._temporary_status_until = time.monotonic() + timeout_ms / 1000.0
        self.statusBar().showMessage(message, timeout_ms)

    def _update_engine_status(self) -> None:
        if self.context is None:
            self._set_status("Engine offline")
        else:
            self._set_status(f"Starting - {self._config_status_text()}")
