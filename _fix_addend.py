"""Fix: restore label+addend support and safe $ replacement."""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 1. objfile.py — add addend to Relocation
# ============================================================
path = 'assemble8080/objfile.py'
src = open(path, encoding='utf-8').read()

# Add addend field to Relocation dataclass
old_reloc = '''@dataclass
class Relocation:
    """A relocation entry: patch at offset with symbol's address."""
    offset: int      # Byte offset from section origin
    size: int        # 1 or 2 bytes
    symbol: str      # Symbol name to resolve'''
new_reloc = '''@dataclass
class Relocation:
    """A relocation entry: patch at offset with symbol's address."""
    offset: int      # Byte offset from section origin
    size: int        # 1 or 2 bytes
    symbol: str      # Symbol name to resolve
    addend: int = 0  # Additive constant added to symbol address'''
assert old_reloc in src, "Relocation class not found"
src = src.replace(old_reloc, new_reloc)

# Update save_obj serialization
old_save = '''            {"offset": r.offset, "size": r.size, "symbol": r.symbol}'''
new_save = '''            {"offset": r.offset, "size": r.size, "symbol": r.symbol, "addend": r.addend}'''
assert old_save in src, "save_obj relocation serialization not found"
src = src.replace(old_save, new_save)

# Update load_obj deserialization
old_load = '''        obj.relocations.append(Relocation(
            offset=r["offset"],
            size=r["size"],
            symbol=r["symbol"],
        ))'''
new_load = '''        obj.relocations.append(Relocation(
            offset=r["offset"],
            size=r["size"],
            symbol=r["symbol"],
            addend=r.get("addend", 0),
        ))'''
assert old_load in src, "load_obj relocation deserialization not found"
src = src.replace(old_load, new_load)

# Update obj_from_asm_result to handle 4-element tuples
old_from = '''    for reloc in getattr(result, 'relocations', []):
        if isinstance(reloc, tuple):
            offset, size, sym = reloc
            obj.relocations.append(Relocation(offset=offset, size=size, symbol=sym))
        elif isinstance(reloc, Relocation):
            obj.relocations.append(reloc)'''
new_from = '''    for reloc in getattr(result, 'relocations', []):
        if isinstance(reloc, tuple):
            if len(reloc) == 4:
                offset, size, sym, addend = reloc
                obj.relocations.append(Relocation(offset=offset, size=size, symbol=sym, addend=addend))
            else:
                offset, size, sym = reloc
                obj.relocations.append(Relocation(offset=offset, size=size, symbol=sym))
        elif isinstance(reloc, Relocation):
            obj.relocations.append(reloc)'''
assert old_from in src, "obj_from_asm_result relocation loop not found"
src = src.replace(old_from, new_from)

open(path, 'w', encoding='utf-8').write(src)
print(f"[OK] {path}")

# ============================================================
# 2. assembler.py — multiple changes
# ============================================================
path = 'assemble8080/assembler.py'
src = open(path, encoding='utf-8').read()

# 2a. Add _parse_label_addend method before _track_relocation
old_track = '''    def _track_relocation(self, offset: int, size: int, symbol: str):
        """Записать запись переноса (offset от начала бинарного буфера)."""
        self._relocations.append((offset, size, symbol))'''
new_track = '''    def _parse_label_addend(self, op_str: str):
        """Разобрать 'label' или 'label+/-N' (включая $N локальные метки)
        в (LABEL_KEY, addend). Возвращает None если не подходит."""
        op_str = op_str.strip()
        m = re.match(r'^(\$[0-9]+|[A-Za-z_][A-Za-z0-9_]*)\\s*([+-])\\s*#?(-?\\d+)$', op_str)
        if m:
            label = m.group(1)
            num = int(m.group(3))
            if m.group(2) == '-':
                num = -num
            return self._sym_key(label), num
        if re.match(r'^(?:\\$[0-9]+|[A-Za-z_][A-Za-z0-9_]*)$', op_str):
            return self._sym_key(op_str), 0
        return None

    def _track_relocation(self, offset: int, size: int, symbol: str, addend: int = 0):
        """Записать запись переноса (offset от начала бинарного буфера)."""
        self._relocations.append((offset, size, symbol, addend))'''
assert old_track in src, "_track_relocation not found"
src = src.replace(old_track, new_track)

# 2b. Fix d16 section (SHLD, LHLD, STA, LDA, JMP, CALL, Jcc)
old_d16 = '''            sym = self._is_import_symbol(operands[0])
            if sym is not None:
                self._track_relocation(self._write_pos + 1, 2, sym)
            else:
                op_str = operands[0].strip()
                if re.match(r'^(?:\\$[0-9]+|[A-Za-z_][A-Za-z0-9_]*)$', op_str):
                    upper = self._sym_key(op_str)
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + 1, 2, upper)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + 1, 2, upper)
            return bytearray([opcode, val & 0xFF, (val >> 8) & 0xFF])'''
new_d16 = '''            sym = self._is_import_symbol(operands[0])
            if sym is not None:
                self._track_relocation(self._write_pos + 1, 2, sym)
            else:
                parsed = self._parse_label_addend(operands[0])
                if parsed is not None:
                    upper, addend = parsed
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + 1, 2, upper, addend)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + 1, 2, upper, addend)
            return bytearray([opcode, val & 0xFF, (val >> 8) & 0xFF])'''
assert old_d16 in src, "d16 section not found"
src = src.replace(old_d16, new_d16)

# 2c. Fix rp,d16 section (LXI)
old_lxi = '''            sym = self._is_import_symbol(operands[1])
            if sym is not None:
                self._track_relocation(self._write_pos + 1, 2, sym)
            else:
                op_str = operands[1].strip()
                if re.match(r'^(?:\\$[0-9]+|[A-Za-z_][A-Za-z0-9_]*)$', op_str):
                    upper = self._sym_key(op_str)
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + 1, 2, upper)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + 1, 2, upper)
            return bytearray([opcode | (rp_code << 4), val & 0xFF, (val >> 8) & 0xFF])'''
new_lxi = '''            sym = self._is_import_symbol(operands[1])
            if sym is not None:
                self._track_relocation(self._write_pos + 1, 2, sym)
            else:
                parsed = self._parse_label_addend(operands[1])
                if parsed is not None:
                    upper, addend = parsed
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + 1, 2, upper, addend)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + 1, 2, upper, addend)
            return bytearray([opcode | (rp_code << 4), val & 0xFF, (val >> 8) & 0xFF])'''
assert old_lxi in src, "rp,d16 (LXI) section not found"
src = src.replace(old_lxi, new_lxi)

# 2d. Fix DW section
old_dw = '''            sym = self._is_import_symbol(part)
            if sym is not None:
                self._track_relocation(self._write_pos + len(result) - 2, 2, sym)
            else:
                part_str = part.strip()
                if re.match(r'^(?:\\$[0-9]+|[A-Za-z_][A-Za-z0-9_]*)$', part_str):
                    upper = self._sym_key(part_str)
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + len(result) - 2, 2, upper)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + len(result) - 2, 2, upper)'''
new_dw = '''            sym = self._is_import_symbol(part)
            if sym is not None:
                self._track_relocation(self._write_pos + len(result) - 2, 2, sym)
            else:
                parsed = self._parse_label_addend(part)
                if parsed is not None:
                    upper, addend = parsed
                    if upper not in self.symbols:
                        # Undefined symbol → import
                        self._imports.add(upper)
                        self._track_relocation(self._write_pos + len(result) - 2, 2, upper, addend)
                    elif self._relocatable:
                        # Defined local symbol in relocatable mode → relocation
                        self._track_relocation(self._write_pos + len(result) - 2, 2, upper, addend)'''
assert old_dw in src, "DW section not found"
src = src.replace(old_dw, new_dw)

# 2e. Fix $ replacement in _parse_operand (line ~1591)
old_parse_dollar = '''        if allow_current and '$' in expr_str:
            expr_str = expr_str.replace('$', str(self.pc))'''
new_parse_dollar = '''        if allow_current and '$' in expr_str:
            # Заменяем только standalone $ (текущий адрес), но НЕ $N (локальные метки)
            expr_str = re.sub(r'\\$(?!\\d)', str(self.pc), expr_str)'''
assert old_parse_dollar in src, "$ replacement in _parse_operand not found"
src = src.replace(old_parse_dollar, new_parse_dollar)

# 2f. Fix $ replacement in _eval (line ~462)
old_eval_dollar = '''            # Заменяем $ на текущий адрес
            expr = expr.replace('$', str(self.pc))'''
new_eval_dollar = '''            # Заменяем $ на текущий адрес (только standalone $, не $N)
            expr = re.sub(r'\\$(?!\\d)', str(self.pc), expr)'''
assert old_eval_dollar in src, "$ replacement in _eval not found"
src = src.replace(old_eval_dollar, new_eval_dollar)

open(path, 'w', encoding='utf-8').write(src)
print(f"[OK] {path}")

# ============================================================
# 3. linker.py — use addend in relocation patching
# ============================================================
path = 'assemble8080/linker.py'
src = open(path, encoding='utf-8').read()

old_link = '''            if reloc.size == 2:
                # 16-bit little-endian
                output[patch_addr] = sym_addr & 0xFF
                output[patch_addr + 1] = (sym_addr >> 8) & 0xFF
            elif reloc.size == 1:
                # 8-bit (low byte only)
                output[patch_addr] = sym_addr & 0xFF'''
new_link = '''            patch_val = (sym_addr + getattr(reloc, 'addend', 0)) & 0xFFFF
            if reloc.size == 2:
                # 16-bit little-endian
                output[patch_addr] = patch_val & 0xFF
                output[patch_addr + 1] = (patch_val >> 8) & 0xFF
            elif reloc.size == 1:
                # 8-bit (low byte only)
                output[patch_addr] = patch_val & 0xFF'''
assert old_link in src, "linker relocation patching not found"
src = src.replace(old_link, new_link)

open(path, 'w', encoding='utf-8').write(src)
print(f"[OK] {path}")

print("\nAll changes applied successfully.")
