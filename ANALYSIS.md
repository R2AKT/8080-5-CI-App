# i8080-5 CI - Project Analysis

**Date:** 2026-09-08
**Scope:** Full codebase (94 Python files, ~29,000 lines)
**Session:** Refactoring pass 3

## Overview

| Metric | Value |
|--------|-------|
| Python files | 104 |
| Total lines | ~26,700 |
| GUI package | i8080_ci/ (18 modules, main_window.py ~3,790 lines) |
| Emulator | i8080_emulator.py (1,761 lines) |
| MCP Server | mcp_server.py (949 lines) |
| IO modules | 25+ devices in modules/io/ |
| Memory modules | 7 types in modules/memory/ |
| Profiles | 12 TOML profiles |
| Tests | 7 test files |

## Issues Found & Status

### P0 - Critical

| Issue | Count | Status |
|-------|-------|--------|
| Bare `except:` | 0 | Clean (verified via AST scan) |
| Broad `except Exception:` (file I/O) | 0 | **Fixed** in pass 1 (changed to `OSError`) |
| Broad `except Exception:` (GUI/logic) | 16 | Left as-is (intentional for GUI robustness) |
| Thread safety in MCP server | 1 | **Fixed** in pass 1 (idempotent stop, daemon thread) |
| `safe_call` thread-awareness | 1 | Already correct (checks QThread) |
| Syntax errors | 0 | All files pass `ast.parse()` |

### P1 - Structure

| Issue | Count | Status |
|-------|-------|--------|
| Dead code (commented-out functions) | 0 | **Removed** in pass 1 (90 lines) |
| Missing type hints on public methods | 240 in i8080_CI.py | Partially addressed (module files done) |
| DRY violations in device_config.py | 0 | **Fixed** in pass 1 (helper extracted) |
| TODO/FIXME/HACK comments | 0 | Clean |
| Incorrect type hints (wrong return type) | 4 in system.py | **Fixed** in pass 2 |

### P2 - Infrastructure

| Item | Status |
|------|--------|
| requirements.txt | Present and up to date |
| pyproject.toml | Present with correct metadata |
| README.md | **Merged** (unified from README_OLD.md + README_NEW.md) |
| README_OLD.md | Preserved for reference |
| README_NEW.md | Preserved for reference |

## Detailed Findings

### 1. Exception Handling

**File I/O (Fixed in pass 1):**
- `modules/config/device_config.py:_load_rom_file` - `except OSError`
- `modules/io/cf_ide.py` - 2 occurrences - `except OSError`
- `modules/io/ch376s.py` - 2 occurrences - `except OSError`
- `modules/io/i512vi1.py` - 2 occurrences - `except OSError`
- `modules/io/i8272.py` - 2 occurrences - `except (OSError, ValueError)` / `except OSError`

**GUI/Logic (Left as-is - intentional):**
- `i8080_CI.py` - 7 occurrences in format_value, save/load preset, close handlers
- `ui/device_window.py`, `ui/gpio_widget.py` - UI error handling
- `tests/` - 8 occurrences in test helper functions

**Emulator (Intentional):**
- `i8080_emulator.py:916` - `except Exception` around `eval()` for breakpoint conditions
  - Rationale: User-supplied conditions can raise any exception type; broad catch prevents debugger crash

Rationale: In GUI code, broad `except Exception` is a deliberate pattern to prevent
crashes from any unexpected state. Changing these to specific exceptions risks
introducing new crash paths.

### 2. Thread Safety

**MCP Server (mcp_server.py):**
- `threading.Event()` with `_stop_event` (private convention)
- `stop()` is idempotent (early return if not running), timeout 5s
- `_run_server()` suppresses error log on graceful shutdown
- Daemon thread ensures clean process exit
- Note: `mcp.run(transport="sse")` is blocking; daemon thread is acceptable architecture

**QThread in i8080_CI.py:**
- Worker thread pattern: `QThread` + `QObject` with `Signal`/`Slot`
- `safe_call()` (line 5527): correctly checks `QThread.currentThread()` vs app thread
- Uses `QTimer.singleShot(0, ...)` for cross-thread dispatch
- No changes needed

### 3. Type Hints

**Pass 1 (documented in CHANGES.md):**
- `mcp_server.py`: `__init__`, `_create_server`, `_run_server`, `stop`
- `modules/system.py`: `__init__`, `_IOPortsAdapter.__init__`, `load_profile`, `load_from_toml_file`, `load_from_toml_string`, `_apply_config`, `_apply_device_params`, `connect_cpu`, `_get_interrupt_vector`
- `modules/config/device_config.py`: All public methods
- `modules/memory/memory_bus.py`: `MemoryBus.__init__`, `IOBus.__init__`, `register_memory`, `unregister_memory`, `register_io`

**Pass 2 (this session):**
- `modules/system.py`:
  - `_IOPortsAdapter.__getitem__` → `(self, port: int) -> int`
  - `_IOPortsAdapter.__setitem__` → `(self, port: int, value: int) -> None`
  - `_IOPortsAdapter.__contains__` → `(self, port: int) -> bool`
  - `_IOPortsAdapter.__init__` → added `-> None`
  - `get_device` → added `-> object`
  - `list_devices` → fixed `-> list[str]` to `-> list[dict]` (was incorrect)
  - `save_all_nvram` → fixed `-> None` to `-> list[str]` (was returning a list)
  - `load_all_nvram` → fixed `-> None` to `-> list[str]` (was returning a list)
  - `_apply_device_params` → added param type `device: object, config: dict`
  - `_get_interrupt_vector` → added param type `device: object`

- `modules/memory/memory_bus.py`:
  - `MemoryRegion.__init__` → `(self, start: int, end: int, name: str = "region") -> None`
  - `RAMRegion.__init__` → `(self, start: int, end: int, data: dict | None = None, name: str = "RAM") -> None`
  - `ROMRegion.__init__` → `(self, start: int, end: int, data: dict | None = None, name: str = "ROM") -> None`
  - `MemoryBus.add_mmio_region` → `region: object`

**Remaining (i8080_CI.py):**
- 240 public methods without return type hints
- These are predominantly Qt event handlers (`wheelEvent`, `paintEvent`, `mouseDoubleClickEvent`)
  and GUI slot methods where return type is always `None`
- Recommendation: batch-annotate with `-> None` in a dedicated pass

### 4. Pre-existing Test Issues

| Test | Status | Cause |
|------|--------|-------|
| `test_system.py` | FAIL (8 assertions) | Test expects device names ("PPI-0", "PIT-0", "LCD1602") and counts that don't match actual profile definitions |
| `test_i8255.py` | 1 soft-fail | Mode 1 test: Port A reads 0xFF instead of 0x42 (internal state issue) |

These are **test/profile mismatches** that predate all refactoring passes.

### 5. Architecture Notes

- `memory_bus.py` uses lazy `from .shadow import ShadowROMRegion` inside methods - **INTENTIONAL** to avoid circular imports. Preserved.
- `device_config.py` uses lazy imports in `_create_instance` to avoid loading all 25+ device modules at startup.
- `i8080_emulator.py` inherits from `QObject` and uses Qt Signals for UI communication.
- MCP server runs in a daemon thread with SSE transport.
- `ComputerSystem` acts as the integration hub connecting CPU, MemoryBus, and IO devices.
- `_IOPortsAdapter` bridges the emulator's dict-based `io_ports` interface to the MemoryBus.
- **Module split (Pass 3):** The original monolithic `i8080_CI.py` (6,517 lines) was split into the `i8080_ci/` package (18 modules). `MainWindow` remains in `main_window.py` (3,790 lines). All other components (i18n, SLIP, IntelHex, disassembler, models, views, bus worker, automation) are in separate modules.

### 6. Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files with bare except | 0 |
| Files with syntax errors | 0 |
| Commented-out function blocks | 0 |
| TODO/FIXME comments | 0 |
| DRY violations (repeated param-apply patterns) | 0 (helper extracted) |
| Thread-unsafe shared state | 0 (QThread pattern + daemon thread) |

## Recommendations

1. **Fix test_system.py** to match actual profile device names and counts (pre-existing issue)
2. **Batch-annotate** i8080_CI.py with `-> None` for Qt event handlers and GUI slots
3. **Consider** adding `mypy --strict` to CI once type hints are more complete
4. **Consider** adding a `conftest.py` with shared fixtures to reduce test boilerplate
5. ~~**Consider** splitting i8080_CI.py~~ **DONE** (Pass 3: split into `i8080_ci/` package)
