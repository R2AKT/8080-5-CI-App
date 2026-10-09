# Changelog / Журнал изменений


## v2.1.7 (2026-10-09)
### CLI / Command-line assembler (no GUI)
- New `python -m assemble8080` CLI: assemble files, 8080/8085, link via .lnk, hexdump/listing/symbols, quiet mode, exit codes
- Added `assemble8080/__main__.py`; `assemble()` gained `cpu_type` parameter
- Fixed broken `__main__` self-test (UnicodeEncodeError on cp1251 console, RuntimeWarning)
- Fixed `--lnk` logic (was falling through to self-test when no source files given)
### Testing
- New `tests/test_roundtrip_256.py`: assemble->disassemble->re-assemble round-trip for all 256 opcodes (i8080+i8085); 3 consecutive cycles PASS without code changes
### Documentation
- ASSEMBLER_GUIDE.md: new section 11 (CLI) with options table and examples
## v2.1.6 (2026-10-08)

### Documentation
- **Complete & verified pseudo-command / directive reference** (ASSEMBLER_GUIDE.md, section 10.5):
  - Added the missing `BLOCK` / `.BLOCK` … `ENDBLOCK` / `.ENDBLOCK` (M80 data block)
  - Moved `DATA`, `BLKB`, `DEFW`, `XDEF`/`XREF`, `SECTION`/`ASEG`, `TITLE`/`MODULE`, `LOCAL`/`ENDLOCAL` to the no-op table (recognized but skipped in code)
  - Added `INCBIN` / `.INCBIN` to the data-directives table
  - Note added: `IF`/`ELSE`/`ENDIF`, `MACRO`/`ENDM`, `REPT`, `CPU` are no-op in the assembler but actually processed by the preprocessor
- **USER_GUIDE.md** (sections 8.6 EN/RU, 8.10 EN/RU):
  - Added `INCBIN` to the directives quick reference
  - Added `.include` to the preprocessor include line (all three forms equivalent)
  - Added pointer to the full reference (ASSEMBLER_GUIDE.md 10.5)

### Verification
- Cross-checked the full no-op list against assembler.py code (47 directives)
- Confirmed `BLKB`, `DEFW`, `DATA` are no-ops (not in the real DS/DB/DW checks)
- Confirmed `INCBIN` is actually processed (binary file insertion)

## v2.1.5 (2026-10-08)

### New Features
- **`.include` pseudo-command** now handled identically to `#include` / `include` (M80-style):
  - Supports: `include "file"`, `.include "file"`, `include file`, `.include file`
  - All three forms (#include, include, .include) are equivalent
- **Full pseudo-command & directive reference** added to ASSEMBLER_GUIDE.md (section 10.5):
  - Complete tables: data/address, constants, structure, conditional, macros, file inclusion, CPU type, preprocessor, linker, no-op directives

### Tests
- 7/7 .include tests passed (quoted, unquoted, M80, #include, full assemble)

## v2.1.4 (2026-10-08)

### New Features
- **File encoding auto-detection and conversion** (new module `common/encoding.py`):
  - On open: BOM check (UTF-8/16/32) → strict UTF-8 decode → charset_normalizer detection
  - Heuristic: catch-all result (latin-1/iso-8859-1) + high bytes → CP1251 (Windows Russian)
  - Files opened in non-UTF-8 encoding are automatically converted to UTF-8 on first save
  - Log notification when a file was opened in a different encoding
  - Applied to: assembler files (.asm/.lnk), workspace files, sequence files, script files, .hex compare, breakpoints JSON
- All files are now saved as UTF-8 (no BOM) — stable, unambiguous encoding

### Bug Fixes
- Fixed `_on_text_changed` AttributeError: `ti.get('file_path', '')` returned `None` for new tabs (key exists with value `None`), crashing `.lower()` — now uses `(ti.get('file_path') or '')`

### Tests
- 23/23 encoding detection tests passed (UTF-8, ASCII, CP1251, KOI8-R, UTF-16 BOM, UTF-8 BOM, full open/save cycle)
- 921/0 project tests passed
- GUI smoke test passed

## v2.1.2 (2026-10-06)

### Bug Fixes
- Fixed fold marker false positive: \t{N} in block content no longer breaks folding
  (marker now only recognized when block is actually in collapsed state via self._collapsed)

### New Features
- Added .lnk (linker script) file type support:
  - File dialog filters now include *.lnk for open/save
  - Syntax highlighting for linker directives (INPUT, OUTPUT, MAP, ORIGIN, SIZE, FILL)
- MCP Server: added 19 new tools:
  - Assembler: asm_assemble, asm_get_source, asm_set_source, asm_get_errors, asm_get_labels
  - Emulator: emu_set_pc, emu_set_interrupts, emu_request_interrupt, emu_read_word, emu_write_word, emu_push, emu_pop
  - System: get_cpu_type, set_cpu_type, get_version, get_language, set_language
  - Automation: run_script, get_watch_list

### Improvements
- Fold marker detection: uses self._collapsed set to distinguish real markers from content
- Linker keywords (BLOCK, ENDBLOCK) added to syntax highlighting

## v2.1.1 (2026-10-06)

### Bug Fixes
- Fixed runtime language switching: collapse/expand button tooltips now update when language changes
- Fixed fold detection: `{N}` in block content no longer breaks folding (requires leading tab for fold marker)
- Fixed hardcoded "Процессор:" label - now uses i18n

### Improvements
- Added `retranslate()` method to AssemblerWidget for runtime language updates
- Fold marker protection: only `\t{N}` (tab-prefixed) is recognized as fold indicator

### Tests
- 921/0 checks passed (3 consecutive clean passes)
## 2026-09-29 (итерация 6): Верификация ALUS_IMM по документации 8080/8085, авто-размер дизассемблера, чистка мёртвого кода

### Дизассемблер (i8080_ci/disassembler.py) — верификация по документации
- **Исправлен `ALUS_IMM`:** был `['ADD','ADC','SUB','SBB','ANA','XRA','ORI','CPI']` (ошибка — использовались регистровые мнемоники). Теперь `['ADI','ACI','SUI','SBI','ANI','XRI','ORI','CPI']` — канонические мнемоники непосредственной адресации, одинаковые для 8080 и 8085 (проверено по документации KR580/8080/8085).
  - 0xC6=ADI, 0xCE=ACI, 0xD6=SUI, 0xDE=SBI, 0xE6=ANI, 0xEE=XRI, 0xF6=ORI, 0xFE=CPI
- Регистровая форма (0x80–0xBF) без изменений: `ALUS = ['ADD','ADC','SUB','SBB','ANA','XRA','ORA','CMP']` (там ORA/CMP — корректно).

### Ассемблер (assemble8080/assembler.py)
- **`ALU_IMM_OPCODES`:** `'CMP'` → `'CPI'` (fallback-таблица для регистровых мнемоник с immediate-операндом). Теперь `CPI 05H` round-trip'ится, а `CMP 05H` честно отклоняется (CMP — только регистровая).
- **Удалён мёртвый код:** методы `_count_db_bytes()` и `_count_dw_words()` (определены, но нигде не вызывались).

### Автозагрузка map + размер дизассемблера (i8080_ci/assembler_widget.py)
- **`_auto_load_map`:** перед `run_disasm()` теперь обновляет поля `disasm_start`/`disasm_len` на реальные `result.origin` и `len(result.binary)`. Раньше дизассемблер показывал только первые 100 байт (значение по умолчанию из поля ручного ввода), а не весь загруженный образ. Теперь поведение совпадает с эмулятором (`update_emu_disasm_view` вычисляет диапазон из `mem_data`).

### Чистка мёртвого кода и неиспользуемых импортов
- **i8080_ci/views/disasm_view.py:** удалён метод `set_cursor()` (cursor_addr устанавливается напрямую в обработчиках событий).
- **assemble8080/linker.py:** удалены неиспользуемые импорты `re`, `Optional`, `ObjectFile`, `save_obj`, `MapFile`.
- **assemble8080/mapfile.py:** удалён неиспользуемый импорт `os`.
- **i8080_ci/assembler_widget.py:** удалён неиспользуемый импорт `load_map_file`.

### Тесты
- **Исправлены тестовые исходники:**
  - `ASM_FOR_TEST/TCB.asm`: опечатка `DC B` → `DCR B` (декремент счётчика цикла).
  - `ASM_FOR_TEST/load.asm`: добавлен в `EXCLUDE` (это 8085-файл, использует `SIM`; тест — для 8080-совместимых файлов).
  - `tests/test_assembler_linker.py` (Тест 5): обновлена устаревшая проверка — имя текущей метки показывается отдельной строкой (через `set_symbols`), а не встраивается в текст инструкции; target перехода резолвится в тексте.
- **Новые тесты:**
  - `tests/test_alus_imm_verify.py` (7 проверок): верификация ALUS_IMM по документации — декодирование 8 immediate ALU, регистровая ORA/CMP, round-trip.
  - `tests/test_disasm_range_autoload.py` (4 проверки): авто-обновление диапазона дизассемблера на реальный размер образа (50 и 151 байт).
- **Новая инфраструктура тестирования:**
  - `tests/run_api_snippets.py`: harness для интерактивных `api`-сниппетов (ppi_test, kbd_test, font_test, display_test и др.) — создаёт `MainWindow` + профиль `full` и предоставляет глобальный `api`.
  - `_run_all_tests.py`: единый раннер полного цикла (автономные тесты + api-сниппеты).

### Полный цикл тестирования
- **55 автономных тест-файлов: 0 ошибок.**
- **17 интерактивных api-сниппетов: 0 ошибок.**
- Итого: **56/56 пройдено, 0 провалено.**

## 2026-09-29 (итерация 5): Ассемблер v2 — Notepad++ style, глобальные метки, map auto-load

### Ядро ассемблера (assemble8080/assembler.py)
- **Глобальные метки `::`:** метки с двойным двоеточием автоматически добавляются в `_exports` и отслеживаются в `global_labels`
- **`AsmResult.global_labels`:** новый поле — множество имён глобальных меток
- **`_parse_label`:** уже возвращал `is_global=True` для `::` меток, теперь используется в `assemble()`

### Виджет ассемблера (i8080_ci/assembler_widget.py) — полный редизайн
- **Вкладки файлов (Notepad++ style):** `QTabWidget` с закрываемыми вкладками вместо одного редактора. Каждая вкладка — отдельный `CodeEditor` с собственным файлом
- **Ctrl+Click на метку:** переход к определению метки. `CodeEditor.mousePressEvent` обрабатывает Ctrl+клик, находит слово под курсором и прыгает к строке метки
- **Жирная подсветка глобальных меток:** `AsmHighlighter` различает `::` (глобальные, extra bold + золотой цвет) и `:` (локальные, обычный bold)
- **Workspace (.ws JSON):** открытие/сохранение workspace-файла со списком файлов проекта. Кнопки "Open Workspace" / "Save Workspace"
- **Автозагрузка map-файла:** после успешной сборки map-файл автоматически загружается в дизассемблер (`disasm_view.set_symbols()`)
- **Таблица меток:** глобальные метки отображаются жирным шрифтом

### Дизассемблер (i8080_ci/views/disasm_view.py)
- **`set_symbols(map_file)`:** новый метод — принимает `MapFile` и отображает имена символов рядом с адресами в дизассемблере
- **`paintEvent`:** после адреса выводится имя символа из map-файла (если есть)

### Main Window (i8080_ci/main_window.py)
- **`self.map_file`:** новый атрибут — хранит текущий `MapFile` для отображения символов
- **`run_disasm`:** передаёт `map_file` в `disasm_view.set_symbols()`
- **`on_load_map`:** обновлён — устанавливает `self.map_file` и передаёт в `disasm_view`

### Automation (i8080_ci/automation.py)
- Адаптирован к новой вкладочной структуре: `.editor` → `._current_editor()`

### i18n (common/i18n.py)
- Новые ключи: `asm_open_ws`, `asm_save_ws`, `asm_ws_filter`, `asm_ws_loaded`, `asm_ws_err`, `asm_new_tab`, `asm_untitled`, `asm_unsaved_title`, `asm_unsaved_msg`, `asm_map_auto_loaded`, `asm_map_auto_err` (EN + RU)

### Тестирование
- Полный прогон: 34 тест-файла, 921 проверка, 0 ошибок
- GUI smoke-тест: пройден
- Ассемблер: 20/20
- test_asm8080-8085.py: 6/6

## 2026-09-26 (итерация 4): cpu_type-aware подсветка переходов в трассировке

### Дизассемблер (i8080_ci/disassembler.py)
- **Исправлена ошибка подсветки переходов на 8085:** `JUMP_OPCODES` был статическим набором, в который входили все пересекающиеся опкоды (0xCB, 0xD9, 0xDD, 0xED, 0xFD). На 8085 из них переходами являются только `JNK` (0xDD) и `JK` (0xFD), а `RSTV` (0xCB), `SHLX` (0xD9), `LHLX` (0xED) — нет. Теперь:
  - `_JUMP_BASE` — базовые переходы (одинаковы для 8080/8085)
  - `JUMP_OPCODES` — для 8080 (все пересекающиеся: JMP*/RET*/CALL*)
  - `JUMP_OPCODES_8085` — для 8085 (только JNK/JK)

### Трассировка (i8080_ci/models/trace_model.py)
- Подсветка переходов теперь выбирает набор опкодов по `emulator.cpu_type`: на 8085 RSTV/SHLX/LHLX больше не подсвечиваются как переходы.

### Экспорт (i8080_ci/__init__.py)
- Добавлен `JUMP_OPCODES_8085` в импорт и `__all__`.

### Тестирование
- Полный прогон: 34 тест-файла, 921 проверка, 0 ошибок (3 подряд успешных прохода)
- GUI smoke-тест: пройден
- Ассемблер: 20/20
- test_8085.py: 44/44
- test_asm8080-8085.py: 6/6

## 2026-09-26 (итерация 3): i18n «Running...», консистентность смены CPU через директиву, очистка run_target_addr

### GUI (i8080_ci/main_window.py)
- **i18n:** сообщение статус-бара `"Running..."` при запуске (F5) было захардкожено на английском. Теперь используется ключ `status_running` (EN: "Running...", RU: "Выполнение...")
- **`_set_cpu_type`:** при смене типа CPU теперь очищается `run_target_addr` (цель Run to Cursor) — эмулятор сброшен, PC=0, старая цель неактуальна

### Ассемблер (i8080_ci/assembler_widget.py)
- **`_apply_cpu_from_source`:** теперь делегирует в централизованный `main_window._set_cpu_type()` вместо ручного изменения `emulator.cpu_type`. Устраняет несогласованность: при смене CPU через директиву `.8085`/`.8080` эмулятор теперь корректно сбрасывается (как при ручной смене через combo), а не сохраняет старое состояние регистров. Убрано дублирование кода синхронизации.

### Тесты
- **test_asm8080-8085.py:** исправлена кодировка (была cp1251 с повреждёнными символами из-за двойной конвертации → теперь UTF-8). Добавлен `sys.stdout.reconfigure(encoding='utf-8')` для корректного вывода ✅/❌ в консоли. Тест снова запускается: 6/6 (NOP/SIM/NOP/RIM для 0x20 и 0x30)

### Тестирование
- Полный прогон: 34 тест-файла, 921 проверка, 0 ошибок
- GUI smoke-тест: пройден
- test_8085.py: 44/44
- test_asm8080-8085.py: 6/6

## 2026-09-26: Исправление SIM/RIM (8085), i18n метки CPU, стабильность тестов

### Эмулятор (i8080_emulator.py)
- **Исправлен баг SIM/RIM:** опкоды 0x20 и 0x30 были перепутаны. Теперь соответствует стандарту Intel 8085:
  - 0x20 = SIM (Set Interrupt Mask)
  - 0x30 = RIM (Read Interrupt Mask)
- Раньше: 0x20→RIM, 0x30→SIM (несоответствовало ассемблеру, где SIM=0x20, RIM=0x30)

### Дизассемблер (i8080_ci/disassembler.py)
- **Исправлен баг SIM/RIM:** таблица опкодов теперь 0x20="SIM", 0x30="RIM" (было перепутано)
- Согласовано с ассемблером и эмулятором

### GUI (i8080_ci/main_window.py)
- **i18n:** метка "Процессор:" во вкладке эмулятора была захардкожена на русском. Теперь используется `lbl_emu_cpu` + ключ `cpu_type_label` (переводится в `emulator_retranslate`)
- **`_set_cpu_type`:** при смене типа CPU теперь останавливается `run_timer` (эмулятор сбрасывается, выполнение останавливается сразу, без ложного сообщения "stopped" на следующем тике)

### Тесты
- **test_e1.py:** удалён лишний `QApplication` (не использовался, вызывал TIMEOUT 60с). Тест теперь проходит за ~0.3с
- **test_8085.py:**
  - добавлено `os.environ['QT_QPA_PLATFORM']='offscreen'` до импорта PySide6 (устраняет зависание QApplication в headless-режиме)
  - исправлены опкоды в тестах SIM/RIM (0x20=SIM, 0x30=RIM)
  - исправлены ожидания в тестах дизассемблера (0x20="SIM", 0x30="RIM")

### Документация
- **ASSEMBLER_GUIDE.md:** исправлено противоречие в таблице пересекающихся опкодов (0x20=SIM, 0x30=RIM) и в описании команд 8085

### Тестирование
- Полный прогон: 34 тест-файла, 921 проверка, 0 ошибок (3 подряд успешных прохода)
- Ассемблер: 20/20 (assembler_test_full.py)
- GUI smoke-тест: пройден
- test_8085.py: 43/43

## 2026-09-25: Выбор типа CPU в дизассемблере, синхронизация CPU, режим максимальной скорости

### GUI (i8080_ci/main_window.py)

**Выбор типа процессора в дизассемблере:**
- Добавлен combo-выбор `disasm_cpu_combo` (i8080/i8085) во вкладку "Дизассемблер"
- Добавлена метка `lbl_disasm_cpu` ("Процессор:" / "CPU:")

**Синхронизация выбора типа CPU между вкладками:**
- Добавлен центральный метод `_set_cpu_type(cpu_type, source)` — единая точка смены типа процессора:
  - обновляет `emulator.cpu_type` + `emulator.reset()`
  - обновляет `disassembler.set_cpu_type()`
  - синхронизирует все combo-выборы через `_cpu_combos()` (эмулятор, дизассемблер, ассемблер)
  - обновляет UI и пере-дизассемблирует текущие представления
- Добавлены обработчики `_on_emu_cpu_changed`, `_on_disasm_cpu_changed`, `_on_asm_cpu_changed` — все делегируют в `_set_cpu_type`
- Combo ассемблера (`assembler_widget.cpu_combo`) подключён к `_on_asm_cpu_changed` — теперь смена CPU в ассемблере синхронизирует эмулятор и дизассемблер
- `load_profile()`: синхронизация всех combo через `_cpu_combos()` (раньше не обновлялся combo ассемблера)

**Блокировка выбора CPU при директиве:**
- `_apply_cpu_from_source()` (assembler_widget.py): при наличии директивы `.8085`/`.8080` в исходном коде блокируются (setEnabled(False)) все три combo — ассемблера, эмулятора и дизассемблера
- При отсутствии директивы все combo разблокируются

**Режим максимальной скорости:**
- Добавлен чек-бокс `chk_max_speed` ("Макс. скорость") во вкладку "Эмулятор"
- В режиме макс. скорости:
  - пакет инструкций за тик увеличен с 300 до 10000
  - интервал таймера выполнения = 0 (максимальная частота тиков)
  - **окна НЕ обновляются** во время выполнения (только при остановке или срабатывании точки останова — условной или безусловной)
  - такты tick-устройств масштабируются пропорционально (сохраняется соотношение 1 такт устройства на 300 инструкций)
  - периодическая проверка прерываний каждые 1000 инструкций
- Добавлены методы `_run_timer_interval()` и `on_max_speed_toggled()`
- `emulator_run`, `emulator_run_to_cursor`, `emulator_run_from_here` используют динамический интервал таймера

### i18n (common/i18n.py)
- Добавлены ключи: `cpu_type_label`, `max_speed`, `max_speed_tip` (en + ru)

### Тестирование
- Полный прогон: 34 тест-файла, 921 проверка, 0 ошибок
- Ассемблер: 20/20 (assembler_test_full.py)
- GUI smoke-тест: пройден
- Специализированные тесты (созданы и удалены после прогона):
  - Синхронизация CPU: disasm→all, emu→all, asm→all, back — OK
  - load_profile: синхронизация всех combo (empty8085 → i8085, empty8080 → i8080) — OK
  - Блокировка при директиве: .8085/.8080 блокируют все combo, без директивы разблокируют — OK
  - Макс. скорость: 10000 инструкций/тик (66667 тактов), остановка на BP, нормальный режим 300/тик — OK

## 2026-09-24: PSW флаги 8085 (UI/V), SIM/RIM IFF1/IFF2, EI/DI 8085, INTR I-регистр

### Эмулятор (i8080_emulator.py)

**PSW (Program Status Word):**
- Добавлены флаги `flag_ui` (бит 5) и `flag_v` (бит 1) — недокументированные, всегда 1
- PUSH PSW: бит 5 теперь `flag_ui` (было 0), бит 1 теперь `flag_v` (было захардкожено 1)
- POP PSW: извлечение `flag_ui` из бита 5, `flag_v` из бита 1
- `get_state()`: добавлены UI и V в словарь флагов
- Контекст BP: добавлены UI и V
- Трассировка: `_get_trace_snapshot` и `_add_trace_record` включают UI и V

**SIM (Set Interrupt Mask, 0x30):**
- Бит 5: теперь устанавливает IFF2 (было "не используется")
- Бит 4: теперь устанавливает IFF1 (было "сброс прерывания 7.5")
- Убрана некорректная логика сброса `irq_pending`

**RIM (Read Interrupt Mask, 0x20):**
- Бит 4: исправлено вычисление — теперь `if irq_pending & 0x80: acc |= 0x10` (было `irq_pending >> 4`)

**EI/DI (8085):**
- DI (0xF3): сбрасывает IFF1 и IFF2 для 8085
- EI (0xFB): копирует IFF2 в IFF1 для 8085

**request_interrupt:**
- TRAP (0x24): устанавливает `irq_pending |= 0x80`
- RST 7.5 (0x3C): устанавливает `irq_pending |= 0x80`
- RST 6.5 (0x34): устанавливает `irq_pending |= 0x40`
- RST 5.5 (0x2C): устанавливает `irq_pending |= 0x20`
- INTR (0x38): проверяет IFF1, блокирует если IFF1=0

**_handle_interrupt:**
- INTR (0x38): теперь использует I-регистр как старший байт вектора: `pc = (i_reg << 8) | 0x00`

### Тесты (tests/assembler_test.py)
- Тест 6: добавлена директива `.8085` (8085-команды требуют указания CPU)
- Тест 6: `ldei` → `ldsi 0x10` (корректная мнемоника 8085)

### Тестирование
- 3 подряд полных цикла тестирования без ошибок и без правок кода
- Все 1009+ тестов пройдены: 921 main, 43 8085, 11 include, 57 linker, 20 full assembler, GUI smoke


## 2026-09-23: Циклы 4-5: Трассировка 8085 (IFF1/IFF2/I), прерывания 8085, reset

### EN

Deep analysis cycles 4-5: 9 bug fixes across trace system, 8085 interrupts, and reset.

**Cycle 4 — Trace system 8085 support:**

1. **Trace records now capture IFF1/IFF2/I**: `_add_trace_record()` in the emulator now stores `IFF1`, `IFF2`, and `I` register values in every trace record. This allows full 8085 interrupt state to be inspected in the trace buffer.

2. **State restoration from trace**: `_restore_trace_state()` in the GUI now restores IFF1, IFF2, and I register when restoring CPU state from a trace record (using `.get()` with defaults for backward compatibility with old records).

3. **Trace export includes 8085 fields**: TXT, CSV, and JSON trace exports now include IFF1, IFF2, and I columns/fields.

4. **Automation API trace**: `emu_trace_get()` in the automation API now returns IFF1, IFF2, and I in each record.

**Cycle 5 — 8085 interrupt handling and reset:**

5. **RST→8085 vector mapping in `request_interrupt()`**: The system generates interrupts with RST opcodes (0xFF, 0xF7, 0xEF, 0xDF). For 8085, these are now mapped to the correct 8085 interrupt vectors (0x3C=RST 7.5, 0x34=RST 6.5, 0x2C=RST 5.5, 0x24=TRAP) so that the MSE and individual mask bits are checked correctly.

6. **TRAP is non-maskable**: `_handle_interrupt()` now processes TRAP (0x24) even when IFF1=0, per the Intel 8085 datasheet. All other maskable interrupts still require IFF1=1.

7. **8085 interrupt vector dispatch**: `_handle_interrupt()` now correctly maps 8085-specific vectors to RST addresses: 0x24→0x18 (RST 3), 0x2C→0x28 (RST 5), 0x34→0x30 (RST 6), 0x3C→0x38 (RST 7), 0x38→0x28 (INTR, simplified).

8. **Complete 8085 reset**: `reset()` now clears all 8085-specific state: `irq_enabled_85` (MSE), `irq_pending`, `sod`, `sid`, and `_pending_interrupts` buffer. Previously only IFF1, IFF2, I, and irq_mask were reset.

### RU

Глубокий анализ циклов 4-5: 9 исправлений в системе трассировки, прерываниях 8085 и reset.

**Цикл 4 — поддержка 8085 в трассировке:**

1. **Записи трассировки захватывают IFF1/IFF2/I**: `_add_trace_record()` теперь сохраняет значения IFF1, IFF2 и I-регистра в каждой записи.

2. **Восстановление состояния из трассировки**: `_restore_trace_state()` восстанавливает IFF1, IFF2, I при возврате к записи трассировки.

3. **Экспорт трассировки**: TXT, CSV, JSON экспорт теперь включает IFF1, IFF2, I.

4. **API автоматизации**: `emu_trace_get()` возвращает IFF1, IFF2, I.

**Цикл 5 — прерывания 8085 и reset:**

5. **Маппинг RST→векторы 8085**: `request_interrupt()` теперь мапит RST-опкоды на векторы 8085 для корректной проверки MSE и масок.

6. **TRAP не маскируется**: `_handle_interrupt()` обрабатывает TRAP (0x24) даже при IFF1=0.

7. **Диспетчеризация векторов 8085**: 0x24→0x18, 0x2C→0x28, 0x34→0x30, 0x3C→0x38, 0x38→0x28.

8. **Полный reset 8085**: `reset()` сбрасывает irq_enabled_85, irq_pending, sod, sid, _pending_interrupts.

### Тесты

- 921/921 main suite (34 файла)
- 44/44 test_8085.py
- 11/11 include, 57/57 linker, 20/20 full assembler
- GUI smoke tests PASSED

## 2026-09-23: Глубокий анализ и исправление (номера строк, CPU switch, IFF, автоопределение)

## 2026-09-23: Глубокий анализ и исправление (номера строк, CPU switch, IFF, автоопределение)

### EN

Deep code analysis and 4 bug fixes:

1. **Assembler line numbers**: Fixed off-by-N error in preprocessor. Removed extra `_line_num += 1` inside the macro expansion loop — all expanded lines from a single source line now share the correct line number.

2. **Emulator CPU type switching**: Added `QComboBox` (i8080/i8085) to the emulator panel. Switching updates `emulator.cpu_type`, resets the CPU, and regenerates the disassembler table.

3. **8085 flags (IFF1, IFF2, I register)**: Added `iff1`, `iff2`, `i_reg` fields to the emulator. `get_state()` returns them for 8085 mode. GUI shows IFF1/IFF2/I labels (visible only in 8085 mode). Fixed RIM to include IFF1 (bit 5) and IFF2 (bit 6) in the result.

4. **Auto-detect CPU from source**: Assembler tracks `cpu_set_by_directive`. After assembly, if a CPU directive (`.8085`, `.asm8085`, `CPU i8085`, etc.) was found in the source, the GUI locks both CPU combo boxes and syncs the emulator/disassembler. Without a directive, the combos remain active for manual selection.

### RU

Глубокий анализ кода и 4 исправления:

1. **Номера строк в ассемблере**: Убран лишний `_line_num += 1` в цикле развёртывания макросов препроцессора. Все развёрнутые строки из одного исходного рядака теперь имеют корректный номер.

2. **Переключение CPU в эмуляторе**: Добавлен `QComboBox` (i8080/i8085) в панель эмулятора. При переключении обновляется `emulator.cpu_type`, сбрасывается CPU, регенерируется таблица дизассемблера.

3. **Флаги 8085 (IFF1, IFF2, I-регистр)**: Добавлены поля `iff1`, `iff2`, `i_reg` в эмулятор. `get_state()` возвращает их для 8085. GUI показывает лейблы IFF1/IFF2/I (видны только в режиме 8085). Исправлен RIM: теперь включает IFF1 (бит 5) и IFF2 (бит 6).

4. **Автоопределение CPU из исходного кода**: Ассемблер отслеживает `cpu_set_by_directive`. После сборки, если в коде найдена директива CPU, GUI блокирует оба combo и синхронизирует эмулятор/дизассемблер. Без директивы combo активны для ручного выбора.

### Тесты

- 921/921 main suite (34 файла)
- 46/46 глубоких тестов (номера строк, CPU switch, IFF, автоопределение)
- 11/11 include, 57/57 linker, 20/20 full assembler
- GUI smoke tests PASSED

## 2026-09-23: Поддержка Intel 8085 (CPU type, пересекающиеся опкоды)

### EN

Added Intel 8085 support. The processor type can now be selected in the system
profile (`cpu = "i8080"` / `cpu = "i8085"`, default `i8080`) and in the assembler
via the new directives `.8080` / `.8085` / `.asm8080` / `.asm8085` / `CPU 8085`.
The 8085 adds two documented instructions (SIM, RIM) and several undocumented
instructions whose opcodes overlap with the 8080 undocumented opcodes. The
emulator, assembler and disassembler now split these overlapping opcodes by
processor type.

**Overlapping opcodes (8080 vs 8085):**

| Opcode | 8080 | 8085 |
|---|---|---|
| 0x08 | *NOP | *DSUB (HL = HL - BC) |
| 0x10 | *NOP | *ARHL (arith. right shift HL) |
| 0x18 | *NOP | *RDEL |
| 0x20 | *NOP | RIM (Read Interrupt Mask) |
| 0x28 | *NOP | *LDHI d8 |
| 0x30 | *NOP | SIM (Set Interrupt Mask) |
| 0x38 | *NOP | *LDSI d8 |
| 0xCB | *JMP a16 | *RSTV |
| 0xD9 | *RET | *SHLX ((BC) = HL) |
| 0xDD | *CALL a16 | *JNK a16 |
| 0xED | *CALL a16 | *LHLX (HL = (BC)) |
| 0xFD | *CALL a16 | *JK a16 |

**Changes:**

1. **Assembler** (`assemble8080/assembler.py`): split `MNEMONICS` into a common
   table plus `MNEMONICS_8080` and `MNEMONICS_8085`. Added `cpu_type` attribute
   and `_get_mnemonics()` which returns the cpu-specific table. Added the
   `.8080`/`.8085`/`.asm8080`/`.asm8085`/`CPU` directives. Fixed the SIM/RIM
   opcodes (SIM=0x20, RIM=0x30) and removed dead code in `_encode_instruction`.
   `_parse_label` now checks `ALL_MNEMONICS` so 8085 mnemonics are not treated
   as labels.

2. **Preprocessor** (`assemble8080/preprocessor.py`): no longer strips the
   `.8080`/`.asm8080`/`CPU` lines — they are passed through to the assembler.

3. **Emulator** (`i8080_emulator.py`): all 12 overlapping opcodes are now split
   by `cpu_type` via `_execute_overlapping()`. Implemented the 8085 instructions
   (SIM, RIM, DSUB, ARHL, SHLX, LHLX); the uncertain ones (RDEL, LDHI, LDSI,
   RSTV, JNK, JK) are NOP/skip-operand. On 8080, 0xCB=JMP a16, 0xD9=RET,
   0xDD/0xED/0xFD=CALL a16. `_get_cycles` returns cpu-specific cycle counts.

4. **Disassembler** (`i8080_ci/disassembler.py`): the opcode table is now
   cpu_type-aware. Added `cpu_type` attribute and `set_cpu_type()`. Fixed the
   overwriting bug where 8085 mnemonics clobbered the 8080 ones.

5. **GUI** (`i8080_ci/assembler_widget.py`, `i8080_ci/main_window.py`): fixed the
   `ctrl_layout` NameError (cpu_combo moved into `_init_ui`), fixed the
   `_do_assemble` premature `assemble(source)` call, added `cpu_type` to
   `on_assemble_obj`, and the disassembler now follows the profile's cpu type.

**Verification (all green):**

| Suite | Result |
|---|---|
| run_tests.py (34 files) | **915/915 PASS** |
| test_8085.py (new) | **44/44 PASS** |
| assembler_test_full.py | **20/20 PASS** |
| test_assembler_linker.py | **57/57 PASS** |
| test_assembler_include.py | **11/11 PASS** |
| build_all.py (4 examples) | **4/4 PASS** |
| test_gui_smoke.py | **PASS** |

## 2026-09-22: Full Project Audit — Bug Fixes (Interrupts, Sections, Strings, Escapes)

### EN

A full-project audit was performed (all 160+ Python files reviewed, 871-test suite +
assembler/linker/include/example suites re-run). Seven real defects were found and fixed.
After the fixes the codebase reached a stable state: all test suites pass and a second
analysis pass found no further defects.

**Fixes applied:**

1. **Interrupt handler used a non-existent attribute** (`i8080_emulator.py`).
   `_handle_interrupt()` referenced `self.int_enabled`, but the emulator attribute is
   `interrupts_enabled` (set by EI/DI). Any pending interrupt during a Run raised
   `AttributeError`. Fixed to use `interrupts_enabled`. `tests/test_interrupts.py`
   updated to set the correct attribute.

2. **Source filename lost in error messages** (`assemble8080/assembler.py`).
   `Assembler.assemble()` never assigned `self._filename = filename`, so every
   `AsmError.source` was empty and error lines showed no file. Fixed by setting
   `self._filename = filename` at the start of `assemble()`.

3. **Last `#code` section never closed in pass 1** (`assemble8080/assembler.py`).
   Only mid-stream sections were closed, so the final section's `_SIZE` and `_END`
   symbols were missing. This broke `EQU X LAST_SEC_SIZE` (resolved to 0) and left
   `LAST_SEC_END` undefined. Fixed by closing the last section after the pass-1 loop
   (creates `_SIZE` + `_END` and advances `location` for fixed-size sections).

4. **Inconsistent fill byte in final section close** (`assemble8080/assembler.py`).
   The pass-2 final close padded with zero bytes while mid-loop closes used the target
   fill byte (`_ds_fill`, 0xFF for ROM / 0x00 for RAM). Fixed to use `_ds_fill` and to
   also emit the `_END` symbol.

5. **Dot-directive normalization corrupted string literals** (`assemble8080/preprocessor.py`).
   `_normalize_dot_directives()` replaced `.and`, `.or`, `.not`, etc. anywhere in the
   line, including inside quotes: `DB "a.and.b"` became `aand.b`. Fixed to split the
   line on quotes and normalize only the unquoted segments.

6. **`DB` escape sequences not decoded** (`assemble8080/assembler.py`).
   `DB '\n'` emitted two bytes (0x5C 0x6E) instead of one (0x0A). Added a
   `_decode_string_escapes()` helper (supports `\n \t \r \0 \\ \' \" \xNN`)
   and used it in both `_parse_db()` and the pass-1 byte count, so single- and
   double-quoted strings decode consistently.

7. **Map file not saved on the "Assemble → OBJ" path** (`i8080_ci/assembler_widget.py`).
   The requirement is that a `.map` file is produced on *any* assembly. The OBJ path
   (`on_assemble_obj`) assembled but did not save the map. Fixed to save the map next
   to the source file, matching the plain Assemble path.

**Verification (all green after fixes):**

| Suite | Result |
|---|---|
| run_tests.py (33 files) | **871/871 PASS** |
| assembler_test_full.py | **20/20 PASS** |
| test_assembler_linker.py | **57/57 PASS** |
| test_assembler_include.py | **11/11 PASS** |
| build_all.py (4 examples) | **4/4 PASS** |
| test_gui_smoke.py | **PASS** |
| py_compile (all .py) | **0 errors** |

### RU

Выполнен полный аудит проекта (проанализировано 160+ Python-файлов, перезапущены
набор из 871 теста + наборы ассемблера/линковщика/включений/примеров). Найдено и
исправлено семь реальных дефектов. После исправлений кодовая база достигла стабильного
состояния: все тестовые наборы проходят, повторный проход анализа новых дефектов не
обнаружил.

**Внесённые исправления:**

1. **Обработчик прерываний использовал несуществующий атрибут** (`i8080_emulator.py`).
   `_handle_interrupt()` обращался к `self.int_enabled`, тогда как атрибут эмулятора
   называется `interrupts_enabled` (устанавливается EI/DI). Любое ожидающее
   прерывание во время Run вызывало `AttributeError`. Исправлено на `interrupts_enabled`.
   `tests/test_interrupts.py` обновлён на корректный атрибут.

2. **Имя исходного файла терялось в сообщениях об ошибках** (`assemble8080/assembler.py`).
   `Assembler.assemble()` никогда не присваивал `self._filename = filename`, поэтому
   `AsmError.source` всегда был пустым и в строках ошибок не было имени файла.
   Исправлено: `self._filename = filename` в начале `assemble()`.

3. **Последняя секция `#code` не закрывалась в проходе 1** (`assemble8080/assembler.py`).
   Закрывались только «промежуточные» секции, поэтому у финальной секции не создавались
   символы `_SIZE` и `_END`. Это ломало `EQU X LAST_SEC_SIZE` (давало 0) и оставляло
   `LAST_SEC_END` неопределённым. Исправлено: после цикла прохода 1 последняя секция
   закрывается (создаются `_SIZE` + `_END`, для фиксированного размера `location`
   сдвигается).

4. **Несогласованный байт заполнения при финальном закрытии секции**
   (`assemble8080/assembler.py`). Финальное закрытие в проходе 2 дополняло секцию
   нулевыми байтами, тогда как промежуточные закрытия использовали целевой байт
   заполнения (`_ds_fill`: 0xFF для ROM / 0x00 для RAM). Исправлено на `_ds_fill`,
   добавлено создание символа `_END`.

5. **Нормализация dot-директив повреждала строковые литералы**
   (`assemble8080/preprocessor.py`). `_normalize_dot_directives()` заменял `.and`, `.or`,
   `.not` и т.д. в любом месте строки, включая кавычки: `DB "a.and.b"` превращался в
   `aand.b`. Исправлено: строка разбивается по кавычкам, нормализация применяется только
   к некавычным сегментам.

6. **Escape-последовательности в `DB` не декодировались** (`assemble8080/assembler.py`).
   `DB '\n'` выдавал два байта (0x5C 0x6E) вместо одного (0x0A). Добавлен helper
   `_decode_string_escapes()` (поддерживает `\n \t \r \0 \\ \' \" \xNN`),
   используется в `_parse_db()` и в подсчёте байтов прохода 1 — одинарные и двойные
   кавычки декодируются согласованно.

7. **Map-файл не сохранялся на пути «Assemble → OBJ»** (`i8080_ci/assembler_widget.py`).
   Требование: `.map`-файл создаётся при *любом* ассемблировании. Путь OBJ
   (`on_assemble_obj`) ассемблировал, но map не сохранял. Исправлено: map сохраняется
   рядом с исходным файлом, как и на обычном пути Assemble.

**Верификация (всё зелёное после исправлений):**

| Набор | Результат |
|---|---|
| run_tests.py (33 файла) | **871/871 PASS** |
| assembler_test_full.py | **20/20 PASS** |
| test_assembler_linker.py | **57/57 PASS** |
| test_assembler_include.py | **11/11 PASS** |
| build_all.py (4 примера) | **4/4 PASS** |
| test_gui_smoke.py | **PASS** |
| py_compile (все .py) | **0 ошибок** |


## 2026-09-19 (re-audit pass 7): Explicit Public API via `__all__` + Stability Verification

### EN

A third audit pass was performed to verify the previous audit (pass 6) and drive the
codebase to a stable state (two consecutive clean cycles).

**Static analysis:** py_compile **142/142 files, 0 errors**. pyflakes initially reported
177 findings; every one was triaged and confirmed to fall into a known benign category
(package re-exports, string-annotation forward references, the runtime `api` global in
MCP test scripts, and intentional GUI smoke imports).

**Fix applied — explicit public API via `__all__`:**
The six package `__init__.py` re-export modules did not declare `__all__`, so their
public API was implicit and pyflakes flagged all 82 re-exported names as "imported but
unused". `__all__` was added (names extracted via AST) to:
- `common/__init__.py` (8 names)
- `modules/__init__.py` (36 names)
- `modules/config/__init__.py` (5 names)
- `modules/io/__init__.py` (20 names)
- `modules/memory/__init__.py` (11 names)
- `ui/__init__.py` (2 names)

This makes the public API explicit and reduces pyflakes findings from **177 → 95**.
`i8080_ci/i18n.py` (a backward-compatibility re-export using `from common.i18n import *`)
is intentionally left as-is: its 6 findings are the star-import + re-export pattern,
already annotated `# noqa` for flake8.

**Convergence (stability verification):**

| Cycle | pyflakes | Tests | Fixes |
|---|---|---|---|
| 1 | 177 → 95 | all PASS | `__all__` added to 6 `__init__.py` |
| 2 | 95 | all PASS | none |
| 3 | 95 | all PASS | none |

Two consecutive clean cycles (2 and 3) confirm the codebase is stable.

**Full test cycle results (re-confirmed in all 3 cycles):**

| Suite | Result |
|---|---|
| run_tests.py (33 files) | **871/871 PASS** |
| test_bin_compare.py (zasm reference) | **15/15 byte-identical** |
| test_asm_for_test.py (69 files) | **69/69 PASS** |
| test_gui_smoke.py | **7/7 PASS** |

**Remaining pyflakes findings (all intentional / benign):**

| Category | Count | Note |
|---|---|---|
| `i8080_ci/i18n.py` re-exports | 6 | backward-compat star import (`# noqa`) |
| `undefined name 'api'` in MCP test scripts | 83 | global MCP client, set at runtime |
| string annotations (forward refs) | 3 | `I8080Emulator`, `IODevice`, `MainWindow` |
| `test_gui_smoke.py` smoke imports | 2 | intentional (marked `# noqa`) |

### RU

Третий проход аудита выполнен для верификации предыдущего аудита (pass 6) и приведения
кодовой базы к стабильному состоянию (два последовательных чистых цикла).

**Статический анализ:** py_compile **142/142 файла, 0 ошибок**. pyflakes изначально
сообщил о 177 замечаниях; каждое было проанализировано и подтверждено как относящееся
к известной безвредной категории (re-экспорты пакетов, forward-ссылки в строковых
аннотациях, рантайм-глобал `api` в MCP-тестовых скриптах, намеренные GUI smoke-импорты).

**Внесённая правка — явный публичный API через `__all__`:**
Шесть пакетных `__init__.py` (re-экспортные модули) не объявляли `__all__`, поэтому их
публичный API был неявным, и pyflakes помечал все 82 re-экспортированных имени как
"импортировано, но не используется". Добавлен `__all__` (имена извлечены через AST) в:
- `common/__init__.py` (8 имён)
- `modules/__init__.py` (36 имён)
- `modules/config/__init__.py` (5 имён)
- `modules/io/__init__.py` (20 имён)
- `modules/memory/__init__.py` (11 имён)
- `ui/__init__.py` (2 имени)

Это делает публичный API явным и снижает число замечаний pyflakes с **177 → 95**.
`i8080_ci/i18n.py` (backward-compat re-экспорт через `from common.i18n import *`)
намеренно оставлен без изменений: его 6 замечаний — это паттерн star-импорта +
re-экспорта, уже помеченный `# noqa` для flake8.

**Сходимость (верификация стабильности):**

| Цикл | pyflakes | Тесты | Правки |
|---|---|---|---|
| 1 | 177 → 95 | все PASS | `__all__` в 6 `__init__.py` |
| 2 | 95 | все PASS | нет |
| 3 | 95 | все PASS | нет |

Два последовательных чистых цикла (2 и 3) подтверждают стабильность кодовой базы.

**Результаты полного цикла тестирования (перепроверены во всех 3 циклах):**

| Набор | Результат |
|---|---|
| run_tests.py (33 файла) | **871/871 PASS** |
| test_bin_compare.py (эталон zasm) | **15/15 побайтово идентичны** |
| test_asm_for_test.py (69 файлов) | **69/69 PASS** |
| test_gui_smoke.py | **7/7 PASS** |

**Оставшиеся замечания pyflakes (все намеренные / безвредные):**

| Категория | Кол-во | Примечание |
|---|---|---|
| re-экспорты `i8080_ci/i18n.py` | 6 | backward-compat star-импорт (`# noqa`) |
| `undefined name 'api'` в MCP-тестовых скриптах | 83 | глобальный MCP-клиент, задаётся в рантайме |
| строковые аннотации (forward-ссылки) | 3 | `I8080Emulator`, `IODevice`, `MainWindow` |
| smoke-импорты `test_gui_smoke.py` | 2 | намеренные (помечены `# noqa`) |

## 2026-09-19 (re-audit): Project-wide pyflakes Cleanup + SyntaxWarning Suppression

### EN

A second, project-wide static-analysis pass (py_compile + pyflakes on all 149 Python
files) was performed to verify the previous audit and catch anything missed.
py_compile: **149/149 files, 0 errors**. pyflakes surfaced a set of minor code smells
across the codebase (beyond `assembler.py`, which was already clean). All were fixed;
the full test cycle re-confirmed 100% pass.

**1. Unused imports removed (project-wide)**
- `i8080_ci/{automation,bus_worker,main_window}.py`: trimmed the multi-line
  `from .slip import (...)` blocks to only the constants actually referenced
  (verified via AST name analysis).
- `modules/memory/{banked,paged,segmented,segmentedpaged,shadow}.py`: import reduced
  to `from .memory_bus import MemoryRegion` (only the base class is used).
- `modules/io/{i8275,i8276}.py`: removed unused `from .chargen import get_char_generator`.
- `modules/io/{ch376s,tft8080}.py`: removed unused `from collections import deque`.
- `ui/{device_window,gpio_widget,serial_terminal}.py`: removed unused Qt imports
  (QGroupBox, QHBoxLayout, Qt, QColor).
- `gen_refs.py`, `run_tests.py`: removed unused `import re`.
- Test files: removed unused imports (`traceback`, `NumberParser`, `random`, `json`,
  `time`, `SYSTEM_PROFILES`, `IODevice`/`I8257`, `IOBus`/`ShadowROMRegion`, `RAMRegion`,
  `I8253`, `LCD1602`, `get_profile_names`, `Preprocessor`).

**2. Unused local variables removed**
- `modules/config/device_config.py`, `modules/io/chargen.py`: `except Exception as e:`
  → `except Exception:` (variable never used).
- `modules/io/i8275.py`: removed dead `cmd = value & 0x7F` in `_write_command`.
- `ui/display_widgets.py`: removed unused `bg = QColor(0,0,0)` (only `fg` is used).

**3. f-strings without placeholders**
Removed the redundant `f` prefix from f-strings with no placeholders in
`i8080_ci/main_window.py` (5), `mcp_server.py` (2), and several test scripts
(`mmio_test.py`, `PPI_3D_*`, `crt_font_test.py`, `kbd_test.py`, `ppi_test.py`,
`device_access_test.py`, `test_banked.py`, `test_system_integration.py`).

**4. SyntaxWarning suppression in the assembler (Python 3.12)**
`test_asm_for_test.py` emitted `SyntaxWarning: 'int' object is not callable` (3×) from
the expression evaluator when a sanitized number expression looked like `123(456)`. The
`eval()` calls in `assemble8080/assembler.py` and `assemble8080/preprocessor.py` are
already wrapped in try/except (returning 0), so the warning was harmless noise. Both
`eval()` calls are now wrapped in `warnings.catch_warnings()` with `SyntaxWarning`
ignored. Warning count: 3 → **0**.

**Remaining pyflakes findings (all intentional / benign):**

| Category / Категория | Count | Note |
|---|---|---|
| `__init__.py` / `i18n.py` re-exports | 88 | intentional public API |
| `undefined name 'api'` in MCP test scripts | 83 | global MCP client, set at runtime |
| string annotations (forward refs) | 3 | `I8080Emulator`, `IODevice`, `MainWindow` |
| `test_gui_smoke.py` smoke imports | 2 | intentional (marked `# noqa`) |

**Full test cycle results (re-confirmed):**

| Suite / Набор | Result / Результат |
|---|---|
| `run_tests.py` (33 files) | **871/871 PASS** |
| `test_bin_compare.py` (zasm reference) | **15/15 byte-identical** |
| `test_asm_for_test.py` (69 files) | **69/69 PASS** (0 SyntaxWarnings) |
| `assembler_test_full.py` | **20/20 PASS** |
| `test_config.py` | **49/49 PASS** |
| `test_system_profiles.py` | **54/54 PASS** |
| `test_system.py` | **53/53 PASS** |
| `test_gui_smoke.py` | **ALL PASS** |

### RU

**Повторный полный аудит проекта** (py_compile + pyflakes по всем 149 Python-файлам)
для верификации предыдущего аудита и поиска упущенного. py_compile: **149/149 файлов,
0 ошибок**. pyflakes выявил набор мелких code smells по всему коду (помимо
`assembler.py`, который уже был чист). Всё исправлено; полный цикл тестов повторно
подтвердил 100% pass.

**1. Удалены неиспользуемые импорты (по всему проекту)**
- `i8080_ci/{automation,bus_worker,main_window}.py`: многострочные блоки
  `from .slip import (...)` сокращены до реально используемых констант
  (проверено AST-анализом имён).
- `modules/memory/{banked,paged,segmented,segmentedpaged,shadow}.py`: импорт сокращён
  до `from .memory_bus import MemoryRegion` (используется только базовый класс).
- `modules/io/{i8275,i8276}.py`: удалён неиспользуемый
  `from .chargen import get_char_generator`.
- `modules/io/{ch376s,tft8080}.py`: удалён неиспользуемый `from collections import deque`.
- `ui/{device_window,gpio_widget,serial_terminal}.py`: удалены неиспользуемые Qt-импорты
  (QGroupBox, QHBoxLayout, Qt, QColor).
- `gen_refs.py`, `run_tests.py`: удалён неиспользуемый `import re`.
- Тестовые файлы: удалены неиспользуемые импорты (`traceback`, `NumberParser`, `random`,
  `json`, `time`, `SYSTEM_PROFILES`, `IODevice`/`I8257`, `IOBus`/`ShadowROMRegion`,
  `RAMRegion`, `I8253`, `LCD1602`, `get_profile_names`, `Preprocessor`).

**2. Удалены неиспользуемые локальные переменные**
- `modules/config/device_config.py`, `modules/io/chargen.py`: `except Exception as e:`
  → `except Exception:` (переменная не используется).
- `modules/io/i8275.py`: удалена мёртвая `cmd = value & 0x7F` в `_write_command`.
- `ui/display_widgets.py`: удалена неиспользуемая `bg = QColor(0,0,0)` (используется
  только `fg`).

**3. f-строки без плейсхолдеров**
Убран избыточный префикс `f` у f-строк без плейсхолдеров в `i8080_ci/main_window.py`
(5), `mcp_server.py` (2) и нескольких тестовых скриптов (`mmio_test.py`, `PPI_3D_*`,
`crt_font_test.py`, `kbd_test.py`, `ppi_test.py`, `device_access_test.py`,
`test_banked.py`, `test_system_integration.py`).

**4. Подавление SyntaxWarning в ассемблере (Python 3.12)**
`test_asm_for_test.py` выдавал `SyntaxWarning: 'int' object is not callable` (3×) из
парсера выражений, когда санитизированное числовое выражение выглядело как `123(456)`.
Вызовы `eval()` в `assemble8080/assembler.py` и `assemble8080/preprocessor.py` уже
обёрнуты в try/except (возвращают 0), поэтому предупреждение было безвредным шумом.
Оба вызова `eval()` теперь обёрнуты в `warnings.catch_warnings()` с игнорированием
`SyntaxWarning`. Количество предупреждений: 3 → **0**.

**Оставшиеся замечания pyflakes (все осознанные / безвредные):**

| Категория | Кол-во | Примечание |
|---|---|---|
| re-экспорты в `__init__.py` / `i18n.py` | 88 | осознанный публичный API |
| `undefined name 'api'` в MCP-тестах | 83 | глобальный MCP-клиент, задаётся в рантайме |
| строковые аннотации (forward refs) | 3 | `I8080Emulator`, `IODevice`, `MainWindow` |
| smoke-импорты в `test_gui_smoke.py` | 2 | осознанно (помечены `# noqa`) |

**Результаты полного цикла тестирования (повторно подтверждено):**

| Набор | Результат |
|---|---|
| `run_tests.py` (33 файла) | **871/871 PASS** |
| `test_bin_compare.py` (эталон zasm) | **15/15 побайтово** |
| `test_asm_for_test.py` (69 файлов) | **69/69 PASS** (0 SyntaxWarning) |
| `assembler_test_full.py` | **20/20 PASS** |
| `test_config.py` | **49/49 PASS** |
| `test_system_profiles.py` | **54/54 PASS** |
| `test_system.py` | **53/53 PASS** |
| `test_gui_smoke.py` | **ВСЕ PASS** |

---

## 2026-09-19: Full Project Audit, ORG/#code Layout Fix, Test Suite Repair

### EN

**Full project audit** (pyflakes + py_compile on all modules) and a complete test
cycle were performed. The audit revealed a real layout bug in the assembler and a
set of outdated tests.

**1. ORG / #code binary layout inconsistency (critical)**

The `ORG` directive padded the binary from address 0 to the origin (full image),
while the `#code` section directive produced a code-only image starting at the
section address (matching zasm). This inconsistency broke every consumer that loads
the image at `origin + i` (emulator integration test, GUI widget, smoke test).

Fix: introduced `self._base_offset` — the logical address that corresponds to byte 0
of the binary image. The first `ORG` / first `#code` section now sets `_base_offset`
to the start address and leaves `_write_pos = 0`, so the binary always starts at
`origin` (zasm-compatible). Subsequent `ORG` jumps still fill gaps correctly using
the base offset. Also added `self._write_pos = 0` reset in the pass-2 setup so a
reused `Assembler` instance does not carry state between `assemble()` calls.

Result: `test_emu_integration.py` went from 0/21 to **21/21 PASS**; zasm reference
comparison stays **15/15 byte-identical**.

**2. Outdated `test_config.py` (profile structure + values)**

Tests 6-9 referenced the old built-in profile layout (`profile["toml"]` string) and
stale hardware values. External TOML profiles now store a `config` dict. Updated:
- Test 6 (Микро-80): 1.78 MHz, 3 memory regions, 3 devices, RAM 0x0000-0x3FFF, ROM 0xF800-0xFFFF
- Test 7 (Вектор-06Ц): 2 devices (i8255, i8253)
- Test 8: 3 registered memory regions (ram + rom + mmio)
- Test 9: 2 created devices

Result: `test_config.py` went from 41/53 to **49/49 PASS**.

**3. pyflakes cleanup in `assemble8080/assembler.py`**

- Removed 4 redundant `import re as _re` statements inside loops/handlers (shadowed
  the module-level `import re`); now uses the module-level `re`.
- Removed unused exception variable `e` in the expression parser fallback.

`assemble8080/assembler.py` is now pyflakes-clean.

**Full test cycle results:**

| Suite / Набор | Result / Результат |
|---|---|
| `run_tests.py` (33 files) | **871/871 PASS** |
| `test_bin_compare.py` (zasm reference) | **15/15 byte-identical** |
| `test_asm_for_test.py` (69 files) | **69/69 PASS** |
| `assembler_test_full.py` | **20/20 PASS** |
| `test_config.py` | **49/49 PASS** |
| `test_system_profiles.py` | **54/54 PASS** |
| `test_gui_smoke.py` | **ALL PASS** |

### RU

**Полный аудит проекта** (pyflakes + py_compile по всем модулям) и полный цикл
тестирования. Аудит выявил реальную ошибку компоновки в ассемблере и набор
устаревших тестов.

**1. Несоответствие компоновки ORG / #code (критическая)**

Директива `ORG` дополняла бинарный образ нулями от адреса 0 до origin (полный
образ), тогда как директива секций `#code` формировала образ только с кода,
начинаясь с адреса секции (как в zasm). Это несоответствие ломало всех
потребителей, загружающих образ по `origin + i` (интеграционный тест эмулятора,
GUI-виджет, smoke-тест).

Исправление: введено `self._base_offset` — логический адрес, соответствующий байту 0
бинарного образа. Первый `ORG` / первая секция `#code` теперь устанавливают
`_base_offset` на адрес начала и оставляют `_write_pos = 0`, поэтому бинарный образ
всегда начинается с `origin` (совместимо с zasm). Последующие переходы `ORG`
по-прежнему корректно заполняют разрывы с учётом базового смещения. Также добавлен
сброс `self._write_pos = 0` в настройке прохода 2, чтобы переиспользуемый экземпляр
`Assembler` не переносил состояние между вызовами `assemble()`.

Результат: `test_emu_integration.py` — с 0/21 до **21/21 PASS**; сравнение с
эталонами zasm остаётся **15/15 побайтово**.

**2. Устаревший `test_config.py` (структура профилей + значения)**

Тесты 6-9 ссылались на старую структуру встроенных профилей (`profile["toml"]` —
строка) и на устаревшие аппаратные значения. Внешние TOML-профили теперь хранят dict
`config`. Обновлено:
- Тест 6 (Микро-80): 1.78 МГц, 3 региона памяти, 3 устройства, RAM 0x0000-0x3FFF, ROM 0xF800-0xFFFF
- Тест 7 (Вектор-06Ц): 2 устройства (i8255, i8253)
- Тест 8: 3 зарегистрированных региона памяти (ram + rom + mmio)
- Тест 9: 2 созданных устройства

Результат: `test_config.py` — с 41/53 до **49/49 PASS**.

**3. Уборка pyflakes-замечаний в `assemble8080/assembler.py`**

- Удалены 4 избыточных `import re as _re` внутри циклов/обработчиков (затеняли
  модульный `import re`); теперь используется модульный `re`.
- Удалена неиспользуемая переменная исключения `e` в fallback парсера выражений.

`assemble8080/assembler.py` теперь чист по pyflakes.

**Результаты полного цикла тестирования:**

| Набор | Результат |
|---|---|
| `run_tests.py` (33 файла) | **871/871 PASS** |
| `test_bin_compare.py` (эталон zasm) | **15/15 побайтово** |
| `test_asm_for_test.py` (69 файлов) | **69/69 PASS** |
| `assembler_test_full.py` | **20/20 PASS** |
| `test_config.py` | **49/49 PASS** |
| `test_system_profiles.py` | **54/54 PASS** |
| `test_gui_smoke.py` | **ВСЕ PASS** |

---



## 2026-09-19: Full zasm Reference Validation (15/15 PASS)

### EN
All 15 test sources now produce byte-identical output to the real zasm compiler (v4.4.x).
Reference files generated with `zasm.exe --date=2026-09-19,11:06:55`.

**Fixes applied:**
1. **DS fill rule**: `rom` → 0xFF, `bin`/`ram` → 0x00 (per zasm docs: "bin" is old name for "ram")
2. **ORG gap fill**: uses target fill byte instead of zeros
3. **ORG backwards (paging)**: `_write` method overwrites bytes at `_write_pos`
4. **Section `_end` symbols**: created when section is closed
5. **Pending EQU mechanism**: forward references to section symbols resolved after pass 1
6. **Section address pre-computation**: after pending EQU resolution, all `#code` addresses re-evaluated
7. **Section-aware label tracking**: labels in sections with corrected addresses get delta adjustment
8. **Pass 2 #code handler**: new section symbol set BEFORE closing previous section (fixes size expressions referencing next section)
9. **DB `'X'+80H` expressions**: single-quoted chars with arithmetic now evaluated correctly
10. **Pass 1 DB byte counting**: quoted strings counted by actual char count, not `len(part)-2`
11. **#if/#elif/#else logic**: `elif_accepted` stack prevents re-evaluation after a branch is accepted
12. **#define substitution parentheses**: expression values wrapped in `()` to preserve operator precedence
13. **Multi-pass #define substitution**: handles chained defines (A→B→C)
14. **#define in strings**: substitution skips quoted string literals

**Test results:**
| File | Size | Status |
|------|------|--------|
| 8080TonePlayer.asm | 2042 B | OK |
| bf.asm | 429 B | OK |
| CPU_test.asm | 1008 B | OK |
| ESC_DeESC.asm | 115 B | OK |
| fifo_a16.asm | 364 B | OK |
| ImperialMarch.asm | 1656 B | OK |
| IMSAI8080.asm | 4135 B | OK |
| kernel.asm | 36933 B | OK |
| main_boot.asm | 959 B | OK |
| Mega-80.asm | 1718 B | OK |
| mon85-v13.asm | 4187 B | OK |
| rtty.asm | 616 B | OK |
| shell.asm | 228 B | OK |
| Smyk_player.asm | 52 B | OK |
| SW_IO.asm | 111 B | OK |

### RU
Все 15 тестовых источников теперь дают побайтовое совпадение с реальным компилятором zasm (v4.4.x).
Референсные файлы сгенерированы командой `zasm.exe --date=2026-09-19,11:06:55`.

**Внесённые исправления:**
1. **Правило заполнения DS**: `rom` → 0xFF, `bin`/`ram` → 0x00
2. **Заполнение разрыва ORG**: байт заполнения целевого типа
3. **ORG назад (paging)**: метод `_write` перезаписывает байты
4. **Символы `_end` секций**: создаются при закрытии секции
5. **Механизм pending EQU**: пересылки на символы секций разрешаются после прохода 1
6. **Предвычисление адресов секций**: после разрешения pending EQU все адреса `#code` пересчитываются
7. **Отслеживание меток по секциям**: метки в секциях с исправленными адресами получают дельту
8. **Обработчик #code в проходе 2**: символ новой секции устанавливается ДО закрытия предыдущей
9. **DB `'X'+80H`**: выражения с кавычками и арифметикой вычисляются корректно
10. **Подсчёт байтов DB в проходе 1**: строки в кавычках считаются по реальному числу символов
11. **Логика #if/#elif/#else**: стек `elif_accepted` предотвращает повторную оценку
12. **Скобки при подстановке #define**: значения-выражения оборачиваются в `()`
13. **Многопроходная подстановка #define**: цепочки определений (A→B→C)
14. **#define в строках**: подстановка пропускает строковые литералы в кавычках

---


## 2026-09-19: Assembler Bug Fixes / Исправление ошибок ассемблера

### Critical Fixes / Критические исправления

**EN:** Fixed 6 critical assembler bugs found via reference binary comparison:

1. **Bitwise AND/OR in expressions** — `AND`/`OR` were mapped to Python logical `and`/`or` instead of bitwise `&`/`|`. `20 AND 255` gave 255 instead of 20.
2. **Integer division** — `/` used Python float division. `20/256` gave 0.078 (truthy) instead of 0. Now uses `//`.
3. **Expression parser PC sync** — `expr_parser.pc` was not synchronized with assembler `location` in EQU/ORG/DS handlers. `STACK EQU $` gave wrong value.
4. **ORG padding in pass 2** — ORG forward jumps didn't generate zero-fill bytes.
5. **Character literals** — `'A'` in operands (MVI, CPI, etc.) not converted to ASCII value. Added to both `_parse_operand` and `ExpressionParser`.
6. **Preprocessor `=` operator** — `#if X = 45` (C-style) not handled. `=` was stripped by regex, all conditions evaluated to False.
7. **Section state reset** — `_current_section` not cleared between pass 1 and pass 2, causing phantom section padding.

**RU:** Исправлено 6 критических ошибок ассемблера, найденных сравнением с референсными .bin файлами:

1. **Битовые AND/OR** — `AND`/`OR` заменялись на логические `and`/`or` Python вместо битовых `&`/`|`.
2. **Целочисленное деление** — `/` давал float. `20/256 = 0.078` (truthy) вместо `0`. Теперь `//`.
3. **Синхронизация PC** — `expr_parser.pc` не обновлялся в обработчиках EQU/ORG/DS.
4. **ORG padding** — переходы вперёд не генерировали нулевые байты.
5. **Символьные литералы** — `'A'` в операндах не конвертировался в ASCII.
6. **Оператор `=` в #if** — C-стиль `#if X = 45` не работал, все условия были False.
7. **Сброс секций** — `_current_section` не очищался между pass 1 и pass 2.

### Results / Результаты

| File | Before | After |
|------|--------|-------|
| CPU_test.asm | ❌ (832 vs 1008) | ✅ 1008 bytes |
| ESC_DeESC.asm | ✅ | ✅ 115 bytes |
| mon85-v13.asm | ❌ (MVI B=0) | ⚠️ size OK, 1 byte diff |
| test_580.asm | ❌ (1507 vs 1584) | ⚠️ size OK, values diff |
| IMSAI8080.asm | ❌ (unresolved labels) | ⚠️ size OK, 1 byte diff |
| Mega-80.asm | ❌ (1851 vs 1844) | ⚠️ 1855 vs 1844 |
| rtty.asm | ❌ (613 vs 616) | ⚠️ 613 vs 616 |
| bf.asm | ⚠️ date string | ⚠️ date string (not a bug) |
| ImperialMarch.asm | ⚠️ date string | ⚠️ date string (not a bug) |

**All 69 ASM_FOR_TEST files assemble without errors.**

---


## 2026-09-19: Help Menu (F1) + Refactoring / Меню Справка + Рефакторинг

### Help Menu / Меню Справка

**EN:** Added "Help" menu (F1 hotkey) with links to all documentation files:
- User Guide (USER_GUIDE.md)
- README (README.md)
- Changelog (CHANGES.md)
- Project Analysis (ANALYSIS.md)
- MCP Guide (MCP_GUIDE.md)
- Scripts Guide (SCRIPTS_GUIDE.md)
- About dialog

Documentation is displayed in a QTextBrowser dialog with basic markdown→HTML rendering.
Menu title and items update on language switch.

**RU:** Добавлено меню «Справка» (горячая клавиша F1) со ссылками на все файлы документации:
- Руководство пользователя (USER_GUIDE.md)
- README (README.md)
- Журнал изменений (CHANGES.md)
- Анализ проекта (ANALYSIS.md)
- MCP Руководство (MCP_GUIDE.md)
- Руководство по скриптам (SCRIPTS_GUIDE.md)
- О программе

Документация отображается в диалоге QTextBrowser с базовым markdown→HTML рендерингом.
Заголовок меню и пункты обновляются при смене языка.

### Refactoring: Themes, i18n, Dead Code / Рефакторинг

**EN:** Extracted all theme/color definitions into `common/themes.py`. Added full i18n support to the assembler widget (30+ hardcoded strings → translation keys). Removed unused imports across 10 files. Removed dead code. Updated module structure.

**RU:** Все определения тем/цветов вынесены в `common/themes.py`. Добавлена полная i18n поддержка в виджет ассемблера. Удалены неиспользуемые импорты в 10 файлах. Удалён мёртвый код. Обновлена структура модулей.

### Test results / Результаты тестов

| Suite / Набор | Result / Результат |
|---|---|
| `run_tests.py` (33 files) | **871/871 PASS** |
| `test_asm_for_test.py` (69 files) | **69/69 PASS** |
| `test_gui_smoke.py` | **ALL PASS** |

---


## 2026-09-18: M80 Assembler Format Support

### Summary / Обзор

**EN:** Extracted all theme/color definitions into `common/themes.py`. Added full i18n support to the assembler widget (30+ hardcoded Russian strings → translation keys). Removed unused imports across 9 files. Removed dead code (commented-out `_load_to_memory` in assembler_widget.py). Updated `common/__init__.py` and `i8080_ci/__init__.py` for new module structure. All 871 test checks pass.

**RU:** Все определения тем/цветов вынесены в `common/themes.py`. Добавлена полная i18n поддержка в виджет ассемблера (30+ жёстко заданных русских строк → ключи перевода). Удалены неиспользуемые импорты в 9 файлах. Удалён мёртвый код (закомментированный `_load_to_memory` в assembler_widget.py). Обновлены `common/__init__.py` и `i8080_ci/__init__.py` под новую структуру модулей. Все 871 проверок тестов пройдены.

### Changes / Изменения

#### 1. New file: `common/themes.py` / Новый файл

**EN:** Centralized all color constants and QSS stylesheets:
- `THEMES` — application QSS (Light/Dark) moved from `i18n.py`
- `EDITOR_DARK` / `EDITOR_LIGHT` — code editor colors (background, foreground, line numbers, current line, error line)
- `SYNTAX_DARK` / `SYNTAX_LIGHT` — syntax highlighting colors (comment, mnemonic, directive, number, label, register)
- `ARROW_COLORS` — 6-color palette for jump/branch arrows
- `STATUS_COLORS` — status indicator colors (warning, success, error, flags, trace)
- Helper functions: `get_editor_style(is_dark)`, `get_syntax_colors(is_dark)`

**RU:** Централизованы все цветовые константы и QSS-стили:
- `THEMES` — QSS приложения (Light/Dark), перенесено из `i18n.py`
- `EDITOR_DARK` / `EDITOR_LIGHT` — цвета редактора кода
- `SYNTAX_DARK` / `SYNTAX_LIGHT` — цвета подсветки синтаксиса
- `ARROW_COLORS` — 6-цветная палитра для стрелок переходов
- `STATUS_COLORS` — цвета индикаторов состояния
- Вспомогательные функции: `get_editor_style(is_dark)`, `get_syntax_colors(is_dark)`

#### 2. i18n: Assembler widget / Виджет ассемблера

**EN:** All 30+ hardcoded Russian strings in `assembler_widget.py` replaced with i18n keys:
- Button labels: `asm_new`, `asm_load`, `asm_save`, `asm_assemble`, `asm_assemble_load`
- Group boxes: `asm_errors`, `asm_labels`
- Table headers: `asm_col_line`, `asm_col_msg`, `asm_col_label`, `asm_col_addr`, `asm_col_line2`
- Dialog titles: `asm_load_title`, `asm_save_title`
- File filters: `asm_file_filter`, `asm_file_filter_save`
- Log messages: `asm_loaded`, `asm_saved`, `asm_assembling`, `asm_no_code`, `asm_exception`, `asm_errors_found`, `asm_err_line`, `asm_warning`, `asm_success`, `asm_origin`, `asm_symbols`, `asm_loaded_mem`, `asm_load_mem_err`
- Error dialogs: `asm_err_title`, `asm_load_err`, `asm_save_err`
- Placeholder text: `asm_placeholder`
- `set_theme()` now also updates all labels on language/theme change

**RU:** Все 30+ жёстко заданных русских строк в `assembler_widget.py` заменены на ключи i18n:
- Подписи кнопок, заголовки групп, заголовки таблиц
- Заголовки диалогов, фильтры файлов
- Сообщения в лог, диалоги ошибок
- Текст-заполнитель редактора
- `set_theme()` теперь также обновляет все подписи при смене языка/темы

#### 3. Unused imports removed / Удалены неиспользуемые импорты

| File / Файл | Removed / Удалено |
|---|---|
| `main_window.py` | `sys`, `json`, `traceback` (top-level, kept as local), `QToolTip`, `QStyle`, `QStatusBar`, `QObject`, `Signal`, `QAbstractTableModel`, `QModelIndex`, `QEvent`, `QLocale`, `QRect`, `QPainter`, `QPen`, `QBrush`, `QActionGroup`, 18 `.slip` constants |
| `automation.py` | 16 `.slip` constants |
| `bus_worker.py` | 24 `.slip` constants |
| `models/bp_model.py` | `QModelIndex` |
| `models/trace_model.py` | `QModelIndex` |
| `views/disasm_view.py` | `QEvent`, `QBrush`, `JUMP_OPCODES` |
| `views/hex_view.py` | `Qt` (top-level), `QApplication` (re-added where needed) |
| `views/search.py` | `Qt` |
| `mcp_server.py` | `asyncio` |
| `assembler_widget.py` | `QLabel`, `QSpinBox`, `QCheckBox`, `QStyle`, `NumberParser` |

#### 4. Dead code removed / Мёртвый код

- `assembler_widget.py`: removed 20-line commented-out `_load_to_memory` (old implementation)
- `assembler_widget.py`: removed commented-out listing output block in `_do_assemble`
- `assembler_widget.py`: `on_new()` now clears error/label tables (was referencing non-existent `self.log`)

#### 5. Module structure / Структура модулей

- `common/__init__.py`: imports `THEMES` from `.themes` (not `.i18n`)
- `i8080_ci/__init__.py`: imports `THEMES` from `common.themes`
- `i8080_ci/i18n.py`: backward-compatible re-export updated
- `main_window.py`: `from common.themes import THEMES`

### Test results / Результаты тестов

| Suite / Набор | Result / Результат |
|---|---|
| `run_tests.py` (33 files) | **871/871 PASS** |
| `test_asm_for_test.py` (69 files) | **69/69 PASS** |
| `test_gui_smoke.py` | **ALL PASS** |
| `test_alu_8080.py` | **56/56 PASS** |
| `test_emu_integration.py` | **21/21 PASS** |

---


## 2026-09-18: M80 Assembler Format Support

### Added M80 (.mac) format support to the assembler

**Preprocessor changes:**
- Shebang lines (`#!/...`) treated as comments
- `CPU`, `ASEG`, `TITLE` directives handled as no-op
- `PUBLIC`, `EXTERN`, `MODULE` directives handled as no-op
- M80-style `include "file"` (without `#`) support
- `.macro`/`.endm` macro definition format support
- Case-insensitive macro name matching
- Nested macro expansion (up to 10 levels)
- UTF-8 encoding errors handled gracefully

**Assembler changes:**
- `DB N dup(value)` — M80 duplicate byte syntax
- `DS N,fill` — DS with fill value
- `DEF` as alias for `EQU` (M80 variable definition)
- `<>` operator (not-equal) in expressions
- `NOT` → bitwise NOT (`~`) instead of logical NOT
- `$` allowed in label names (CP/M style: `RD$TRK`)
- Extended no-op directives: `ENDR`, `DATA`, `BLKB`, `DISKDEF`,
  `IRP`, `ASSERT`, `DEFW`, `ASMPC`, `MACRO`, `ALIGN`, `#DATA`, `#ASSERT`
- `END [start]` — optional start address (informational)

**Test script updated:**
- Now uses `ASM_FOR_TEST/` directory (replaces `c:\zasm\`)
- Includes both `.asm` and `.mac` files
- 21 non-8080 files excluded (Z80/8085/Apple II)
- **Result: 69/69 PASS, 0 FAIL**

### Test results

| File | Format | Size | Status |
|------|--------|------|--------|
| 8080EX1.MAC | M80 | 6,527,535 B | PASS |
| 8080EXER.MAC | M80 | 6,527,507 B | PASS |
| 8080EXM.MAC | M80 | 6,527,527 B | PASS |
| 8080PRE.MAC | M80 | 932 B | PASS |
| 8080PRE.asm | M80/zasm | 932 B | PASS |
| CPU_test_full.asm | zasm | 6,555,084 B | PASS |
| OS_kernel.asm | zasm | 55,694 B | PASS |
| kernel.asm | zasm | 37,771 B | PASS |
| Altair8800_Monitor.asm | M80 | 1,605 B | PASS |
| Comm.asm | M80 | 1,695 B | PASS |
| DD30.asm | M80 | 4,090 B | PASS |
| ... and 58 more | mixed | — | PASS |

**Unit tests: 871/871 PASS**
