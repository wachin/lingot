from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
from typing import Iterable


class LingotLibraryError(RuntimeError):
    pass


class Snapshot(ctypes.Structure):
    _fields_ = [
        ("running", ctypes.c_int),
        ("frequency", ctypes.c_double),
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
    ]


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
