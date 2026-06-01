# PyQt6 Port Roadmap

## Best Porting Strategy

[x] Confirmed the current application architecture.

LINGOT is currently a C/autotools program with a GTK 3 + Glade user interface. The core tuner logic, audio backends, FFT, filters, configuration model, Scala scale support, and message queue already live mostly outside the GTK UI in `liblingot.la`.

[x] Chosen recommended migration path.

The safest PyQt6 port is to keep the existing C engine as the authoritative runtime at first, expose it through a small stable binding layer, and replace only the GTK executable with a Python/PyQt6 frontend. Rewriting the DSP, threading, audio backends, FFT behavior, config compatibility, and tests in Python all at once would create much higher regression risk.

Recommended shape:

- C library remains responsible for audio capture, pitch detection, FFT/SPL data, filters, scale math, config parsing/writing, and translated messages.
- Python/PyQt6 becomes responsible for application startup, windows, menus, timers, dialogs, drawing, settings persistence, and user interaction.
- A thin binding layer exposes a small C API suitable for Python `ctypes`, `cffi`, or a compiled extension.
- The old GTK executable stays buildable until the PyQt6 frontend reaches feature parity.

## Repository Findings

[x] Located entry point: `src/lingot.c`.

[x] Located reusable engine/library sources:

- `src/lingot-core.c`
- `src/lingot-audio.c`
- `src/lingot-audio-alsa.c`
- `src/lingot-audio-jack.c`
- `src/lingot-audio-oss.c`
- `src/lingot-audio-pulseaudio.c`
- `src/lingot-fft.c`
- `src/lingot-filter.c`
- `src/lingot-signal.c`
- `src/lingot-config.c`
- `src/lingot-config-scale.c`
- `src/lingot-msg.c`

[x] Located GTK-specific UI sources:

- `src/lingot-gui-mainframe.c`
- `src/lingot-gui-mainframe.glade`
- `src/lingot-gui-config-dialog.c`
- `src/lingot-gui-config-dialog.glade`
- `src/lingot-gui-config-dialog-scale.c`
- `src/lingot-gui-gauge.c`
- `src/lingot-gui-spectrum.c`
- `src/lingot-gui-strobe-disc.c`
- `src/lingot-gui-i18n.h`

[x] Located persistent data code:

- Main config: `src/lingot-io-config.c`
- UI settings: `src/lingot-io-ui-settings.c`
- Test configs: `test/resources/*.conf`

[x] Identified custom drawing surfaces to port to PyQt6 paint events:

- Gauge display
- Strobe disc display
- Spectrum display

[x] Identified timer-driven UI behavior to port to `QTimer`:

- Gauge sampling timer
- Visualization redraw timer
- Error/message dispatch timer

## Phase 1: Stabilize The C Engine Boundary

[x] Define a minimal GUI-facing C API that hides internal structs from Python.

Proposed API responsibilities:

- Initialize default paths and audio systems.
- Create/load/save/destroy configs.
- Create/destroy/restart tuner core.
- Start/stop core thread.
- Read current frequency.
- Read current SPL/spectrum data.
- Read closest note and cents error.
- Enumerate audio systems/devices/sample rates.
- Pop queued messages.

[x] Add a wrapper source pair, for example:

- `src/lingot-pyqt-api.h`
- `src/lingot-pyqt-api.c`

[x] Make the wrapper API memory-safe for Python callers.

Rules:

- Avoid exposing direct ownership of internal pointers unless lifetime is explicit.
- Prefer caller-provided buffers for arrays such as spectrum data.
- Return simple status codes.
- Provide destroy/free functions for anything allocated by C.

[x] Add build output for a shared library loadable from Python.

Options:

- Keep autotools and install/load `liblingot.so`.
- Add a small CMake or Meson side build only for the Python frontend.
- Keep `libtool` output and document `LD_LIBRARY_PATH` for development.

[ ] Add C tests for the new wrapper API before wiring PyQt6 to it.

## Phase 2: Create The PyQt6 Application Skeleton

[x] Add a Python package, for example:

- `pyqt6_lingot/`
- `pyqt6_lingot/__main__.py`
- `pyqt6_lingot/app.py`
- `pyqt6_lingot/bindings.py`
- `pyqt6_lingot/main_window.py`
- `pyqt6_lingot/config_dialog.py`
- `pyqt6_lingot/widgets/gauge.py`
- `pyqt6_lingot/widgets/spectrum.py`
- `pyqt6_lingot/widgets/strobe_disc.py`

[x] Choose binding technology.

Recommended first choice: `ctypes`.

Reason: the required API can be small and C-shaped, avoiding a heavier compiled Python extension while the port is still moving. If the API grows complex, switch to `cffi` or a proper extension later.

[x] Add dependency metadata.

Candidate files:

- `pyproject.toml`
- `requirements.txt`

Minimum Python dependencies:

- `PyQt6`

Likely development dependencies:

- `pytest`

[x] Implement command-line compatibility.

Required behavior:

- Preserve `lingot [-c config]`.
- Preserve default config path `~/.config/lingot/lingot.conf`.
- Preserve alternate config path `~/.config/lingot/{config}.conf`.
- Create default config when missing.

## Phase 3: Port The Main Window

[x] Add an initial PyQt6 main window based on `src/lingot-gui-mainframe.glade`.

PyQt6 widgets:

- `QMainWindow`
- `QMenuBar`
- `QSplitter`
- `QFrame`
- `QLabel`
- custom `QWidget` drawing areas

[x] Port the main menu shell.

[x] Wire Open Configuration and Save Configuration to the C config loader/saver.

Required menus/actions:

- File -> Open Configuration
- File -> Save Configuration
- File -> Quit
- Edit -> Preferences
- View -> Gauge
- View -> Strobe Disc
- View -> Spectrum
- Help -> About

[x] Port persisted UI settings.

The first PyQt6 version can either:

- Reuse `src/lingot-io-ui-settings.c` through the wrapper API.
- Or use `QSettings` while preserving values where practical.

Implemented: reuse the existing settings file through the wrapper API to avoid behavior drift.

[x] Persist PyQt6 preferences dialog size through the existing UI settings file.

[x] Port runtime timers with `QTimer`.

Required timers:

- Error dispatch
- Gauge sampling
- Visualization redraw

[x] Preserve core lifecycle.

Required behavior:

- Start core after window creation.
- Stop/destroy core on close.
- Restart core after applying config changes.

[x] Add status-bar feedback for engine state, active configuration, and user actions.

## Phase 4: Port Custom Visual Widgets

[x] Port gauge drawing from Cairo/GTK to `QPainter`.

Source reference: `src/lingot-gui-gauge.c`.

[x] Port spectrum drawing from Cairo/GTK to `QPainter`.

Source reference: `src/lingot-gui-spectrum.c`.

[x] Add current-frequency and target-frequency markers to the PyQt6 spectrum.

[x] Port strobe disc drawing from Cairo/GTK to `QPainter`.

Source reference: `src/lingot-gui-strobe-disc.c`.

[ ] Keep rendering math close to the C implementation.

This reduces visual regressions and keeps user-facing behavior familiar.

[x] Add visual smoke tests.

Implemented in `pyqt6_lingot/test/test_widgets.py` (14 tests):
- GaugeWidget: paint default, positive/negative error, NaN error, custom range
- SpectrumWidget: paint empty, with samples, with target frequency, custom scale
- StrobeDiscWidget: paint default, zero/positive/negative error, multiple ticks

## Phase 5: Port The Configuration Dialog

[x] Add an initial functional preferences dialog for core tuner parameters.

[x] Recreate the full dialog layout from `src/lingot-gui-config-dialog.glade`.

PyQt6 widgets:

- `QDialog`
- `QTabWidget`
- `QComboBox`
- `QSlider`
- `QDoubleSpinBox`
- `QSpinBox`
- `QCheckBox`
- `QTableView`
- `QDialogButtonBox`

[x] Port input tab.

Required behavior:

- Audio system selection. [x]
- Audio device selection. [x]
- Device list refresh when audio system changes. [x]

[x] Port performance/algorithm settings.

Implemented with sliders (GtkScale-style) for calculation rate and noise threshold,
matching the GTK Adjustments tab layout.

Required behavior:

- Noise threshold. [x]
- Calculation rate. [x]
- Temporal window. [x]
- FFT size. [x]
- Minimum/maximum frequency. [x]
- Optimize internal parameters toggle. [x]

[x] Port scale editor.

Required behavior:

- Scale name. [x]
- Base/root frequency behavior. [x]
- Note names. [x]
- Cents shifts. [x]
- Ratio shift formatting/parsing. [x]
- Add/delete notes. [x]
- Import Scala `.scl` files. [x]
- Octave selector (0-6). [x]
- Deviation (root frequency error) in scale tab. [x]
- Frequency column in scale table. [x]

[x] Preserve validation behavior.

Required behavior:

- Reject invalid min/max frequency. [x]
- Reject invalid or incomplete scale data. [x]
- Apply defaults. [x]
- Apply without closing. [x]
- OK applies and closes. [x]
- Cancel closes without changing the running core. [x]

## Phase 6: Internationalization

[x] Decide how translations are handled in the PyQt6 frontend.

Implemented: Python gettext, reusing existing `.po` files from the repository.

[x] Port user-visible GTK strings to Python gettext calls.

Added `pyqt6_lingot/i18n.py` for gettext initialization. Wrapped user-visible strings
in `main_window.py`, `config_dialog.py`, and `app.py` with `_()` calls. Added Python
source files to `po/POTFILES.in`.

[x] Keep existing `.po` files intact during the first PyQt6 milestone.

## Phase 7: Packaging And Desktop Integration

[x] Add a runnable development entry point.

Examples:

- `python -m pyqt6_lingot`
- `lingot-pyqt6`

[x] Update install rules without removing the GTK executable immediately.

Recommended transition:

- Build old `lingot` GTK app as before. [x]
- Add new `lingot-pyqt6` executable. [x]
- Rename/switch default only after parity testing.

[x] Add manual page for the experimental `lingot-pyqt6` executable.

[x] Reuse existing app metadata and icon.

Files:

- `icons/org.nongnu.lingot.svg` [x]
- `org.nongnu.lingot.desktop` [x]
- `org.lingot.lingot.desktop` [x]
- `org.nongnu.lingot.appdata.xml` [x]
- `org.lingot.lingot.appdata.xml` [x]

[x] Document development setup.

Include:

- System packages for audio backends and `liblingot`.
- Python virtual environment setup.
- PyQt6 install.
- How to point Python at the local shared library.

## Phase 8: Test And Parity Matrix

[ ] Keep existing C tests passing.

Current test areas:

- Config scale
- Core
- Filter
- IO config
- Signal

[x] Add Python tests for config-path behavior.

Tests cover config load/save, default config creation, and alternate config
path (`-c name`) behavior through the bindings layer.

[x] Add Python tests for binding calls.

Comprehensive test suite in `pyqt6_lingot/test/test_bindings.py` (32 tests) covering:
- Pure-Python tests for Snapshot, ScaleNote, Scale, ConfigValues, UiSettings
- C library tests for initialization, config values, context lifecycle, scale
  reading/writing, snapshot/spectrum, message queue, and config file compatibility
- Tests skip gracefully when liblingot.so is not available

[x] Add GUI smoke tests where practical.

Implemented in `pyqt6_lingot/test/test_widgets.py` (27+ tests) covering:
- Widget rendering: GaugeWidget, SpectrumWidget, StrobeDiscWidget offscreen paint
- MainWindow: construction, menus, gauge/strobe toggle, spectrum toggle, status bar
- ConfigDialog: construction, all 4 tabs, tab widgets (audio, sliders, FFT, scale table)
- Tests require liblingot.so are skipped gracefully

[ ] Manually verify audio backends.

Backend matrix:

- ALSA
- JACK
- PulseAudio
- OSS, if still supported on the target system

[ ] Manually verify workflows.

Workflow matrix:

- First run creates config.
- `-c bass` loads `~/.config/lingot/bass.conf`.
- Open config.
- Save config.
- Preferences apply/restart core.
- Gauge/strobe toggle.
- Spectrum show/hide.
- About dialog.
- Close saves UI settings.

## Suggested Milestones

[x] Milestone 1: PyQt6 main window launches with menus and empty custom widgets.

[x] Milestone 2: Python can load the C library and start/stop the tuner core.

[x] Milestone 3: Main window shows live frequency, note, cents error, and spectrum data.

[x] Milestone 4: Gauge, strobe disc, and spectrum reach visual parity.

[x] Milestone 5: Configuration dialog reaches functional parity.

[x] Milestone 6: Existing config files and UI settings remain compatible.

Verified with 7 config compatibility tests in `pyqt6_lingot/test/test_bindings.py`:
- Loads all 4 legacy config files (0.01, 0.9.2b8, 1.0.2b, 1.1.0) through the Python bindings
- Verifies FFT size, scale notes, and base frequency are valid after loading
- Tests load → start → snapshot → stop lifecycle with a legacy config
- Tests save/load round-trip for configs (gracefully handles legacy configs that can't be saved)
- Tests that default config values are valid

[ ] Milestone 7: Packaging supports both GTK and PyQt6 frontends.

[ ] Milestone 8: PyQt6 frontend becomes the default executable after parity approval.

## Risks

[ ] Python binding lifetime bugs.

Mitigation: keep wrapper API small, avoid exposing internal pointers, and test create/start/stop/destroy loops.

[ ] Audio thread and Qt event loop interactions.

Mitigation: keep audio and DSP threads in C, poll stable snapshots from Qt timers, and avoid calling UI code from C callbacks.

[ ] Visual regressions in custom drawings.

Mitigation: port drawing math directly and add smoke screenshots/tests.

[ ] Configuration compatibility regressions.

Mitigation: reuse existing C config load/save initially and test all files in `test/resources/`.

[ ] Scope creep into a full Python engine rewrite.

Mitigation: defer pure-Python DSP/audio until the PyQt6 frontend is already proven.

## Immediate Next Steps

[x] Add `src/lingot-pyqt-api.h` and `src/lingot-pyqt-api.c`.

[x] Expose only enough API to create config, start core, stop core, read frequency, read SPL data, and pop messages.

[x] Add a minimal `pyqt6_lingot` package with a `QMainWindow`.

[x] Draw placeholder gauge/spectrum widgets.

[x] Connect Qt timers to the wrapper API.

[x] Verify the frontend can launch, close, and cleanly stop the C core.

Verified: 46 tests pass (32 bindings + 14 widget smoke tests) including
context create/start/stop/destroy cycles, config load/save, scale read/write,
snapshot retrieval, legacy config loading, and widget rendering.
