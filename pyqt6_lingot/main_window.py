from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
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

from .bindings import LingotContext, LingotLibraryError, Snapshot
from .config_dialog import ConfigDialog
from .widgets.gauge import GaugeWidget
from .widgets.spectrum import SpectrumWidget
from .widgets.strobe_disc import StrobeDiscWidget


class MainWindow(QMainWindow):
    def __init__(self, context: LingotContext | None, config_filename: str = "") -> None:
        super().__init__()
        self.context = context
        self.config_filename = config_filename
        self.current_snapshot = Snapshot()
        self.show_gauge = True

        self.setWindowTitle("Lingot")
        self.resize(760, 520)

        self.gauge = GaugeWidget()
        self.strobe = StrobeDiscWidget()
        self.spectrum = SpectrumWidget()

        self.frequency_label = QLabel("-- Hz")
        self.tone_label = QLabel("--")
        self.error_label = QLabel("-- cents")

        self._build_actions()
        self._build_layout()
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

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        top_splitter = QSplitter()

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

        top_splitter.addWidget(self.visual_frame)
        top_splitter.addWidget(label_frame)
        top_splitter.setSizes([460, 220])

        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.spectrum)
        main_splitter.setSizes([310, 190])

        root.addWidget(main_splitter)
        self.setCentralWidget(central)

    def _build_timers(self) -> None:
        self.snapshot_timer = QTimer(self)
        self.snapshot_timer.setInterval(40)
        self.snapshot_timer.timeout.connect(self._refresh_snapshot)
        self.snapshot_timer.start()

        self.message_timer = QTimer(self)
        self.message_timer.setInterval(250)
        self.message_timer.timeout.connect(self._dispatch_messages)
        self.message_timer.start()

    def _refresh_snapshot(self) -> None:
        if self.context is None:
            self.frequency_label.setText("engine offline")
            self.tone_label.setText("--")
            self.error_label.setText("-- cents")
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
        elif self.current_snapshot.has_pitch:
            self.frequency_label.setText(f"{self.current_snapshot.frequency:.2f} Hz")
            self.tone_label.setText(self.current_snapshot.note_name or "--")
            self.error_label.setText(f"{self.current_snapshot.error_cents:+.2f} cents")
        else:
            self.frequency_label.setText("-- Hz")
            self.tone_label.setText("--")
            self.error_label.setText("-- cents")

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
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    def _preferences(self) -> None:
        if self.context is None:
            QMessageBox.warning(self, "Lingot", "The Lingot engine is not available.")
            return
        dialog = ConfigDialog(self.context, self)
        dialog.exec()

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About Lingot",
            "Lingot\nExperimental PyQt6 frontend",
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override name
        self.snapshot_timer.stop()
        self.message_timer.stop()
        if self.context is not None:
            self.context.stop()
        super().closeEvent(event)
