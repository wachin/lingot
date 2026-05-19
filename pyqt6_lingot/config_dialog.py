from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .bindings import ConfigValues, LingotContext, LingotLibraryError, Scale, ScaleNote


class ConfigDialog(QDialog):
    def __init__(self, context: LingotContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(420)

        self.values = context.config_values()
        self.original_scale = context.scale()
        self._context_scale_changed_during_dialog = False
        self._build_ui()
        self._load_values(self.values)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_input_tab(), "Input")
        tabs.addTab(self._build_algorithm_tab(), "Algorithm")
        tabs.addTab(self._build_frequency_tab(), "Frequency")
        tabs.addTab(self._build_scale_tab(), "Scale")
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

    def _build_input_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.audio_system = QComboBox()
        for index, name in self.context.audio_systems():
            self.audio_system.addItem(name, index)
        self.audio_system.currentIndexChanged.connect(self._refresh_audio_devices)

        self.audio_device = QComboBox()
        self.audio_device.setEditable(True)

        form.addRow("Audio system", self.audio_system)
        form.addRow("Device", self.audio_device)
        return page

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

    def _build_scale_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        scale_form = QFormLayout()
        self.scale_name = QLineEdit()
        self.scale_base_frequency = QDoubleSpinBox()
        self.scale_base_frequency.setRange(1.0, 22050.0)
        self.scale_base_frequency.setDecimals(6)
        self.scale_base_frequency.setSingleStep(1.0)
        self.scale_base_frequency.setSuffix(" Hz")
        scale_form.addRow("Name", self.scale_name)
        scale_form.addRow("Base frequency", self.scale_base_frequency)
        root.addLayout(scale_form)

        self.scale_table = QTableWidget(0, 2)
        self.scale_table.setHorizontalHeaderLabels(["Note", "Shift"])
        self.scale_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.scale_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        root.addWidget(self.scale_table)

        buttons = QHBoxLayout()
        self.scale_add_button = QPushButton("Add")
        self.scale_remove_button = QPushButton("Remove")
        self.scale_import_button = QPushButton("Import .scl")
        self.scale_add_button.clicked.connect(self._add_scale_row)
        self.scale_remove_button.clicked.connect(self._remove_scale_row)
        self.scale_import_button.clicked.connect(self._import_scl)
        buttons.addWidget(self.scale_add_button)
        buttons.addWidget(self.scale_remove_button)
        buttons.addWidget(self.scale_import_button)
        buttons.addStretch()
        root.addLayout(buttons)
        return page

    def _load_values(self, values: ConfigValues) -> None:
        system_index = self.audio_system.findData(values.audio_system_index)
        self.audio_system.setCurrentIndex(max(0, system_index))
        self._refresh_audio_devices()
        current_device = self.context.audio_device()
        device_index = self.audio_device.findText(current_device)
        if device_index >= 0:
            self.audio_device.setCurrentIndex(device_index)
        else:
            self.audio_device.setEditText(current_device)

        fft_index = self.fft_size.findData(values.fft_size)
        self.fft_size.setCurrentIndex(max(0, fft_index))
        self.temporal_window.setValue(values.temporal_window)
        self.noise_threshold.setValue(values.min_overall_snr)
        self.calculation_rate.setValue(values.calculation_rate)
        self.min_frequency.setValue(values.min_frequency)
        self.max_frequency.setValue(values.max_frequency)
        self.root_frequency_error.setValue(values.root_frequency_error)
        self.optimize_parameters.setChecked(bool(values.optimize_internal_parameters))
        self._load_scale(self.context.scale())

    def _refresh_audio_devices(self) -> None:
        previous = self.audio_device.currentText() if hasattr(self, "audio_device") else ""
        self.audio_device.clear()
        system_index = self.audio_system.currentData()
        if system_index is None:
            return
        for device in self.context.audio_devices(int(system_index)):
            self.audio_device.addItem(device)
        if previous:
            index = self.audio_device.findText(previous)
            if index >= 0:
                self.audio_device.setCurrentIndex(index)
            else:
                self.audio_device.setEditText(previous)

    def _collect_values(self) -> ConfigValues:
        values = ConfigValues()
        values.audio_system_index = int(self.audio_system.currentData() or 0)
        values.fft_size = int(self.fft_size.currentData())
        values.temporal_window = self.temporal_window.value()
        values.min_overall_snr = self.noise_threshold.value()
        values.calculation_rate = self.calculation_rate.value()
        values.min_frequency = self.min_frequency.value()
        values.max_frequency = self.max_frequency.value()
        values.root_frequency_error = self.root_frequency_error.value()
        values.optimize_internal_parameters = int(self.optimize_parameters.isChecked())
        return values

    def _load_scale(self, scale: Scale) -> None:
        self.scale_name.setText(scale.name)
        self.scale_base_frequency.setValue(scale.base_frequency)
        self.scale_table.setRowCount(0)
        for note in scale.notes:
            self._add_scale_row(note)

    def _add_scale_row(self, note: ScaleNote | None = None) -> None:
        row = self.scale_table.rowCount()
        self.scale_table.insertRow(row)
        if note is None:
            note = ScaleNote("?", min(row * 100.0, 1199.0), f"{min(row * 100.0, 1199.0):.6f}")
        self.scale_table.setItem(row, 0, QTableWidgetItem(note.name))
        self.scale_table.setItem(row, 1, QTableWidgetItem(note.shift or f"{note.cents:.6f}"))

    def _remove_scale_row(self) -> None:
        row = self.scale_table.currentRow()
        if row <= 0:
            QMessageBox.warning(self, "Scale", "The reference note cannot be removed.")
            return
        self.scale_table.removeRow(row)

    def _collect_scale(self) -> Scale:
        notes: list[ScaleNote] = []
        names: set[str] = set()

        for row in range(self.scale_table.rowCount()):
            name_item = self.scale_table.item(row, 0)
            shift_item = self.scale_table.item(row, 1)
            name = name_item.text().strip() if name_item is not None else ""
            if not name or name == "?" or any(char in name for char in " \t\n{}"):
                raise LingotLibraryError("Scale note names must be non-empty and cannot contain spaces or braces.")
            if name in names:
                raise LingotLibraryError("Scale note names must be unique.")
            names.add(name)

            shift = shift_item.text().strip() if shift_item is not None else ""
            if not shift:
                raise LingotLibraryError("Scale shifts must be non-empty.")
            notes.append(ScaleNote(name, 0.0, shift))

        if not notes:
            raise LingotLibraryError("The scale must contain at least one note.")

        return Scale(
            self.scale_name.text().strip() or "Untitled scale",
            self.scale_base_frequency.value(),
            notes,
        )

    def _import_scl(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open Scale File",
            "",
            "Scala files (*.scl)",
        )
        if not filename:
            return
        try:
            self.context.import_scl(filename)
            self._context_scale_changed_during_dialog = True
            self._load_scale(self.context.scale())
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    def _apply(self) -> bool:
        if self.min_frequency.value() >= self.max_frequency.value():
            QMessageBox.warning(
                self,
                "Invalid Frequencies",
                "Minimum frequency must be lower than maximum frequency.",
            )
            return False

        try:
            values = self._collect_values()
            scale = self._collect_scale()
            self.context.set_config_values(values)
            self.context.set_audio_device(self.audio_device.currentText())
            self.context.set_scale_shifts(scale)
            self.context.restart()
            self.values = self.context.config_values()
            self._context_scale_changed_during_dialog = False
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))
            return False
        return True

    def _accept(self) -> None:
        if self._apply():
            self.accept()

    def reject(self) -> None:
        if self._context_scale_changed_during_dialog:
            try:
                self.context.set_scale_shifts(self.original_scale)
            except LingotLibraryError:
                pass
        super().reject()
