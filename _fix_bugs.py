"""Fix assembler bugs found during deep analysis."""
import re

path = 'assemble8080/assembler.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

fixes = 0

# Fix 1: RAL 0x17 -> 0x67
old = "'RAL':   (0x17, '', 1),"
new = "'RAL':   (0x67, '', 1),"
if old in src:
    src = src.replace(old, new)
    fixes += 1
    print("FIX 1: RAL 0x17 -> 0x67")

# Fix 2: RAR 0x1F -> 0x6F
old = "'RAR':   (0x1F, '', 1),"
new = "'RAR':   (0x6F, '', 1),"
if old in src:
    src = src.replace(old, new)
    fixes += 1
    print("FIX 2: RAR 0x1F -> 0x6F")

# Fix 3: XTHL 0xE3 -> 0xEB
old = "'XTHL':  (0xE3, '', 1),"
new = "'XTHL':  (0xEB, '', 1),"
if old in src:
    src = src.replace(old, new)
    fixes += 1
    print("FIX 3: XTHL 0xE3 -> 0xEB")

# Fix 4: ALU two-operand form - use second operand for register
# Current code uses operands[0] when second operand is a register.
# Need to change: when len(operands)>=2 and op2 IS a register, use op2's reg code.
old_block = """            # Check if operand is a valid register; if not, try immediate (ALU ops)
            op_upper = operands[0].strip().upper()
            if op_upper in REGISTERS or op_upper in ('BC', 'DE', 'HL', 'PSW'):
                reg_code = self._get_reg_code(operands[0], line_num)
                if mnemonic in ('INR', 'DCR'):
                    return bytearray([opcode + reg_code * 8])
                return bytearray([opcode | reg_code])"""

new_block = """            # Check if operand is a valid register; if not, try immediate (ALU ops)
            # For ALU ops with 2 operands (e.g. "add a,b"), use the SECOND operand
            if len(operands) >= 2 and mnemonic not in ('INR', 'DCR'):
                op2_u = operands[1].strip().upper()
                if op2_u in REGISTERS:
                    reg_code = self._get_reg_code(operands[1], line_num)
                    return bytearray([opcode | reg_code])
            op_upper = operands[0].strip().upper()
            if op_upper in REGISTERS or op_upper in ('BC', 'DE', 'HL', 'PSW'):
                reg_code = self._get_reg_code(operands[0], line_num)
                if mnemonic in ('INR', 'DCR'):
                    return bytearray([opcode + reg_code * 8])
                return bytearray([opcode | reg_code])"""

if old_block in src:
    src = src.replace(old_block, new_block)
    fixes += 1
    print("FIX 4: ALU two-operand uses second operand")
else:
    print("WARN: FIX 4 pattern not found (CRLF?)")
    # Try with \r\n
    old_block_crlf = old_block.replace('\n', '\r\n')
    new_block_crlf = new_block.replace('\n', '\r\n')
    if old_block_crlf in src:
        src = src.replace(old_block_crlf, new_block_crlf)
        fixes += 1
        print("FIX 4: ALU two-operand (CRLF)")

# Fix 5: INR/DCR SP and M
# The formula opcode + reg_code*8 works for B(0)-A(7) but M needs special handling.
# Also SP is not in REGISTERS dict, so _get_reg_code('sp') may return wrong value.
# Fix: add special handling for INR/DCR with SP and M.
old_inr = """                if mnemonic in ('INR', 'DCR'):
                    return bytearray([opcode + reg_code * 8])
                return bytearray([opcode | reg_code])"""

new_inr = """                if mnemonic in ('INR', 'DCR'):
                    # INR/DCR: B=0,C=1,D=2,E=3,H=4,L=5,SP=6,A=7,M=8
                    # M is special: INR M=0x3E, DCR M=0x3F
                    if op_upper == 'M':
                        return bytearray([0x3E]) if mnemonic == 'INR' else bytearray([0x3F])
                    if op_upper == 'SP':
                        return bytearray([opcode + 6 * 8])
                    return bytearray([opcode + reg_code * 8])
                return bytearray([opcode | reg_code])"""

if old_inr in src:
    src = src.replace(old_inr, new_inr, 1)  # only first occurrence (in the register path)
    fixes += 1
    print("FIX 5a: INR/DCR M and SP special handling")
else:
    old_inr_crlf = old_inr.replace('\n', '\r\n')
    new_inr_crlf = new_inr.replace('\n', '\r\n')
    if old_inr_crlf in src:
        src = src.replace(old_inr_crlf, new_inr_crlf, 1)
        fixes += 1
        print("FIX 5a: INR/DCR M and SP (CRLF)")
    else:
        print("WARN: FIX 5a pattern not found")

# Also fix the fallthrough INR/DCR (second occurrence)
old_inr2 = """            reg_code = self._get_reg_code(operands[0], line_num)
            if mnemonic in ('INR', 'DCR'):
                return bytearray([opcode + reg_code * 8])
            return bytearray([opcode | reg_code])"""

new_inr2 = """            reg_code = self._get_reg_code(operands[0], line_num)
            if mnemonic in ('INR', 'DCR'):
                op_u2 = operands[0].strip().upper()
                if op_u2 == 'M':
                    return bytearray([0x3E]) if mnemonic == 'INR' else bytearray([0x3F])
                if op_u2 == 'SP':
                    return bytearray([opcode + 6 * 8])
                return bytearray([opcode + reg_code * 8])
            return bytearray([opcode | reg_code])"""

if old_inr2 in src:
    src = src.replace(old_inr2, new_inr2, 1)
    fixes += 1
    print("FIX 5b: INR/DCR fallthrough M and SP")
else:
    old_inr2_crlf = old_inr2.replace('\n', '\r\n')
    new_inr2_crlf = new_inr2.replace('\n', '\r\n')
    if old_inr2_crlf in src:
        src = src.replace(old_inr2_crlf, new_inr2_crlf, 1)
        fixes += 1
        print("FIX 5b: INR/DCR fallthrough (CRLF)")
    else:
        print("WARN: FIX 5b pattern not found")

# Fix 6: PUSH/POP - add 'PS' and 'F' as PSW aliases
old_push = """            op_u = operands[0].strip().upper()
            if op_u in ('A', 'PSW'):
                rp_code = 3"""
new_push = """            op_u = operands[0].strip().upper()
            if op_u in ('A', 'PSW', 'PS', 'F'):
                rp_code = 3"""

if old_push in src:
    src = src.replace(old_push, new_push)
    fixes += 1
    print("FIX 6: PUSH/POP PS/F aliases")
else:
    old_push_crlf = old_push.replace('\n', '\r\n')
    new_push_crlf = new_push.replace('\n', '\r\n')
    if old_push_crlf in src:
        src = src.replace(old_push_crlf, new_push_crlf)
        fixes += 1
        print("FIX 6: PUSH/POP PS/F (CRLF)")
    else:
        print("WARN: FIX 6 pattern not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print(f"\nTotal fixes applied: {fixes}")
