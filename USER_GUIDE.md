# i8080-5 CI — User Guide / Пользовательское руководство

> **Version / Версия:** 2.2
> **Date / Дата:** 2026-09-21
> **Platform / Платформа:** Windows / Linux
> **UI Languages / Языки интерфейса:** Русский, English

---

> **Note (v2.2):** Added the **Assembler** tab (section 8) — write, assemble, and load i8080 source. Fixed auto-sync of the assembler view from memory.
> **Примечание (v2.2):** Добавлена вкладка **«Ассемблер»** (раздел 8) — написание, сборка и загрузка i8080-кода. Исправлена автосинхронизация вида ассемблера с памятью.

> **Note (v2.1):** Application code is organized in the `i8080_ci/` package. Entry point remains `i8080_CI.py`.
> **Примечание (v2.1):** Код приложения организован в пакете `i8080_ci/`. Точка входа — `i8080_CI.py`.

## Contents / Содержание

1. [Overview / Обзор](#1-overview--обзор)
2. [Installation / Установка](#2-installation--установка)
3. [Interface Overview / Обзор интерфейса](#3-interface-overview--обзор-интерфейса)
4. [Control Tab / Вкладка «Управление»](#4-control-tab--вкладка-управление)
5. [Data Tab / Вкладка «Данные»](#5-data-tab--вкладка-данные)
6. [Hex Editor / Hex-редактор](#6-hex-editor--hex-редактор)
7. [Disassembler / Дизассемблер](#7-disassembler--дизассемблер)
8. [Assembler / Ассемблер](#8-assembler--ассемблер)
9. [Memory Test / Тест памяти](#9-memory-test--тест-памяти)
10. [IO Sequencer / IO Секвенсор](#10-io-sequencer--io-секвенсор)
11. [Comparison / Сравнение](#11-comparison--сравнение)
12. [Scripts / Скрипты](#12-scripts--скрипты)
13. [Emulator / Эмулятор](#13-emulator--эмулятор)
14. [Trace Log / Трассировка](#14-trace-log--трассировка)
15. [Hotkeys / Горячие клавиши](#15-hotkeys--горячие-клавиши)
16. [MCP Integration / MCP-интеграция](#16-mcp-integration--mcp-интеграция)
17. [Typical Workflows / Типовые сценарии](#17-typical-workflows--типовые-сценарии)

---

## 1. Overview / Обзор

**EN:**

**i8080-5 CI** (i8080-5 Control Interface) — a comprehensive environment for working with the Intel 8080 processor and devices based on it. The program combines:

- **i8080 Emulator** — full CPU emulation with all 256 instructions, including undocumented
- **Debugger** — breakpoints (regular & conditional), step execution, watch windows, trace
- **Hex Editor** — view and edit memory images
- **Disassembler** — with jump arrows and instruction-type color highlighting
- **Real Device Control** — read/write memory and IO ports via COM port (SLIP protocol)
- **Memory Test** — test device RAM with various patterns
- **IO Sequencer** — execute sequences of input/output operations
- **Comparison** — compare current memory image with a file
- **Scripts** — automation via Python scripts
- **MCP Server** — integration with AI assistants

The program supports **Russian and English** interface languages and **Light/Dark** themes.

**RU:**

**i8080-5 CI** (i8080-5 Control Interface) — комплексная среда для работы с процессором Intel 8080 и устройствами на его базе. Программа объединяет:

- **Эмулятор i8080** — полная эмуляция процессора со всеми 256 инструкциями, включая недокументированные
- **Отладчик** — точки останова (обычные и условные), пошаговое выполнение, watch-окна, трассировка
- **Hex-редактор** — просмотр и редактирование образов памяти
- **Дизассемблер** — со стрелками переходов, подсветкой типов команд
- **Работа с реальным устройством** — чтение/запись памяти и IO-портов по COM-порту (протокол SLIP)
- **Тест памяти** — тестирование RAM устройства различными паттернами
- **IO Секвенсор** — выполнение последовательности операций ввода-вывода
- **Сравнение** — сравнение текущего образа памяти с файлом
- **Скрипты** — автоматизация через Python-скрипты
- **MCP-сервер** — интеграция с AI-ассистентами

Программа поддерживает **русский и английский** языки интерфейса и **светлую/тёмную** темы.

---

## 2. Installation / Установка

### 2.1. Requirements / Требования

**EN:**
- Python 3.10+
- PySide6
- pyserial
- For MCP: `mcp`, `uvicorn`, `starlette`, `pydantic`, `pydantic-settings`

**RU:**
- Python 3.10+
- PySide6
- pyserial
- Для MCP: `mcp`, `uvicorn`, `starlette`, `pydantic`, `pydantic-settings`

### 2.2. Install Dependencies / Установка зависимостей

```bash
pip install PySide6 pyserial
pip install mcp uvicorn starlette pydantic pydantic-settings
```

### 2.3. Run / Запуск

```bash
python i8080_CI.py
```

**EN:** The program launches with a 1280×720 window. Language and theme are auto-detected from system settings (can be changed in the interface).

**RU:** Программа запускается с окном 1280×720. Язык и тема определяются автоматически из системных настроек (можно изменить в интерфейсе).

---

## 3. Interface Overview / Обзор интерфейса

**EN:** The main window consists of:
1. **Top panel** — COM port selection, baud rate, connect/disconnect, language and theme selection
2. **Tabs** — 11 tabs with various functions
3. **Log** — bottom panel with operation log

**RU:** Главное окно состоит из:
1. **Верхняя панель** — выбор COM-порта, скорости, подключение/отключение, выбор языка и темы
2. **Вкладки** — 11 вкладок с различными функциями
3. **Журнал** — нижняя панель с журналом операций

### Tab Order / Порядок вкладок

| # | EN | RU | Purpose |
|---|---|---|---|
| 0 | Assembler | Ассемблер | Write & assemble i8080 code |
| 1 | Disassembler | Дизассемблер | Disassemble code |
| 2 | Hex Editor | Hex редактор | View and edit memory |
| 3 | Emulator | Эмулятор | i8080 debugger |
| 4 | Trace Log | Трассировка | Execution trace view |
| 5 | Scripts | Скрипты | Automation |
| 6 | Control | Управление | Connection, bus, files |
| 7 | Data | Данные | Read/write memory and IO |
| 8 | Memory Test | Тест памяти | Test RAM |
| 9 | IO Sequencer | IO последовательность | IO sequences |
| 10 | Comparison | Сравнение | Compare memory images |
---

## 4. Control Tab / Вкладка «Управление»

### 4.1. Device Connection / Подключение к устройству

**EN:**
1. Select COM port from the dropdown
2. Select baud rate (9600, 38400, 57600, 115200)
3. Click **"Connect"**
4. Program sends NOP to verify connection

> 💡 If device is not detected, click **"Refresh"** to update port list.

**RU:**
1. Выберите COM-порт из выпадающего списка
2. Выберите скорость (9600, 38400, 57600, 115200)
3. Нажмите **«Подключиться»**
4. Программа отправит NOP для проверки соединения

> 💡 Если устройство не обнаружено, нажмите **«Обновить»** для обновления списка портов.

### 4.2. Bus Control / Управление шиной

**EN:**
- **"Hold Bus (HOLD)"** — sends HOLD signal to processor. Program waits for HLDA confirmation.
- **"Release Bus (UnHOLD)"** — releases bus, processor continues.

> ⚠️ **Important:** Bus must be held before reading/writing device memory. On application close, bus is released automatically.

**RU:**
- **«Захватить шину (HOLD)»** — отправляет сигнал HOLD процессору. Программа ожидает подтверждения HLDA.
- **«Освободить шину (UnHOLD)»** — освобождает шину, процессор продолжает работу.

> ⚠️ **Важно:** Перед чтением/записью памяти устройства необходимо захватить шину. При закрытии программы шина освобождается автоматически.

### 4.3. Files / Файлы

**EN:**
- **"Save Dump (.hex)"** — save current memory image in Intel HEX or BIN format
- **"Load Firmware (.hex/.bin)"** — load firmware into local memory image. For BIN files, base address is requested. After loading, option to write to device is offered.

**RU:**
- **«Сохранить дамп (.hex)»** — сохранение текущего образа памяти в Intel HEX или BIN формат
- **«Загрузить прошивку (.hex/.bin)»** — загрузка прошивки в локальный образ памяти. Для BIN-файлов запрашивается базовый адрес. После загрузки предлагается записать в устройство.

### 4.4. MCP Server / MCP-сервер

**EN:** The **"MCP Server: OFF/ON"** button toggles the built-in MCP server for AI assistant integration.

**RU:** Кнопка **«MCP Server: OFF/ON»** включает/выключает встроенный MCP-сервер для интеграции с AI-ассистентами.

---

## 5. Data Tab / Вкладка «Данные»

**EN:** Allows reading and writing values to device memory and IO ports.

### Memory (RAM/ROM)
- **Address (HEX)** — memory address (4 hex digits)
- **Bit Width** — 8, 16, 24, 32 bits
- **Value (HEX)** — value to write
- **Endianness** — Little-endian or Big-endian
- **"Read"** and **"Write"** buttons

### IO Ports
- Same as memory, but address is port number (2 hex digits)

> ⚠️ Device connection and bus hold required for both memory and IO operations.

**RU:** Позволяет читать и записывать значения в память и IO-порты устройства.

### Память (RAM/ROM)
- **Адрес (HEX)** — адрес в памяти (4 hex-цифры)
- **Разрядность** — 8, 16, 24, 32 бита
- **Значение (HEX)** — значение для записи
- **Порядок байтов** — Little-endian или Big-endian
- Кнопки **«Прочитать»** и **«Записать»**

### IO-порты
- Аналогично памяти, но адрес — это номер порта (2 hex-цифры)

> ⚠️ Для работы с памятью и IO необходимо подключение и захват шины.

---

## 6. Hex Editor / Hex-редактор

### 6.1. Overview / Обзор

**EN:** The hex editor displays memory as a table:
- **Column 0** — row address
- **Columns 1-16** — bytes (00-F)
- **Column 17** — ASCII representation

**RU:** Hex-редактор отображает образ памяти в виде таблицы:
- **Колонка 0** — адрес строки
- **Колонки 1-16** — байты (00-F)
- **Колонка 17** — ASCII-представление

### 6.2. Features / Возможности

**EN:**
- **Editing** — double-click a cell to edit
- **Tooltips** — hover over byte shows corresponding instruction mnemonic
- **Undo/Redo** — Ctrl+Z / Ctrl+Y (up to 100 operations)
- **Context menu** (right-click):
  - Copy address
  - Copy value
  - Invert byte
  - Fill range
  - Disassemble from here
  - Go to address
- **Search** — Ctrl+F (HEX pattern, ASCII string, HEX with mask `??`)
- **Go to address** — Ctrl+G
- **Read block** — read block from device into image

**RU:**
- **Редактирование** — двойной клик по ячейке для редактирования
- **Подсказки** — при наведении на байт показывается мнемоника инструкции
- **Undo/Redo** — Ctrl+Z / Ctrl+Y (до 100 операций)
- **Контекстное меню** (правый клик):
  - Копировать адрес
  - Копировать значение
  - Инвертировать байт
  - Заполнить диапазон
  - Дизассемблировать отсюда
  - Перейти к адресу
- **Поиск** — Ctrl+F (HEX-паттерн, ASCII-строка, HEX с маской `??`)
- **Переход к адресу** — Ctrl+G
- **Чтение блока** — чтение блока из устройства в образ

---

## 7. Disassembler / Дизассемблер

### 7.1. Overview / Обзор

**EN:** The disassembler displays code with:
- **Jump arrows** — colored arrows showing jump targets (JMP, CALL, Jcc, Ccc, RST)
- **Color highlighting by instruction type:**
  - 🔵 Blue — jumps (JMP, CALL, Jcc, Ccc, RST)
  - 🟢 Green — memory operations (LDA, STA, LHLD, SHLD, LDAX, STAX, XCHG, XTHL)
  - 🟣 Purple — IO (IN, OUT)
  - ⚪ Gray — control (NOP, HLT, DI, EI, RET, PCHL, SPHL)
  - 🟠 Orange — registers and data (MVI, LXI, INR, DCR, MOV, INX, DCX)
  - 🟡 Yellow — arithmetic and logic (ADD, ADC, SUB, SBB, ANA, XRA, ORA, CMP, etc.)
  - 🟢 Teal — stack (PUSH, POP)
  - 🔴 Red — undocumented instructions (NOP*, RET*, CALL*)
- **Jump comments** — `; -> XXXXh` shows jump target

**RU:** Дизассемблер отображает код с:
- **Стрелками переходов** — цветные стрелки показывают цели переходов
- **Цветовой подсветкой типов команд:**
  - 🔵 Синий — переходы (JMP, CALL, Jcc, Ccc, RST)
  - 🟢 Зелёный — операции с памятью (LDA, STA, LHLD, SHLD, LDAX, STAX, XCHG, XTHL)
  - 🟣 Фиолетовый — ввод-вывод (IN, OUT)
  - ⚪ Серый — управление (NOP, HLT, DI, EI, RET, PCHL, SPHL)
  - 🟠 Оранжевый — регистры и данные (MVI, LXI, INR, DCR, MOV, INX, DCX)
  - 🟡 Жёлтый — арифметика и логика (ADD, ADC, SUB, SBB, ANA, XRA, ORA, CMP и др.)
  - 🟢 Бирюзовый — стек (PUSH, POP)
  - 🔴 Красный — недокументированные команды (NOP*, RET*, CALL*)
- **Комментариями переходов** — `; -> XXXXh`

### 7.2. Controls / Управление

**EN:**
- **Start** — start address for disassembly
- **Len** — length (number of bytes)
- **"Disassemble"** — perform disassembly
- **Auto on read/load** — auto-disassemble on device read or file load
- **"Export"** — export disassembly listing to file (.asm / .txt)

**RU:**
- **Start** — начальный адрес дизассемблирования
- **Len** — длина (количество байт)
- **«Дизассемблировать»** — выполнить дизассемблирование
- **Авто при чтении/загрузке** — автоматическое дизассемблирование
- **«Экспорт»** — экспорт листинга в файл (.asm / .txt)

### 7.3. Font Size / Размер шрифта

**Ctrl + mouse wheel** — change disassembler font size.

---

## 8. Assembler / Ассемблер

**EN:**

The **Assembler** tab (tab 0, the first tab) lets you write i8080 assembly source, assemble it to machine code, and load the result into the emulator memory for debugging. It is powered by the built-in two-pass assembler (`assemble8080`).

### 8.1. Interface / Интерфейс

| Button | Purpose |
|---|---|
| 📄 New Program | Clear the editor and the error/label panels |
| 📂 Load .asm | Load a source file (`.asm` / `.inc` / `.s`) |
| 💾 Save .asm | Save the source to a file |
| 🔨 Assemble | Assemble the code — shows errors, labels, and binary size |
| 🚀 Assemble & Load | Assemble and write the binary into emulator memory at the `ORG` address |

### 8.2. Editor / Редактор

- **Syntax highlighting** — mnemonics, directives, registers, numbers, labels, comments
- **Line numbers** — on the left margin
- **Jump arrows** — colored arrows (next to line numbers) showing jump targets (JMP, CALL, Jcc, Ccc)
- **Autocomplete** — mnemonics, registers, directives, and your own labels (pops up after 2 characters)
- **Ctrl + mouse wheel** — change font size (8–36 pt)
- **Error lines** — highlighted in red after a failed assembly

### 8.3. Error Panel / Панель ошибок

Below the editor. After assembly it lists all errors with line numbers. **Double-click** a row to jump to that line in the editor.

### 8.4. Label Table / Таблица меток

On the right. After a successful assembly it lists all labels with their addresses and source lines. **Double-click** a row to jump to the label's line.

### 8.5. Number Formats / Форматы чисел

| Format | Example | Value |
|---|---|---|
| Hex prefix | `0xFF` | 255 |
| Hex suffix | `FFH`, `0FFH` | 255 |
| Decimal | `255`, `255D` | 255 |
| Binary | `11111111B` | 255 |
| Octal | `377Q`, `377O` | 255 |

### 8.6. Directives / Директивы

| Directive | Purpose |
|---|---|
| `ORG addr` | Set the origin (start) address; the binary is emitted starting at `addr` |
| `DB ...` | Define bytes (numbers, strings, expressions) |
| `DW ...` | Define words (16-bit, little-endian) |
| `DS n[,fill]` | Reserve `n` bytes (optionally filled with `fill`) |
| `EQU expr` | Define a symbolic constant (`LABEL EQU value`) |
| `END` | End of program (optional) |

Dot-prefixed forms are also accepted: `.org`, `.db`, `.dw`, `.ds`, `.equ`, `.end`, `.byte`, `.word`, `.space`, `.ascii`, `.text`.

### 8.7. Comments and Special Symbols / Комментарии и спецсимволы

- `;` — comment to end of line (anywhere)
- `*` — comment when at the start of a line (M80 style)
- `$` — current address (location counter)
- **Labels** — `LABEL:`; usable in expressions and as jump targets; forward references are supported

### 8.8. Expressions / Выражения

Arithmetic and logical expressions are supported in operands and in `EQU`:

- Arithmetic: `+  -  *  /  %` (integer division)
- Bitwise: `&  |  ~  ^`, `SHL`/`<<`, `SHR`/`>>`, `MOD`
- Logical: `AND`, `OR`, `NOT`, `XOR`
- Comparison (zasm): `EQ`, `NE`, `GT`, `LT`, `GE`, `LE`, `<>`
- `HIGH expr`, `LOW expr` — high / low byte
- Character literals: `'A'` = 0x41, with escapes `\n`, `\t`, `\r`, `\0`; e.g. `'A'+80H` = 0xC1

### 8.9. Data (DB) / Данные (DB)

```asm
DB 42H, 'A', 10010110B      ; byte, char, binary
DB "Hello"                  ; string (double quotes)
DB 'Hi'                     ; string (single quotes)
DB <literal text>           ; zasm: literal text in angle brackets
DB 10 dup(0)                ; M80: repeat a value 10 times
DB CR, LF                    ; carriage return, line feed
DB __date__, __TIME__        ; build date / time
```

### 8.10. Preprocessor / Препроцессор

| Feature | Syntax |
|---|---|
| Include file | `#include "file.inc"` or `include "file.inc"` |
| Constant | `#define NAME value` |
| Conditional | `#if expr` / `#elif expr` / `#else` / `#endif` |
| Conditional (no `#`) | `IF expr` / `ELSE` / `ENDIF` |
| Macro | `NAME MACRO [params]` … `ENDM` |
| Repeat block | `REPT n` … `ENDM` |

**Macros** support parameters referenced as `&PARAM`, `%PARAM`, `#PARAM`, or `\PARAM` (zasm style):

```asm
DELAY MACRO N
    MVI B, N
LOOP: DCR B
      JNZ LOOP
ENDM
...
DELAY 10        ; expands with N = 10
```

**zasm compatibility:** `#target`, `#charset`, `XDEF`/`XREF`/`SECTION`, `.asm8080`, and the `<...>` line wrapper are recognized.

### 8.11. Loading into Memory / Загрузка в память

**"Assemble & Load"** assembles the code and writes the binary into the emulator memory at the `ORG` address, then sets the emulator PC to that address. After that you can debug it in the **Emulator** tab (F5 to run, F11 to step).

### 8.12. Sync from Memory / Синхронизация с памятью

When you edit memory in the **Hex Editor**, the Assembler view is automatically re-disassembled from the current memory — unless you are actively editing the assembler source. This keeps the assembler in sync with the actual memory contents.

### 8.13. Example / Пример

```asm
        ORG 0100H
START:  MVI A, 55H        ; A = 0x55
        OUT 01H           ; output to port 1
        MVI B, 0FFH       ; B = FF
LOOP:   DCR B             ; B = B - 1
        JNZ LOOP          ; repeat while B != 0
        LDA DATA
        STA DATA+1
        CALL SUBR
        HLT
SUBR:   INR A
        RET
DATA:   DB 42H, 'A'
        DW 1234H
        DS 10
        END
```

**RU:**

Вкладка **«Ассемблер»** (вкладка 0, первая) позволяет писать исходный код i8080 на ассемблере, собирать его в машинный код и загружать результат в память эмулятора для отладки. Работает на встроенном двухпроходном ассемблере (`assemble8080`).

### 8.1. Интерфейс

| Кнопка | Назначение |
|---|---|
| 📄 Новая программа | Очистить редактор и панели ошибок/меток |
| 📂 Загрузить .asm | Загрузить исходный файл (`.asm` / `.inc` / `.s`) |
| 💾 Сохранить .asm | Сохранить исходный код в файл |
| 🔨 Ассемблировать | Собрать код — показать ошибки, метки и размер бинарника |
| 🚀 Ассемблировать и загрузить | Собрать и записать бинарник в память эмулятора по адресу `ORG` |

### 8.2. Редактор

- **Подсветка синтаксиса** — мнемоники, директивы, регистры, числа, метки, комментарии
- **Номера строк** — в левой колонке
- **Стрелки переходов** — цветные стрелки (рядом с номерами строк) показывают цели переходов (JMP, CALL, Jcc, Ccc)
- **Автодополнение** — мнемоники, регистры, директивы и ваши метки (появляется после 2 символов)
- **Ctrl + колесо мыши** — изменение размера шрифта (8–36 pt)
- **Строки с ошибками** — подсвечиваются красным после неудачной сборки

### 8.3. Панель ошибок

Под редактором. После сборки перечисляет все ошибки с номерами строк. **Двойной клик** по строке — переход к этой строке в редакторе.

### 8.4. Таблица меток

Справа. После успешной сборки перечисляет все метки с их адресами и строками исходника. **Двойной клик** по строке — переход к строке метки.

### 8.5. Форматы чисел

| Формат | Пример | Значение |
|---|---|---|
| HEX с префиксом | `0xFF` | 255 |
| HEX с суффиксом | `FFH`, `0FFH` | 255 |
| Десятичный | `255`, `255D` | 255 |
| Двоичный | `11111111B` | 255 |
| Восьмеричный | `377Q`, `377O` | 255 |

### 8.6. Директивы

| Директива | Назначение |
|---|---|
| `ORG addr` | Установить начальный адрес; бинарник выводится начиная с `addr` |
| `DB ...` | Определить байты (числа, строки, выражения) |
| `DW ...` | Определить слова (16 бит, little-endian) |
| `DS n[,fill]` | Зарезервировать `n` байт (опционально заполнить `fill`) |
| `EQU expr` | Определить символьную константу (`МЕТКА EQU значение`) |
| `END` | Конец программы (необязательно) |

Принимаются и формы с точкой: `.org`, `.db`, `.dw`, `.ds`, `.equ`, `.end`, `.byte`, `.word`, `.space`, `.ascii`, `.text`.

### 8.7. Комментарии и спецсимволы

- `;` — комментарий до конца строки (в любом месте)
- `*` — комментарий, если стоит в начале строки (стиль M80)
- `$` — текущий адрес (счётчик позиции)
- **Метки** — `МЕТКА:`; используются в выражениях и как цели переходов; поддерживаются вперёд-ссылки

### 8.8. Выражения

В операндах и в `EQU` поддерживаются арифметические и логические выражения:

- Арифметика: `+  -  *  /  %` (целочисленное деление)
- Побитовые: `&  |  ~  ^`, `SHL`/`<<`, `SHR`/`>>`, `MOD`
- Логические: `AND`, `OR`, `NOT`, `XOR`
- Сравнение (zasm): `EQ`, `NE`, `GT`, `LT`, `GE`, `LE`, `<>`
- `HIGH expr`, `LOW expr` — старший / младший байт
- Символьные литералы: `'A'` = 0x41, с экранированием `\n`, `\t`, `\r`, `\0`; например `'A'+80H` = 0xC1

### 8.9. Данные (DB)

```asm
DB 42H, 'A', 10010110B      ; байт, символ, двоичное
DB "Hello"                  ; строка (двойные кавычки)
DB 'Hi'                     ; строка (одинарные кавычки)
DB <literal text>           ; zasm: литеральный текст в угловых скобках
DB 10 dup(0)                ; M80: повторить значение 10 раз
DB CR, LF                    ; возврат каретки, перевод строки
DB __date__, __TIME__        ; дата / время сборки
```

### 8.10. Препроцессор

| Возможность | Синтаксис |
|---|---|
| Включение файла | `#include "file.inc"` или `include "file.inc"` |
| Константа | `#define NAME value` |
| Условие | `#if expr` / `#elif expr` / `#else` / `#endif` |
| Условие (без `#`) | `IF expr` / `ELSE` / `ENDIF` |
| Макрос | `NAME MACRO [параметры]` … `ENDM` |
| Повтор блока | `REPT n` … `ENDM` |

**Макросы** поддерживают параметры, ссылаемые как `&PARAM`, `%PARAM`, `#PARAM` или `\PARAM` (стиль zasm):

```asm
DELAY MACRO N
    MVI B, N
LOOP: DCR B
      JNZ LOOP
ENDM
...
DELAY 10        ; разворачивается с N = 10
```

**Совместимость с zasm:** распознаются `#target`, `#charset`, `XDEF`/`XREF`/`SECTION`, `.asm8080` и обёртка строки `<...>`.

### 8.11. Загрузка в память

**«Ассемблировать и загрузить»** собирает код и записывает бинарник в память эмулятора по адресу `ORG`, затем устанавливает PC эмулятора на этот адрес. После этого его можно отлаживать на вкладке **«Эмулятор»** (F5 — запуск, F11 — шаг).

### 8.12. Синхронизация с памятью

При редактировании памяти в **Hex-редакторе** вид ассемблера автоматически пере-дизассемблируется из текущей памяти — если вы не редактируете исходный код ассемблера. Это держит ассемблер в синхроне с фактическим содержимым памяти.

### 8.13. Пример

```asm
        ORG 0100H
START:  MVI A, 55H        ; A = 0x55
        OUT 01H           ; вывод в порт 1
        MVI B, 0FFH       ; B = FF
LOOP:   DCR B             ; B = B - 1
        JNZ LOOP          ; повторять пока B != 0
        LDA DATA
        STA DATA+1
        CALL SUBR
        HLT
SUBR:   INR A
        RET
DATA:   DB 42H, 'A'
        DW 1234H
        DS 10
        END
```

---

## 9. Memory Test / Тест памяти

**EN:**

### Parameters
- **Start** — start address (HEX)
- **End** — end address (HEX)
- **Pattern** — pattern selection:
  - **Checker** — chessboard pattern (55/AA)
  - **Zero** — all zeros
  - **One** — all FF
  - **Addr** — value equals address

### Run
Click **"Run Memory Test"**. Progress shown in progress bar. Errors logged with address, expected and actual values.

> ⚠️ Memory test overwrites RAM contents. Do not run on areas with important data.

**RU:**

### Параметры
- **Start** — начальный адрес (HEX)
- **End** — конечный адрес (HEX)
- **Паттерн** — выбор:
  - **Checker** — шахматный паттерн (55/AA)
  - **Zero** — все нули
  - **One** — все FF
  - **Addr** — значение равно адресу

### Запуск
Нажмите **«Запустить тест памяти»**. Прогресс в прогресс-баре. Ошибки в журнале с адресом, ожидаемым и полученным значениями.

> ⚠️ Тест памяти перезаписывает содержимое RAM. Не запускайте на важных данных.

---

## 10. IO Sequencer / IO Секвенсор

### 10.1. Single IO Operations / Одиночные операции

**EN:**
- **Port (HEX)** — port number
- **Value (HEX)** — value
- **"Read (IN)"** and **"Write (OUT)"** buttons

**RU:**
- **Порт (HEX)** — номер порта
- **Значение (HEX)** — значение
- Кнопки **«Читать (IN)»** и **«Записать (OUT)»**

### 10.2. Sequences / Последовательности

**EN:**

**Sequence format:**
```
W 01 FF ; Write FF to port 01h
R 02    ; Read from port 02h
D 10    ; Delay 10 ms
```

- **W PP DD** — write value DD to port PP
- **R PP** — read from port PP
- **D NN** — delay NN milliseconds
- Lines starting with `;` or `#` are comments

**Controls:**
- **"Load File..."** — load sequence from file
- **"Execute Sequence"** — run sequence

**RU:**

**Формат последовательности:**
```
W 01 FF ; Запись FF в порт 01h
R 02    ; Чтение из порта 02h
D 10    ; Задержка 10 мс
```

- **W PP DD** — запись значения DD в порт PP
- **R PP** — чтение из порта PP
- **D NN** — задержка NN миллисекунд
- Строки, начинающиеся с `;` или `#` — комментарии

**Управление:**
- **«Загрузить файл...»** — загрузка последовательности из файла
- **«Выполнить последовательность»** — выполнение

---

## 11. Comparison / Сравнение

**EN:**

### Usage
1. **"Load file for comparison"** — load file (.hex / .bin)
2. **"Compare"** — run comparison
3. **"Export Report"** — export results to file (.txt / .csv)

### Results
Table displays differences:
- **Address** — difference address
- **Current** — current value
- **File** — value from file
- **Status** — difference type:
  - 🟡 **Modified** — value differs
  - 🟢 **Added in file** — exists in file, missing in current image
  - 🔴 **Removed** — exists in current image, missing in file

**RU:**

### Использование
1. **«Загрузить файл для сравнения»** — загрузка файла (.hex / .bin)
2. **«Сравнить»** — выполнение сравнения
3. **«Экспорт отчёта»** — экспорт результатов в файл (.txt / .csv)

### Результаты
Таблица отображает различия:
- **Адрес** — адрес различия
- **Текущий** — текущее значение
- **Файл** — значение из файла
- **Статус** — тип различия:
  - 🟡 **Изменено** — значение отличается
  - 🟢 **Добавлено в файле** — есть в файле, отсутствует в текущем образе
  - 🔴 **Удалено** — есть в текущем образе, отсутствует в файле

---

## 12. Scripts / Скрипты

**EN:**

### Interface
- **Code editor** — Python script editor
- **Output** — script output (print)
- Buttons:
  - **▶ Run Script** — execute
  - **Load Script** — load from file (.py / .txt)
  - **Save Script** — save to file
  - **Clear Output** — clear output window

### Available Functions

| Function | Purpose |
|---|---|
| `read_mem(addr)` | Read byte from local image |
| `write_mem(addr, val)` | Write byte to local image |
| `read_block(addr, size)` | Read block from local image |
| `write_block(addr, data)` | Write block to local image |
| `fill_mem(addr, size, val)` | Fill range |
| `dev_read_mem(addr)` | Read from device memory |
| `dev_write_mem(addr, val)` | Write to device memory |
| `dev_read_io(port)` | Read device IO port |
| `dev_write_io(port, val)` | Write to device IO port |
| `download(addr, size)` | Read block from device |
| `upload(addr, size)` | Write block to device |
| `download_all(start, end)` | Read all device memory |
| `upload_all()` | Write entire image to device |
| `hold_bus()` | Hold bus |
| `unhold_bus()` | Release bus |
| `wait_bus(timeout)` | Wait for bus hold |
| `wait_unhold(timeout)` | Wait for bus release |
| `load_file(path, base_addr)` | Load file into image |
| `save_file(path)` | Save image to file |
| `disassemble(addr, length, show)` | Disassemble |
| `search(pattern, mode)` | Search in image |
| `refresh()` | Refresh GUI |
| `log(msg)` | Output to log |
| `status()` | Current state |
| `goto(addr)` | Go to address |

Full guide: **SCRIPTS_GUIDE.md**

**RU:**

### Интерфейс
- **Редактор кода** — редактор Python-скрипта
- **Вывод** — вывод скрипта (print)
- Кнопки:
  - **▶ Выполнить скрипт**
  - **Загрузить скрипт** — загрузка из файла (.py / .txt)
  - **Сохранить скрипт** — сохранение в файл
  - **Очистить вывод** — очистка окна вывода

### Доступные функции

| Функция | Назначение |
|---|---|
| `read_mem(addr)` | Чтение байта из локального образа |
| `write_mem(addr, val)` | Запись байта в локальный образ |
| `read_block(addr, size)` | Чтение блока из локального образа |
| `write_block(addr, data)` | Запись блока в локальный образ |
| `fill_mem(addr, size, val)` | Заполнение диапазона |
| `dev_read_mem(addr)` | Чтение из памяти устройства |
| `dev_write_mem(addr, val)` | Запись в память устройства |
| `dev_read_io(port)` | Чтение IO-порта устройства |
| `dev_write_io(port, val)` | Запись в IO-порт устройства |
| `download(addr, size)` | Чтение блока из устройства |
| `upload(addr, size)` | Запись блока в устройство |
| `download_all(start, end)` | Чтение всей памяти устройства |
| `upload_all()` | Запись всего образа в устройство |
| `hold_bus()` | Захват шины |
| `unhold_bus()` | Освобождение шины |
| `wait_bus(timeout)` | Ожидание захвата шины |
| `wait_unhold(timeout)` | Ожидание освобождения шины |
| `load_file(path, base_addr)` | Загрузка файла в образ |
| `save_file(path)` | Сохранение образа в файл |
| `disassemble(addr, length, show)` | Дизассемблирование |
| `search(pattern, mode)` | Поиск в образе |
| `refresh()` | Обновление GUI |
| `log(msg)` | Вывод в журнал |
| `status()` | Текущее состояние |
| `goto(addr)` | Переход к адресу |

Подробное описание — в **SCRIPTS_GUIDE.md**.

---

## 13. Emulator / Эмулятор

**EN:** Full i8080 CPU debugger. Tab is divided into 4 columns:

### 13.1. Column 1: Disassembled Code

Displays disassembled code with:
- **►** — current PC position (yellow highlight)
- **●** — breakpoints (red = regular, orange = conditional)
- **▷** — Run to Cursor (green)
- Jump arrows

**Interaction:**
- **Single click** — set Run to Cursor
- **Double click** — toggle breakpoint
- **Context menu** (right-click):
  - ▶ Run to Cursor (Ctrl+F10)
  - ⤳ Run from Here
  - ⇢ Jump to Cursor
  - ● Toggle Breakpoint
  - ◉ Set Conditional BP...

### 13.2. Column 2: Watch

Watch window for observing memory and register values.

**Watch types:**
- **Memory (byte)** — watch a memory byte
- **Memory (word)** — watch a word (2 bytes)
- **Register** — watch a register (A, B, C, D, E, H, L, BC, DE, HL, SP, PC, FLAGS)

**Display formats:** hex, dec, signed, bin, ascii

**Features:**
- Add/remove watch items
- Clear all items
- Save/Load presets (JSON)
- Highlight changed values (red background)

### 13.3. Column 3: Breakpoints

**Table columns:**
- **Address** — breakpoint address
- **Condition** — trigger condition (for conditional BP)
- **Enabled** — enabled/disabled (✓/✗)
- **Hits** — hit count

**Buttons:**
- **+** — add breakpoint
- **🔧** — edit condition (double-click row)
- **🚫** — enable/disable
- **❌** — remove selected
- **✕** — clear all
- **💾** — save BP preset (JSON)
- **📂** — load BP preset

### 13.4. Column 4: Registers, Flags, Stack, Statistics

- **Registers** — A, B, C, D, E, H, L, SP, PC, BC, DE, HL. Changed registers highlighted in red.
- **Flags** — S, Z, AC, P, CY. Set flags highlighted in red.
- **Stack** — top 8 values. Stack top highlighted in red.
- **Statistics** — cycle count, state (Halted / Running / Ready).

### 13.5. Bottom Control Panel

| Button | Hotkey | Purpose |
|---|---|---|
| Reset | Ctrl+F2 | Reset emulator |
| Set PC... | — | Set PC manually |
| Step Into | F11 | Step with subroutine entry |
| Step Over | F10 | Step without subroutine entry |
| ▶ Run | F5 | Start execution |
| ■ Stop | F8 | Stop execution |
| ☑ Trace | — | Enable trace recording |

### 13.6. Conditional Breakpoints

**Available variables:**
- Registers: `A`, `B`, `C`, `D`, `E`, `H`, `L`, `BC`, `DE`, `HL`, `SP`, `PC`
- Flags: `S`, `Z`, `AC`, `P`, `CY`
- Memory: `mem[0x0100]`
- IO ports: `io[0x01]`
- Cycles: `cycles`
- Operators: `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`

**Examples:**
```
A == 0x55                    — stop when A becomes 0x55
HL > 0x1000                  — when HL exceeds 0x1000
mem[0x0100] == 0xFF          — when memory cell becomes FF
Z == 1                       — when Zero flag is set
cycles > 10000               — after 10000 cycles
HL > 0x1000 and Z == 0       — combined conditions
```

**RU:**

Полноценный отладчик процессора i8080. Вкладка разделена на 4 колонки:

### 13.1. Колонка 1: Дизассемблированный код

Отображает код с:
- **►** — текущая позиция PC (жёлтая подсветка)
- **●** — точки останова (красный — обычная, оранжевый — условная)
- **▷** — курсор Run to Cursor (зелёный)
- Стрелки переходов

**Взаимодействие:**
- **Одинарный клик** — установка курсора Run to Cursor
- **Двойной клик** — установка/удаление точки останова
- **Контекстное меню** (правый клик):
  - ▶ Run to Cursor (Ctrl+F10)
  - ⤳ Run from Here
  - ⇢ Jump to Cursor
  - ● Toggle Breakpoint
  - ◉ Set Conditional BP...

### 13.2. Колонка 2: Watch

Watch-окно для наблюдения за значениями памяти и регистров.

**Типы наблюдения:**
- **Память (байт)**
- **Память (слово)**
- **Регистр** (A, B, C, D, E, H, L, BC, DE, HL, SP, PC, FLAGS)

**Форматы:** hex, dec, signed, bin, ascii

**Возможности:**
- Добавление/удаление элементов
- Очистка всех элементов
- Сохранение/загрузка пресетов (JSON)
- Подсветка изменённых значений (красный фон)

### 13.3. Колонка 3: Breakpoints / Точки останова

**Кнопки:**
- **+** — добавить точку останова
- **🔧** — редактировать условие
- **🚫** — включить/выключить
- **❌** — удалить выбранную
- **✕** — очистить все
- **💾** — сохранить пресет BP (JSON)
- **📂** — загрузить пресет BP

### 13.4. Колонка 4: Регистры, Флаги, Стек, Статистика

- **Регистры** — изменённые подсвечиваются красным
- **Флаги** — установленные подсвечиваются красным
- **Стек** — верхние 8 значений, вершина подсвечена
- **Статистика** — такты, состояние (Остановлен / Выполняется / Готов)

### 13.5. Нижняя панель управления

| Кнопка | Горячая клавиша | Назначение |
|---|---|---|
| Reset | Ctrl+F2 | Сброс эмулятора |
| Set PC... | — | Установка PC вручную |
| Step Into | F11 | Шаг с заходом в подпрограммы |
| Step Over | F10 | Шаг без захода в подпрограммы |
| ▶ Run | F5 | Запуск выполнения |
| ■ Stop | F8 | Остановка выполнения |
| ☑ Трассировка | — | Включение записи трассировки |

### 13.6. Условные точки останова

**Доступные переменные:**
- Регистры: `A`, `B`, `C`, `D`, `E`, `H`, `L`, `BC`, `DE`, `HL`, `SP`, `PC`
- Флаги: `S`, `Z`, `AC`, `P`, `CY`
- Память: `mem[0x0100]`
- IO-порты: `io[0x01]`
- Такты: `cycles`

**Примеры условий:**
```
A == 0x55                    — когда A станет 0x55
HL > 0x1000                  — когда HL превысит 0x1000
mem[0x0100] == 0xFF          — когда ячейка станет FF
Z == 1                       — когда флаг Zero установлен
cycles > 10000               — после 10000 тактов
HL > 0x1000 and Z == 0       — комбинация условий
```

---

## 14. Trace Log / Трассировка

### 14.1. Control Panel / Панель управления

**EN:**
- **🔥 Enable Recording** — enable trace recording
- **🗑 Clear** — clear trace buffer
- **💾 Export** — export trace (TXT / CSV / JSON)
- **Depth** — max record count (default 10000)
- **Records: X / Y** — current / max

**RU:**
- **🔥 Включить запись** — включение записи трассировки
- **🗑 Очистить** — очистка буфера
- **💾 Экспорт** — экспорт трассировки (TXT / CSV / JSON)
- **Глубина** — максимальное количество записей (по умолчанию 10000)
- **Записей: X / Y** — текущее / максимальное

### 14.2. Search / Поиск

**EN:**

Search field supports:
- **Address (HEX)** — e.g., `0010` — search by PC address
- **Register OP value** — e.g., `A==55`, `HL>1000`, `SP<=F000`, `Z=1`
- **Mnemonic** — e.g., `CPI`, `JMP`

**Comparison operators:** `=`, `==`, `!=`, `>`, `<`, `>=`, `<=`

**RU:**

Поле поиска поддерживает:
- **Адрес (HEX)** — например, `0010`
- **Регистр ОП значение** — например, `A==55`, `HL>1000`, `SP<=F000`, `Z=1`
- **Мнемоника** — например, `CPI`, `JMP`

**Операторы сравнения:** `=`, `==`, `!=`, `>`, `<`, `>=`, `<=`

### 14.3. Trace Table / Таблица трассировки

| Column / Колонка | Purpose / Назначение |
|---|---|
| # | Record number / Номер записи |
| PC | Instruction address / Адрес инструкции |
| Bytes | Instruction bytes / Байты инструкции |
| Mnemonic | Instruction mnemonic / Мнемоника |
| A | Accumulator / Аккумулятор |
| BC | BC pair / Пара BC |
| DE | DE pair / Пара DE |
| HL | HL pair / Пара HL |
| SP | Stack pointer / Указатель стека |
| Flags | Flags (S Z A P C) / Флаги |

### 14.4. Export / Экспорт

Supported formats: **TXT**, **CSV**, **JSON**

---

## 15. Hotkeys / Горячие клавиши

### General / Общие

| Key / Клавиша | Purpose / Назначение |
|---|---|
| Ctrl+O | Load firmware / Загрузить прошивку |
| Ctrl+S | Save dump / Сохранить дамп |
| Ctrl+E | Export disassembler / Экспорт дизассемблера |
| Ctrl+Q | Quit / Выход |
| Ctrl+F | Search in memory / Поиск в памяти |
| Ctrl+G | Go to address / Перейти к адресу |
| Ctrl+D | Disassemble / Дизассемблировать |
| Ctrl+H | Hold bus / Захватить шину |
| Ctrl+U | Release bus / Освободить шину |
| Ctrl+R | Refresh / Обновить |
| Ctrl+Z | Undo |
| Ctrl+Y / Ctrl+Shift+Z | Redo |

### Emulator / Эмулятор

| Key / Клавиша | Purpose / Назначение |
|---|---|
| F5 | Run / Запуск |
| F10 | Step Over / Шаг без захода |
| F11 | Step Into / Шаг с заходом |
| F8 | Stop / Остановка |
| Ctrl+F2 | Reset / Сброс |
| Ctrl+F10 | Run to Cursor |

### Assembler / Ассемблер

| Key / Клавиша | Purpose / Назначение |
|---|---|
| Ctrl + mouse wheel | Change editor font size / Изменить размер шрифта редактора |

---

## 16. MCP Integration / MCP-интеграция

**EN:** The program includes a built-in MCP server for integration with AI assistants (Claude, Cursor, VS Code, etc.).

### Enabling MCP Server
1. "Control" tab
2. Click **"MCP Server: OFF"** — it will toggle to **"MCP Server: ON"**
3. Server available at `http://127.0.0.1:8000/sse`

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "i8080-ci": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

Full description: **MCP_GUIDE.md**

**RU:** Программа включает встроенный MCP-сервер для интеграции с AI-ассистентами (Claude, Cursor, VS Code и др.).

### Включение MCP-сервера
1. Вкладка «Управление»
2. Нажмите **«MCP Server: OFF»** — переключится на **«MCP Server: ON»**
3. Сервер доступен по адресу `http://127.0.0.1:8000/sse`

### Конфигурация для Claude Desktop
```json
{
  "mcpServers": {
    "i8080-ci": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

Подробное описание: **MCP_GUIDE.md**

---

## 17. Typical Workflows / Типовые сценарии

### 17.1. Load and Disassemble Firmware / Загрузка и дизассемблирование

**EN:**
1. "Control" tab → "Load Firmware" → select .hex/.bin file
2. "Disassembler" tab → "Disassemble"
3. Study code using jump arrows and color highlighting

**RU:**
1. Вкладка «Управление» → «Загрузить прошивку» → выберите .hex/.bin файл
2. Вкладка «Дизассемблер» → «Дизассемблировать»
3. Изучите код, используя стрелки переходов и цветовую подсветку

### 17.2. Debug in Emulator / Отладка в эмуляторе

**EN:**
1. Load firmware
2. "Emulator" tab
3. Set breakpoints (double-click code line)
4. Press F5 to run or F11 for step execution
5. Observe registers, flags, and stack
6. Use Watch window to monitor memory

**RU:**
1. Загрузите прошивку
2. Вкладка «Эмулятор»
3. Установите точки останова (двойной клик по строке кода)
4. Нажмите F5 для запуска или F11 для пошагового выполнения
5. Наблюдайте за регистрами, флагами и стеком
6. Используйте Watch-окно для наблюдения за памятью

### 17.3. Conditional Debugging / Условная отладка

**EN:**
1. Set a breakpoint
2. Double-click breakpoint → enter condition
3. Run execution — will stop only when condition is met

**RU:**
1. Установите точку останова
2. Двойной клик по точке → введите условие
3. Запустите — остановится только при выполнении условия

### 17.4. Analysis with Trace / Анализ с трассировкой

**EN:**
1. "Emulator" tab → enable "Trace" checkbox
2. Execute program (F5) or step (F11)
3. "Trace Log" tab — study execution history
4. Use search to filter
5. Export trace for further analysis

**RU:**
1. Вкладка «Эмулятор» → включите «Трассировка»
2. Выполните программу (F5) или пошагово (F11)
3. Вкладка «Трассировка» — изучите историю
4. Используйте поиск для фильтрации
5. Экспортируйте трассировку для анализа

### 17.5. Work with Real Device / Работа с реальным устройством

**EN:**
1. Connect to device (COM port)
2. Hold bus (Ctrl+H)
3. Read/write memory and IO ports
4. Release bus (Ctrl+U)

**RU:**
1. Подключитесь к устройству (COM-порт)
2. Захватите шину (Ctrl+H)
3. Читайте/записывайте память и IO-порты
4. Освободите шину (Ctrl+U)

### 17.6. Device Memory Test / Тестирование памяти устройства

**EN:**
1. Connect to device and hold bus
2. "Memory Test" tab
3. Specify range and pattern
4. Run test
5. Study results in log

**RU:**
1. Подключитесь к устройству и захватите шину
2. Вкладка «Тест Памяти»
3. Укажите диапазон и паттерн
4. Запустите тест
5. Изучите результаты в журнале

### 17.7. Compare Images / Сравнение образов

**EN:**
1. Load current image (or connect to device and read memory)
2. "Comparison" tab → "Load file for comparison"
3. Click "Compare"
4. Study differences in table

**RU:**
1. Загрузите текущий образ (или подключитесь к устройству и прочитайте память)
2. Вкладка «Сравнение» → «Загрузить файл для сравнения»
3. Нажмите «Сравнить»
4. Изучите различия в таблице

---

### 17.8. Write, Assemble & Debug a Program / Написание, сборка и отладка программы

**EN:**
1. "Assembler" tab → type or load the source
2. Click **"Assemble"** — check the error panel and the label table
3. Click **"Assemble & Load"** — the binary is written to memory at the `ORG` address and PC is set there
4. "Emulator" tab → set breakpoints (double-click a code line)
5. Press F5 to run or F11 to step; watch registers, flags, and stack

**RU:**
1. Вкладка «Ассемблер» → введите или загрузите исходный код
2. Нажмите **«Ассемблировать»** — проверьте панель ошибок и таблицу меток
3. Нажмите **«Ассемблировать и загрузить»** — бинарник записан в память по адресу `ORG`, PC установлен туда
4. Вкладка «Эмулятор» → установите точки останова (двойной клик по строке кода)
5. Нажмите F5 для запуска или F11 для пошагового выполнения; наблюдайте за регистрами, флагами и стеком

---

## Appendix / Приложения

### A. Supported i8080 Instructions / Поддерживаемые инструкции

**EN:** The emulator supports all 256 i8080 instructions, including undocumented:
- NOP* (08, 10, 18, 20, 28, 30, 38, DD, ED, FD)
- RET* (D9)
- CALL* (CB)

**RU:** Эмулятор поддерживает все 256 инструкций i8080, включая недокументированные.

### B. Device Communication Protocol / Протокол связи

**EN:** SLIP protocol via COM port:
- Baud rates: 9600, 38400, 57600, 115200
- Commands: NOP, HOLD, UNHOLD, read/write memory, read/write IO

**RU:** Протокол SLIP через COM-порт:
- Скорости: 9600, 38400, 57600, 115200
- Команды: NOP, HOLD, UNHOLD, чтение/запись памяти, чтение/запись IO

### C. File Formats / Форматы файлов

- **Intel HEX (.hex)** — standard firmware format
- **Binary (.bin)** — binary format (base address requested on load)

### D. Preset Formats / Форматы пресетов

- **Watch presets** — JSON (watch_preset.json)
- **BP presets** — JSON (bp_preset.json)

---

*Documentation generated for i8080-5 CI version 2.2.*
*Документация сгенерирована для версии 2.2 программы i8080-5 CI.*
