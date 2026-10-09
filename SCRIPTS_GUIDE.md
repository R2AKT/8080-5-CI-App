# SCRIPTS_GUIDE.md — Руководство по скриптам i8080-5 CI

> **Версия:** 2.1.7  
> **Дата:** 2026-10-09  
> **Вкладка:** «Скрипты» (Scripts)

Скрипты позволяют автоматизировать работу с программой: читать/записывать память, управлять эмулятором, дизассемблировать код и управлять устройством через COM-порт.

---

## Содержание

1. [Открытие вкладки скриптов](#1-открытие-вкладки-скриптов)
2. [Интерфейс вкладки](#2-интерфейс-вкладки)
3. [Как пишутся скрипты](#3-как-пишутся-скрипты)
4. [Справочник функций](#4-справочник-функций)
5. [Функции эмулятора (через `api`)](#5-функции-эмулятора-через-api)
6. [Примеры скриптов](#6-примеры-скриптов)
7. [Советы и ограничения](#7-советы-и-ограничения)
8. [Скрипты автоматизации, тестов и сборки](#8-скрипты-автоматизации-тестов-и-сборки)

---

## 1. Открытие вкладки скриптов

Откройте вкладку **«Скрипты»** (Scripts) в главной панели вкладок.

## 2. Интерфейс вкладки

| Элемент | Назначение |
|---|---|
| ▶ Run Script | Выполнить скрипт из редактора |
| Load Script | Загрузить скрипт из файла (`.py` / `.txt`) |
| Save Script | Сохранить скрипт в файл |
| Clear Output | Очистить окно вывода |
| Редактор кода | Редактор Python-скрипта |
| Вывод (Output) | Результат выполнения скрипта |

Результат `print()` и `log()` попадает в окно «Вывод».

---

## 3. Как пишутся скрипты

Скрипты выполняются как обычный Python-код. Все функции API доступны **напрямую** (без префикса), а также через объект `api`.

```python
# Оба варианта работают:
fill_mem(0x0000, 256, 0x55)      # напрямую
api.fill_mem(0x0000, 256, 0x55)  # через api
```

Функции эмулятора доступны **только через `api`**:

```python
api.emu_get_reg("A")
api.emu_reset()
```

Вывод в окно вывода — через `print()` или `log()`:

```python
print("Привет из скрипта")
log("Сообщение в журнал программы")
```

---

## 4. Справочник функций

### 📦 Локальная память (не требует устройства)

| Функция | Описание | Возвращает |
|---|---|---|
| `read_mem(addr)` | Прочитать байт по адресу | `int` или `None` |
| `write_mem(addr, val)` | Записать байт | `None` |
| `read_block(addr, size)` | Прочитать блок | `list[int]` |
| `write_block(addr, data)` | Записать блок | `None` |
| `fill_mem(addr, size, val)` | Заполнить диапазон | `None` |

### 🔌 Память и порты устройства (требуют шину)

| Функция | Описание | Возвращает |
|---|---|---|
| `dev_read_mem(addr)` | Прочитать байт из устройства | `int` или `None` |
| `dev_write_mem(addr, val)` | Записать байт в устройство | `bool` |
| `dev_read_io(port)` | Прочитать IO-порт | `int` или `None` |
| `dev_write_io(port, val)` | Записать IO-порт | `bool` |

### 🔄 Синхронизация устройство ↔ образ (требуют шину)

| Функция | Описание | Возвращает |
|---|---|---|
| `download(addr, size)` | Устройство → образ | `list[int]` или `None` |
| `upload(addr, size)` | Образ → устройство | `bool` |
| `download_all(start=0, end=0xFFFF)` | Вся память устройства → образ | `list[int]` |
| `upload_all()` | Весь образ → устройство | `bool` |

### 🚌 Шина (требуют подключения)

| Функция | Описание | Возвращает |
|---|---|---|
| `hold_bus()` | Захватить шину (HOLD) | `bool` |
| `unhold_bus()` | Освободить шину | `bool` |
| `wait_bus(timeout=5.0)` | Ждать захвата шины | `bool` |
| `wait_unhold(timeout=5.0)` | Ждать освобождения шины | `bool` |

### 📁 Файлы

| Функция | Описание | Возвращает |
|---|---|---|
| `load_file(path, base_addr=0)` | Загрузить `.hex`/`.bin` в образ | `int` (кол-во байт) |
| `save_file(path)` | Сохранить образ в файл | `bool` |

### 🛠 Утилиты

| Функция | Описание | Возвращает |
|---|---|---|
| `disassemble(addr=None, length=None, show=False)` | Дизассемблировать образ | `list[str]` |
| `search(pattern, mode="hex")` | Поиск в образе (`hex`/`ascii`) | `list[int]` |
| `refresh()` | Обновить hex-редактор и дизассемблер | `None` |
| `log(msg)` | Вывод в журнал программы | `None` |
| `status()` | Состояние программы | `dict` |
| `goto(addr)` | Перейти к адресу в hex-редакторе | `None` |

### 🎵 Ассемблер (asm_*)

| Функция | Описание | Возвращает |
|---|---|---|
| `asm_get_source()` | Прочитать текущий исходный код ассемблера | `str` |
| `asm_set_source(source)` | Установить исходный код ассемблера | `None` |
| `asm_load_file(path)` | Загрузить `.asm` файл в редактор ассемблера | `bool` |
| `asm_assemble(source=None, load_to_memory=False)` | Скомпилировать (опц. загрузить в память) | `AsmResult` |
| `asm_get_binary()` | Прочитать последний скомпилированный бинарник | `bytes` |
| `asm_get_symbols()` | Прочитать таблицу символов последнего компиля | `dict` |
| `asm_assemble_obj(path, source=None)` | Скомпилировать и сохранить объектный файл (`.obj`) | `ObjectFile` |
| `asm_link(script_path=None, obj_paths=None, origin=0, size=0x10000, fill=0xFF)` | Слинковать объектные файлы (по `.lnk` скрипту или списку `.obj`) | `LinkResult` |
| `asm_load_map(path)` | Загрузить `.map` файл в дизассемблер для резолва символов | `MapFile` |

**Поле `AsmResult`:** `success` (bool), `binary` (bytes), `origin` (int), `symbols` (dict), `errors` (list), `warnings` (list), `listing` (str), `end_address` (int), `exports` (list), `imports` (list), `relocations` (list)

**Поле `LinkResult`:** `success` (bool), `binary` (bytes), `origin` (int), `size` (int), `symbols` (dict), `errors` (list), `warnings` (list), `map_text` (str)

---

## 5. Функции эмулятора (через `api`)

| Функция | Описание | Возвращает |
|---|---|---|
| `api.emu_reset()` | Сброс эмулятора | `str` |
| `api.emu_step()` | Выполнить одну инструкцию | `str` |
| `api.emu_get_reg(reg)` | Прочитать регистр | `int` |
| `api.emu_set_reg(reg, val)` | Установить регистр | `str` |
| `api.emu_get_psw()` | Прочитать PSW | `int` |
| `api.emu_set_psw(val)` | Установить PSW | `str` |
| `api.emu_get_flags()` | Прочитать флаги | `dict` |
| `api.emu_set_flag(flag, val)` | Установить флаг | `str` |
| `api.emu_get_state()` | Полное состояние | `dict` |

**Регистры:** `A`, `B`, `C`, `D`, `E`, `H`, `L`, `BC`, `DE`, `HL`, `SP`, `PC`  
**Флаги:** `S`, `Z`, `AC`, `P`, `CY`

---

## 6. Примеры скриптов

### Пример 1: Заполнить память паттерном

```python
# Заполнить 256 байт паттерном 0x55, начиная с 0x0000
fill_mem(0x0000, 256, 0x55)
refresh()
log("Память заполнена паттерном 0x55")
```

### Пример 2: Дизассемблировать и вывести

```python
# Дизассемблировать 16 байт с адреса 0x0000
for line in disassemble(0x0000, 16):
    print(line)
```

### Пример 3: Поиск в памяти

```python
# Найти все JMP (0xC3)
results = search('C3', 'hex')
print(f"Найдено {len(results)} JMP инструкций:")
for addr in results:
    print(f"  0x{addr:04X}")
```

### Пример 4: Поиск ASCII-строки

```python
results = search("HELLO", "ascii")
print(f"Найдено {len(results)} совпадений")
for addr in results:
    print(f"  0x{addr:04X}")
```

### Пример 5: Работа с эмулятором

```python
# Сбросить эмулятор
api.emu_reset()

# Установить регистры
api.emu_set_reg("A", 0x55)
api.emu_set_reg("BC", 0x1234)

# Выполнить 5 инструкций
for i in range(5):
    api.emu_step()

# Вывести состояние
state = api.emu_get_state()
print(f"PC=0x{state['PC']:04X}, A=0x{state['A']:02X}")
print(f"Флаги: {state['flags']}")
```

### Пример 6: Проверка значения памяти

```python
# Проверить значение по адресу 0x0100
val = read_mem(0x0100)
if val is None:
    print("Адрес 0x0100 не инициализирован")
else:
    print(f"0x0100 = 0x{val:02X}")
```

### Пример 7: Работа с устройством (требует подключения)

```python
# Захватить шину
hold_bus()
if not wait_bus(5.0):
    print("Не удалось захватить шину")
else:
    # Прочитать байт из устройства
    val = dev_read_mem(0x0000)
    print(f"Устройство 0x0000 = 0x{val:02X}")

    # Освободить шину
    unhold_bus()
    wait_unhold(5.0)
```

### Пример 8: Считать память устройства в образ

```python
hold_bus()
if wait_bus(5.0):
    # Считать 4 КБ с адреса 0x0000
    data = download(0x0000, 4096)
    if data:
        print(f"Считано {len(data)} байт")
    unhold_bus()
    wait_unhold(5.0)
```

### Пример 9: Состояние программы

```python
s = status()
print(f"Подключено: {s['connected']}")
print(f"Шина активна: {s['bus_active']}")
print(f"Размер образа: {s['mem_size']} байт")
```

### Пример 10: Сложный скрипт — анализ диапазона

```python
# Проанализировать диапазон 0x0000-0x00FF
print("=== Анализ диапазона 0x0000-0x00FF ===")

# Подсчитать количество каждого байта
from collections import Counter
block = read_block(0x0000, 256)
counts = Counter(block)

# Вывести самые частые байты
print("Самые частые байты:")
for val, count in counts.most_common(5):
    print(f"  0x{val:02X}: {count} раз")

# Дизассемблировать диапазон
print("\nДизассемблирование:")
for line in disassemble(0x0000, 32):
    print(line)
```

### Пример 11: Ассемблирование и загрузка в память

```python
# Установить исходный код
src = (
    'ORG 0x0100\n'
    'start:\n'
    '    LXI B, 0x0005\n'
    '    MVI A, 0x41\n'
    'loop:\n'
    '    DCR B\n'
    '    JNZ loop\n'
    '    HLT\n'
)
asm_set_source(src)

# Скомпилировать и загрузить в память
result = asm_assemble(load_to_memory=True)
if result.success:
    print(f'Успех: {len(result.binary)} байт, ORG=0x{result.origin:04X}')
    print(f'Символы: {result.symbols}')
else:
    print('Ошибки:')
    for err in result.errors:
        print(f'  {err}')

# Прочитать бинарник
binary = asm_get_binary()
print(f'Бинарник: {binary.hex()}')
```

### Пример 12: Загрузка .asm файла и компиляция

```python
# Загрузить файл
if asm_load_file('program.asm'):
    result = asm_assemble(load_to_memory=True)
    if result.success:
        print(f'Загружено {len(result.binary)} байт в 0x{result.origin:04X}')
        # Дизассемблировать для проверки
        for line in disassemble(result.origin, len(result.binary)):
            print(line)
    else:
        for err in result.errors:
            print(f'Ошибка: {err}')
else:
    print('Не удалось загрузить файл')
```

### Пример 13: Объектные файлы и линковка

```python
# Модуль A: определяет и экспортирует HELPER
srcA = (
    'ORG 0x0200\n'
    'EXPORT HELPER\n'
    'HELPER:\n'
    '    MVI A, 42\n'
    '    RET\n'
)
asm_set_source(srcA)
asm_assemble_obj('helper.obj')

# Модуль B: импортирует HELPER и вызывает его
srcB = (
    'ORG 0x0100\n'
    'IMPORT HELPER\n'
    'START:\n'
    '    CALL HELPER\n'
    '    HLT\n'
)
asm_set_source(srcB)
asm_assemble_obj('main.obj')

# Линковка двух объектов
result = asm_link(obj_paths=['main.obj', 'helper.obj'], origin=0, size=0x10000)
if result.success:
    print(f'Слинковано: {len(result.binary)} байт')
    print(f'HELPER = 0x{result.symbols["HELPER"]:04X}')
    # Сохранить бинарник и map
    with open('app.bin', 'wb') as f:
        f.write(result.binary)
    if result.map_text:
        with open('app.map', 'w', encoding='utf-8') as f:
            f.write(result.map_text)
        # Загрузить map в дизассемблер для резолва символов
        asm_load_map('app.map')
else:
    for err in result.errors:
        print(f'Ошибка: {err}')
```

---

## 7. Советы и ограничения

### ✅ Советы

- **Используйте `print()`** для вывода результатов в окно «Вывод».
- **Используйте `log()`** для записи в журнал программы (вкладка «Управление»).
- **Обрабатывайте ошибки** через `try/except` для надёжности:

```python
try:
    val = read_mem(0x0000)
    print(f"0x0000 = 0x{val:02X}")
except Exception as e:
    print(f"Ошибка: {e}")
```

- **Используйте `refresh()`** после изменения памяти, чтобы обновить hex-редактор и дизассемблер.

### ⚠️ Ограничения

- **Скрипты выполняются синхронно** в главном потоке GUI. Долгие скрипты заблокируют интерфейс.
- **Функции устройства** (`dev_*`, `download`, `upload`) требуют подключения к устройству и захвата шины.
- **Скрипты не имеют доступа к GUI напрямую** (только через API).
- **Скрипты выполняются с правами программы** — будьте осторожны с записью в память устройства.

### 🔍 Пример обработки ошибок подключения

```python
s = status()
if not s['connected']:
    print("Устройство не подключено. Подключитесь во вкладке 'Управление'.")
else:
    hold_bus()
    if wait_bus(5.0):
        val = dev_read_mem(0x0000)
        print(f"0x0000 = 0x{val:02X}" if val is not None else "Ошибка чтения")
        unhold_bus()
        wait_unhold(5.0)
```

---

## 8. Скрипты автоматизации, тестов и сборки

Помимо встроенных скриптов вкладки «Скрипты», в корне проекта и в каталоге `tests/` есть консольные скрипты для автоматизации: запуск тестов, сборка примеров, генерация документов и референсов, а также CLI-ассемблер. Все команды выполняются из корня проекта.

### 8.1. Запуск тестов

| Скрипт | Назначение | Запуск |
|---|---|---|
| `run_tests.py` | Запускает 34 автономных unit-теста (без `api`) и сводит результат по ✅/❌. Базовый результат: 921 проверка пройдено, 0 провалов, 0 ошибок. | `python run_tests.py` |
| `_run_all_tests.py` | Полный цикл: (1) все автономные тесты в `tests/`, (2) интерактивные `api`-сниппеты через `run_api_snippets.py`. | `python _run_all_tests.py` |
| `tests/run_api_snippets.py` | Harness для 17 интерактивных `api`-сниппетов: загружает профиль `full`, создаёт `MainWindow` + `AutomationAPI` и выполняет каждый сниппет. | `python tests/run_api_snippets.py` |
| `tests/test_roundtrip_256.py` | Round-trip: assemble → disassemble → re-assemble → сравнение байтов для всех 256 опкодов (i8080 + i8085), по умолчанию 3 цикла. | `python tests/test_roundtrip_256.py [N]` |
| `tests/test_bin_compare.py` | Сравнение вывода ассемблера с 15 референсными файлами, сгенерированными реальным zasm (байт-в-байт). | `python tests/test_bin_compare.py` |

Примеры:

```bash
# Только unit-тесты (34 скрипта, 921 проверка)
python run_tests.py

# Полный цикл (автономные тесты + api-сниппеты)
python _run_all_tests.py

# Round-trip 256 опкодов, 3 цикла
python tests/test_roundtrip_256.py

# Сравнение с референсами zasm
python tests/test_bin_compare.py
```

### 8.2. Сборка и генерация документов

| Скрипт | Назначение | Запуск |
|---|---|---|
| `build_snapshot.py` | Регенерирует `PROJECT_SNAPSHOT.md` — монолитный срез проекта (дерево, AST-описание модулей, полный код ключевых файлов, тесты, профили). | `python build_snapshot.py [project_root] [output_file]` |
| `gen_refs.py` | Генерирует референсные `.bin`/`.rom` файлы реальным компилятором zasm (`c:\zasm\zasm.exe`) для 15 исходников в `ASM_FOR_TEST/`. | `python gen_refs.py` |
| `md2html.py` | Конвертация Markdown в HTML со sticky-навигацией, CSS и адаптивным дизайном. | `python md2html.py [input.md] [output.html]` |
| `clean_pycache.py` | Удаляет Python-кеш (`__pycache__/`, `*.pyc`, `*.pyo`) из дерева проекта. | `python clean_pycache.py [путь] [--dry-run]` |

Примеры:

```bash
# Пересоздать срез проекта
python build_snapshot.py

# Сгенерировать референсы zasm
python gen_refs.py

# HTML из Markdown
python md2html.py README.md

# Очистить кеш (предпросмотр без удаления)
python clean_pycache.py --dry-run
```

### 8.3. CLI ассемблера

Автономная сборка Intel 8080/8085 без GUI. Точка входа — `python -m assemble8080`.

```bash
# Самопроверка (без аргументов)
python -m assemble8080

# Собрать файл
python -m assemble8080 program.asm -o program.bin -m program.map

# Собрать для i8085 с hexdump и таблицей символов
python -m assemble8080 program.asm --cpu 8085 --hex --symbols

# Линковка по .lnk-скрипту
python -m assemble8080 --lnk app.lnk -o app.bin
```

| Опция | Описание |
|---|---|
| `sources` | Входные файлы `.asm`/`.mac`/`.s` |
| `-o`, `--output` | Выходной бинарник (по умолчанию `<input>.bin`) |
| `-m`, `--map` | Выходной map-файл (по умолчанию `<input>.map`) |
| `--obj` | Выходной объектный файл (по умолчанию `<input>.obj`) |
| `--cpu {8080,8085}` | Тип CPU (по умолчанию 8080) |
| `--lnk` | Линковочный скрипт `.lnk` для многофайловой сборки |
| `--hex` | Вывести hexdump результата |
| `--list` | Вывести листинг (адрес, байты, исходник) |
| `--symbols` | Вывести таблицу символов |
| `-q`, `--quiet` | Тихий режим (только ошибки) |
| `--version` | Версия ассемблера |

Коды возврата: `0` — успех, `1` — ошибка. Без аргументов (ни файлов, ни `--lnk`) выполняется самопроверка. Полное описание — в `ASSEMBLER_GUIDE.md` (раздел «Командная строка / CLI»).

### 8.4. Примеры ассемблера

В каталоге `assembler_example/` — 4 примера с проверкой ожидаемых байтов. Общий модуль — `_common.py` (функции `read`, `write_bin`, `assemble_file`, `report`, `save_obj_file`, `save_map`, `run_link`, `hexdump`).

| Пример | Что демонстрирует | Запуск |
|---|---|---|
| `01_hello` | Одиночный файл `hello.asm` → `hello.bin` + `hello.map` | `python assembler_example/01_hello/build.py` |
| `02_directives` | Все директивы (`#if`, `#include`, `#path`, `MACRO`, `REPT`, `DB`/`DW`/`DS`, `EQU`) | `python assembler_example/02_directives/build.py` |
| `03_macros` | Макросы, вложенные макросы, `REPT`, условная сборка | `python assembler_example/03_macros/build.py` |
| `04_multifile` | Многофайловая сборка с линковкой (`main.asm` + `helper.asm` → `.obj` → `app.lnk` → `app.bin` + `app.map`) | `python assembler_example/04_multifile/build.py` |

Собрать все примеры разом:

```bash
python assembler_example/build_all.py
```

### 8.5. Точки входа приложения

| Скрипт | Назначение | Запуск |
|---|---|---|
| `i8080_CI.py` | Главный вход GUI-приложения (PySide6, `MainWindow`). | `python i8080_CI.py` |
| `mcp_headless.py` | Headless-запуск MCP-сервера без GUI (SSE, порт 8000) для VS Code-плагина. | `python mcp_headless.py --profile full --port 8000` |
| `mcp_server.py` | Реализация MCP-сервера (`MCPServerManager`), используется `mcp_headless.py`. | — (модуль) |
| `i8080_emulator.py` | Модуль эмулятора процессора Intel 8080 (ядро, команды пересылки данных). | — (модуль) |
| `version.py` | Версия и сборка проекта (`__version__`, `__build__`). | — (модуль) |

> **Служебные скрипты** с префиксом `_` (`_apply_fixes.py`, `_audit_and_version.py`, `_facts.py`–`_facts4.py`, `_final_fixes.py`, `_fix_en.py`, `_read_code.py`–`_read_code4.py`, `_verify_fixes.py`, `_i18n_count.py`) — одноразовые утилиты для разовых правок и аудита; в штатной работе не используются.

---

*Конец документа SCRIPTS_GUIDE.md*