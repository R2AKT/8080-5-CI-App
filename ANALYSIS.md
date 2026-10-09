# i8080-5 CI — Project Analysis / Анализ проекта

**Date / Дата:** 2026-10-09
**Scope / Объём:** Full codebase (~160 Python files, ~41,500 lines) + VS Code plugin
**Session / Сессия:** Full re-analysis (architecture, dual-CPU, CLI assembler, MCP server, VS Code plugin)

---

## Overview / Обзор

| Metric / Метрика | Value / Значение |
|--------|-------|
| Python files / Файлов Python | ~160 (core project, без разовых root-скриптов аудита) |
| Total lines / Всего строк | ~41,500 |
| GUI package / GUI-пакет | i8080_ci/ (19 модулей, main_window.py 4 192 строки) |
| Emulator / Эмулятор | i8080_emulator.py (2 000 строк, dual-CPU i8080/i8085) |
| Assembler / Ассемблер | assemble8080/ (10 модулей, assembler.py 1 919 строк, CLI) |
| MCP Server / MCP-сервер | mcp_server.py (1 213 строк, 70 tools + 6 resources + 9 prompts) |
| IO modules / Модули IO | 23 device-модуля в modules/io/ |
| Memory modules / Модули памяти | 7 типов в modules/memory/ |
| Profiles / Профили | 12 TOML-профилей (+ 9 шаблонов в template/) |
| Tests / Тесты | 66 test-файлов, 921 checks (100% PASS) + zasm reference 15/15 |
| i18n keys / Клавиши i18n | ~330 UI-ключей на язык (LANGS) + ~85–91 описания мнемоник (MNEMONIC_INFO) |
| VS Code plugin / Плагин VS Code | v0.2.1 (TypeScript, MCP-клиент) |

---

## Architecture / Module Overview / Архитектура и обзор модулей

**EN:**

The project is a dual-CPU (i8080 + i8085) hardware CI/debugger with three independent entry
points: a PySide6 GUI, a headless MCP server, and a standalone CLI assembler. The CPU emulator
is a `QObject` that exposes Qt signals, so the same core drives the GUI, the headless host, and
the MCP server.

**Top-level entry points / Точ входа верхнего уровня:**

| File / Файл | Lines / Строк | Role / Роль |
|-------|-------|--------|
| `i8080_CI.py` | 15 | GUI entry point — thin wrapper (`QApplication` + `MainWindow`) |
| `i8080_emulator.py` | 2 000 | i8080/i8085 CPU emulator, `QObject` + Qt signals, dual-CPU via `cpu_type` |
| `mcp_server.py` | 1 213 | FastMCP MCP server, SSE transport, port 8000; 70 tools + 6 resources + 9 prompts |
| `mcp_headless.py` | 108 | Headless MCP entry (`python mcp_headless.py --profile full --port 8000`), `HeadlessHost` + `MCPServerManager` |
| `version.py` | 9 | `__version__=2.1.7`, `__build__=20261009`, `__app_name__="i8080-5 CI"` |

**`assemble8080/` — assembler package (10 modules, 3 348 lines) / Пакет ассемблера:**

| File / Файл | Lines / Строк | Role / Роль |
|-------|-------|--------|
| `assembler.py` | 1 919 | Two-pass assembler (pass 1 labels, pass 2 code); CLI via `__main__.py` / `_cli_main`; `assemble(source, filename, now, cpu_type) -> AsmResult` |
| `preprocessor.py` | 630 | `MACRO/ENDM`, `REPT/ENDM`, `#include`/`include`/`.include`, `#define`, `#if/#elif/#else/#endif`, `IF/ENDIF/ELSE`, `#path`/`.path`, `#target`, `#charset` |
| `linker.py` | 255 | `.lnk` script: `INPUT/OUTPUT/MAP/ORIGIN/SIZE/FILL` |
| `mapfile.py` | 162 | MAP-file generation |
| `objfile.py` | 137 | `.obj` intermediate format |
| `numbers.py` | 84 | Numeric parsing (hex/bin/dec/oct) |
| `symbols.py` | 77 | Symbol table |
| `errors.py` | 37 | Error types |
| `__main__.py` | 19 | CLI entry point |
| `__init__.py` | 28 | Package exports |

The assembler is a **standalone CLI** (no GUI dependency) and is CPU-aware (`cpu_type` selects
i8080 vs i8085 opcode set).

**`i8080_ci/` — application package (19 modules, 9 221 lines) / Пакет приложения:**

| File / Файл | Lines / Строк | Role / Роль |
|-------|-------|--------|
| `main_window.py` | 4 192 | `MainWindow` (monolithic) |
| `assembler_widget.py` | 2 037 | `CodeEditor`, tabs, `.ws` workspace, Ctrl+Click labels, `::` global highlight |
| `automation.py` | 736 | `AutomationAPI` |
| `headless_host.py` | 316 | `HeadlessHost` (GUI-less system host) |
| `bus_worker.py` | 249 | `QThread` serial bus worker |
| `disassembler.py` | 233 | Disassembler, `cpu_type`-aware |
| `slip.py` | 61 | SLIP protocol (real hardware over COM) |
| `intelhex.py` | 51 | Intel HEX read/write |
| `i18n.py` | 4 | i18n re-export shim |
| `models/` | — | `hex_model`, `watch_model`, `bp_model`, `trace_model` (4) |
| `views/` | — | `disasm_view`, `hex_view`, `search` (3) |

**`common/` — shared utilities (4 modules, 1 198 lines) / Общие утилиты:**

| File / Файл | Lines / Строк | Role / Роль |
|-------|-------|--------|
| `i18n.py` | 969 | `LANGS` (en/ru) + `MNEMONIC_INFO`, `set_language()` |
| `encoding.py` | 109 | File-encoding auto-detection: BOM → UTF-8 → `charset_normalizer` → CP1251 |
| `themes.py` | 115 | Light/dark themes |

**`modules/` — hardware model (38 modules, 9 492 lines) / Модель железа:**

| File / Файл | Lines / Строк | Role / Роль |
|-------|-------|--------|
| `system.py` | 496 | `ComputerSystem` — integration hub (CPU + MemoryBus + IO) |
| `memory/` | — | 7 types: `banked`, `paged`, `shadow`, `segmented`, `segmentedpaged`, `mmio`, `memory_bus` |
| `io/` | — | 23 device modules + `iodevice` base: `i8255`, `i8253`, `i8251`, `i8259`, `i8257`, `i8272`, `i8275`, `i8276`, `i8279`, `i16550`, `i512vi1`, `cf_ide`, `ch376s`, `am9511`, `lcd1602`, `lcd2004`, `tft8080`, `keyboard8x8`, `keyboard8279_adapter`, `cube3d`, `discrete_video`, `bitmap_video`, `chargen` |
| `config/` | — | `device_config` (469), `system_profiles` (115) |

**`ui/` — Qt widgets (8 modules, 1 802 lines) / Qt-виджеты:**
`cube3d_widget`, `device_manager`, `device_window`, `display_widgets`, `gpio_widget`,
`keyboard_widget`, `serial_terminal`.

**`profiles/` — TOML system profiles / TOML-профили системы:**
12 profiles: `micro80`, `microsha`, `radio86rk`, `apogey`, `orion128`, `vector06c`,
`specialist`, `full`, `empty8080`, `empty8085`, `lvovpk01`, `display_test`; plus 9 templates in
`template/`.

**`tests/` — test suite (74 files, 11 719 lines) / Тесты:**
66 test files + 8 helpers. `run_tests.py` = **921 passed / 0 failed**. `test_bin_compare.py` =
**15 zasm references byte-identical**. `test_roundtrip_256.py` = **3 cycles PASS**. Includes
`test_8085.py`, `test_asm8080-8085.py`, and a GUI smoke test.

**`Plugins/i8080_ci-vscode/` — VS Code plugin v0.2.1 / Плагин VS Code:**
TypeScript extension acting as an MCP client for the headless server (`src/`, `tsconfig.json`,
`build.js`, `e2e_test.js`).

**RU:**

Проект — dual-CPU (i8080 + i8085) аппаратный CI/отладчик с тремя независимыми точками входа:
PySide6 GUI, headless MCP-сервер и автономный CLI-ассемблер. Эмулятор CPU — это `QObject` с
Qt-сигналами, поэтому одно ядро управляет GUI, headless-хостом и MCP-сервером.

**Точки входа верхнего уровня:**

| Файл | Строк | Роль |
|-------|-------|--------|
| `i8080_CI.py` | 15 | Точка входа GUI — тонкая обёртка (`QApplication` + `MainWindow`) |
| `i8080_emulator.py` | 2 000 | Эмулятор i8080/i8085, `QObject` + Qt-сигналы, dual-CPU через `cpu_type` |
| `mcp_server.py` | 1 213 | FastMCP MCP-сервер, SSE-транспорт, порт 8000; 70 tools + 6 resources + 9 prompts |
| `mcp_headless.py` | 108 | Headless MCP-вход (`python mcp_headless.py --profile full --port 8080`), `HeadlessHost` + `MCPServerManager` |
| `version.py` | 9 | `__version__=2.1.7`, `__build__=20261009`, `__app_name__="i8080-5 CI"` |

**`assemble8080/` — пакет ассемблера (10 модулей, 3 348 строк):**

| Файл | Строк | Роль |
|-------|-------|--------|
| `assembler.py` | 1 919 | Двухпроходный ассемблер (pass 1 — метки, pass 2 — код); CLI через `__main__.py` / `_cli_main`; `assemble(source, filename, now, cpu_type) -> AsmResult` |
| `preprocessor.py` | 630 | `MACRO/ENDM`, `REPT/ENDM`, `#include`/`include`/`.include`, `#define`, `#if/#elif/#else/#endif`, `IF/ENDIF/ELSE`, `#path`/`.path`, `#target`, `#charset` |
| `linker.py` | 255 | `.lnk`-скрипт: `INPUT/OUTPUT/MAP/ORIGIN/SIZE/FILL` |
| `mapfile.py` | 162 | Генерация MAP-файла |
| `objfile.py` | 137 | Промежуточный формат `.obj` |
| `numbers.py` | 84 | Разбор чисел (hex/bin/dec/oct) |
| `symbols.py` | 77 | Таблица символов |
| `errors.py` | 37 | Типы ошибок |
| `__main__.py` | 19 | Точка входа CLI |
| `__init__.py` | 28 | Экспорты пакета |

Ассемблер — **автономный CLI** (без зависимости от GUI) и CPU-aware (`cpu_type` выбирает набор
опкодов i8080 или i8085).

**`i8080_ci/` — пакет приложения (19 модулей, 9 221 строка):**

| Файл | Строк | Роль |
|-------|-------|--------|
| `main_window.py` | 4 192 | `MainWindow` (монолит) |
| `assembler_widget.py` | 2 037 | `CodeEditor`, вкладки, `.ws`-workspace, Ctrl+Click по меткам, `::` глобальная подсветка |
| `automation.py` | 736 | `AutomationAPI` |
| `headless_host.py` | 316 | `HeadlessHost` (хост системы без GUI) |
| `bus_worker.py` | 249 | `QThread`-worker последовательной шины |
| `disassembler.py` | 233 | Дизассемблер, `cpu_type`-aware |
| `slip.py` | 61 | SLIP-протокол (реальное железо через COM) |
| `intelhex.py` | 51 | Чтение/запись Intel HEX |
| `i18n.py` | 4 | Shim реэкспорта i18n |
| `models/` | — | `hex_model`, `watch_model`, `bp_model`, `trace_model` (4) |
| `views/` | — | `disasm_view`, `hex_view`, `search` (3) |

**`common/` — общие утилиты (4 модуля, 1 198 строк):**

| Файл | Строк | Роль |
|-------|-------|--------|
| `i18n.py` | 969 | `LANGS` (en/ru) + `MNEMONIC_INFO`, `set_language()` |
| `encoding.py` | 109 | Автоопределение кодировки: BOM → UTF-8 → `charset_normalizer` → CP1251 |
| `themes.py` | 115 | Светлая/тёмная темы |

**`modules/` — модель железа (38 модулей, 9 492 строки):**

| Файл | Строк | Роль |
|-------|-------|--------|
| `system.py` | 496 | `ComputerSystem` — интеграционный хаб (CPU + MemoryBus + IO) |
| `memory/` | — | 7 типов: `banked`, `paged`, `shadow`, `segmented`, `segmentedpaged`, `mmio`, `memory_bus` |
| `io/` | — | 23 device-модуля + базовый `iodevice`: `i8255`, `i8253`, `i8251`, `i8259`, `i8257`, `i8272`, `i8275`, `i8276`, `i8279`, `i16550`, `i512vi1`, `cf_ide`, `ch376s`, `am9511`, `lcd1602`, `lcd2004`, `tft8080`, `keyboard8x8`, `keyboard8279_adapter`, `cube3d`, `discrete_video`, `bitmap_video`, `chargen` |
| `config/` | — | `device_config` (469), `system_profiles` (115) |

**`ui/` — Qt-виджеты (8 модулей, 1 802 строки):**
`cube3d_widget`, `device_manager`, `device_window`, `display_widgets`, `gpio_widget`,
`keyboard_widget`, `serial_terminal`.

**`profiles/` — TOML-профили системы:**
12 профилей: `micro80`, `microsha`, `radio86rk`, `apogey`, `orion128`, `vector06c`,
`specialist`, `full`, `empty8080`, `empty8085`, `lvovpk01`, `display_test`; плюс 9 шаблонов в
`template/`.

**`tests/` — тестовый набор (74 файла, 11 719 строк):**
66 test-файлов + 8 helpers. `run_tests.py` = **921 passed / 0 failed**. `test_bin_compare.py` =
**15 zasm-ссылок побайтово идентичны**. `test_roundtrip_256.py` = **3 цикла PASS**. Включает
`test_8085.py`, `test_asm8080-8085.py` и GUI smoke-тест.

**`Plugins/i8080_ci-vscode/` — плагин VS Code v0.2.1:**
TypeScript-расширение, работающее как MCP-клиент для headless-сервера (`src/`, `tsconfig.json`,
`build.js`, `e2e_test.js`).

---

## Design Decisions / Ключевые решения по дизайну

**EN:**

- **Two-pass assembler** — pass 1 collects labels, pass 2 emits code; enables forward references.
- **Dual-CPU core** — a single `i8080_emulator.py` handles both i8080 and i8085 via `cpu_type`;
  the 8085 adds `SIM/RIM/DSUB/ARHL/RDEL/LDHI/LDSI/RSTV/SHLX/JNK/LHLX/JK`.
- **SLIP protocol** — real-hardware communication over COM ports (`slip.py`, `bus_worker.py`).
- **TOML system profiles** — declarative hardware configuration (`profiles/`), loaded by
  `system_profiles.py` / `device_config.py`.
- **FastMCP with SSE transport** — the MCP server (`mcp_server.py`) exposes 70 tools over SSE on
  port 8000; a separate headless entry (`mcp_headless.py`) runs it without the GUI.
- **PySide6 GUI** — RU/EN i18n and light/dark themes; `MainWindow` remains monolithic.
- **File-encoding auto-detection** — BOM → UTF-8 → `charset_normalizer` → CP1251 fallback
  (`common/encoding.py`).
- **VS Code plugin** — TypeScript extension (v0.2.1) that talks to the headless MCP server.

**RU:**

- **Двухпроходный ассемблер** — pass 1 собирает метки, pass 2 выдаёт код; позволяет вперёд-ссылки.
- **Dual-CPU ядро** — единый `i8080_emulator.py` обрабатывает и i8080, и i8085 через `cpu_type`;
  8085 добавляет `SIM/RIM/DSUB/ARHL/RDEL/LDHI/LDSI/RSTV/SHLX/JNK/LHLX/JK`.
- **SLIP-протокол** — связь с реальным железом через COM-порты (`slip.py`, `bus_worker.py`).
- **TOML-профили системы** — декларативная конфигурация железа (`profiles/`), загружается
  `system_profiles.py` / `device_config.py`.
- **FastMCP с SSE-транспортом** — MCP-сервер (`mcp_server.py`) отдаёт 70 tools по SSE на порту
  8000; отдельный headless-вход (`mcp_headless.py`) запускает его без GUI.
- **PySide6 GUI** — RU/EN i18n и светлая/тёмная темы; `MainWindow` остаётся монолитным.
- **Автоопределение кодировки файлов** — BOM → UTF-8 → `charset_normalizer` → fallback CP1251
  (`common/encoding.py`).
- **Плагин VS Code** — TypeScript-расширение (v0.2.1), общающееся с headless MCP-сервером.

---

## Issues Found & Status / Найденные проблемы и статус

> Note / Примечание: the tables below record the 2026-09-14 audit (passes 1–7). Line numbers may
> have shifted since the codebase grew (emulator 1 761 → 2 000 lines, `main_window.py` 3 790 →
> 4 192 lines). / Таблицы ниже фиксируют аудит от 2026-09-14 (проходы 1–7). Номера строк могли
> сдвинуться после роста кодовой базы (эмулятор 1 761 → 2 000 строк, `main_window.py` 3 790 →
> 4 192 строки).

### P0 — Critical / Критические

**EN:**

| Issue | Count | Status |
|-------|-------|--------|
| Bare `except:` | 0 | Clean (verified via AST scan) |
| Broad `except Exception:` (file I/O) | 0 | **Fixed** in pass 1 (changed to `OSError`) |
| Broad `except Exception:` (GUI/logic) | 16 | Left as-is (intentional for GUI robustness) |
| Thread safety in MCP server | 1 | **Fixed** in pass 1 (idempotent stop, daemon thread) |
| `safe_call` thread-awareness | 1 | Already correct (checks QThread) |
| Syntax errors | 0 | All files pass `ast.parse()` |

**RU:**

| Проблема | Кол-во | Статус |
|-------|-------|--------|
| Голые `except:` | 0 | Чисто (проверено AST-сканом) |
| Широкие `except Exception:` (файловый I/O) | 0 | **Исправлено** в Pass 1 (заменено на `OSError`) |
| Широкие `except Exception:` (GUI/логика) | 16 | Оставлено как есть (осознанно для надёжности GUI) |
| Thread safety в MCP-сервере | 1 | **Исправлено** в Pass 1 (идемпотентный stop, daemon-поток) |
| `safe_call` thread-awareness | 1 | Уже корректно (проверяет QThread) |
| Ошибки синтаксиса | 0 | Все файлы проходят `ast.parse()` |

### P1 — Structure / Структура

**EN:**

| Issue | Count | Status |
|-------|-------|--------|
| Dead code (commented-out functions) | 0 | **Removed** in pass 1 (90 lines) |
| Missing type hints on public methods | ~240 in main_window.py | Partially addressed (module files done) |
| DRY violations in device_config.py | 0 | **Fixed** in pass 1 (helper extracted) |
| TODO/FIXME/HACK comments | 0 | Clean |
| Incorrect type hints (wrong return type) | 4 in system.py | **Fixed** in pass 2 |
| Unused imports / variables (pyflakes) | ~40 | **Fixed** in pass 6 (project-wide) |
| f-strings without placeholders | ~20 | **Fixed** in pass 6 |
| SyntaxWarning in assembler `eval()` | 3 | **Fixed** in pass 6 (warnings suppressed) |
| Implicit public API in re-export `__init__.py` (no `__all__`) | 82 names in 6 files | **Fixed** in pass 7 (`__all__` added) |

**RU:**

| Проблема | Кол-во | Статус |
|-------|-------|--------|
| Мёртвый код (закомментированные функции) | 0 | **Удалён** в Pass 1 (90 строк) |
| Отсутствующие type hints на публичных методах | ~240 в main_window.py | Частично решено (модульные файлы готовы) |
| DRY-нарушения в device_config.py | 0 | **Исправлено** в Pass 1 (выделен helper) |
| TODO/FIXME/HACK комментарии | 0 | Чисто |
| Неправильные type hints (ошибочный return type) | 4 в system.py | **Исправлено** в Pass 2 |
| Неиспользуемые импорты / переменные (pyflakes) | ~40 | **Исправлено** в Pass 6 (по всему проекту) |
| f-строки без плейсхолдеров | ~20 | **Исправлено** в Pass 6 |
| SyntaxWarning в `eval()` ассемблера | 3 | **Исправлено** в Pass 6 (warnings подавлены) |
| Неявный публичный API в re-экспортных `__init__.py` (нет `__all__`) | 82 имени в 6 файлах | **Исправлено** в Pass 7 (добавлен `__all__`) |

### P2 — Infrastructure / Инфраструктура

**EN:**

| Item | Status |
|------|--------|
| requirements.txt | Present and up to date |
| pyproject.toml | Present with correct metadata |
| README.md | Bilingual (EN + RU), unified from two sources |
| Logo | Created (SVG, КР580ВМ80А theme) |
| Documentation | All 5 documents bilingual |

**RU:**

| Элемент | Статус |
|------|--------|
| requirements.txt | Есть, актуален |
| pyproject.toml | Есть, корректные метаданные |
| README.md | Двуязычный (EN + RU), объединён из двух источников |
| Логотип | Создан (SVG, тема КР580ВМ80А) |
| Документация | Все 5 документов двуязычные |

---

## Detailed Findings / Подробные результаты

### 1. Exception Handling / Обработка исключений

**EN:**

**File I/O (Fixed in pass 1):**
- `modules/config/device_config.py:_load_rom_file` — `except OSError`
- `modules/io/cf_ide.py` — 2 occurrences — `except OSError`
- `modules/io/ch376s.py` — 2 occurrences — `except OSError`
- `modules/io/i512vi1.py` — 2 occurrences — `except OSError`
- `modules/io/i8272.py` — 2 occurrences — `except (OSError, ValueError)` / `except OSError`

**GUI/Logic (Left as-is — intentional):**
- `i8080_ci/main_window.py` — 7 occurrences in format_value, save/load preset, close handlers
- `ui/device_window.py`, `ui/gpio_widget.py` — UI error handling
- `tests/` — 8 occurrences in test helper functions

**Emulator (Intentional):**
- `i8080_emulator.py` — `except Exception` around `eval()` for breakpoint conditions
  - Rationale: User-supplied conditions can raise any exception type; broad catch prevents debugger crash

**RU:**

**Файловый I/O (исправлено в Pass 1):**
- `modules/config/device_config.py:_load_rom_file` — `except OSError`
- `modules/io/cf_ide.py` — 2 вхождения — `except OSError`
- `modules/io/ch376s.py` — 2 вхождения — `except OSError`
- `modules/io/i512vi1.py` — 2 вхождения — `except OSError`
- `modules/io/i8272.py` — 2 вхождения — `except (OSError, ValueError)` / `except OSError`

**GUI/Логика (оставлено — осознанно):**
- `i8080_ci/main_window.py` — 7 вхождений в format_value, save/load preset, close handlers
- `ui/device_window.py`, `ui/gpio_widget.py` — обработка ошибок UI
- `tests/` — 8 вхождений в helper-функциях тестов

**Эмулятор (осознанно):**
- `i8080_emulator.py` — `except Exception` вокруг `eval()` для условий точек останова
  - Обоснование: Пользовательские условия могут бросить любой тип исключения; широкий catch предотвращает крах отладчика

---

### 2. Thread Safety / Потокобезопасность

**EN:**

**MCP Server (mcp_server.py):**
- `threading.Event()` with `_stop_event` (private convention)
- `stop()` is idempotent (early return if not running), timeout 5s
- `_run_server()` suppresses error log on graceful shutdown
- Daemon thread ensures clean process exit
- Note: `mcp.run(transport="sse")` is blocking; daemon thread is acceptable architecture

**QThread in main_window.py:**
- Worker thread pattern: `QThread` + `QObject` with `Signal`/`Slot`
- `safe_call()`: correctly checks `QThread.currentThread()` vs app thread
- Uses `QTimer.singleShot(0, ...)` for cross-thread dispatch
- No changes needed

**RU:**

**MCP-сервер (mcp_server.py):**
- `threading.Event()` с `_stop_event` (частный по конвенции)
- `stop()` идемпотентен (ранний return если не работает), таймаут 5с
- `_run_server()` подавляет лог ошибок при штатном останове
- Daemon-поток обеспечивает чистое завершение процесса
- Примечание: `mcp.run(transport="sse")` блокирующий; daemon-поток — приемлемая архитектура

**QThread в main_window.py:**
- Паттерн рабочего потока: `QThread` + `QObject` с `Signal`/`Slot`
- `safe_call()`: корректно проверяет `QThread.currentThread()` vs app thread
- Использует `QTimer.singleShot(0, ...)` для кросс-потокового диспетчера
- Изменения не требовались

---

### 3. Type Hints / Типизация

**EN:**

**Pass 1 (documented in CHANGES.md):**
- `mcp_server.py`: `__init__`, `_create_server`, `_run_server`, `stop`
- `modules/system.py`: `__init__`, `_IOPortsAdapter`, `load_profile`, `load_from_toml_file`, etc.
- `modules/config/device_config.py`: All public methods
- `modules/memory/memory_bus.py`: All public methods

**Pass 2:**
- `modules/system.py`: 10 type hint fixes (wrong return types corrected)
- `modules/memory/memory_bus.py`: 4 type hint additions

**Remaining (main_window.py):**
- ~240 public methods without return type hints
- Predominantly Qt event handlers (`wheelEvent`, `paintEvent`, `mouseDoubleClickEvent`) and GUI slots
- Recommendation: batch-annotate with `-> None` in a dedicated pass

**RU:**

**Pass 1 (документировано в CHANGES.md):**
- `mcp_server.py`: `__init__`, `_create_server`, `_run_server`, `stop`
- `modules/system.py`: `__init__`, `_IOPortsAdapter`, `load_profile`, `load_from_toml_file`, и др.
- `modules/config/device_config.py`: Все публичные методы
- `modules/memory/memory_bus.py`: Все публичные методы

**Pass 2:**
- `modules/system.py`: 10 исправлений type hints (исправлены неверные return types)
- `modules/memory/memory_bus.py`: 4 добавления type hints

**Осталось (main_window.py):**
- ~240 публичных методов без return type hints
- Преимущественно Qt event handlers (`wheelEvent`, `paintEvent`, `mouseDoubleClickEvent`) и GUI слоты
- Рекомендация: массовая аннотация с `-> None` в отдельном проходе

---

### 4. Port Inversion (Mikro-80) / Инверсия портов (Микро-80)

**EN:**

The Mikro-80 hardware has I8255 PPI registers wired in reverse order:
- CPU port 0x04 → device offset 3 (Ctrl)
- CPU port 0x07 → device offset 0 (Port A)

Implemented via `_port_invert_map` in `MemoryBus`:
- `io_read(port)` / `io_write(port, value)` check the map before accessing device
- Configured per-device via `port_invert = true` in TOML profile

**RU:**

В аппаратной части Микро-80 регистры I8255 PPI физически перевёрнуты:
- CPU-порт 0x04 → device offset 3 (Ctrl)
- CPU-порт 0x07 → device offset 0 (Port A)

Реализовано через `_port_invert_map` в `MemoryBus`:
- `io_read(port)` / `io_write(port, value)` проверяют карту перед обращением к устройству
- Настройка per-device через `port_invert = true` в TOML-профиле

---

### 5. Architecture Notes / Архитектурные заметки

**EN:**
- `memory_bus.py` uses lazy `from .shadow import ShadowROMRegion` inside methods — **INTENTIONAL** to avoid circular imports
- `device_config.py` uses lazy imports in `_create_instance` to avoid loading all 23+ device modules at startup
- `i8080_emulator.py` inherits from `QObject` and uses Qt Signals for UI communication; the same core is reused by the headless host and the MCP server
- MCP server runs in a daemon thread with SSE transport (port 8000)
- `ComputerSystem` acts as the integration hub connecting CPU, MemoryBus, and IO devices
- `_IOPortsAdapter` bridges the emulator's dict-based `io_ports` interface to the MemoryBus
- **Module split (Pass 3):** Original monolithic `i8080_CI.py` (6,517 lines) split into `i8080_ci/` package (19 modules). `MainWindow` remains monolithic (4,192 lines).
- **Assembler split:** The assembler now lives in the standalone `assemble8080/` package (CLI, no GUI dependency), separate from the GUI's `assembler_widget.py`.
- **i18n (Pass 4):** ~330 UI keys per language in `LANGS` plus `MNEMONIC_INFO` tables; global `set_language()` for cross-dialog propagation

**RU:**
- `memory_bus.py` использует lazy import `from .shadow import ShadowROMRegion` внутри методов — **ОСОЗНАННО** для избежания циклических импортов
- `device_config.py` использует lazy imports в `_create_instance` для избежания загрузки всех 23+ модулей при старте
- `i8080_emulator.py` наследуется от `QObject` и использует Qt Signals для UI-коммуникации; то же ядро переиспользуется headless-хостом и MCP-сервером
- MCP-сервер работает в daemon-потоке с SSE-транспортом (порт 8000)
- `ComputerSystem` — интеграционный хаб, связывающий CPU, MemoryBus и IO-устройства
- `_IOPortsAdapter` связывает dict-based интерфейс `io_ports` эмулятора с MemoryBus
- **Разбиение модулей (Pass 3):** Монолитный `i8080_CI.py` (6 517 строк) разбит на пакет `i8080_ci/` (19 модулей). `MainWindow` остался монолитным (4 192 строки).
- **Разбиение ассемблера:** Ассемблер теперь в автономном пакете `assemble8080/` (CLI, без зависимости от GUI), отдельно от GUI-`assembler_widget.py`.
- **i18n (Pass 4):** ~330 UI-ключей на язык в `LANGS` плюс таблицы `MNEMONIC_INFO`; глобальный `set_language()` для меж-диалоговой передачи

---

### 6. Code Quality Metrics / Метрики качества кода

| Metric / Метрика | Value / Значение |
|--------|-------|
| Files with bare except / Файлов с голым except | 0 |
| Files with syntax errors / Файлов с синтаксическими ошибками | 0 |
| Commented-out function blocks / Закомментированных блоков функций | 0 |
| TODO/FIXME comments / TODO/FIXME комментарии | 0 |
| DRY violations / DRY-нарушения | 0 (helper extracted) |
| Thread-unsafe shared state / Непотокобезопасное общее состояние | 0 |
| Test coverage / Покрытие тестами | 66 files, 921 checks, 100% + zasm 15/15 |
| i18n coverage / Покрытие i18n | ~330 UI keys × 2 languages + MNEMONIC_INFO |

---

## Recommendations / Рекомендации

**EN:**

1. ✅ ~~**Fix test_system.py** to match actual profile device names~~ — DONE (Pass 5)
2. **Batch-annotate** main_window.py with `-> None` for Qt event handlers and GUI slots
3. **Consider** adding `mypy --strict` to CI once type hints are more complete
4. **Consider** adding a `conftest.py` with shared fixtures to reduce test boilerplate
5. ✅ ~~**Consider** splitting i8080_CI.py~~ — DONE (Pass 3: split into `i8080_ci/` package)
6. **Consider** extracting `_port_invert_map` setup into a `bus.set_port_inversion(base, num_ports)` method for encapsulation
7. **Consider** closing the 1-key i18n gap (LANGS: 332 EN vs 331 RU) and aligning `MNEMONIC_INFO` counts (85 EN vs 91 RU)

**RU:**

1. ✅ ~~**Исправить test_system.py** под реальные имена устройств профилей~~ — ГОТОВО (Pass 5)
2. **Массовая аннотация** main_window.py с `-> None` для Qt event handlers и GUI слотов
3. **Рассмотреть** добавление `mypy --strict` в CI после завершения type hints
4. **Рассмотреть** добавление `conftest.py` с общими fixtures для уменьшения бойлплейта тестов
5. ✅ ~~**Рассмотреть** разбиение i8080_CI.py~~ — ГОТОВО (Pass 3: разбит на `i8080_ci/` пакет)
6. **Рассмотреть** вынесение настройки `_port_invert_map` в метод `bus.set_port_inversion(base, num_ports)` для инкапсуляции
7. **Рассмотреть** закрытие 1-ключевого разрыва i18n (LANGS: 332 EN vs 331 RU) и выравнивание счётчиков `MNEMONIC_INFO` (85 EN vs 91 RU)

---

## i18n Status / Статус i18n

**EN:** ✅ Complete (Pass 4 + Pass 5, 2026-09-14). `LANGS` holds ~330 UI strings per language
(332 EN / 331 RU) with RU/EN switching; `MNEMONIC_INFO` adds per-mnemonic descriptions (85 EN /
91 RU). Device Manager, Device Window, and Search Dialog fully translated. One-key gap between
EN and RU remains in `LANGS`.

**RU:** ✅ Завершено (Pass 4 + Pass 5, 2026-09-14). `LANGS` содержит ~330 UI-строк на язык
(332 EN / 331 RU) с переключением RU/EN; `MNEMONIC_INFO` добавляет описания по мнемоникам
(85 EN / 91 RU). Диспетчер устройств, Окно устройств и Диалог поиска полностью переведены.
Одноключевой разрыв между EN и RU в `LANGS` сохраняется.
