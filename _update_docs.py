# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. version.py
v = open('version.py', encoding='utf-8').read()
v = v.replace('__version__ = "2.1.13"', '__version__ = "2.1.14"')
v = v.replace('__build__ = "20261012"', '__build__ = "20261013"')
open('version.py', 'w', encoding='utf-8', newline='').write(v)
print("version.py -> 2.1.14 / 20261013")

# 2. README.md badge
r = open('README.md', encoding='utf-8').read()
r = r.replace('Version-2.1.7-orange', 'Version-2.1.14-orange')
open('README.md', 'w', encoding='utf-8', newline='').write(r)
print("README.md badge -> 2.1.14")

# 3. CHANGES.md - insert new entry before v2.1.13
c = open('CHANGES.md', encoding='utf-8').read()
entry = """## v2.1.14 (2026-10-13)

### Поддержка label+addend, безопасная замена $, эталон опкодов, чистка тестов

**Новый функционал (PROMPT_i8080_ci_addend_fix.md):**
- **label+addend в d16/rp,d16/DW:** `LXI H, $1000+#6`, `DW TBL+2` — перенос с
  аддитивной константой. `_parse_label_addend` + `_track_relocation(offset,size,sym,addend)`
  (4-элементный кортеж). `Relocation.addend` в `.obj` (JSON, по умолчанию 0),
  линкер патчит `sym_addr + addend`.
- **Безопасная замена `$`:** regex `$(?!\\d)` — подставляется только одиночный `$`
  (текущий PC), локальные метки `$1`/`$2` не трогаются.

**Эталон опкодов (анти-галлюцинация):**
- Создан `OPCODE_REFERENCE.md` (452 строки) — единый источник правды по опкодам/
  мнемоникам 8080/8085 (246 команд, источник demin.ws) с обязательным промптом
  для ИИ-агента. Подтверждено: RAL=0x17, RAR=0x1F, XTHL=0xE3, XCHG=0xEB,
  INR M=0x34, DCR M=0x35, SIM=0x30, RIM=0x20. INR/DCR SP не существует.

**Чистка тестов (устаревшие ожидания, не баги ядра):**
- `test_assembler_linker.py`: метки в UPPER (сохранение исходного регистра v2.1.12)
  + 4-элементные кортежи relocations (addend). 57/0.
- `test_alus_imm_verify.py`: `CMP imm` принимается как алиас `CPI` (0xFE) —
  намеренное поведение ассемблера. 7/0.
- `test_asm8080-8085.py`: заголовок теста SIM (0x30).

**Верификация ядра (глубокий анализ):**
- INR/DCR: все опкоды B..M,A совпадают с эталоном; `INR SP`/`DCR SP` корректно
  отклоняются (нет такой команды).
- ALU two-operand (ASxxxx `op reg, #imm`): `cmp a,#5`->CPI и др. — корректно.
- PUSH/POP: B/D/H/PSW -> C5/D5/E5/F5 (POP C1/D1/E1/F1) — корректно.

**Тесты:** 921/0 (run_tests, 34 файла) + 203/0 (cycle1) + 57/0 (linker) +
7/0 (alus) + 6/0 (asm8080-8085) + 44/0 (8085) + 17/0 (api snippets).
"""
anchor = "## v2.1.13 (2026-10-12)"
if anchor in c:
    c = c.replace(anchor, entry + anchor, 1)
    open('CHANGES.md', 'w', encoding='utf-8', newline='').write(c)
    print("CHANGES.md -> v2.1.14 entry added")
else:
    print("CHANGES.md anchor NOT FOUND")
print("DONE")
