# Анализ ассемблера: текущее состояние (assemble8080)

## 1. Двухпроходный алгоритм

### Архитектура

Ассемблер реализует классическую **двухпроходную сборку**:

```
Препроцессор (preprocessor.py)
    ↓
Преход 1: сбор меток и адресов
    ↓
Преход 2: генерация кода
    ↓
AsmResult (binary, symbols, listing, map_text)
```

### Преход 1 — сбор меток

- Итерирует по обработанным строкам (после препроцессора)
- Регистрирует метки в `self.symbols` (ключ — UPPER, значение — текущий `location`)
- Двойное двоеточие (`LABEL::`) → глобальная метка (добавляется в `_global_labels` и `_exports`)
- Одинарное двоеточие (`LABEL:`) → локальная метка
- Метка без двоеточия (совместимость) — если первый токен не мнемоника и не директива
- Директивы `ORG`, `#code` (секции zasm), `DS`, `DB`, `DW` — сдвигают `location`
- `EQU`/`DEF` — вычисляют значение; если есть forward-ссылки — откладываются в `_pending_equ`
- Директивы CPU (`.8080`/`.8085`/`CPU 8080`/`CPU 8085`) — устанавливают `self.cpu_type`
- 47 no-op директив — пропускаются (`continue`)
- `END` — завершает проход

### Преход 2 — генерация кода

- Повторно итерирует по тем же строкам
- `ORG` — устанавливает `_base_offset` (первый ORG) или заполняет/откатывает буфер
- `#code` — переключает секцию, заполняет предыдущую до фиксированного размера
- `DB`/`DW`/`DS` — генерирует байты данных
- `INCBIN` — читает бинарный файл и вставляет в поток (см. §7)
- Инструкции — кодируются через `_encode_instruction()` с учётом `cpu_type`
- `IMPORT`-символы в операндах — отслеживаются как relocations
- Результат: `AsmResult` с `binary`, `symbols`, `listing`, `map_text`

### Ключевые структуры

| Структура | Назначение |
|---|---|
| `MNEMONICS` | Базовая таблица (общие задокументированные команды 8080/8085) |
| `MNEMONICS_8080` | Недокументированные 8080 (NOP*, JMP*, RET*, CALL*) |
| `MNEMONICS_8085` | Команды 8085 (SIM, RIM, DSUB, ARHL, RDEL, LDHI, LDSI, RSTV, SHLX, JNK, LHLX, JK) |
| `ExpressionParser` | Вычисление выражений (метки, `$`, `HIGH`/`LOW`, `#define`, char literals) |
| `AsmResult` | Результат: `binary`, `origin`, `symbols`, `errors`, `listing`, `exports`, `imports`, `relocations`, `map_text`, `global_labels`, `equ_symbols` |

---

## 2. Препроцессор (preprocessor.py, 630 строк)

### Поддерживаемые директивы

| Директива | Описание |
|---|---|
| `#include "file"` / `include "file"` / `.include "file"` | Включение файла (M80-стиль и C-стиль) |
| `#define NAME value` | Макрос-константа (подстановка в выражениях) |
| `#if` / `#elif` / `#else` / `#endif` | Условная компиляция (C-стиль) |
| `IF` / `ENDIF` / `ELSE` | Условная компиляция (M80-стиль, без `#`) |
| `MACRO` / `ENDM` | Макросы с параметрами (`&PARAM`, `%PARAM`, `#PARAM`, `\PARAM`) |
| `REPT n` / `ENDM` | Повтор блока n раз (расширяется до обработки строк) |
| `#path "dir"` / `.path "dir"` | Дополнительные каталоги поиска include |
| `#target rom` / `#target bin` | Целевой тип (влияет на fill-байт DS: rom=0xFF, bin/ram=0x00) |
| `#charset` | Пропускается (информационная) |

### Порядок поиска include-файлов

```
1. Каталог текущего файла (current_dir) — всегда первым
2. Каталоги из #path / .path (в порядке объявления)
3. include_dirs (каталог главного файла, CWD)
```

### Макросы

Форматы определения:
```asm
NAME MACRO [params]
NAME: MACRO [params]
.macro NAME [params]
```

Подстановка параметров: `&PARAM`, `%PARAM`, `#PARAM`, `\PARAM` (zasm-совместимо).
Максимальная вложенность: 10 уровней. REPT/ENDM расширяется **до** обработки строк.

### Нормализация

- Псевдокоманды с точкой (`.org`, `.db`, `.dw`, `.ds`, `.equ`, `.end`, `.macro`, `.endm`, `.byte`, `.word`, `.space`, `.include`, `.define`, `.if`, `.else`, `.endif`, `.high`, `.low`, `.not`, `.and`, `.or`, `.xor`, `.mod`, `.shl`, `.shr`) нормализуются к безточечной форме
- Нормализация применяется только вне строковых литералов (кавычек)
- `XDEF`/`XREF`/`SECTION`/`ASEG`/`TITLE`/`PUBLIC`/`EXTERN`/`MODULE` — пропускаются (no-op)
- `CPU`/`.8080`/`.8085`/`.asm8080`/`.asm8085` — **НЕ** удаляются (их обрабатывает ассемблер)

---

## 3. Директива CPU и поддержка i8080/i8085

### Директивы выбора процессора

| Директива | Результат |
|---|---|
| `.8080` / `.asm8080` | `cpu_type = "i8080"` |
| `.8085` / `.asm8085` | `cpu_type = "i8085"` |
| `CPU 8080` | `cpu_type = "i8080"` |
| `CPU 8085` | `cpu_type = "i8085"` |

Директива может встречаться в любом месте исходного кода и переопределяет `cpu_type` для последующих инструкций. По умолчанию — `"i8080"`.

### Таблицы мнемоник

| Таблица | Содержимое |
|---|---|
| `MNEMONICS` | ~70 задокументированных команд (общие для 8080/8085) |
| `MNEMONICS_8080` | 4 недокументированные: `NOP*`(0x08), `JMP*`(0xCB), `RET*`(0xD9), `CALL*`(0xDD/0xED/0xFD) |
| `MNEMONICS_8085` | 12 команд: `SIM`(0x20), `RIM`(0x30), `DSUB`(0x08), `ARHL`(0x10), `RDEL`(0x18), `LDHI`(0x28), `LDSI`(0x38), `RSTV`(0xCB), `SHLX`(0xD9), `JNK`(0xDD), `LHLX`(0xED), `JK`(0xFD) |

Метод `_get_mnemonics()` возвращает объединение `MNEMONICS` + специфичную таблицу в зависимости от `cpu_type`.

### Недокументированные опкоды

Опкоды 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xCB, 0xD9, 0xDD, 0xED, 0xFD **не являются реальными инструкциями** — они пересекаются между 8080 и 8085. В round-trip тесте они исключаются из byte-сравнения.

---

## 4. CLI и Python API

### Python API

```python
from assemble8080.assembler import assemble, Assembler, AsmResult

# Быстрый вызов:
result = assemble(source, filename="", now=None, cpu_type="i8080") -> AsmResult

# Полная инициализация:
asm = Assembler(now=None)
asm.cpu_type = "i8080"  # или "i8085"
result = asm.assemble(source, filename="")
```

Параметры `assemble()`:
- `source` — исходный текст
- `filename` — имя файла (для ошибок и поиска `#include`)
- `now` — фиксированная дата для `__date__`/`__time__` (воспроизводимость)
- `cpu_type` — `"i8080"` (по умолчанию) или `"i8085"`; директива CPU в коде может переопределить

### CLI: `python -m assemble8080`

```
python -m assemble8080 [sources...] [options]
```

| Опция | Описание |
|---|---|
| `sources` | Входные файлы `.asm`/`.mac`/`.s` (nargs="*") |
| `-o` / `--output` | Выходной бинарный файл (по умолчанию: `<input>.bin`) |
| `-m` / `--map` | Выходной map-файл (по умолчанию: `<input>.map`) |
| `--obj` | Выходной объектный файл (по умолчанию: `<input>.obj`) |
| `--cpu {8080,8085}` | Тип CPU (по умолчанию: 8080) |
| `--lnk` | Скрипт линковки `.lnk` (режим линковки) |
| `--hex` | Печать hexdump результата |
| `--list` | Печать листинга (адрес, байты, исходник) |
| `--symbols` | Печать таблицы символов |
| `-q` / `--quiet` | Тихий режим (только ошибки) |
| `--version` | Версия |

### Поведение без аргументов

Если нет ни `sources`, ни `--lnk` — запускается **встроенный самопроверочный тест** (`_run_selftest()`): ассемблирует тестовую программу (ORG 0100H, MVI/OUT/DCR/JNZ/CALL/HLT/DB/DW/DS) и печатает результат.

### Коды выхода

- `0` — успех
- `1` — ошибки сборки/линковки

### Кодировка консоли

`__main__.py` и `_cli_main()` перекодируют `sys.stdout`/`sys.stderr` в UTF-8 с `errors="replace"` (защита от UnicodeEncodeError в cp1251-консоли Windows).

---

## 5. Линковщик, объектные файлы, map-файлы

### Линковщик (linker.py, 255 строк)

Формат скрипта `.lnk`:
```
INPUT file1.obj file2.obj [...]
OUTPUT file.bin
MAP file.map
ORIGIN 0x0000
SIZE 0x10000
FILL 0xFF
```

Алгоритм:
1. Проверка конфликтов ORG (два модуля на одном адресе)
2. Сборка глобальной таблицы символов (exports)
3. Проверка неразрешённых imports
4. Выделение буфера (заполнение FILL)
5. Размещение данных объектов по ORG
6. Применение relocations (16-bit little-endian / 8-bit)
7. Генерация map-файла

Публичный API:
- `parse_link_script(text) -> dict`
- `link(objects, origin, size, fill) -> LinkResult`
- `link_from_script(script_path) -> LinkResult`

`LinkResult`: `success`, `binary`, `origin`, `size`, `symbols`, `errors`, `warnings`, `map_text`.

### Объектные файлы (objfile.py, 137 строк)

Формат: JSON, версия `"i8080-obj-v1"`.

Содержимое:
- `name`, `source`, `org`, `size`
- `data` — hex-строка бинарных данных
- `symbols` — `{имя: offset_from_org}`
- `exports` — `[имя]`
- `imports` — `[имя]`
- `relocations` — `[{offset, size, symbol}]`

Функции: `save_obj(path, obj)`, `load_obj(path)`, `obj_from_asm_result(result, source_name)`.

### Map-файлы (mapfile.py, 162 строк)

Формат (текст):
```
; i8080-5 CI map file v1
; source: main.asm
; date: 2026-09-22 08:45:00
; org: 0x0100
; size: 256
; symbols: 12

ADDRESS   SIZE  TYPE    NAME
0000      0003  CODE    boot_start
0100      0002  DATA    my_var
```

Функции: `generate_map(result, source_name, date_str)`, `parse_map(text)`, `load_map_file(path)`, `save_map_file(path, content)`.

Map-файл генерируется автоматически при успешной сборке (записывается в `result.map_text`).

---

## 6. Валидация

### Round-trip тест (tests/test_roundtrip_256.py)

- **Покрытие**: все 256 значений старшего байта дизассемблируются в непустой текст
- **Round-trip**: программа из всех documented-опкодов → дизассемблер → ассемблер → байты совпадают
- Запускается на **3 последовательных цикла** (по умолчанию)
- Проверяется для обоих CPU: i8080 (314 documented байт) и i8085 (332 documented байт)
- Недокументированные NOP*/RET*/CALL*/JMP* исключаются из byte-сравнения
- Запуск: `python tests/test_roundtrip_256.py [N]`

### Сравнение с zasm (tests/test_bin_compare.py)

- **15 референсных файлов**, сгенерированных реальным zasm (`c:\zasm\zasm.exe`)
- Фиксированная дата: `2026-09-19 11:06:55` (для воспроизводимости `__date__`/`__time__`)
- Байт-в-байт сравнение результата ассемблера с референсным `.bin`/`.rom`
- Файлы: 8080TonePlayer, bf, CPU_test, ESC_DeESC, fifo_a16, ImperialMarch, IMSAI8080, kernel, main_boot, Mega-80, mon85-v13, rtty, shell, Smyk_player, SW_IO

---

## 7. No-op директивы и INCBIN

### 47 no-op директив

В обоих проходах (pass 1 и pass 2) следующая группа директив пропускается (`continue`):

```
XDEF, XREF, SECTION, .XDEF, .XREF, .SECTION,
IF, ENDIF, ELSE, LOCAL, ENDLOCAL, ERROR,
.IF, .ENDIF, .ELSE, .LOCAL, .ENDLOCAL, .ERROR,
CPU, ASEG, TITLE, .TITLE,
ENDR, DATA, BLKB, DISKDEF, IRP, ASSERT,
DEFW, .DATA, .BLKB, .DISKDEF, .IRP, .ASSERT,
.DEFW, #DATA, #ASSERT, ASMPC, MACRO, ALIGN, .ALIGN,
BLOCK, .BLOCK, ENDBLOCK, .ENDBLOCK,
INCBIN, .INCBIN
```

Всего: **47** записей (включая dot- и #-варианты).

### INCBIN — не true no-op

Несмотря на наличие в no-op списке, `INCBIN`/`.INCBIN` **фактически обрабатывается** в pass 2:

```python
# INCBIN — include binary file
if mnemonic in ('INCBIN', '.INCBIN'):
    bin_filename = operand.strip().strip('"').strip("'")
    # Resolve path relative to source file directory
    src_dir = os.path.dirname(self._filename) if self._filename else '.'
    bin_path = bin_filename if os.path.isabs(bin_filename) else os.path.join(src_dir, bin_filename)
    with open(bin_path, 'rb') as bf:
        bin_data = bf.read()
    self._write(bytearray(bin_data))
    location += len(bin_data)
    continue
```

В pass 1 INCBIN является no-op (не сдвигает `location`), что может приводить к неточному учёту адресов при forward-ссылках после INCBIN. В pass 2 бинарные данные реально вставляются в поток.

---

## 8. Структура пакета

```
assemble8080/
├── __init__.py        # Экспорт публичного API
├── assembler.py       # 1919 строк — ядро (MNEMONICS, ExpressionParser, Assembler, CLI)
├── preprocessor.py    # 630 строк — препроцессор
├── linker.py          # 255 строк — линковщик
├── mapfile.py         # 162 строки — map-файлы
├── objfile.py         # 137 строк — объектные файлы
├── numbers.py         # Парсер чисел
├── symbols.py         # Таблица символов
├── errors.py          # Типы ошибок
└── __main__.py        # 19 строк — CLI entry point
```

### Публичный API (`__init__.py`)

```python
from assemble8080 import (
    Assembler, assemble, AsmError, AsmResult,
    MNEMONICS, REGISTERS, REG_PAIRS, parse_number,
    Preprocessor, PreprocessorError, NumberParser,
    MapFile, MapEntry, generate_map, parse_map, load_map_file, save_map_file,
    ObjectFile, Relocation, save_obj, load_obj, obj_from_asm_result,
    link, link_from_script, parse_link_script, LinkResult, LinkError,
)
```
