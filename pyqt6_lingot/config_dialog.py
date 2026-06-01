from __future__ import annotations

import math

from PyQt6.QtCore import Qt
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
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .bindings import ConfigValues, LingotContext, LingotLibraryError, Scale, ScaleNote, UiSettings

# Number of octaves shown in the frequency combo boxes.
_FREQUENCY_COMBO_N_OCTAVES = 6
_FREQUENCY_COMBO_FIRST_OCTAVE = 1


class ConfigDialog(QDialog):
    def __init__(
        self,
        context: LingotContext,
        parent=None,
        ui_settings: UiSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.ui_settings = ui_settings
        self.setWindowTitle(_("Lingot configuration"))
        self.setMinimumSize(420, 400)

        self.values = context.config_values()
        self.original_scale = context.scale()
        self._context_scale_changed_during_dialog = False
        self._build_ui()
        self._load_values(self.values, self.original_scale, self.context.audio_device())
        self._restore_ui_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_capture_tab(), _("Capture"))
        tabs.addTab(self._build_adjustments_tab(), _("Adjustments"))
        tabs.addTab(self._build_settings_tab(), _("Settings"))
        tabs.addTab(self._build_scale_tab(), _("Scale"))
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self._reject)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply)
        defaults_button = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if defaults_button is not None:
            defaults_button.clicked.connect(self._restore_defaults)
        root.addWidget(buttons)

    # -- Capture tab (audio input) -------------------------------------

    def _build_capture_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(9, 9, 9, 9)
        form.setSpacing(9)

        header = QLabel("<b>" + _("Select the audio source:") + "</b>")
        form.addRow(header)

        self.audio_system = QComboBox()
        self.audio_system.setToolTip(_("Here you can pick the sound system."))
        for index, name in self.context.audio_systems():
            self.audio_system.addItem(name, index)
        self.audio_system.currentIndexChanged.connect(self._refresh_audio_devices)

        self.audio_device = QComboBox()
        self.audio_device.setEditable(True)
        self.audio_device.setToolTip(
            _("Choose the audio device if you have more than one. "
            "If you are using JACK, you can also connect Lingot to a "
            "desired source with an external JACK control application.")
        )

        form.addRow(_("Audio system"), self.audio_system)
        form.addRow(_("Device"), self.audio_device)
        return page

    # -- Adjustments tab (calculation rate + noise) ---------------------

    def _build_adjustments_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(9, 9, 11, 9)
        form.setSpacing(6)

        header = QLabel(_("Adjust the following refresh rates:"))
        header.setStyleSheet("font-weight: bold;")
        form.addRow(header)

        # Calculation rate slider (1 – 30 Hz)
        self.calculation_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.calculation_rate_slider.setRange(1, 30)
        self.calculation_rate_slider.setSingleStep(1)
        self.calculation_rate_slider.setPageStep(10)
        self.calculation_rate_slider.setToolTip(
            _("Number of calculations of the fundamental frequency per second.")
        )
        self.calculation_rate_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.calculation_rate_slider.setTickInterval(1)
        self.calculation_rate_label = QLabel("25 Hz")
        self.calculation_rate_slider.valueChanged.connect(
            lambda v: self.calculation_rate_label.setText(f"{v} Hz")
        )
        rate_row = QWidget()
        rate_layout = QHBoxLayout(rate_row)
        rate_layout.setContentsMargins(0, 0, 0, 0)
        rate_layout.addWidget(self.calculation_rate_slider, 1)
        rate_layout.addWidget(self.calculation_rate_label)
        form.addRow(_("Calculation rate"), rate_row)

        noise_header = QLabel(_("Adjust the noise level:"))
        noise_header.setStyleSheet("font-weight: bold;")
        form.addRow(noise_header)

        # Minimum SNR slider (0 – 40 dB)
        self.noise_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_threshold_slider.setRange(0, 40)
        self.noise_threshold_slider.setSingleStep(1)
        self.noise_threshold_slider.setPageStep(10)
        self.noise_threshold_slider.setToolTip(
            _("Minimum signal-to-noise ratio to consider the captured signal as "
            "something relevant. Try to keep this level low, and raise it if you "
            "experience problems in very noisy environments. This level is depicted "
            "in the spectrum area as a yellow dotted line.")
        )
        self.noise_threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.noise_threshold_slider.setTickInterval(5)
        self.noise_threshold_label = QLabel("20 dB")
        self.noise_threshold_slider.valueChanged.connect(
            lambda v: self.noise_threshold_label.setText(f"{v} dB")
        )
        noise_row = QWidget()
        noise_layout = QHBoxLayout(noise_row)
        noise_layout.setContentsMargins(0, 0, 0, 0)
        noise_layout.addWidget(self.noise_threshold_slider, 1)
        noise_layout.addWidget(self.noise_threshold_label)
        form.addRow(_("Minimum SNR"), noise_row)

        return page

    # -- Settings tab (algorithm / frequency range) --------------------

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(9, 9, 9, 9)
        form.setSpacing(6)

        header = QLabel(_("Instrument frequency range"))
        header.setStyleSheet("font-weight: bold;")
        form.addRow(header)

        # Minimum frequency (editable combo with note names)
        self.min_frequency_combo = QComboBox()
        self.min_frequency_combo.setEditable(True)
        self.min_frequency_combo.setToolTip(
            _("This is the lowest frequency you want to tune in this instrument. "
            "You can put here either a frequency or select a note from the popup list.")
        )

        # Maximum frequency (editable combo with note names)
        self.max_frequency_combo = QComboBox()
        self.max_frequency_combo.setEditable(True)
        self.max_frequency_combo.setToolTip(
            _("This is the highest frequency you want to tune in this instrument. "
            "You can put here either a frequency or select a note from the popup list.")
        )

        form.addRow(_("Minimum note"), self.min_frequency_combo)
        form.addRow(_("Maximum note"), self.max_frequency_combo)

        # Optimize parameters
        self.optimize_parameters = QCheckBox(_("Optimize parameters automatically"))
        self.optimize_parameters.setToolTip(
            _("Leave this option ON and Lingot will optimize some parameters for you.")
        )
        self.optimize_parameters.stateChanged.connect(self._optimize_toggled)
        form.addRow(self.optimize_parameters)

        # FFT size
        self.fft_size_label = QLabel(_("FFT size"))
        self.fft_size = QComboBox()
        self.fft_size.setToolTip(
            _("The FFT buffer gives Lingot a first look to the spectrum. Higher values "
            "can help Lingot to hook up the correct peak, but it's also computationally "
            "more expensive. Don't use high values here unless you need to tune high "
            "frequency.")
        )
        for value in (256, 512, 1024, 2048, 4096):
            self.fft_size.addItem(str(value), value)
        form.addRow(self.fft_size_label, self.fft_size)

        # Temporal window
        self.temporal_window_label = QLabel(_("Temporal window"))
        self.temporal_window = QDoubleSpinBox()
        self.temporal_window.setRange(0.0, 15.0)
        self.temporal_window.setDecimals(3)
        self.temporal_window.setSingleStep(0.01)
        self.temporal_window.setSuffix(" seconds")
        self.temporal_window.setToolTip(
            _("This is the most recent amount of data considered for tuning. The longer "
            "it is, the more accuracy you can obtain, but also the dynamic response "
            "gets slower. Also, if you raise this parameter, the computational cost "
            "increases. The size of the buffer, in samples, must be greater than or "
            "equal to the FFT buffer size.")
        )
        form.addRow(self.temporal_window_label, self.temporal_window)

        return page

    # -- Scale tab (name, deviation, octave, table) --------------------

    def _build_scale_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        # Top form: name + deviation + octave
        top_form = QFormLayout()
        top_form.setContentsMargins(0, 0, 0, 0)
        self.scale_name = QLineEdit()
        self.scale_name.setToolTip(_("Scale name, only for your information."))
        top_form.addRow(_("Name"), self.scale_name)

        # Deviation (root frequency error)
        self.root_frequency_error = QSpinBox()
        self.root_frequency_error.setRange(-500, 500)
        self.root_frequency_error.setSingleStep(1)
        self.root_frequency_error.setSuffix(" cents")
        self.root_frequency_error.setToolTip(
            _("Applies a shift in frequency to all the notes defined in the table below.")
        )
        self.root_frequency_error.valueChanged.connect(self._deviation_changed)
        dev_row = QWidget()
        dev_layout = QHBoxLayout(dev_row)
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_layout.addWidget(self.root_frequency_error, 1)
        dev_layout.addWidget(QLabel(_("Octave")))
        self.octave_combo = QComboBox()
        self.octave_combo.setToolTip(
            _("Octave whose frequencies are being displayed in the table below. "
            "Change this parameter if you want to display the assigned frequencies "
            "in other octaves, but try to assign the frequencies always to the 4th "
            "octave (The 4th octave usually covers the frequencies from 261.63 Hz "
            "to 523.25 Hz).")
        )
        for octave in range(7):
            self.octave_combo.addItem(str(octave), octave)
        self.octave_combo.setCurrentIndex(4)
        self.octave_combo.currentIndexChanged.connect(self._octave_changed)
        dev_layout.addWidget(self.octave_combo)
        top_form.addRow(_("Deviation"), dev_row)

        root.addLayout(top_form)

        # Scale table (Name, Shift, Frequency)
        self.scale_table = QTableWidget(0, 3)
        self.scale_table.setHorizontalHeaderLabels([_("Name"), _("Shift"), _("Frequency [Hz]")])
        self.scale_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.scale_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.scale_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.scale_table.setMinimumHeight(260)
        self.scale_table.cellChanged.connect(self._scale_cell_changed)
        root.addWidget(self.scale_table)

        # Buttons: Insert / Delete / Import
        buttons = QHBoxLayout()
        self.scale_add_button = QPushButton(_("Insert"))
        self.scale_add_button.setToolTip(
            _("Adds a new note to the list, just above the selected line, or appends "
            "it to the end if no line is selected. Is not possible to add a note "
            "before the reference (the first) one.")
        )
        self.scale_remove_button = QPushButton(_("Delete"))
        self.scale_remove_button.setToolTip(
            _("Deletes the selected notes. The reference note, i.e., the first one, "
            "cannot be removed.")
        )
        self.scale_import_button = QPushButton(_("Import .scl"))
        self.scale_import_button.setToolTip(
            _("Imports the scale from an external .scl file, with the Scala project "
            "format (http://www.huygens-fokker.org/scala/)")
        )
        self.scale_add_button.clicked.connect(self._add_scale_row)
        self.scale_remove_button.clicked.connect(self._remove_scale_row)
        self.scale_import_button.clicked.connect(self._import_scl)
        buttons.addWidget(self.scale_add_button)
        buttons.addWidget(self.scale_remove_button)
        buttons.addWidget(self.scale_import_button)
        buttons.addStretch()
        root.addLayout(buttons)

        return page

    # ------------------------------------------------------------------
    # Value loading / saving
    # ------------------------------------------------------------------

    def _restore_ui_settings(self) -> None:
        if self.ui_settings is None:
            return
        if self.ui_settings.config_dialog_width > 0 and self.ui_settings.config_dialog_height > 0:
            self.resize(
                self.ui_settings.config_dialog_width,
                self.ui_settings.config_dialog_height,
            )

    def _load_values(
        self,
        values: ConfigValues,
        scale: Scale | None = None,
        audio_device: str | None = None,
    ) -> None:
        # -- Capture --
        system_index = self.audio_system.findData(values.audio_system_index)
        self.audio_system.setCurrentIndex(max(0, system_index))
        self._refresh_audio_devices()
        current_device = audio_device if audio_device is not None else self.audio_device.currentText()
        device_index = self.audio_device.findText(current_device)
        if device_index >= 0:
            self.audio_device.setCurrentIndex(device_index)
        else:
            self.audio_device.setEditText(current_device)

        # -- Adjustments --
        self.calculation_rate_slider.setValue(max(1, min(30, int(values.calculation_rate + 0.5))))
        self.noise_threshold_slider.setValue(max(0, min(40, int(values.min_overall_snr + 0.5))))

        # -- Settings --
        fft_index = self.fft_size.findData(values.fft_size)
        self.fft_size.setCurrentIndex(max(0, fft_index))
        self.temporal_window.setValue(values.temporal_window)
        self.optimize_parameters.setChecked(bool(values.optimize_internal_parameters))
        self._optimize_toggled()

        # -- Scale --
        if scale is not None:
            self._load_scale(scale)
        self.root_frequency_error.setValue(int(values.root_frequency_error + 0.5))
        self._populate_frequency_combos(scale)

    def _collect_values(self) -> ConfigValues:
        values = ConfigValues()
        values.audio_system_index = int(self.audio_system.currentData() or 0)
        values.fft_size = int(self.fft_size.currentData())
        values.temporal_window = self.temporal_window.value()
        values.min_overall_snr = float(self.noise_threshold_slider.value())
        values.calculation_rate = float(self.calculation_rate_slider.value())
        values.root_frequency_error = float(self.root_frequency_error.value())
        values.optimize_internal_parameters = int(self.optimize_parameters.isChecked())

        # Parse min/max frequency from the combo box text
        min_freq = self._parse_frequency(self.min_frequency_combo.currentText())
        max_freq = self._parse_frequency(self.max_frequency_combo.currentText())
        if min_freq > 0:
            values.min_frequency = min_freq
        if max_freq > 0:
            values.max_frequency = max_freq

        return values

    # ------------------------------------------------------------------
    # Audio device helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Scale helpers
    # ------------------------------------------------------------------

    def _load_scale(self, scale: Scale) -> None:
        self._block_scale_table_signals(True)
        self.scale_name.setText(scale.name)
        self.scale_table.setRowCount(0)
        for note in scale.notes:
            self._add_scale_row(note)
        self._update_scale_frequencies()
        self._block_scale_table_signals(False)

    def _add_scale_row(self, note: ScaleNote | None = None) -> None:
        self._block_scale_table_signals(True)
        row = self.scale_table.rowCount()
        self.scale_table.insertRow(row)
        if note is None:
            note = ScaleNote("?", min(row * 100.0, 1199.0), f"{min(row * 100.0, 1199.0):.6f}")
        self.scale_table.setItem(row, 0, QTableWidgetItem(note.name))
        self.scale_table.setItem(row, 1, QTableWidgetItem(note.shift or f"{note.cents:.6f}"))
        freq = self._compute_note_frequency(note.cents)
        self.scale_table.setItem(row, 2, QTableWidgetItem(f"{freq:.4f}"))
        self._block_scale_table_signals(False)

    def _remove_scale_row(self) -> None:
        row = self.scale_table.currentRow()
        if row <= 0:
            QMessageBox.warning(self, _("Scale"), _("The reference note cannot be removed."))
            return
        self.scale_table.removeRow(row)

    def _block_scale_table_signals(self, block: bool) -> None:
        self.scale_table.blockSignals(block)

    def _scale_cell_changed(self, row: int, column: int) -> None:
        """Recompute frequencies when a shift value is edited."""
        if column == 1:
            self._update_scale_frequencies()

    def _update_scale_frequencies(self) -> None:
        """Recompute the frequency column for all rows based on the base
        frequency and the shift values."""
        if self.scale_table.rowCount() == 0:
            return
        base_freq = self._get_base_frequency_from_table()
        for row in range(self.scale_table.rowCount()):
            shift_item = self.scale_table.item(row, 1)
            if shift_item is None:
                continue
            shift_text = shift_item.text().strip()
            cents = self._parse_shift_to_cents(shift_text)
            freq = base_freq * math.pow(2.0, cents / 1200.0)
            freq_item = self.scale_table.item(row, 2)
            if freq_item is None:
                freq_item = QTableWidgetItem()
                self.scale_table.setItem(row, 2, freq_item)
            freq_item.setText(f"{freq:.4f}")

    def _get_base_frequency_from_table(self) -> float:
        """Get the frequency of the first note as the base frequency."""
        freq_item = self.scale_table.item(0, 2)
        if freq_item is not None:
            try:
                return float(freq_item.text())
            except ValueError:
                pass
        return 261.625565  # mid-C fallback

    def _compute_note_frequency(self, cents: float) -> float:
        """Compute frequency for a note given its cents offset from the base."""
        base_freq = self._get_base_frequency_from_table()
        if self.scale_table.rowCount() <= 1:
            # First note: use the base frequency directly
            return base_freq
        return base_freq * math.pow(2.0, cents / 1200.0)

    @staticmethod
    def _parse_shift_to_cents(shift_text: str) -> float:
        """Parse a shift string (either 'N/M' ratio or decimal cents) to cents."""
        shift_text = shift_text.strip()
        if "/" in shift_text:
            parts = shift_text.split("/", 1)
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                if den > 0:
                    return 1200.0 * math.log2(num / den)
            except (ValueError, ZeroDivisionError):
                pass
        try:
            return float(shift_text)
        except ValueError:
            return 0.0

    # ------------------------------------------------------------------
    # Frequency combo helpers (for min/max frequency)
    # ------------------------------------------------------------------

    def _populate_frequency_combos(self, scale: Scale | None = None) -> None:
        """Populate the min/max frequency combo boxes with note names from the
        current scale across several octaves."""
        self.min_frequency_combo.blockSignals(True)
        self.max_frequency_combo.blockSignals(True)

        self.min_frequency_combo.clear()
        self.max_frequency_combo.clear()

        if scale is None:
            try:
                scale = self.context.scale()
            except LingotLibraryError:
                self.min_frequency_combo.blockSignals(False)
                self.max_frequency_combo.blockSignals(False)
                return

        for note_index in range(len(scale.notes)):
            for octave in range(
                _FREQUENCY_COMBO_FIRST_OCTAVE,
                _FREQUENCY_COMBO_FIRST_OCTAVE + _FREQUENCY_COMBO_N_OCTAVES,
            ):
                cents = scale.notes[note_index].cents
                freq = scale.base_frequency * math.pow(2.0, cents / 1200.0)
                # Apply octave offset (octave 4 is the base)
                freq *= math.pow(2.0, octave - 4)
                label = f"{scale.notes[note_index].name}{octave} <{freq:.2f}>"
                self.min_frequency_combo.addItem(label, freq)
                self.max_frequency_combo.addItem(label, freq)

        self.min_frequency_combo.blockSignals(False)
        self.max_frequency_combo.blockSignals(False)

    @staticmethod
    def _parse_frequency(text: str) -> float:
        """Extract a numeric frequency from text like 'C4 <261.63>' or plain '440'."""
        if not text:
            return -1.0
        # Try to extract from <...> markers
        if "<" in text and ">" in text:
            start = text.index("<") + 1
            end = text.index(">")
            text = text[start:end]
        try:
            value = float(text)
            if 0.0 < value < 20000.0:
                return value
        except ValueError:
            pass
        return -1.0

    # ------------------------------------------------------------------
    # Optimize toggle
    # ------------------------------------------------------------------

    def _optimize_toggled(self) -> None:
        enabled = not self.optimize_parameters.isChecked()
        self.fft_size_label.setEnabled(enabled)
        self.fft_size.setEnabled(enabled)
        self.temporal_window_label.setEnabled(enabled)
        self.temporal_window.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Deviation / octave change handlers
    # ------------------------------------------------------------------

    def _deviation_changed(self, _value: int) -> None:
        self._update_scale_frequencies()

    def _octave_changed(self, _index: int) -> None:
        self._update_scale_frequencies()

    # ------------------------------------------------------------------
    # Scale validation and collection
    # ------------------------------------------------------------------

    def _collect_scale(self) -> Scale:
        notes: list[ScaleNote] = []
        names: set[str] = set()
        last_cents = -1.0

        for row in range(self.scale_table.rowCount()):
            name_item = self.scale_table.item(row, 0)
            shift_item = self.scale_table.item(row, 1)
            name = name_item.text().strip() if name_item is not None else ""
            if not name or name == "?" or any(char in name for char in " \t\n{}"):
                raise LingotLibraryError(
                    "Scale note names must be non-empty and cannot contain "
                    "spaces or braces."
                )
            if name in names:
                raise LingotLibraryError("Scale note names must be unique.")
            names.add(name)

            shift = shift_item.text().strip() if shift_item is not None else ""
            if not shift:
                raise LingotLibraryError("Scale shifts must be non-empty.")

            cents = self._parse_shift_to_cents(shift)
            if (row == 0 and abs(cents) > 1e-10) or cents < last_cents or cents >= 1200.0:
                raise LingotLibraryError(
                    "Invalid scale shift values. Shifts must be between 0 and "
                    "1200 cents and must be ordered."
                )
            last_cents = cents
            notes.append(ScaleNote(name, cents, shift))

        if not notes:
            raise LingotLibraryError("The scale must contain at least one note.")

        # Base frequency is the frequency of the first note
        base_freq = self._get_base_frequency_from_table()

        return Scale(
            self.scale_name.text().strip() or "Untitled scale",
            base_freq,
            notes,
        )

    # ------------------------------------------------------------------
    # Import .scl
    # ------------------------------------------------------------------

    def _import_scl(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            _("Open Scale File"),
            "",
            _("Scala files (*.scl)"),
        )
        if not filename:
            return
        try:
            self.context.import_scl(filename)
            self._context_scale_changed_during_dialog = True
            scale = self.context.scale()
            self._load_scale(scale)
            self._populate_frequency_combos(scale)
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    # ------------------------------------------------------------------
    # Apply / Accept / Cancel / Defaults
    # ------------------------------------------------------------------

    def _apply(self) -> bool:
        if self.min_frequency_combo.currentText() and self.max_frequency_combo.currentText():
            min_freq = self._parse_frequency(self.min_frequency_combo.currentText())
            max_freq = self._parse_frequency(self.max_frequency_combo.currentText())
            if min_freq > 0 and max_freq > 0 and min_freq >= max_freq:
                QMessageBox.warning(
                    self,
                    _("Invalid Frequencies"),
                    _("Minimum frequency must be lower than maximum frequency."),
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
            # Refresh frequency combos with the newly applied scale
            self._populate_frequency_combos(self.context.scale())
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))
            return False
        return True

    def _restore_defaults(self) -> None:
        try:
            default_scale = self.context.default_scale()
            self._load_values(self.context.default_config_values(), default_scale, "")
            self._populate_frequency_combos(default_scale)
        except LingotLibraryError as exc:
            QMessageBox.warning(self, "Lingot", str(exc))

    def _accept(self) -> None:
        if self._apply():
            self.accept()

    def _reject(self) -> None:
        if self._context_scale_changed_during_dialog:
            try:
                self.context.set_scale_shifts(self.original_scale)
            except LingotLibraryError:
                pass
        super().reject()

    # ------------------------------------------------------------------
    # UI settings persistence
    # ------------------------------------------------------------------

    def _save_ui_settings(self) -> None:
        if self.ui_settings is not None:
            self.ui_settings.config_dialog_width = self.width()
            self.ui_settings.config_dialog_height = self.height()

    def done(self, result: int) -> None:
        self._save_ui_settings()
        super().done(result)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override name
        self._save_ui_settings()
        super().closeEvent(event)