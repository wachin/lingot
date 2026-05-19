from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .bindings import ConfigValues, LingotContext, LingotLibraryError


class ConfigDialog(QDialog):
    def __init__(self, context: LingotContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(420)

        self.values = context.config_values()
        self._build_ui()
        self._load_values(self.values)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_algorithm_tab(), "Algorithm")
        tabs.addTab(self._build_frequency_tab(), "Frequency")
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply)
        root.addWidget(buttons)

    def _build_algorithm_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.fft_size = QComboBox()
        for value in (256, 512, 1024, 2048, 4096):
            self.fft_size.addItem(str(value), value)

        self.temporal_window = QDoubleSpinBox()
        self.temporal_window.setRange(0.0, 15.0)
        self.temporal_window.setDecimals(3)
        self.temporal_window.setSingleStep(0.05)
        self.temporal_window.setSuffix(" s")

        self.noise_threshold = QDoubleSpinBox()
        self.noise_threshold.setRange(0.0, 40.0)
        self.noise_threshold.setDecimals(2)
        self.noise_threshold.setSingleStep(0.5)
        self.noise_threshold.setSuffix(" dB")

        self.calculation_rate = QDoubleSpinBox()
        self.calculation_rate.setRange(1.0, 30.0)
        self.calculation_rate.setDecimals(2)
        self.calculation_rate.setSingleStep(0.5)
        self.calculation_rate.setSuffix(" Hz")

        self.optimize_parameters = QCheckBox()

        form.addRow("FFT size", self.fft_size)
        form.addRow("Temporal window", self.temporal_window)
        form.addRow("Noise threshold", self.noise_threshold)
        form.addRow("Calculation rate", self.calculation_rate)
        form.addRow("Optimize internal parameters", self.optimize_parameters)
        return page

    def _build_frequency_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.min_frequency = QDoubleSpinBox()
        self.min_frequency.setRange(0.0, 22050.0)
        self.min_frequency.setDecimals(2)
        self.min_frequency.setSingleStep(1.0)
        self.min_frequency.setSuffix(" Hz")

        self.max_frequency = QDoubleSpinBox()
        self.max_frequency.setRange(1.0, 22050.0)
        self.max_frequency.setDecimals(2)
        self.max_frequency.setSingleStep(1.0)
        self.max_frequency.setSuffix(" Hz")

        self.root_frequency_error = QDoubleSpinBox()
        self.root_frequency_error.setRange(-500.0, 500.0)
        self.root_frequency_error.setDecimals(2)
        self.root_frequency_error.setSingleStep(0.5)
        self.root_frequency_error.setSuffix(" cents")

        form.addRow("Minimum frequency", self.min_frequency)
        form.addRow("Maximum frequency", self.max_frequency)
        form.addRow("Root frequency error", self.root_frequency_error)
        return page

    def _load_values(self, values: ConfigValues) -> None:
        fft_index = self.fft_size.findData(values.fft_size)
        self.fft_size.setCurrentIndex(max(0, fft_index))
        self.temporal_window.setValue(values.temporal_window)
        self.noise_threshold.setValue(values.min_overall_snr)
        self.calculation_rate.setValue(values.calculation_rate)
        self.min_frequency.setValue(values.min_frequency)
        self.max_frequency.setValue(values.max_frequency)
        self.root_frequency_error.setValue(values.root_frequency_error)
        self.optimize_parameters.setChecked(bool(values.optimize_internal_parameters))

    def _collect_values(self) -> ConfigValues:
        values = ConfigValues()
        values.audio_system_index = self.values.audio_system_index
        values.fft_size = int(self.fft_size.currentData())
        values.temporal_window = self.temporal_window.value()
        values.min_overall_snr = self.noise_threshold.value()
        values.calculation_rate = self.calculation_rate.value()
        values.min_frequency = self.min_frequency.value()
        values.max_frequency = self.max_frequency.value()
        values.root_frequency_error = self.root_frequency_error.value()
        values.optimize_internal_parameters = int(self.optimize_parameters.isChecked())
        return values

    def _apply(self) -> bool:
        if self.min_frequency.value() >= self.max_frequency.value():
            QMessageBox.warning(
                self,
                "Invalid Frequencies",
                "Minimum frequency must be lower than maximum frequency.",
            )
            return False

        try:
            self.context.set_config_values(self._collect_values())
            self.context.restart()
            self.values = self.context.config_values()
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))
            return False
        return True

    def _accept(self) -> None:
        if self._apply():
            self.accept()
