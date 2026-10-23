# Deep Audit: assemble8080/ Core (2026-10-23)

## 1. assembler.py — Opcode Verification vs OPCODE_REFERENCE.md

**ALL 8080/8085 opcodes are CORRECT.** Every single opcode, size, and encoding formula matches the reference exactly.

### Verified encoding formulas (all correct):
| Instruction | Formula | Verified |
|---|---|---|
| MOV | `0x40 + dst*8 + src` | ✓ |
| MVI | `0x06 + reg*8` | ✓ |
| INR | `0x04 + reg*8` | ✓ |
| DCR | `0x05 + reg*8` | ✓ |
| INX/DCX | `0x03/0x0B + rp*16` | ✓ |
| DAD | `0x09 + rp*16` | ✓ |
| LXI | `0x01 + rp*16` | ✓ |
| PUSH/POP | `0xC5/0xC1 + rp*16` | ✓ |
| ALU r | `base + reg` (ADD=0x80, ADC=0x88, SUB=0x90, SBB=0x98, ANA=0xA0, XRA=0xA8, ORA=0xB0, CMP=0xB8) | ✓ |
| ALI d8 | ADI=0xC6, ACI=0xCE, SUI=0xD6, SBI=0xDE, ANI=0xE6, XRI=0xEE, ORI=0xF6, CPI=0xFE | ✓ |
| RST n | `0xC7 + n*8` | ✓ |
| Jcc/Ccc | 0xC2/CA/D2/DA/E2/EA/F2/FA, 0xC4/CC/D4/DC/E4/EC/F4/FC | ✓ |
| Rcc | 0xC0/C8/D0/D8/E0/E8/F0/F8 | ✓ |
| 8085: SIM=0x30, RIM=0x20, DSUB=0x08, ARHL=0x10, RDEL=0x18, LDHI=0x28, LDSI=0x38, RSTV=0xCB, SHLX=0xD9, JNK=0xDD, LHLX=0xED, JK=0xFD | ✓ |
| 8080 NOPs: 0x08, 0xCB(JMP*), 0xD9(RET*), 0xDD(CALL*) | ✓ |
| STAX H/L → MOV M,A (0x77), LDAX H/L → MOV A,M (0x7E) | ✓ |
| MOV r,#imm → MVI (ASxxxx compat) | ✓ |
| ALU r,#imm → ALI (ASxxxx compat) | ✓ |

### No missing instructions.
All 246 8080 instructions are covered through the encoding tables.

### BUG FOUND: `_parse_label` missing 'CODE' in exclude list (line 650)

The zasm `CODE SECTION ADDR SIZE` directive is handled at lines 803/1110 via:
```python
if mnemonic == 'CODE' or stripped.startswith('#code'):
```
But `'CODE'` is NOT in the `_parse_label` exclude tuple (line 650). A bare line:
```
CODE 100H, *
```
(no label prefix) would be consumed as a **label** named "CODE" (stored in symbol table), and the remainder `100H, *` would be misparsed as an instruction → "Unknown instruction: 100H" error.

**Fix:** Add `'CODE'` to the exclude tuple in `_parse_label`.

### MINOR BUG: Pass 1 size mismatch for INR/DCR with comma operand

In pass 1 (line ~942), the `fmt == 'r'` size check:
```python
if ',' in op_u:
    size = 2  # ASxxxx 2-operand form
```
This applies to ALL `fmt='r'` instructions including INR/DCR. If someone writes `INR A, 5` (invalid 8080), pass 1 advances by 2 bytes, but pass 2's `_encode_instruction` for INR/DCR always returns 1 byte. Location drift.

**Impact:** Low — only triggers on syntactically invalid input. No valid 8080 program is affected.

**Fix:** Restrict the comma-check to ALU ops only (exclude INR/DCR from the `size = 2` branch).

---

## 2. preprocessor.py — Syntax & Edge Cases

**Overall: Correct and robust.** Handles:
- `#include` / `.include` / `include` (3 forms) ✓
- `#define` with recursive expansion (10-pass limit) ✓
- `#if` / `#elif` / `#else` / `#endif` with proper stack tracking ✓
- Bare `IF` / `ELSE` / `ENDIF` (assembler-style) ✓
- MACRO / ENDM definitions and expansion ✓
- REPT n ... ENDM expansion ✓
- `#path` / `.path` include directory management ✓
- `#target rom/bin` ✓
- Circular include protection (`included_files` set) ✓
- Include depth limit (16) ✓
- String-aware substitution (quotes protected) ✓
- Dot-directive normalization (`.org` → `org`, etc.) ✓

### LIMITATION: `.IF` / `.ELSE` / `.ENDIF` not handled as conditional blocks

The preprocessor's conditional handler uses:
```python
re.match(r'^IF\b', stripped, re.IGNORECASE)
```
A line `.IF condition` starts with `.`, so it doesn't match. It falls through to `_normalize_dot_directives` (which converts `.IF` → `IF`), but by then the conditional handler has already passed. The assembler then sees bare `IF` and treats it as a no-op directive.

**Impact:** Users who write `.IF` (M80-style dot-prefixed conditional) get silently ignored conditions. Must use `#if` or bare `IF` instead. Not a crash, but a silent logic gap.

---

## 3. objfile.py — Serialization/Deserialization

**Correct.** JSON-based format (i8080-obj-v1):
- Binary data as hex string ✓
- Symbol addresses converted to offsets from org ✓
- Imports excluded from local symbols ✓
- Relocations with offset/size/symbol/addend ✓
- Data lines (DB/DW/DS) captured from listing ✓
- `load_obj` validates format version ✓
- `obj_from_asm_result` handles 3-tuple and 4-tuple relocations ✓

No bugs found.

---

## 4. linker.py — Relocation & Sequential Placement

**Correct.** Key behaviors verified:
- Sequential placement: objects laid back-to-back from ORIGIN, each object's own org ignored for placement ✓
- 16-bit little-endian relocation patches ✓
- 8-bit (low byte) relocation support ✓
- Case-insensitive symbol matching (default) / case-sensitive mode ✓
- Duplicate export detection with warning ✓
- Unresolved import detection with error ✓
- Library resolution: on-demand module pulling, no duplicates ✓
- Output buffer sizing: `max(configured_size, origin + max(obj.org+obj.size))` — slightly over-allocates but never under-allocates ✓

### MINOR: Output size over-allocation
```python
output_size = max(size, origin + max((o.org + o.size for o in objects), default=0))
```
Uses the object's assembler org (not placement base). If an object has org=0x8000 but is placed at 0x0000, the buffer is sized for 0x8000+size instead of the actual sequential end. Wastes memory, never causes corruption.

---

## 5. mapfile.py — DATA/CODE Classification

**Correct.** Classification logic:
- Checks if the symbol's address matches a listing entry
- If the listing source (after stripping label prefix) starts with DB/DW/DS → "DATA"
- Otherwise → "CODE"
- EQU symbols are filtered out (not shown in map) ✓
- Size computation: distance to next symbol, or to end of binary for last ✓

No bugs found.

---

## 6. librarian.py — Library Creation/Loading

**Correct.**
- JSON archive format (i8080-lib-v1) with index + modules ✓
- Export symbol → module name index for linker resolution ✓
- Duplicate module name detection ✓
- Duplicate export symbol across modules detection ✓
- Format version validation on load ✓
- Auto-creates output directory ✓

No bugs found.

---

## 7. numbers.py — Number Parsing

**Correct.** Handles:
- `0x1A`, `0X1A` — hex prefix ✓
- `1AH`, `1Ah`, `01AH` — hex suffix ✓
- `26`, `26d`, `26D` — decimal (optional suffix) ✓
- `00011010B`, `11010b` — binary ✓
- `32q`, `32o` — octal (Q or O suffix) ✓
- Leading zeros stripped correctly (00100 → 100) ✓
- `is_number()`, `is_valid_hex()` helpers ✓

Identical logic to `parse_number()` in assembler.py. No conflicts.

---

## Summary of Findings

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | **BUG** | assembler.py:650 | `CODE` missing from `_parse_label` exclude list — bare `CODE addr,size` consumed as label |
| 2 | Minor | assembler.py:~942 | Pass 1 advances 2 bytes for `INR/DCR r, imm` (invalid syntax), pass 2 emits 1 byte — location drift on invalid input |
| 3 | Limitation | preprocessor.py:143 | `.IF`/`.ELSE`/`.ENDIF` (dot-prefixed) not handled as conditional blocks — silently ignored |
| 4 | Cosmetic | OPCODE_REFERENCE.md | Column header says "циклов" (cycles) but values are byte sizes (1/2/3), not T-cycles |
| 5 | Minor | linker.py | Output buffer sized by `obj.org + obj.size` (assembler org) rather than sequential placement end — over-allocation only |

**No wrong opcodes. No missing instructions. No corruption bugs.**
The core encoding logic is 100% correct against OPCODE_REFERENCE.md.
