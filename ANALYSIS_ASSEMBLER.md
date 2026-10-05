# Анализ ассемблера: include, структура, линковщик

## 1. Баг: поиск include-файлов

### Корень проблемы

**Цепочка вызовов при сборке из GUI:**

```
assembler_widget.py:641  →  self.assembler.assemble(source)   # filename НЕ передаётся!
assembler.py:574         →  def assemble(self, source, filename="")
assembler.py:578         →  Preprocessor(include_dirs=['.', os.path.dirname(filename) or '.'])
                           # filename="" → dirname("")="" → include_dirs=['.', '.']
preprocessor.py:198      →  cur_dir = os.path.dirname(os.path.abspath(filename)) if filename != '<input>' else None
                           # filename="" → abspath("")=CWD → cur_dir=CWD
preprocessor.py:264-267  →  search_dirs = ['.', '.']
                           # current_dir=CWD уже в списке → НЕ вставляется в начало
```

**Результат:** поиск всегда идёт в CWD (каталог программы), а не в каталог исходного файла.

### Даже при передаче filename (тесты)

```python
# test_asm_for_test.py:
res = assemble(source, filename=path)  # path = "C:\...\ASM_FOR_TEST\kernel.asm"
```

```
assembler.py:578  →  include_dirs=['.', 'C:\...\ASM_FOR_TEST']
preprocessor.py   →  cur_dir='C:\...\ASM_FOR_TEST' (уже в include_dirs!)
_process_include  →  current_dir not in search_dirs → False → НЕ перемещается в начало
```

**Результат:** CWD всё равно ищется ПЕРВЫМ. Если в CWD есть файл с тем же именем — он будет найден вместо нужного.

### Что нужно исправить

| # | Файл | Проблема | Исправление |
|---|---|---|---|
| 1 | `assembler_widget.py` | Не хранит путь загруженного файла | Добавить `self._current_file`, заполнять в `on_load_file`, очищать в `on_new` |
| 2 | `assembler_widget.py:641` | Не передаёт filename в `assemble()` | `self.assembler.assemble(source, self._current_file or "")` |
| 3 | `assembler.py:578` | Порядок `include_dirs`: CWD первым | `include_dirs=[os.path.dirname(filename) or '.', '.']` |
| 4 | `preprocessor.py:264-267` | Если `current_dir` уже в списке — не перемещается в начало | Перемещать в начало всегда |
| 5 | `preprocessor.py` | Нет директивы для дополнительных путей | Добавить `#path "dir"` / `.path "dir"` |
| 6 | `automation.py:607` | `asm_assemble` не передаёт filename | Передавать `self._current_file` |

### Новая логика поиска include

```
Порядок поиска файла "foo.inc":
1. Каталог файла, содержащего #include (относительный путь)
2. Каталоги из #path / .path (в порядке объявления)
3. Каталог главного исходного файла
4. CWD (каталог запуска программы)
```

### Директива `#path`

```asm
#path "C:\Projects\shared"
#path "../lib"
; или dot-форма:
.path "C:\Projects\shared"
```

Добавляет каталог в список поиска (до CWD, после каталога текущего файла).

---

## 2. Структура проекта: нужен ли рефакторинг?

### Текущая структура

```
i8080-5_CI-AI-analysis/
├── assemble8080/          # Ядро ассемблера (самостоятельный пакет)
│   ├── __init__.py
│   ├── assembler.py       #   1506 строк — ядро (MNEMONICS, parse, assemble)
│   ├── preprocessor.py    #   591 строк — препроцессор
│   ├── numbers.py         #   84 строки — парсер чисел
│   ├── symbols.py         #   77 строк — таблица символов
│   └── errors.py          #   37 строк — типы ошибок
├── i8080_ci/              # GUI + API
│   ├── assembler_widget.py  # 743 строки — вкладка Ассемблер
│   ├── automation.py        # 640 строк — скриптовый API (asm_*)
│   ├── main_window.py       # 3952 строки — главное окно
│   ├── models/              #   Qt-модели
│   └── views/               #   Qt-виджеты
├── modules/               # Аппаратные модули
├── common/                # Общие утилиты (i18n, themes)
├── ui/                    # Дополнительные UI-виджеты
├── tests/                 # Тесты
├── i8080_emulator.py      # Эмулятор (1761 строк, standalone)
├── mcp_server.py          # MCP-сервер (953 строки, standalone)
└── i8080_CI.py            # Точка входа
```

### Оценка

**Структура адекватна.** Паттерн тот же, что и для других компонентов:
- `i8080_emulator.py` (ядро) + `i8080_ci/` (GUI) — аналогично
- `assemble8080/` (ядро) + `i8080_ci/assembler_widget.py` (GUI) — аналогично
- `modules/` (ядро) + `ui/` (GUI) — аналогично

**Единственный вопрос:** `assembler.py` — 1506 строк в одном файле. Можно разбить:
- `mnemonics.py` — таблица инструкций (MNEMONICS dict, ~400 строк)
- `parser.py` — парсер строк (parse_line, parse_operand)
- `assembler.py` — оркестрация (assemble, two-pass)

Но это **косметический** рефакторинг, не критичный. Оставлю как есть.

**Вывод:** рефакторинг структуры НЕ нужен. Нужна только правка include-логики.

---

## 3. Линковщик: нужен ли и как реализовать?

### Зачем

| Сценарий | Пример из ASM_FOR_TEST |
|---|---|
| Крупная программа из модулей | `kernel.asm` + `kernel_syscall.asm` + `kernel_tty.asm` |
| Переиспользуемые библиотеки | `delay.asm`, `div16.asm`, `mul16.asm` |
| Управление раскладкой памяти | ROM @ 0x0000, RAM @ 0x8000, vectors @ 0x0008 |
| Разделение ответственности | Один файл — драйвер, другой — логика |

### Что нужно для линковщика 8080

8080 имеет **плоское 64 КБ адресное пространство** — нет сегментов, нет PIC. Это упрощает линковку:

```
Объектный файл (JSON):
{
  "name": "kernel_syscall",
  "org": 0x0100,
  "binary": "000102...",          // hex
  "symbols": {                     // определённые символы
    "syscall_handler": 0x0100,
    "syscall_table": 0x0150
  },
  "undefined": ["main", "print"],  // внешние ссылки
  "relocations": [                 // где нужно подставить адрес
    {"offset": 0x0003, "type": "abs16", "symbol": "main"},
    {"offset": 0x0010, "type": "abs16", "symbol": "print"}
  ]
}
```

### Алгоритм линковки

```
1. Загрузить все .obj файлы
2. Проверить конфликты ORG (два модуля на одном адресе)
3. Объединить таблицы символов
4. Разрешить undefined → defined (между модулями)
5. Применить relocation: записать адрес символа в binary
6. Сложить все binary по адресам ORG
7. Вывести итоговый .bin + карту памяти
```

### Оценка сложности

| Компонент | Строки | Сложность |
|---|---|---|
| Формат .obj (JSON) + read/write | ~100 | Низкая |
| Symbol resolution | ~100 | Низкая |
| Relocation engine | ~150 | Средняя |
| Memory layout / ORG conflicts | ~100 | Низкая |
| CLI / API (link function) | ~100 | Низкая |
| GUI (кнопка "Link", список модулей) | ~200 | Средняя |
| Тесты | ~200 | Средняя |
| **Итого** | **~950** | **Средняя** |

### Интеграция в проект

```
assemble8080/
├── assembler.py       # Ассемблер (существует)
├── linker.py          # Линковщик (новый, ~400 строк)
├── objfile.py         # Формат объектного файла (новый, ~100 строк)
└── ...

i8080_ci/
├── assembler_widget.py  # Добавить: "Assemble → .obj" + "Link .obj → .bin"
└── automation.py        # Добавить: asm_assemble_obj(), asm_link()
```

### Рекомендация

**Линковщик нужен**, но как **фаза 2**. Сначала:
1. ✅ Исправить include (баг)
2. ✅ Добавить `#path` (удобство)
3. ✅ Добавить экспорт в .obj (ассемблер уже почти готов — нужна только сериализация)
4. 🔜 Линковщик (отдельная задача, ~950 строк)

---

## 4. План работ

### Фаза 1: Исправление include (сейчас)

- [ ] `assembler_widget.py`: добавить `self._current_file`, передавать в `assemble()`
- [ ] `assembler.py`: исправить порядок `include_dirs`
- [ ] `preprocessor.py`: исправить `_process_include` (перемещать current_dir в начало)
- [ ] `preprocessor.py`: добавить директиву `#path` / `.path`
- [ ] `automation.py`: передавать filename в `asm_assemble`
- [ ] Тесты: include из каталога файла, #path, вложенные include

### Фаза 2: Линковщик (позже)

- [ ] `assemble8080/objfile.py`: формат .obj (JSON)
- [ ] `assemble8080/linker.py`: линковщик
- [ ] `assembler.py`: режим "assemble to .obj" (с relocations)
- [ ] GUI: кнопки "Assemble → OBJ" / "Link → BIN"
- [ ] Тесты
