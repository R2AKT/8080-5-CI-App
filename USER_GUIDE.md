# i8080-5 CI — User Guide / Пользовательское руководство

> **Version / Версия:** 2.1
> **Date / Дата:** 2026-09-14
> **Platform / Платформа:** Windows / Linux
> **UI Languages / Языки интерфейса:** Русский, English

---

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
8. [Memory Test / Тест памяти](#8-memory-test--тест-памяти)
9. [IO Sequencer / IO Секвенсор](#9-io-sequencer--io-секвенсор)
10. [Comparison / Сравнение](#10-comparison--сравнение)
11. [Scripts / Скрипты](#11-scripts--скрипты)
12. [Emulator / Эмулятор](#12-emulator--эмулятор)
13. [Trace Log / Трассировка](#13-trace-log--трассировка)
14. [Hotkeys / Горячие клавиши](#14-hotkeys--горячие-клавиши)
15. [MCP Integration / MCP-интеграция](#15-mcp-integration--mcp-интеграция)
16. [Typical Workflows / Типовые сценарии](#16-typical-workflows--типовые-сценарии)

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
2. **Tabs** — 10 tabs with various functions
3. **Log** — bottom panel with operation log

**RU:** Главное окно состоит из:
1. **Верхняя панель** — выбор COM-порта, скорости, подключение/отключение, выбор языка и темы
2. **Вкладки** — 10 вкладок с различными функциями
3. **Журнал** — нижняя панель с журналом операций

### Tab Order / Порядок вкладок

| # | EN | RU | Purpose |
|---|---|---|---|
| 0 | Control | Управление | Connection, bus, files |
| 1 | Data | Данные | Read/write memory and IO |
| 2 | Hex Editor | Hex Редактор | View and edit memory |
| 3 | Disassembler | Дизассемблер | Disassemble code |
| 4 | Memory Test | Тест Памяти | Test RAM |
| 5 | IO Sequencer | IO Секвенсор | IO sequences |
| 6 | Comparison | Сравнение | Compare memory images |
| 7 | Scripts | Скрипты | Automation |
| 8 | Emulator | Эмулятор | i8080 debugger |
| 9 | Trace Log | Трассировка | Execution trace view |

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

## 8. Memory Test / Тест памяти

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

## 9. IO Sequencer / IO Секвенсор

### 9.1. Single IO Operations / Одиночные операции

**EN:**
- **Port (HEX)** — port number
- **Value (HEX)** — value
- **"Read (IN)"** and **"Write (OUT)"** buttons

**RU:**
- **Порт (HEX)** — номер порта
- **Значение (HEX)** — значение
- Кнопки **«Читать (IN)»** и **«Записать (OUT)»**

### 9.2. Sequences / Последовательности

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

## 10. Comparison / Сравнение

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

## 11. Scripts / Скрипты

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

## 12. Emulator / Эмулятор

**EN:** Full i8080 CPU debugger. Tab is divided into 4 columns:

### 12.1. Column 1: Disassembled Code

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

### 12.2. Column 2: Watch

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

### 12.3. Column 3: Breakpoints

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

### 12.4. Column 4: Registers, Flags, Stack, Statistics

- **Registers** — A, B, C, D, E, H, L, SP, PC, BC, DE, HL. Changed registers highlighted in red.
- **Flags** — S, Z, AC, P, CY. Set flags highlighted in red.
- **Stack** — top 8 values. Stack top highlighted in red.
- **Statistics** — cycle count, state (Halted / Running / Ready).

### 12.5. Bottom Control Panel

| Button | Hotkey | Purpose |
|---|---|---|
| Reset | Ctrl+F2 | Reset emulator |
| Set PC... | — | Set PC manually |
| Step Into | F11 | Step with subroutine entry |
| Step Over | F10 | Step without subroutine entry |
| ▶ Run | F5 | Start execution |
| ■ Stop | F8 | Stop execution |
| ☑ Trace | — | Enable trace recording |

### 12.6. Conditional Breakpoints

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

### 12.1. Колонка 1: Дизассемблированный код

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

### 12.2. Колонка 2: Watch

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

### 12.3. Колонка 3: Breakpoints / Точки останова

**Кнопки:**
- **+** — добавить точку останова
- **🔧** — редактировать условие
- **🚫** — включить/выключить
- **❌** — удалить выбранную
- **✕** — очистить все
- **💾** — сохранить пресет BP (JSON)
- **📂** — загрузить пресет BP

### 12.4. Колонка 4: Регистры, Флаги, Стек, Статистика

- **Регистры** — изменённые подсвечиваются красным
- **Флаги** — установленные подсвечиваются красным
- **Стек** — верхние 8 значений, вершина подсвечена
- **Статистика** — такты, состояние (Остановлен / Выполняется / Готов)

### 12.5. Нижняя панель управления

| Кнопка | Горячая клавиша | Назначение |
|---|---|---|
| Reset | Ctrl+F2 | Сброс эмулятора |
| Set PC... | — | Установка PC вручную |
| Step Into | F11 | Шаг с заходом в подпрограммы |
| Step Over | F10 | Шаг без захода в подпрограммы |
| ▶ Run | F5 | Запуск выполнения |
| ■ Stop | F8 | Остановка выполнения |
| ☑ Трассировка | — | Включение записи трассировки |

### 12.6. Условные точки останова

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

## 13. Trace Log / Трассировка

### 13.1. Control Panel / Панель управления

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

### 13.2. Search / Поиск

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

### 13.3. Trace Table / Таблица трассировки

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

### 13.4. Export / Экспорт

Supported formats: **TXT**, **CSV**, **JSON**

---

## 14. Hotkeys / Горячие клавиши

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

---

## 15. MCP Integration / MCP-интеграция

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

## 16. Typical Workflows / Типовые сценарии

### 16.1. Load and Disassemble Firmware / Загрузка и дизассемблирование

**EN:**
1. "Control" tab → "Load Firmware" → select .hex/.bin file
2. "Disassembler" tab → "Disassemble"
3. Study code using jump arrows and color highlighting

**RU:**
1. Вкладка «Управление» → «Загрузить прошивку» → выберите .hex/.bin файл
2. Вкладка «Дизассемблер» → «Дизассемблировать»
3. Изучите код, используя стрелки переходов и цветовую подсветку

### 16.2. Debug in Emulator / Отладка в эмуляторе

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

### 16.3. Conditional Debugging / Условная отладка

**EN:**
1. Set a breakpoint
2. Double-click breakpoint → enter condition
3. Run execution — will stop only when condition is met

**RU:**
1. Установите точку останова
2. Двойной клик по точке → введите условие
3. Запустите — остановится только при выполнении условия

### 16.4. Analysis with Trace / Анализ с трассировкой

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

### 16.5. Work with Real Device / Работа с реальным устройством

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

### 16.6. Device Memory Test / Тестирование памяти устройства

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

### 16.7. Compare Images / Сравнение образов

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

*Documentation generated for i8080-5 CI version 2.1.*
*Документация сгенерирована для версии 2.1 программы i8080-5 CI.*
