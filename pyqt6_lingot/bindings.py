from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable


class LingotLibraryError(RuntimeError):
    pass


class Snapshot(ctypes.Structure):
    _fields_ = [
        ("running", ctypes.c_int),
        ("frequency", ctypes.c_double),
        ("target_frequency", ctypes.c_double),
        ("error_cents", ctypes.c_double),
        ("closest_note_index", ctypes.c_int),
        ("closest_note_name", ctypes.c_char_p),
        ("spectrum_size", ctypes.c_uint),
    ]

    @property
    def note_name(self) -> str:
        if not self.closest_note_name:
            return ""
        return self.closest_note_name.decode("utf-8", errors="replace")

    @property
    def has_pitch(self) -> bool:
        return self.closest_note_index >= 0 and not math.isnan(self.error_cents)


class ConfigValues(ctypes.Structure):
    _fields_ = [
        ("audio_system_index", ctypes.c_int),
        ("fft_size", ctypes.c_uint),
        ("temporal_window", ctypes.c_double),
        ("min_overall_snr", ctypes.c_double),
        ("calculation_rate", ctypes.c_double),
        ("min_frequency", ctypes.c_double),
        ("max_frequency", ctypes.c_double),
        ("root_frequency_error", ctypes.c_double),
        ("optimize_internal_parameters", ctypes.c_int),
        ("sample_rate", ctypes.c_int),
        ("oversampling", ctypes.c_uint),
        ("gauge_range", ctypes.c_double),
    ]


class UiSettings(ctypes.Structure):
    _fields_ = [
        ("spectrum_visible", ctypes.c_int),
        ("gauge_visible", ctypes.c_int),
        ("win_width", ctypes.c_int),
        ("win_height", ctypes.c_int),
        ("config_dialog_width", ctypes.c_int),
        ("config_dialog_height", ctypes.c_int),
        ("horizontal_paned_pos", ctypes.c_int),
        ("vertical_paned_pos", ctypes.c_int),
        ("visualization_rate", ctypes.c_double),
        ("error_dispatch_rate", ctypes.c_double),
        ("gauge_sampling_rate", ctypes.c_double),
    ]


@dataclass
class ScaleNote:
    name: str
    cents: float
    shift: str = ""


@dataclass
class Scale:
    name: str
    base_frequency: float
    notes: list[ScaleNote]


def _candidate_libraries() -> Iterable[Path | str]:
    env_path = os.environ.get("LINGOT_LIBRARY_PATH")
    if env_path:
        yield env_path

    repo_root = Path(__file__).resolve().parent.parent
    yield repo_root / ".libs" / "liblingot.so"
    yield repo_root / "liblingot.so"
    yield "liblingot.so"


def _load_library() -> ctypes.CDLL:
    errors: list[str] = []
    for candidate in _candidate_libraries():
        try:
            return ctypes.CDLL(str(candidate))
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")
    details = "\n".join(errors)
    raise LingotLibraryError(f"Could not load liblingot.so.\n{details}")


class LingotBindings:
    def __init__(self) -> None:
        self.lib = _load_library()
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        self.lib.lingot_pyqt_initialize.argtypes = [ctypes.c_char_p]
        self.lib.lingot_pyqt_initialize.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_new.argtypes = []
        self.lib.lingot_pyqt_context_new.restype = ctypes.c_void_p

        self.lib.lingot_pyqt_context_destroy.argtypes = [ctypes.c_void_p]
        self.lib.lingot_pyqt_context_destroy.restype = None

        self.lib.lingot_pyqt_context_load_config.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
        ]
        self.lib.lingot_pyqt_context_load_config.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_save_config.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
        ]
        self.lib.lingot_pyqt_context_save_config.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_get_config_values.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ConfigValues),
        ]
        self.lib.lingot_pyqt_context_get_config_values.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_set_config_values.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ConfigValues),
        ]
        self.lib.lingot_pyqt_context_set_config_values.restype = ctypes.c_int

        self.lib.lingot_pyqt_get_default_config_values.argtypes = [
            ctypes.POINTER(ConfigValues),
        ]
        self.lib.lingot_pyqt_get_default_config_values.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_get_audio_device.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        self.lib.lingot_pyqt_context_get_audio_device.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_set_audio_device.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
        ]
        self.lib.lingot_pyqt_context_set_audio_device.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_get_scale_info.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_uint),
        ]
        self.lib.lingot_pyqt_context_get_scale_info.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_get_scale_note.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_double),
        ]
        self.lib.lingot_pyqt_context_get_scale_note.restype = ctypes.c_int

        self.lib.lingot_pyqt_get_default_scale_info.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_uint),
        ]
        self.lib.lingot_pyqt_get_default_scale_info.restype = ctypes.c_int

        self.lib.lingot_pyqt_get_default_scale_note.argtypes = [
            ctypes.c_uint,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_double),
        ]
        self.lib.lingot_pyqt_get_default_scale_note.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_set_scale.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_double,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_double),
        ]
        self.lib.lingot_pyqt_context_set_scale.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_set_scale_shifts.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_double,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
        ]
        self.lib.lingot_pyqt_context_set_scale_shifts.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_import_scl.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
        ]
        self.lib.lingot_pyqt_context_import_scl.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_start.argtypes = [ctypes.c_void_p]
        self.lib.lingot_pyqt_context_start.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_stop.argtypes = [ctypes.c_void_p]
        self.lib.lingot_pyqt_context_stop.restype = None

        self.lib.lingot_pyqt_context_restart.argtypes = [ctypes.c_void_p]
        self.lib.lingot_pyqt_context_restart.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_get_snapshot.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(Snapshot),
        ]
        self.lib.lingot_pyqt_context_get_snapshot.restype = ctypes.c_int

        self.lib.lingot_pyqt_context_copy_spectrum.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_uint,
        ]
        self.lib.lingot_pyqt_context_copy_spectrum.restype = ctypes.c_uint

        self.lib.lingot_pyqt_pop_message.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.lingot_pyqt_pop_message.restype = ctypes.c_int

        self.lib.lingot_pyqt_get_ui_settings.argtypes = [ctypes.POINTER(UiSettings)]
        self.lib.lingot_pyqt_get_ui_settings.restype = ctypes.c_int

        self.lib.lingot_pyqt_set_ui_settings.argtypes = [ctypes.POINTER(UiSettings)]
        self.lib.lingot_pyqt_set_ui_settings.restype = ctypes.c_int

        self.lib.lingot_pyqt_save_ui_settings.argtypes = []
        self.lib.lingot_pyqt_save_ui_settings.restype = None

        self.lib.lingot_pyqt_audio_system_count.argtypes = []
        self.lib.lingot_pyqt_audio_system_count.restype = ctypes.c_int

        self.lib.lingot_pyqt_audio_system_name.argtypes = [ctypes.c_int]
        self.lib.lingot_pyqt_audio_system_name.restype = ctypes.c_char_p

        self.lib.lingot_pyqt_audio_system_device_count.argtypes = [ctypes.c_int]
        self.lib.lingot_pyqt_audio_system_device_count.restype = ctypes.c_int

        self.lib.lingot_pyqt_audio_system_device_name.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        self.lib.lingot_pyqt_audio_system_device_name.restype = ctypes.c_int

        self.lib.lingot_pyqt_config_filename.argtypes = []
        self.lib.lingot_pyqt_config_filename.restype = ctypes.c_char_p

    def initialize(self, config_name: str | None = None) -> None:
        raw = config_name.encode("utf-8") if config_name else None
        if self.lib.lingot_pyqt_initialize(raw) != 0:
            raise LingotLibraryError("Lingot initialization failed")

    def config_filename(self) -> str:
        raw = self.lib.lingot_pyqt_config_filename()
        return raw.decode("utf-8", errors="replace") if raw else ""

    def ui_settings(self) -> UiSettings:
        settings = UiSettings()
        if self.lib.lingot_pyqt_get_ui_settings(ctypes.byref(settings)) != 0:
            raise LingotLibraryError("Could not read UI settings")
        return settings

    def set_ui_settings(self, settings: UiSettings) -> None:
        if self.lib.lingot_pyqt_set_ui_settings(ctypes.byref(settings)) != 0:
            raise LingotLibraryError("Could not update UI settings")

    def save_ui_settings(self) -> None:
        self.lib.lingot_pyqt_save_ui_settings()

    def audio_systems(self) -> list[tuple[int, str]]:
        systems: list[tuple[int, str]] = []
        for index in range(max(0, self.lib.lingot_pyqt_audio_system_count())):
            raw = self.lib.lingot_pyqt_audio_system_name(index)
            if raw:
                systems.append((index, raw.decode("utf-8", errors="replace")))
        return systems

    def audio_devices(self, audio_system_index: int) -> list[str]:
        devices: list[str] = []
        count = max(0, self.lib.lingot_pyqt_audio_system_device_count(audio_system_index))
        for index in range(count):
            text = ctypes.create_string_buffer(512)
            result = self.lib.lingot_pyqt_audio_system_device_name(
                audio_system_index, index, text, len(text)
            )
            if result == 0:
                devices.append(text.value.decode("utf-8", errors="replace"))
        return devices

    def default_config_values(self) -> ConfigValues:
        values = ConfigValues()
        if self.lib.lingot_pyqt_get_default_config_values(ctypes.byref(values)) != 0:
            raise LingotLibraryError("Could not read default configuration values")
        return values

    def default_scale(self) -> Scale:
        name_buffer = ctypes.create_string_buffer(512)
        base_frequency = ctypes.c_double()
        notes_count = ctypes.c_uint()
        result = self.lib.lingot_pyqt_get_default_scale_info(
            name_buffer,
            len(name_buffer),
            ctypes.byref(base_frequency),
            ctypes.byref(notes_count),
        )
        if result != 0:
            raise LingotLibraryError("Could not read default scale")

        notes: list[ScaleNote] = []
        for index in range(notes_count.value):
            note_buffer = ctypes.create_string_buffer(128)
            shift_buffer = ctypes.create_string_buffer(128)
            cents = ctypes.c_double()
            result = self.lib.lingot_pyqt_get_default_scale_note(
                index,
                note_buffer,
                len(note_buffer),
                shift_buffer,
                len(shift_buffer),
                ctypes.byref(cents),
            )
            if result != 0:
                raise LingotLibraryError("Could not read default scale note")
            notes.append(
                ScaleNote(
                    note_buffer.value.decode("utf-8", errors="replace"),
                    cents.value,
                    shift_buffer.value.decode("utf-8", errors="replace"),
                )
            )
        return Scale(
            name_buffer.value.decode("utf-8", errors="replace"),
            base_frequency.value,
            notes,
        )


class LingotContext:
    def __init__(self, bindings: LingotBindings) -> None:
        self.bindings = bindings
        self._ptr = bindings.lib.lingot_pyqt_context_new()
        if not self._ptr:
            raise LingotLibraryError("Could not create Lingot context")

    def start(self) -> None:
        self.bindings.lib.lingot_pyqt_context_start(self._ptr)

    def stop(self) -> None:
        if self._ptr:
            self.bindings.lib.lingot_pyqt_context_stop(self._ptr)

    def restart(self) -> None:
        if self._ptr and self.bindings.lib.lingot_pyqt_context_restart(self._ptr) != 0:
            raise LingotLibraryError("Could not restart Lingot core")

    def close(self) -> None:
        if self._ptr:
            self.bindings.lib.lingot_pyqt_context_destroy(self._ptr)
            self._ptr = None

    def snapshot(self) -> Snapshot:
        snapshot = Snapshot()
        if self._ptr:
            self.bindings.lib.lingot_pyqt_context_get_snapshot(
                self._ptr, ctypes.byref(snapshot)
            )
        return snapshot

    def spectrum(self, size: int) -> list[float]:
        if not self._ptr or size <= 0:
            return []
        buffer = (ctypes.c_double * size)()
        copied = self.bindings.lib.lingot_pyqt_context_copy_spectrum(
            self._ptr, buffer, size
        )
        return [buffer[index] for index in range(copied)]

    def load_config(self, filename: str) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_load_config(
            self._ptr, filename.encode("utf-8")
        )
        if result != 0:
            raise LingotLibraryError(f"Could not load configuration: {filename}")

    def save_config(self, filename: str) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_save_config(
            self._ptr, filename.encode("utf-8")
        )
        if result != 0:
            raise LingotLibraryError(f"Could not save configuration: {filename}")

    def config_values(self) -> ConfigValues:
        values = ConfigValues()
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_get_config_values(
            self._ptr, ctypes.byref(values)
        )
        if result != 0:
            raise LingotLibraryError("Could not read configuration values")
        return values

    def set_config_values(self, values: ConfigValues) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_set_config_values(
            self._ptr, ctypes.byref(values)
        )
        if result != 0:
            raise LingotLibraryError("Configuration values are invalid")

    def audio_systems(self) -> list[tuple[int, str]]:
        return self.bindings.audio_systems()

    def audio_devices(self, audio_system_index: int) -> list[str]:
        return self.bindings.audio_devices(audio_system_index)

    def default_config_values(self) -> ConfigValues:
        return self.bindings.default_config_values()

    def default_scale(self) -> Scale:
        return self.bindings.default_scale()

    def audio_device(self) -> str:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        text = ctypes.create_string_buffer(512)
        result = self.bindings.lib.lingot_pyqt_context_get_audio_device(
            self._ptr, text, len(text)
        )
        if result != 0:
            return ""
        return text.value.decode("utf-8", errors="replace")

    def set_audio_device(self, device: str) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_set_audio_device(
            self._ptr, device.encode("utf-8")
        )
        if result != 0:
            raise LingotLibraryError("Audio device is invalid")

    def scale(self) -> Scale:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")

        name_buffer = ctypes.create_string_buffer(512)
        base_frequency = ctypes.c_double()
        notes_count = ctypes.c_uint()
        result = self.bindings.lib.lingot_pyqt_context_get_scale_info(
            self._ptr,
            name_buffer,
            len(name_buffer),
            ctypes.byref(base_frequency),
            ctypes.byref(notes_count),
        )
        if result != 0:
            raise LingotLibraryError("Could not read scale")

        notes: list[ScaleNote] = []
        for index in range(notes_count.value):
            note_buffer = ctypes.create_string_buffer(128)
            shift_buffer = ctypes.create_string_buffer(128)
            cents = ctypes.c_double()
            result = self.bindings.lib.lingot_pyqt_context_get_scale_note(
                self._ptr,
                index,
                note_buffer,
                len(note_buffer),
                shift_buffer,
                len(shift_buffer),
                ctypes.byref(cents),
            )
            if result != 0:
                raise LingotLibraryError("Could not read scale note")
            notes.append(
                ScaleNote(
                    note_buffer.value.decode("utf-8", errors="replace"),
                    cents.value,
                    shift_buffer.value.decode("utf-8", errors="replace"),
                )
            )

        return Scale(
            name_buffer.value.decode("utf-8", errors="replace"),
            base_frequency.value,
            notes,
        )

    def set_scale(self, scale: Scale) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        encoded_names = [note.name.encode("utf-8") for note in scale.notes]
        names_array = (ctypes.c_char_p * len(encoded_names))(*encoded_names)
        cents_array = (ctypes.c_double * len(scale.notes))(
            *[note.cents for note in scale.notes]
        )
        result = self.bindings.lib.lingot_pyqt_context_set_scale(
            self._ptr,
            scale.name.encode("utf-8"),
            scale.base_frequency,
            len(scale.notes),
            names_array,
            cents_array,
        )
        if result != 0:
            raise LingotLibraryError("Scale values are invalid")

    def set_scale_shifts(self, scale: Scale) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        encoded_names = [note.name.encode("utf-8") for note in scale.notes]
        encoded_shifts = [
            (note.shift or f"{note.cents:.6f}").encode("utf-8")
            for note in scale.notes
        ]
        names_array = (ctypes.c_char_p * len(encoded_names))(*encoded_names)
        shifts_array = (ctypes.c_char_p * len(encoded_shifts))(*encoded_shifts)
        result = self.bindings.lib.lingot_pyqt_context_set_scale_shifts(
            self._ptr,
            scale.name.encode("utf-8"),
            scale.base_frequency,
            len(scale.notes),
            names_array,
            shifts_array,
        )
        if result != 0:
            raise LingotLibraryError("Scale values are invalid")

    def import_scl(self, filename: str) -> None:
        if not self._ptr:
            raise LingotLibraryError("Lingot context is closed")
        result = self.bindings.lib.lingot_pyqt_context_import_scl(
            self._ptr, filename.encode("utf-8")
        )
        if result != 0:
            raise LingotLibraryError(f"Could not import Scala scale: {filename}")

    def pop_message(self) -> tuple[int, int, str] | None:
        text = ctypes.create_string_buffer(1001)
        msg_type = ctypes.c_int()
        error_code = ctypes.c_int()
        result = self.bindings.lib.lingot_pyqt_pop_message(
            text, len(text), ctypes.byref(msg_type), ctypes.byref(error_code)
        )
        if not result:
            return None
        return (
            msg_type.value,
            error_code.value,
            text.value.decode("utf-8", errors="replace"),
        )
