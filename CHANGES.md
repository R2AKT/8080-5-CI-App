# Changelog / Журнал изменений

---

## Pass 6 — Tooling: Snapshot Builder + md2html CLI / Инструменты: генератор среза + CLI для md2html

**Date / Дата:** 2026-09-16

### Summary / Обзор

**EN:** Created `build_snapshot.py` — an automated project snapshot generator that traverses the entire project tree, classifies files, performs AST analysis, and produces a 10-section `PROJECT_SNAPSHOT.md` without any hardcoded file names. Updated `md2html.py` to accept command-line arguments (`input.md [output.html]`) instead of hardcoded paths. Created `analyze_project.py` for quick project health checks (syntax, imports, TODOs, consistency).

**RU:** Создан `build_snapshot.py` — автоматический генератор среза проекта, обходящий всё дерево, классифицирующий файлы, выполняющий AST-анализ и создающий 10-секционный `PROJECT_SNAPSHOT.md` без захардкоженных имён файлов. Обновлён `md2html.py` — теперь принимает аргументы командной строки (`input.md [output.html]`) вместо захардкоженных путей. Создан `analyze_project.py` для быстрой проверки здоровья проекта (синтаксис, импорты, TODO, консистентность).

### Changes / Изменения

#### 1. build_snapshot.py (new) / build_snapshot.py (новый)

**EN:** 736-line Python script that generates `PROJECT_SNAPSHOT.md` by:
- Walking the project tree (`os.walk`), skipping `__pycache__`, `.git`, `venv`
- Classifying files by extension and name patterns (code, tests, profiles, docs, HTML, config, assets)
- Running AST analysis on every `.py` file (classes, methods, docstrings, imports, constants)
- Extracting main window info (tabs via `create_tab_*`, shortcuts via `QShortcut`, menus via `addMenu`)
- Extracting dict constants (PORT_COUNTS, JUMP_OPCODES, LANGS) for appendices
- Producing 10 sections: tree, module descriptions, full code, refactoring changes, tests, profiles, main window, iterations, known issues, appendices

**RU:** Скрипт на 736 строк, генерирующий `PROJECT_SNAPSHOT.md`:
- Обход дерева проекта (`os.walk`), пропуск `__pycache__`, `.git`, `venv`
- Классификация файлов по расширению и паттернам имени (код, тесты, профили, доки, HTML, конфиги, ресурсы)
- AST-анализ каждого `.py` (классы, методы, docstring, импорты, константы)
- Извлечение информации о главном окне (вкладки через `create_tab_*`, хоткеи через `QShortcut`, меню через `addMenu`)
- Извлечение словарных констант (PORT_COUNTS, JUMP_OPCODES, LANGS) для приложений
- 10 разделов: дерево, описание модулей, полный код, изменения рефакторинга, тесты, профили, главное окно, итерации, известные проблемы, приложения

#### 2. md2html.py (updated) / md2html.py (обновлён)

**EN:** Replaced hardcoded `MD_PATH`/`HTML_PATH` with `argparse` CLI:
- `python md2html.py input.md` → outputs `input.html`
- `python md2html.py input.md output.html` → explicit output
- `<title>` now derived from input filename
- Error handling for missing input file

**RU:** Заменены захардкоженные `MD_PATH`/`HTML_PATH` на CLI через `argparse`:
- `python md2html.py input.md` → вывод `input.html`
- `python md2html.py input.md output.html` → явный вывод
- `<title>` теперь берётся из имени входного файла
- Обработка ошибки при отсутствии входного файла

#### 3. analyze_project.py (new) / analyze_project.py (новый)

**EN:** Diagnostic script checking: AST syntax of all .py files, local import resolution, TODO/FIXME markers, main_window tab/shortcut/menu counts, i18n sections, profile/test counts, known issue status, file statistics.

**RU:** Диагностический скрипт: AST-синтаксис всех .py, разрешение локальных импортов, маркеры TODO/FIXME, количество вкладок/хоткеев/меню в main_window, секции i18n, количество профилей/тестов, статус известных проблем, статистика файлов.

#### 4. i18n refactoring: common/ package / Рефакторинг i18n: пакет common/

**EN:** Extracted `i18n.py` into a new top-level `common/` package to eliminate the cross-package dependency `ui/` → `i8080_ci/`. The `ui/` package no longer needs `i8080_ci` in its import path. `i8080_ci/i18n.py` is kept as a thin re-export for backward compatibility.

**RU:** Вынесен `i18n.py` в новый топ-уровневый пакет `common/` для устранения меж-пакетной зависимости `ui/` → `i8080_ci/`. Пакет `ui/` больше не требует `i8080_ci` в пути импорта. `i8080_ci/i18n.py` сохранён как тонкий re-export для обратной совместимости.

| Before / Было | After / Стало |
|------|--------|
| `ui/` → `i8080_ci.i18n` (absolute, fragile) | `ui/` → `common.i18n` (independent) |
| `i8080_ci/` → `.i18n` (relative) | `i8080_ci/` → `common.i18n` (explicit) |

### Files Modified / Изменённые файлы

1. `build_snapshot.py` (new, 736 lines)
2. `md2html.py` (updated: argparse CLI)
3. `analyze_project.py` (new, 205 lines)
4. `common/__init__.py` (new)
5. `common/i18n.py` (moved from `i8080_ci/i18n.py`)
6. `i8080_ci/i18n.py` (replaced with re-export shim)
7. `i8080_ci/__init__.py` (import updated)
8. `i8080_ci/main_window.py` (import updated)
9. `i8080_ci/bus_worker.py` (import updated)
10. `ui/device_manager.py` (import updated)
11. `ui/device_window.py` (import updated)

### Test Results / Результаты тестов

| Check / Проверка | Result / Результат |
|---------|--------|
| Syntax (121 .py files) / Синтаксис | ✅ All pass / Все прошли |
| Local imports / Локальные импорты | ✅ All resolve / Все разрешаются |
| TODO/FIXME in project code / В коде проекта | ✅ None (only in tooling scripts) / Нет (только в скриптах инструментов) |
| main_window.py tabs / Вкладки | ✅ 10 tabs, correct order / 10 вкладок, верный порядок |
| i18n sections / Секции i18n | ✅ EN + RU present / EN + RU на месте |
| Profiles / Профили | ✅ 11 TOML files / 11 TOML-файлов |
| Tests / Тесты | ✅ 52 test files / 52 тестовых файла |
| Unit tests (31 files) / Unit-тесты | ✅ 794 checks, 0 failed / 794 проверки, 0 ошибок |
| Integration tests (3 files) / Интеграционные | ✅ 139 checks, 0 failed / 139 проверок, 0 ошибок |
| **Total / Итого** | **✅ 933 checks, 0 failed / 933 проверки, 0 ошибок** |

### Test Fixes / Исправления тестов

**EN:** Updated `test_config.py`, `test_system.py`, `test_system_profiles.py` to match current profile data (radio86rk: 3 regions/3 devices, micro80: 3 regions/3 devices, vector06c: 1 region/2 devices). Fixed `profile["toml"]` → `profile["config"]` with `load_from_dict()`. Fixed device names (PPI-0→PPI, PIT-0→Keyboard). Fixed memory region names (RAM-48K→RAM, ROM-16K→ROM).

**RU:** Обновлены `test_config.py`, `test_system.py`, `test_system_profiles.py` под актуальные данные профилей (radio86rk: 3 региона/3 устройства, micro80: 3/3, vector06c: 1/2). Исправлен `profile["toml"]` → `profile["config"]` с `load_from_dict()`. Исправлены имена устройств (PPI-0→PPI, PIT-0→Keyboard). Исправлены имена регионов памяти (RAM-48K→RAM, ROM-16K→ROM).

---

## Pass 5 — Port Inversion + I8255 Fix / Инверсия портов + Исправление I8255

**Date / Дата:** 2026-09-14

### Summary / Обзор

**EN:** Implemented port range inversion for Mikro-80 profile (PPI registers physically wired in reverse order). Fixed I8255 Port B direction check bug. Fixed I8255 `set_port_input` to write to `external_input`. Fixed I8276 default character attribute (0x00→0x07). Added global language state for cross-dialog i18n. 30 new test checks in `test_port_invert.py`.

**RU:** Реализована инверсия диапазона портов для профиля Микро-80 (регистры PPI физически перевёрнуты). Исправлен баг проверки направления Port B в I8255. Исправлен `set_port_input` I8255 для записи в `external_input`. Исправлен атрибут по умолчанию в I8276 (0x00→0x07). Добавлено глобальное состояние языка для меж-диалоговой i18n. 30 новых проверок в `test_port_invert.py`.

### Changes / Изменения

#### 1. Port Inversion (Mikro-80) / Инверсия портов (Микро-80)

**EN:**
**Problem:** Mikro-80 hardware has I8255 PPI registers wired in reverse: CPU port 0x04 reaches device offset 3 (Ctrl) instead of offset 0 (Port A).

**Solution:** Added `_port_invert_map` to `MemoryBus` and `port_invert` option in device config profiles.

**RU:**
**Проблема:** В аппаратной части Микро-80 регистры I8255 PPI перевёрнуты: CPU-порт 0x04 достигает device offset 3 (Ctrl) вместо offset 0 (Port A).

**Решение:** Добавлена `_port_invert_map` в `MemoryBus` и опция `port_invert` в профилях конфигурации устройств.

| File / Файл | Change / Изменение |
|------|--------|
| `modules/memory/memory_bus.py` | Added `_port_invert_map` dict; `io_read`/`io_write` now check it |
| `modules/system.py` | `_apply_config()`: reads `port_invert` from device config, builds map |
| `profiles/micro80.toml` | Added `port_invert = true` to PPI device |

**Mapping (base=0x04, 4 ports):**
```
CPU 0x04 -> device 0x07 (Ctrl,  offset 3)
CPU 0x05 -> device 0x06 (Port C, offset 2)
CPU 0x06 -> device 0x05 (Port B, offset 1)
CPU 0x07 -> device 0x04 (Port A, offset 0)
```

#### 2. I8255 Fixes / Исправления I8255

**EN:**
- **Port B direction bug:** `io_read` checked `(ctrl >> 1) & 1` (Mode B bit) instead of `ctrl & 1` (Port B direction bit D0)
- **set_port_input:** wrote to `port_a`/`port_b`/`port_c` (output registers) instead of `external_input` (which is what `io_read` reads in input mode)

**RU:**
- **Баг направления Port B:** `io_read` проверял `(ctrl >> 1) & 1` (бит Mode B) вместо `ctrl & 1` (бит направления Port B D0)
- **set_port_input:** записывал в `port_a`/`port_b`/`port_c` (регистры вывода) вместо `external_input` (то что читает `io_read` во входном режиме)

| File / Файл | Before / Было | After / Стало |
|------|--------|-------|
| `modules/io/i8255.py` | `if (ctrl >> 1) & 1:` | `if ctrl & 1:` |
| `modules/io/i8255.py` | `self.port_a = value` | `self.external_input[0] = value` |

#### 3. I8276 Default Attribute / Атрибут по умолчанию I8276

**EN:** Changed default character attribute from 0x00 (black on black = invisible) to 0x07 (bright white on black).

**RU:** Изменён атрибут символа по умолчанию с 0x00 (чёрный на чёрном = невидимый) на 0x07 (яркий белый на чёрном).

#### 4. Global Language State (i18n) / Глобальное состояние языка (i18n)

**EN:**
**Problem:** `DeviceManagerDialog.tr()` used `get_system_language()` (system locale) but didn't know about user's language selection in `MainWindow.lang_combo`.

**Solution:** Added `_current_lang` + `set_language()` to `i18n.py`.

**RU:**
**Проблема:** `DeviceManagerDialog.tr()` использовал `get_system_language()` (системный locale) и не знал о выборе языка пользователем в `MainWindow.lang_combo`.

**Решение:** Добавлены `_current_lang` + `set_language()` в `i18n.py`.

| File / Файл | Change / Изменение |
|------|--------|
| `i8080_ci/i18n.py` | Added `_current_lang` global, `set_language(lang)` function |
| `i8080_ci/i18n.py` | `get_system_language()` now checks `_current_lang` first |
| `i8080_ci/main_window.py` | Import + call `set_language()` in `__init__` and `on_lang_changed` |

#### 5. New Tests / Новые тесты

**EN:** `tests/test_port_invert.py` — 30 checks covering:
- Inversion map correctness
- IO read/write through inversion
- I8255 Port A input mode via inverted bus
- Keyboard8x8 + port_invert full integration (press/release key)
- Reset behavior (new bus = clean map)
- Full profile loading (micro80)

Also: `tests/test_system_integration.py` rewritten (54 checks) with correct device names and logical test flow.

**RU:** `tests/test_port_invert.py` — 30 проверок:
- Корректность карты инверсии
- IO read/write через инверсию
- I8255 Port A во входном режиме через инвертированную шину
- Keyboard8x8 + port_invert полная интеграция (нажатие/отпускание клавиши)
- Поведение Reset (новая шина = чистая карта)
- Полная загрузка профиля (micro80)

Также: `tests/test_system_integration.py` переписан (54 проверки) с корректными именами устройств и логической структурой.

### Files Modified / Изменённые файлы

1. `modules/memory/memory_bus.py` — `_port_invert_map` in `__init__`, `io_read`, `io_write`
2. `modules/system.py` — port inversion setup in `_apply_config()`
3. `modules/io/i8255.py` — Port B direction fix (bit 0), set_port_input fix
4. `modules/io/i8276.py` — default attribute 0x00→0x07
5. `i8080_ci/i18n.py` — `set_language()`, global state, dm_* key fixes
6. `i8080_ci/main_window.py` — `set_language()` calls
7. `tests/test_port_invert.py` — NEW (30 checks)
8. `tests/test_system_integration.py` — REWRITTEN (54 checks)
9. `profiles/micro80.toml` — `port_invert = true` added

### Test Results / Результаты тестов

```
test_port_invert.py:         30/30 PASS (new)
test_i8255.py:               17/17 PASS
test_i8276.py:               32/32 PASS
test_system_integration.py:  54/54 PASS (rewritten)
test_interrupts.py:          12/12 PASS
test_integration_full.py:    31/31 PASS
test_i8253.py:               26/26 PASS
test_i8259.py:               25/25 PASS
test_i8251.py:               14/14 PASS
test_i8279.py:               35/35 PASS
... (30 files total, 767 checks)
```

---

## Pass 4 — i18n Complete / i18n Завершено

**Date / Дата:** 2026-09-08

### Summary / Обзор

**EN:** Fixed all 26 i18n issues identified in I18N_AUDIT.md. All UI strings now properly support RU/EN language switching. Added 11 new keys, fixed 8 status labels, fixed 2 local variable bugs, fixed 1 format bug.

**RU:** Исправлены все 26 проблем i18n, выявленные в I18N_AUDIT.md. Все UI-строки теперь корректно поддерживают переключение RU/EN. Добавлено 11 новых ключей, исправлено 8 статусных меток, исправлены 2 бага с локальными переменными, исправлен 1 форматный баг.

### Changes / Изменения

- Added 11 new keys to LANGS (both EN and RU): `endian_little`, `endian_big`, `test_pattern_checker`, `test_pattern_zero`, `test_pattern_one`, `test_pattern_addr`, `mcp_off`, `mcp_on`, `bus_active`, `bus_free`, `search_placeholder`
- Fixed 8 status/label strings that weren't updated on language switch
- Fixed 2 bugs with local variables (`devices_menu`, `act_device_manager`)
- Fixed 1 format bug (`status_label_size`)
- Fixed combo boxes (theme, endianness x2, test pattern) to use `tr()`
- Fixed MCP button initial text and toggle handler
- Fixed trace search placeholder (was hardcoded Russian)
- Added full `retranslate_ui` coverage for all previously-missed widgets

### Files Modified / Изменённые файлы

1. `i8080_ci/i18n.py` — 11 new keys per language
2. `i8080_ci/main_window.py` — 26 fixes across init, retranslate_ui, handlers
3. `i8080_ci/views/search.py` — placeholder + retranslate fix

---

## Pass 3 — Module Split / Разбиение на модули

**Date / Дата:** 2026-09-08

### Summary / Обзор

**EN:** Split the monolithic `i8080_CI.py` (6,517 lines) into a modular `i8080_ci/` package (18 files). `MainWindow` remains monolithic in `main_window.py`. All imports verified, application launches successfully.

**RU:** Разбит монолитный `i8080_CI.py` (6 517 строк) на модульный пакет `i8080_ci/` (18 файлов). `MainWindow` остался монолитным в `main_window.py`. Все импорты верифицированы, приложение запускается успешно.

### New Package Structure / Новая структура пакета

```
i8080_CI.py                # Entry point / Точка входа (15 lines, was 6,517)
i8080_ci/
│   __init__.py            # Package exports / Экспорт пакета
│   i18n.py                # LANGS + THEMES + get_system_language()
│   slip.py                # SLIP constants + SlipProtocol
│   intelhex.py            # IntelHex parse/generate
│   disassembler.py        # JUMP_OPCODES + I8080Disassembler
│   bus_worker.py          # BusWorker (QThread serial communication)
│   automation.py          # AutomationAPI (script interface)
│   main_window.py         # MainWindow (monolithic / монолитный)
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

### Key Decisions / Ключевые решения

| Decision / Решение | Rationale / Обоснование |
|----------|-----------|
| MainWindow stays monolithic / MainWindow остаётся монолитным | Avoids high-risk mixin refactoring (120+ interdependent methods) |
| No circular deps / Нет циклических зависимостей | MainWindow imports from package; nothing imports from main_window |
| Duck typing preserved / Duck typing сохранён | AutomationAPI accepts main_window without import |
| Lazy imports preserved / Lazy imports сохранены | memory_bus.py, device_config.py unchanged |

### Verification / Верификация

| Check / Проверка | Result / Результат |
|-------|--------|
| 18/18 files syntax valid / 18/18 файлов синтаксически валидны | PASS |
| All module imports / Все импорты модулей | PASS |
| Application launch / Запуск приложения | PASS |
| test_memory_bus.py | PASS |
| test_memory_models.py | PASS (21/21) |

---

## Pass 2 — Type Hints Fix / Исправление типизации

**Date / Дата:** 2026-09-08

### Summary / Обзор

**EN:** Full analysis and targeted refactoring. 14 type hint fixes applied across 2 files. README.md created (merged from README_OLD.md + README_NEW.md). ANALYSIS.md updated.

**RU:** Полный анализ и целенаправленный рефакторинг. 14 исправлений type hints в 2 файлах. README.md создан (объединён из README_OLD.md + README_NEW.md). ANALYSIS.md обновлён.

### Type Hints Fixed / Исправленная типизация

**modules/system.py:**

| Method / Метод | Change / Изменение |
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

**modules/memory/memory_bus.py:**

| Method / Метод | Change / Изменение |
|--------|--------|
| `MemoryRegion.__init__` | Added full type annotations |
| `RAMRegion.__init__` | Added full type annotations |
| `ROMRegion.__init__` | Added full type annotations |
| `MemoryBus.add_mmio_region` | `region` → `region: object` |

### Documentation / Документация

- **README.md** — Created: unified bilingual merge of README_OLD.md and README_NEW.md
- **ANALYSIS.md** — Updated with pass 2 findings, corrected metrics
- **README_OLD.md** / **README_NEW.md** — Preserved for reference

---

## Pass 1 — Initial Refactoring / Начальный рефакторинг

**Date / Дата:** 2026-09-08

### Summary / Обзор

**EN:** 16 changes applied across 12 files. All changes verified with `ast.parse()`.

**RU:** 16 изменений в 12 файлах. Все изменения верифицированы через `ast.parse()`.

### P0 — Critical Fixes / Критические исправления

#### Exception Handling: File I/O / Обработка исключений: Файловый I/O

**EN:** Changed `except Exception:` to `except OSError:` in 9 occurrences across 5 files.

**RU:** Заменено `except Exception:` на `except OSError:` в 9 местах в 5 файлах.

| File / Файл | Method / Метод | Change / Изменение |
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

#### MCP Server Thread Safety / Потокобезопасность MCP-сервера

**EN:**
- Removed debug comments from `stop_event`
- Renamed `stop_event` → `_stop_event` (private by convention)
- `stop()`: Added idempotency guard, timeout increased from 2s to 5s
- `stop()`: Sets `self.thread = None` after join to prevent double-join
- `_run_server()`: Suppresses error log on graceful shutdown
- Added type hints

**RU:**
- Удалены debug-комментарии из `stop_event`
- Переименовано `stop_event` → `_stop_event` (частный по конвенции)
- `stop()`: Добавлена идемпотентность, таймаут увеличен с 2с до 5с
- `stop()`: Устанавливает `self.thread = None` после join
- `_run_server()`: Подавляет лог ошибок при штатном останове
- Добавлены type hints

### P1 — Structural Improvements / Структурные улучшения

#### Dead Code Removal / Удаление мёртвого кода

**EN:** 90 lines removed across 4 files.

**RU:** 90 строк удалено в 4 файлах.

| File / Файл | Removed / Удалено | Reason / Причина |
|------|---------|--------|
| `modules/io/i8255.py` | 26 lines | Old `io_read` implementation |
| `modules/io/i8257.py` | 5 lines | Old `io_write` stub |
| `modules/io/keyboard8x8.py` | 12 lines | Old `get_state` |
| `ui/display_widgets.py` | 47 lines | Old `paintEvent` |

#### DRY: device_config.py / DRY: device_config.py

**EN:** Extracted repeated parameter-apply patterns into `_apply_optional_params()` static helper. Used in 3 places.

**RU:** Выделены повторяющиеся паттерны применения параметров в статический helper `_apply_optional_params()`. Используется в 3 местах.

#### Type Hints Added / Добавленные type hints

| File / Файл | Methods annotated / Методы с аннотациями |
|------|-------------------|
| `mcp_server.py` | `__init__`, `_create_server`, `_run_server`, `stop` |
| `modules/system.py` | 9 methods |
| `modules/config/device_config.py` | All public methods |
| `modules/memory/memory_bus.py` | 5 methods |

### Files Modified / Изменённые файлы

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
