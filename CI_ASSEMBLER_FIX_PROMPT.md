# Промпт: Корректировка i8080_ci assembler + linker для нативной поддержки ASxxxx

## Задача

Сделать ci assembler (R2AKT/8080-5-CI-App) нативно понимающим формат ASxxxx,
который генерирует компилятор SmallC 8080. После исправлений SmallC должен
собираться напрямую: `cc8080.exe -s test.c → test.s → ci assembler → .obj → ci linker → .bin`.
Никаких конвертеров, прослоек, преобразователей.

## Файлы для модификации

| Файл | Роль |
|------|------|
| `ci-app/assemble8080/assembler.py` | Двухпроходный ассемблер 8080/8085 (~1966 строк) |
| `ci-app/assemble8080/linker.py` | Линкер: .obj → .bin (255 строк) |
| `ci-app/assemble8080/objfile.py` | Формат .obj (JSON) — НЕ менять |
| `ci-app/assemble8080/__init__.py` | Экспорты — НЕ менять |
| `ci-app/assemble8080/__main__.py` | CLI entry — НЕ менять |

## Контекст: что генерирует SmallC

SmallC 8080 — компилятор C89/C99-subset для Intel 8080/8085. Генерирует
assembly в формате ASxxxx (стандартный формат для 8080). Пример вывода:

```asm
; Small C 8080;
;	Coder (2.4,84/11/27)
;	Front End (2.7,84/11/28)
		;program area SMALLC_GENERATED is RELOCATABLE
		.area	SMALLC_GENERATED	(REL,CON)
		.module SMALLC_GENERATED
		.list   (err, loc, bin, eqt, cyc, lin, src, lst, md)
		.nlist  (pag)
		.area  SMALLC_GENERATED  (REL,CON,CSEG)
main:
	dcx 	sp
	lxi 	h,#62915
	lxi 	d,#16456
	lxi 	b,#0
	dad 	sp
	call	ccplong
	push	b
	push	b
	lxi 	h,#4
	dad 	sp
	lxi 	b,#0
	dad 	sp
	call	ccplong
	dcx 	sp
	lxi 	h,#1
	dad 	sp
	call	ccgint
	call	ccgfloat
	lxi 	b,#0
	dad 	sp
	call	ccplong
	lxi 	h,#0
	dad 	sp
	call	ccgfloat
	push	h
	push	d
	lxi 	h,#9
	dad 	sp
	call	ccgfloat
	call	ccfne
	mov 	a,h
	ora 	l
	jz  	$1
	lxi 	h,#1
	jmp 	$0
	pop 	b
	pop 	b
$1:
	lxi 	h,#1
	dad 	sp
	call	ccgint
	push	h
	push	d
	lxi 	h,#28836
	lxi 	d,#16429
	pop 	d
	mov 	a,l
	stax	d
	lxi 	h,#7
	dad 	sp
	call	ccgfloat
	push	h
	push	d
	lxi 	h,#28836
	lxi 	d,#16429
	call	ccfne
	mov 	a,h
	ora 	l
	jz  	$2
	lxi 	h,#2
	jmp 	$0
	pop 	b
	pop 	b
$2:
	lxi 	h,#0
	jmp 	$0
$0:
	xchg
	lxi 	h,#8
	dad 	sp
	sphl
	xchg
	ret
		.area  SMALLC_GENERATED_DATA  (REL,CON,DSEG)
	.globl	main

;0 error(s) in compilation
;	literal pool:0
;	global pool:1
;	Macro pool:60
	;	.end
```

Runtime-библиотека `crun8080lib.asm` (3199 строк) также в формате ASxxxx и
использует все 8080/8085 мнемоники включая `mul`, `div`, `or`, `orai`,
`cmp` с immediate, `mov` с immediate.

## Полный список ASxxxx-фич, которые использует SmallC

### 1. Директивы (в начале/конце файла)

| Директива | Пример | Действие |
|-----------|--------|----------|
| `.area NAME (FLAGS)` | `.area SMALLC_GENERATED (REL,CON)` | Объявление секции. Игнорировать. |
| `.module NAME` | `.module SMALLC_GENERATED` | Имя модуля. Игнорировать. |
| `.list (flags)` | `.list (err, loc, bin, ...)` | Флаги листинга. Игнорировать. |
| `.nlist (flags)` | `.nlist (pag)` | Флаги нелистинга. Игнорировать. |
| `.globl name1, name2` | `.globl main` | Экспорт символов. |
| `.end` | `.end` | Конец модуля. Остановить сборку. |

### 2. Числа

| Формат | Пример | Значение |
|--------|--------|----------|
| `#N` | `#62915` | **Decimal** 62915 = 0xF5FB |
| `0xNN` | `0xFF` | Hex |
| `NNNH` | `FFH` | Hex (суффикс H) |
| `N` | `255` | Decimal |
| `NB` | `101B` | Binary |
| `NQ` | `177Q` | Octal |

### 3. Локальные метки

| Формат | Пример |
|--------|--------|
| `$N:` | `$1:` (определение) |
| `$N` | `jz $1` (ссылка) |

Метки `$N` — обычные метки, видимые в пределах файла. Не требуют
специального scope-механизма.

### 4. Мнемоники (ASxxxx короткие формы)

| ASxxxx | Эквивалент | Операнды |
|--------|-----------|----------|
| `or` | ORA | register |
| `and` | ANA | register |
| `xor` | XRA | register |
| `orai` | ORI | immediate |
| `andi` | ANI | immediate |
| `xori` | XRI | immediate |
| `cmp` + imm | CPI | immediate |
| `mov` + imm | MVI | register, immediate |
| `mov` + reg | MOV | register, register |

### 5. Data-директивы

| ASxxxx | Эквивалент |
|--------|-----------|
| `.db N` | DB N |
| `.ds N` | DS N |
| `.dw N` | DW N |

### 6. 8085-инструкции (в runtime)

`mul r`, `div r` — стандартные 8085. Ассемблер должен поддерживать их
при `--cpu 8085` (уже есть в MNEMONICS_8085).

---

## Список исправлений для assembler.py

### Исправление 1: `parse_number()` — поддержка `#N` decimal

**Где:** функция `parse_number()` (строка ~282)

**Проблема:** ASxxxx использует `#N` для decimal. Ci assembler не понимает
префикс `#` и возвращает None.

**Решение:** В начале `parse_number()`, после `text = text.strip()`, добавить:

```python
    # ASxxxx: #N = decimal
    if text.startswith('#'):
        text = text[1:]
        try:
            return int(text, 10)
        except ValueError:
            return None
```

**Важно:** `#62915` = decimal 62915, НЕ hex. Это критично для корректности.

---

### Исправление 2: `_parse_label()` — поддержка `$N` local labels

**Где:** метод `Assembler._parse_label()` (строка ~602)

**Проблема:** Regex требует `[A-Za-z_]` в начале имени метки. `$1:` не
распознаётся.

**Решение:** В `_parse_label()`, ПЕРЕД основным regex для обычных меток,
добавить:

```python
        # ASxxxx: $N local label (with colon)
        m = re.match(r'^\$(\d+)\s*:\s*(.*)', line)
        if m:
            return f'${m.group(1)}', False, m.group(2)
        # ASxxxx: $N local label (without colon, followed by instruction)
        m = re.match(r'^\$(\d+)\s+(.*)', line)
        if m:
            return f'${m.group(1)}', False, m.group(2)
```

**Важно:** Метка `$1` хранится в `self.symbols` как строка `'$1'` (с `$`).
Ссылки `jz $1` должны резолвиться через `self.symbols['$1']`.

---

### Исправление 3: ASxxxx directives в Pass 1

**Где:** метод `Assembler.assemble()`, Pass 1 (строка ~720)

**Проблема:** Ассемблер не знает директивы `.area`, `.module`, `.list`,
`.nlist`, `.globl`, `.end` и выдаёт "Неизвестная мнемоника".

**Решение:** В Pass 1, после извлечения mnemonic и до обработки ORG, добавить:

```python
            # ASxxxx directives: .area, .module, .list, .nlist — no-op
            if mnemonic in ('AREA', 'MODULE', 'LIST', 'NLIST'):
                continue
            # ASxxxx: .globl name1, name2, name3 — export symbols
            if mnemonic == 'GLOBL':
                if operand:
                    for name in self._split_operands(operand):
                        name = name.strip().upper()
                        if name:
                            self._global_labels.add(name)
                            self._exports.add(name)
                continue
            # ASxxxx: .end — stop assembly
            if mnemonic in ('END', '.END'):
                break
```

**Примечание:** `.area` может иметь параметры `(REL,CON)`, `(REL,CON,CSEG)`,
`(REL,CON,DSEG)`. Просто игнорировать всю строку.

---

### Исправление 4: ASxxxx directives в Pass 2

**Где:** метод `Assembler.assemble()`, Pass 2 (строка ~1050)

**Проблема:** То же, что и в Pass 1, но в Pass 2.

**Решение:** В Pass 2, после обработки ORG и до обработки инструкций, добавить:

```python
            # ASxxxx directives: .area, .module, .list, .nlist — no-op
            if mnemonic in ('AREA', 'MODULE', 'LIST', 'NLIST'):
                continue
            # ASxxxx: .globl — no-op in pass 2 (already collected in pass 1)
            if mnemonic == 'GLOBL':
                continue
            # ASxxxx: .end — stop
            if mnemonic in ('END', '.END'):
                break
```

---

### Исправление 5: Мнемоник-алиасы ASxxxx

**Где:** словарь `MNEMONICS` (строка ~107)

**Проблема:** ASxxxx использует `or`, `and`, `xor` (register forms) и
`orai`, `andi`, `xori` (immediate forms). Ci assembler знает только
`ORA`, `ANA`, `XRA`, `ORI`, `ANI`, `XRI`.

**Решение:** В словарь `MNEMONICS` добавить:

```python
    # ASxxxx aliases
    'OR':    (0xB0, 'r', 1),    # = ORA (OR register)
    'AND':   (0xA0, 'r', 1),    # = ANA (AND register)
    'XOR':   (0xA8, 'r', 1),    # = XRA (XOR register)
    'ORAI':  (0xF6, 'd8', 2),   # = ORI (OR immediate)
    'ANDI':  (0xE6, 'd8', 2),   # = ANI (AND immediate)
    'XORI':  (0xEE, 'd8', 2),   # = XRI (XOR immediate)
```

**Важно:** `OR` (0xB0, 'r', 1) — это ORA с регистром. `ORAI` (0xF6, 'd8', 2)
— это ORI с immediate. Не путать.

---

### Исправление 6: `cmp` с immediate → CPI

**Где:** метод `Assembler._encode_instruction()`, обработка `fmt == 'r'`
(строка ~1325)

**Проблема:** `cmp a,#5` — ASxxxx форма сравнения с immediate. Ci assembler
ожидает `cmp a` (register) или `cpi 5` (immediate).

**Решение:** В обработчике `fmt == 'r'`, если mnemonic в списке ALU-операций
и есть 2 операнда, а второй — НЕ регистр, кодировать как immediate:

```python
        if fmt == 'r':
            if len(operands) >= 2:
                # ASxxxx 2-operand form: cmp a, #5 → CPI 5
                op2_upper = operands[1].strip().upper()
                if op2_upper not in REGISTERS and op2_upper not in ('BC', 'DE', 'HL', 'PSW'):
                    ALU_IMM2 = {'CMP': 0xFE, 'ADD': 0xC6, 'ADC': 0xCE, 'SUB': 0xD6,
                                'SBB': 0xDE, 'ANA': 0xE6, 'XRA': 0xEE, 'ORA': 0xF6,
                                'OR': 0xF6, 'AND': 0xE6, 'XOR': 0xEE}
                    if mnemonic in ALU_IMM2:
                        val = self._parse_operand(operands[1], line_num, allow_current=True)
                        if val is not None:
                            return bytearray([ALU_IMM2[mnemonic], val & 0xFF])
            # ... existing single-operand handling ...
```

Также в обработчике `fmt == 'r'`, если операнд НЕ регистр (1-операндная форма),
кодировать как immediate:

```python
            # Not a register — try as immediate value (ALU d8 forms)
            ALU_IMM_OPCODES = {'ADD': 0xC6, 'ADC': 0xCE, 'SUB': 0xD6, 'SBB': 0xDE,
                               'ANA': 0xE6, 'XRA': 0xEE, 'ORA': 0xF6, 'CPI': 0xFE,
                               'CMP': 0xFE, 'OR': 0xF6, 'AND': 0xE6, 'XOR': 0xEE}
            if mnemonic in ALU_IMM_OPCODES:
                val = self._parse_operand(operands[0], line_num, allow_current=True)
                if val is not None:
                    return bytearray([ALU_IMM_OPCODES[mnemonic], val & 0xFF])
```

---

### Исправление 7: `mov` с immediate → MVI

**Где:** метод `Assembler._encode_instruction()`, обработка `fmt == 'r,r'`
(строка ~1364)

**Проблема:** `mov a,#5` — ASxxxx форма. Ci assembler ожидает `mov a,h`
(register→register) или `mvi a,5`.

**Решение:** В обработчике `fmt == 'r,r'`, если mnemonic == 'MOV' и второй
операнд НЕ регистр, кодировать как MVI:

```python
        if fmt == 'r,r':
            if len(operands) < 2:
                self._error(line_num, f"{mnemonic}: не хватает операндов")
                return bytearray([opcode])
            # ASxxxx: mov a, #5 → MVI A, 5
            src_upper = operands[1].strip().upper()
            if mnemonic == 'MOV' and src_upper not in REGISTERS and src_upper not in ('BC', 'DE', 'HL', 'PSW'):
                dst_code = self._get_reg_code(operands[0], line_num)
                val = self._parse_operand(operands[1], line_num, allow_current=True)
                if val is not None:
                    return bytearray([0x06 | (dst_code << 3), val & 0xFF])
            # ... existing register→register handling ...
```

---

### Исправление 8: d16 format — auto-import + relocation tracking

**Где:** метод `Assembler._encode_instruction()`, обработка `fmt == 'd16'`
(строка ~1411)

**Проблема:** `call ccplong` — символ `ccplong` не определён в текущем файле.
Ci assembler не отслеживает такие символы как импорты и не создаёт
relocation entries. Результат: 0 relocations в .obj, линкер не может
разрешить адреса.

**Решение:** В обработчике `fmt == 'd16'`, после получения `val`, добавить
auto-import логику:

```python
        if fmt == 'd16':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: не хватает операнда")
                return bytearray([opcode, 0x00, 0x00])
            val = self._parse_operand(operands[0], line_num, allow_current=True)
            if val is None:
                self._error(line_num, f"Неизвестный операнд: {operands[0]}")
                val = 0
            # Track relocation for undefined symbols
            sym = self._is_import_symbol(operands[0])
            if sym is None:
                # Check if operand is an undefined symbol (auto-import)
                op_str = operands[0].strip()
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', op_str):
                    upper = op_str.upper()
                    if upper not in self.symbols:
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + 1, 2, upper)
            else:
                self._track_relocation(self._write_pos + 1, 2, sym)
            return bytearray([opcode, val & 0xFF, (val >> 8) & 0xFF])
```

**Важно:** `self._write_pos + 1` — потому что opcode занимает 1 байт,
а 16-bit адрес начинается со следующего байта. `size=2` — 16-bit little-endian.

**Аналогично** для `fmt == 'rp,d16'` (SHLD, LHLD, STA, LDA) — второй операнд
может быть символом.

---

### Исправление 9: Import paths (если есть)

**Где:** все `import` statements в `assembler.py`

**Проблема:** Если в файле есть `from assemble8080.mapfile import ...`
(абсолютный импорт), а файл вызывается как `python -m assemble8080`,
будет `ModuleNotFoundError`.

**Решение:** Все внутренние импорты должны быть относительными:

```python
from .mapfile import ...
from .objfile import ...
from .preprocessor import ...
```

НЕ `from assemble8080.mapfile import ...`.

---

## Список исправлений для linker.py

### Исправление 10: ORG conflict — не ошибка, а warning

**Где:** функция `link()`, Step 1 (строка ~99)

**Проблема:** Если два .obj файла имеют одинаковый ORG (например, оба 0x0000),
линкер выдаёт ошибку и останавливается. Но в ASxxxx `.area (REL,CON)`
означает relocatable section — ORG не задан, и оба файла имеют ORG=0.
Это НОРМАЛЬНО.

**Решение:** Заменить ошибку на warning + автоматическое смещение:

```python
    # Step 1: Check for ORG conflicts
    # If multiple objects have the same ORG, auto-assign sequential addresses
    placed = {}  # {org: [obj_names]}
    for obj in objects:
        if obj.org in placed:
            placed[obj.org].append(obj.name)
        else:
            placed[obj.org] = [obj.name]

    # Auto-assign: first object keeps ORG, subsequent get ORG + size
    # (caller should set proper ORG values before calling link())
    # If all objects have ORG=0, assign sequential addresses
    if len(placed.get(0, [])) > 1:
        warnings.append(
            f"Multiple objects at ORG 0x0000: {', '.join(placed[0])}. "
            f"Auto-assigning sequential addresses."
        )
        current_addr = 0
        for obj in objects:
            if obj.org == 0:
                obj.org = current_addr
                current_addr += obj.size
```

**Альтернатива (проще):** Оставить как есть (ошибка), но в вызывающем коде
(link_direct.py или CLI) явно задавать ORG для каждого .obj перед вызовом
`link()`. Это текущий подход — он работает.

**Рекомендация:** Оставить текущее поведение (ошибка при конфликте ORG),
но добавить в CLI (`_cli_main`) возможность задать ORG через параметр:

```
python -m assemble8080 --cpu 8085 --obj out.obj --org 0x0100 input.s
```

И в `link_from_script` — если ORG не задан в .lnk, использовать ORG из .obj.

---

### Исправление 11: Relocation resolution — использовать all_symbols

**Где:** функция `link()`, Step 6 (строка ~156)

**Проблема:** Текущий код ищет символ сначала в `global_symbols`, потом в
`all_symbols`. Это правильно. Но нужно убедиться, что `all_symbols`
содержит ВСЕ символы из ВСЕХ .obj (включая локальные).

**Текущий код (уже правильный):**
```python
    # Step 6: Apply relocations
    for obj in objects:
        for reloc in obj.relocations:
            sym_addr = global_symbols.get(reloc.symbol) or all_symbols.get(reloc.symbol)
            if sym_addr is None:
                warnings.append(f"Relocation: symbol '{reloc.symbol}' not found (in {obj.name})")
                continue
            patch_addr = obj.org + reloc.offset
            if patch_addr >= output_size:
                continue
            if reloc.size == 2:
                output[patch_addr] = sym_addr & 0xFF
                output[patch_addr + 1] = (sym_addr >> 8) & 0xFF
            elif reloc.size == 1:
                output[patch_addr] = sym_addr & 0xFF
```

**Проверка:** Убедиться, что `all_symbols` строится ДО Step 6 и содержит
символы из всех .obj. Текущий код (Step 2) делает это правильно.

**Вывод:** Линкер в текущем виде работает корректно, ЕСЛИ .obj файлы
содержат правильные relocations (после исправления 8 в assembler).

---

## Что НЕ менять

1. **SmallC компилятор** (`code8080.c`, `gen.c`, `expr.c`, etc.) — генерирует
   корректный ASxxxx. Не трогать.
2. **Runtime** (`crun8080lib.asm`) — корректный ASxxxx. Не трогать.
   (Исключение: bug в `ccf_docmp` — это отдельная задача, не связана с
   ассемблером.)
3. **Формат .obj** (`objfile.py`) — JSON format v1. Не менять.
4. **CLI interface** (`__main__.py`, `_cli_main`) — не менять (кроме
   возможного добавления `--org` параметра).
5. **MUL/DIV** — это 8085-инструкции. Они уже в `MNEMONICS_8085`.
   Ассемблер с `--cpu 8085` их поддерживает. Это НЕ баг.
6. **Preprocessor** (`preprocessor.py`) — не менять.
7. **Map file** (`mapfile.py`) — не менять.

## После исправлений: удалить

- `convert_asm.py` — конвертер ASXXXX→ci формат. Больше не нужен.
- `link_simple.py` — workaround-линкер. Больше не нужен.

## Верификация

### Тест 1: Сборка t42.s

```bash
cd c:\smallc
python -m ci-app.assemble8080 --cpu 8085 --obj test/t42_direct.obj test/t42.s
```

**Ожидаемый результат:**
- `[OK] test/t42.s: 140 bytes, origin=0x0000, symbols=4`
- `test/t42_direct.obj` создан
- В .obj: 11 relocations, 4 imports (CCPLONG, CCGINT, CCGFLOAT, CCFNE)
- Символы: MAIN=0, $0=130, $1=52, $2=118

### Тест 2: Сборка crun8080lib.asm

```bash
python -m ci-app.assemble8080 --cpu 8085 --obj test/crun8080lib_direct.obj crun8080lib.asm
```

**Ожидаемый результат:**
- `[OK] crun8080lib.asm: ~4017 bytes, origin=0x0000, symbols=~202`
- Все 8085-инструкции (mul, div) собраны
- Все `.globl` символы в exports

### Тест 3: Линковка

```python
import json, sys
sys.path.insert(0, 'ci-app')
from assemble8080.linker import link
from assemble8080.objfile import load_obj

obj1 = load_obj('test/t42_direct.obj')
obj2 = load_obj('test/crun8080lib_direct.obj')

# Set ORG: user code at 0x0100, runtime at 0x1000
obj1.org = 0x0100
obj2.org = 0x1000

result = link([obj1, obj2], origin=0x0000, size=0x10000, fill=0xFF)
assert result.success, f"Link failed: {result.errors}"
assert len(result.binary) == 0x10000

# Verify relocations resolved
# CCPLONG should be at 0x1000 + offset_in_runtime
# CCGFLOAT should be at 0x1000 + offset_in_runtime
# CCFNE should be at 0x1000 + offset_in_runtime
print(f"CCPLONG = 0x{result.symbols['CCPLONG']:04X}")
print(f"CCGFLOAT = 0x{result.symbols['CCGFLOAT']:04X}")
print(f"CCFNE = 0x{result.symbols['CCFNE']:04X}")

with open('test/t42_linked.bin', 'wb') as f:
    f.write(result.binary)
print("OK: test/t42_linked.bin written")
```

**Ожидаемый результат:**
- `CCPLONG = 0x11BE` (или близкое, зависит от runtime layout)
- `CCGFLOAT = 0x11CA`
- `CCFNE = 0x18D0`
- Бинарный файл 64KB, fill=0xFF

### Тест 4: Эмуляция (опционально)

```bash
python run8080.py test/t42_linked.bin
```

**Ожидаемый результат:** Программа выполняется и завершается HLT.
(Примечание: t42 может зависать из-за bug в `ccf_docmp` в runtime —
это отдельная задача, не связанная с ассемблером.)

## Критерии приёмки

1. `t42.s` собирается БЕЗ ошибок и БЕЗ конвертера
2. `crun8080lib.asm` собирается БЕЗ ошибок
3. .obj файлы содержат правильные relocations и imports
4. Линкер разрешает все relocations
5. Итоговый .bin содержит корректные адреса в call/jmp инструкциях
6. `convert_asm.py` и `link_simple.py` удалены
7. SmallC компилятор НЕ изменён
8. Runtime НЕ изменён

## Технические детали для реализации

### Структура AsmResult (не менять)

```python
@dataclass
class AsmResult:
    success: bool
    binary: bytes
    origin: int
    symbols: dict          # {name: absolute_address}
    errors: list
    warnings: list
    listing: list          # [(addr, bytes, source_line)]
    map_text: str
    # Internal (for objfile):
    exports: set           # {name}
    imports: set           # {name}
    relocations: list      # [(offset, size, symbol_name)]
```

### Формат .obj (не менять)

```json
{
  "format": "i8080-obj-v1",
  "name": "t42",
  "source": "test/t42.s",
  "org": 0,
  "size": 140,
  "data": "hex string",
  "symbols": {"MAIN": 0, "$0": 130, "$1": 52, "$2": 118},
  "exports": ["MAIN"],
  "imports": ["CCPLONG", "CCGINT", "CCGFLOAT", "CCFNE"],
  "relocations": [
    {"offset": 10, "size": 2, "symbol": "CCPLONG"},
    {"offset": 22, "size": 2, "symbol": "CCPLONG"},
    ...
  ]
}
```

### MNEMONICS format

```python
MNEMONICS = {
    'NAME': (opcode, format, size),
    # format: '', 'r', 'r,r', 'd8', 'd16', 'rp', 'rpsw', 'rp,d16', 'r,d8'
    # size: instruction size in bytes
}
```

### REGISTERS (не менять)

```python
REGISTERS = {'B': 0, 'C': 1, 'D': 2, 'E': 3, 'H': 4, 'L': 5, 'M': 6, 'A': 7}
REG_PAIRS = {'BC': 0, 'DE': 1, 'HL': 2, 'SP': 3}
```
