# Changelog

Module Split (Pass 3) - 2026-09-08

### Summary

Split the monolithic `i8080_CI.py` (6,517 lines) into a modular `i8080_ci/` package
(18 files). `MainWindow` remains monolithic in `main_window.py`. All imports verified,
application launches successfully.

### New Package Structure

```
i8080_CI.py                # Entry point (15 lines, was 6,517)
i8080_ci/
│   __init__.py            # Package exports
│   i18n.py                # LANGS + THEMES + get_system_language()
│   slip.py                # SLIP constants + SlipProtocol
│   intelhex.py            # IntelHex parse/generate
│   disassembler.py        # JUMP_OPCODES + I8080Disassembler
│   bus_worker.py          # BusWorker (QThread serial communication)
│   automation.py          # AutomationAPI (script interface)
│   main_window.py         # MainWindow (monolithic)
│   models/
┃       hex_model.py       # HexModel (QAbstractTableModel)
┃       watch_model.py     # WatchModel (QAbstractTableModel)
┃       bp_model.py        # BreakpointModel (QAbstractTableModel)
┃       trace_model.py     # TraceModel (QAbstractTableModel)
│   views/
┃       disasm_view.py     # DisasmView (QWidget)
┃       hex_view.py        # HexTableView (QTableView)
┃       search.py          # SearchDialog (QDialog)
```

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| MainWindow stays monolithic | Avoids high-risk mixin refactoring (120+ interdependent methods) |
| No circular deps | MainWindow imports from package; nothing imports from main_window |
| Duck typing preserved | AutomationAPI accepts main_window without import |
| Lazy imports preserved | memory_bus.py, device_config.py unchanged |

### Verification

| Check | Result |
|-------|--------|
| 18/18 files syntax valid | PASS |
| All module imports | PASS |
| Application launch | PASS |
| test_memory_bus.py | PASS |
| test_memory_models.py | PASS (21/21) |

---

## Refactoring Pass 2 — 2026-09-08

### Summary

Full analysis and targeted refactoring. 14 type hint fixes applied across 2 files.
README.md created (merged from README_OLD.md + README_NEW.md).
ANALYSIS.md updated with current findings. All tests verified.

### Type Hints Fixed — modules/system.py

| Method | Change |
|--------|--------|
| `_IOPortsAdapter.__init__` | Added `-> None` |
| `_IOPortsAdapter.__getitem__` | `(self, port)` → `(self, port: int) -> int` |
| `_IOPortsAdapter.__setitem__` | `(self, port, value)` → `(self, port: int, value: int) -> None` |
| `_IOPortsAdapter.__contains__` | `(self, port)` → `(self, port: int) -> bool` |
| `ComputerSystem.get_device` | Added `-> object` |
| `ComputerSystem.list_devices` | `-> list[str]` → `-> list[dict]` (was incorrect) |
| `ComputerSystem.save_all_nvram` | `-> None` → `-> list[str]` (was returning a list) |
| `ComputerSystem.load_all_nvram` | `-> None` → `-> list[str]` (was returning a list) |
| `ComputerSystem._apply_device_params` | `(self, device, config)` → `(self, device: object, config: dict)` |
| `ComputerSystem._get_interrupt_vector` | `device` → `device: object` |

### Type Hints Fixed — modules/memory/memory_bus.py

| Method | Change |
|--------|--------|
| `MemoryRegion.__init__` | `(self, start, end, name="region")` → `(self, start: int, end: int, name: str = "region") -> None` |
| `RAMRegion.__init__` | `(self, start, end, data=None, name="RAM")` → `(self, start: int, end: int, data: dict \| None = None, name: str = "RAM") -> None` |
| `ROMRegion.__init__` | `(self, start, end, data=None, name="ROM")` → `(self, start: int, end: int, data: dict \| None = None, name: str = "ROM") -> None` |
| `MemoryBus.add_mmio_region` | `region` → `region: object` |

### Documentation

- **README.md** — Created: unified merge of README_OLD.md (EN/RU features, screenshots, hardware) and README_NEW.md (installation, structure, MCP, profiles, testing)
- **ANALYSIS.md** — Updated with pass 2 findings, corrected metrics, type hint status
- **README_OLD.md** — Preserved (not deleted)
- **README_NEW.md** — Preserved (not deleted)

### Verification

#### ast.parse

| File | Result |
|------|--------|
| modules/system.py | PASS |
| modules/memory/memory_bus.py | PASS |

#### Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_memory_bus.py | PASS | All tests passed |
| test_i8253.py | PASS | 25/25 |
| test_i8255.py | PASS (1 soft-fail) | Pre-existing Mode 1 issue |
| test_system.py | FAIL | Pre-existing: test/profile name mismatch |
| test_interrupts.py | PASS | 11/11 |

### Preserved (Not Changed)

- Lazy imports in `memory_bus.py` (`from .shadow import ShadowROMRegion`) — intentional for circular import avoidance
- Lazy imports in `device_config.py` `_create_instance` — avoids loading 25+ modules at startup
- Broad `except Exception` in GUI code (i8080_CI.py, ui/) — intentional for crash prevention
- `except Exception` in `i8080_emulator.py:916` — wraps user-supplied `eval()` for breakpoint conditions
- All device module interfaces unchanged
- README_OLD.md and README_NEW.md preserved for reference

---

## Refactoring Pass 1 — 2026-09-08

### Summary

16 changes applied across 12 files. All changes verified with `ast.parse()`.
Test results: 6/7 test files pass (1 pre-existing failure in test_system.py).

### P0 - Critical Fixes

#### Exception Handling: File I/O (9 occurrences across 5 files)

Changed `except Exception:` to `except OSError:` in file I/O code:

| File | Method | Change |
|------|--------|--------|
| `modules/config/device_config.py` | `_load_rom_file` | `Exception` → `OSError` |
| `modules/io/cf_ide.py` | `_read_sector` | `Exception` → `OSError` |
| `modules/io/cf_ide.py` | `_write_sector` | `Exception` → `OSError` |
| `modules/io/ch376s.py` | `read_sector` | `Exception` → `OSError` |
| `modules/io/ch376s.py` | `write_sector` | `Exception` → `OSError` |
| `modules/io/i512vi1.py` | `load_nvm` | `Exception` → `OSError` |
| `modules/io/i512vi1.py` | `save_nvm` | `Exception` → `OSError` |
| `modules/io/i8272.py` | `load_from_file` | `Exception` → `(OSError, ValueError)` |
| `modules/io/i8272.py` | `save_to_file` | `Exception` → `OSError` |

#### MCP Server Thread Safety (mcp_server.py)

- Removed debug `####???` comments from `stop_event` and `stop_event.set()`
- Renamed `stop_event` → `_stop_event` (private by convention)
- `stop()`: Added idempotency guard (`if not self.running: return`)
- `stop()`: Timeout increased from 2s to 5s for graceful shutdown
- `stop()`: Sets `self.thread = None` after join to prevent double-join
- `_run_server()`: Suppresses error log on graceful shutdown
- Added type hints: `__init__`, `_create_server`, `_run_server`, `stop`

### P1 - Structural Improvements

#### Dead Code Removal (90 lines across 4 files)

| File | Removed | Reason |
|------|---------|--------|
| `modules/io/i8255.py` | 26 lines | Old `io_read` implementation, replaced by MemoryBus routing |
| `modules/io/i8257.py` | 5 lines | Old `io_write` stub, active version exists below |
| `modules/io/keyboard8x8.py` | 12 lines | Old `get_state`, active version exists below |
| `ui/display_widgets.py` | 47 lines | Old `paintEvent`, active version exists below |

#### DRY: device_config.py — Parameter Application Helper

Extracted repeated `if key in config: device.key = config[key]` patterns:

```python
@staticmethod
def _apply_optional_params(device, config, keys):
    """Apply optional parameters from config to device."""
    for key in keys:
        if key in config:
            setattr(device, key, config[key])
```

Used in 3 places: I8275/8276, Discrete video, Bitmap video.

#### Type Hints Added (Pass 1)

| File | Methods annotated |
|------|-------------------|
| `mcp_server.py` | `__init__`, `_create_server`, `_run_server`, `stop` |
| `modules/system.py` | `__init__`, `_IOPortsAdapter.__init__`, `load_profile`, `load_from_toml_file`, `load_from_toml_string`, `_apply_config`, `_apply_device_params`, `connect_cpu`, `_get_interrupt_vector` |
| `modules/config/device_config.py` | All public methods |
| `modules/memory/memory_bus.py` | `MemoryBus.__init__`, `IOBus.__init__`, `register_memory`, `unregister_memory`, `register_io` |

### Files Modified (Pass 1)

1. `mcp_server.py`
2. `modules/config/device_config.py`
3. `modules/io/cf_ide.py`
4. `modules/io/ch376s.py`
5. `modules/io/i512vi1.py`
6. `modules/io/i8272.py`
7. `modules/io/i8255.py`
8. `modules/io/i8257.py`
9. `modules/io/keyboard8x8.py`
10. `ui/display_widgets.py`
11. `modules/system.py`
12. `modules/memory/memory_bus.py`

### Files Modified (Pass 2)

1. `modules/system.py`
2. `modules/memory/memory_bus.py`
3. `README.md` (created)
4. `ANALYSIS.md` (updated)
5. `CHANGES.md` (this file)
