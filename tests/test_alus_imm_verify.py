"""Верификация ALUS_IMM по документации 8080/8085.

Проверяет:
1. Все 8 immediate ALU опкодов (0xC6-0xFE) декодируются правильно
2. Регистровая форма (0x80-0xBF) использует ORA/CMP
3. Непосредственная форма (0xF6/0xFE) использует ORI/CPI
4. Round-trip: ассемблирование -> дизассемблирование -> сравнение
5. CMP с immediate операндом НЕ принимается (только CPI)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from assemble8080.assembler import Assembler
from i8080_ci.disassembler import I8080Disassembler as Disassembler


def _mem_dict(data, base=0x0100):
    """Convert bytearray to {addr: byte} dict for disassembler."""
    return {base + i: b for i, b in enumerate(data)}


def test_disassembler_immediate_alu():
    """Все 8 immediate ALU опкодов декодируются с правильными мнемониками."""
    dis = Disassembler()
    # 0xC6=ADD, 0xCE=ADC, 0xD6=SUB, 0xDE=SBB, 0xE6=ANA, 0xEE=XRA, 0xF6=ORI, 0xFE=CPI
    mem = bytearray([
        0xC6, 0x01,  # ADD 01h
        0xCE, 0x02,  # ADC 02h
        0xD6, 0x03,  # SUB 03h
        0xDE, 0x04,  # SBB 04h
        0xE6, 0x05,  # ANA 05h
        0xEE, 0x06,  # XRA 06h
        0xF6, 0x07,  # ORI 07h
        0xFE, 0x08,  # CPI 08h
        0xC9,        # RET
    ])
    lines = dis.disassemble(_mem_dict(mem), 0x0100, len(mem))
    expected = ['ADI 01h', 'ACI 02h', 'SUI 03h', 'SBI 04h',
                'ANI 05h', 'XRI 06h', 'ORI 07h', 'CPI 08h', 'RET']
    for i, exp in enumerate(expected):
        actual = lines[i][2]
        assert actual == exp, f'Line {i}: expected "{exp}", got "{actual}"'
    print('  PASS: disassembler immediate ALU')


def test_disassembler_register_alu():
    """Регистровая форма: ORA (0xB0-B7) и CMP (0xB8-BF)."""
    dis = Disassembler()
    mem = bytearray([
        0xB0,  # ORA B
        0xB1,  # ORA C
        0xB2,  # ORA D
        0xB3,  # ORA E
        0xB4,  # ORA H
        0xB5,  # ORA L
        0xB6,  # ORA M
        0xB7,  # ORA A
        0xB8,  # CMP B
        0xB9,  # CMP C
        0xBA,  # CMP D
        0xBB,  # CMP E
        0xBC,  # CMP H
        0xBD,  # CMP L
        0xBE,  # CMP M
        0xBF,  # CMP A
    ])
    lines = dis.disassemble(_mem_dict(mem), 0x0100, len(mem))
    regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
    for i, r in enumerate(regs):
        assert lines[i][2] == f'ORA {r}', f'Line {i}: expected "ORA {r}", got "{lines[i][2]}"'
    for i, r in enumerate(regs):
        assert lines[8 + i][2] == f'CMP {r}', f'Line {8+i}: expected "CMP {r}", got "{lines[8+i][2]}"'
    print('  PASS: disassembler register ALU (ORA/CMP)')


def test_assembler_cpi_ori():
    """CPI и ORI в основной таблице ассемблера."""
    asm = Assembler()
    r = asm.assemble('    ORG 0100H\n        CPI 05H\n        ORI 0AH\n        RET')
    assert r.binary == bytearray([0xFE, 0x05, 0xF6, 0x0A, 0xC9]), \
        f'Expected FE 05 F6 0A C9, got {r.binary.hex()}'
    print('  PASS: assembler CPI/ORI via main table')


def test_assembler_alu_imm_fallback():
    """Fallback: регистровая мнемоника + immediate операнд."""
    # ADD 01H -> 0xC6 01 (fallback, не ADI)
    asm = Assembler()
    r = asm.assemble('    ORG 0100H\n        ADD 01H\n        RET')
    assert r.binary == bytearray([0xC6, 0x01, 0xC9]), \
        f'Expected C6 01 C9, got {r.binary.hex()}'
    
    # ADC 02H -> 0xCE 02
    asm2 = Assembler()
    r2 = asm2.assemble('    ORG 0100H\n        ADC 02H\n        RET')
    assert r2.binary == bytearray([0xCE, 0x02, 0xC9]), \
        f'Expected CE 02 C9, got {r2.binary.hex()}'
    
    # SUB 03H -> 0xD6 03
    asm3 = Assembler()
    r3 = asm3.assemble('    ORG 0100H\n        SUB 03H\n        RET')
    assert r3.binary == bytearray([0xD6, 0x03, 0xC9]), \
        f'Expected D6 03 C9, got {r3.binary.hex()}'
    
    # SBB 04H -> 0xDE 04
    asm4 = Assembler()
    r4 = asm4.assemble('    ORG 0100H\n        SBB 04H\n        RET')
    assert r4.binary == bytearray([0xDE, 0x04, 0xC9]), \
        f'Expected DE 04 C9, got {r4.binary.hex()}'
    
    # ANA 05H -> 0xE6 05
    asm5 = Assembler()
    r5 = asm5.assemble('    ORG 0100H\n        ANA 05H\n        RET')
    assert r5.binary == bytearray([0xE6, 0x05, 0xC9]), \
        f'Expected E6 05 C9, got {r5.binary.hex()}'
    
    # XRA 06H -> 0xEE 06
    asm6 = Assembler()
    r6 = asm6.assemble('    ORG 0100H\n        XRA 06H\n        RET')
    assert r6.binary == bytearray([0xEE, 0x06, 0xC9]), \
        f'Expected EE 06 C9, got {r6.binary.hex()}'
    
    print('  PASS: assembler ALU immediate fallback (ADD/ADC/SUB/SBB/ANA/XRA)')


def test_assembler_cmp_imm_rejected():
    """CMP с immediate операндом НЕ принимается (используйте CPI)."""
    asm = Assembler()
    r = asm.assemble('    ORG 0100H\n        CMP 05H\n        RET')
    # CMP 05H: main table has CMP as (0xB8, 'r', 1), tries to parse 05H as register
    # 05H is not a register, ALU_IMM_OPCODES no longer has 'CMP'
    # Should produce an error
    assert r.errors, f'Expected error for CMP 05H, but got binary: {r.binary.hex() if r.binary else "None"}'
    print(f'  PASS: assembler rejects CMP 05H (error: {r.errors[0]})')


def test_roundtrip_all_immediate():
    """Полный round-trip: assemble -> disassemble -> compare."""
    source = """    ORG 0100H
        ADD 01H
        ADC 02H
        SUB 03H
        SBB 04H
        ANA 05H
        XRA 06H
        ORI 07H
        CPI 08H
        RET"""
    asm = Assembler()
    r = asm.assemble(source)
    assert r.binary, f'Assembly failed: {r.errors}'
    
    dis = Disassembler()
    lines = dis.disassemble(_mem_dict(r.binary), 0x0100, len(r.binary))
    
    expected = ['ADI 01h', 'ACI 02h', 'SUI 03h', 'SBI 04h',
                'ANI 05h', 'XRI 06h', 'ORI 07h', 'CPI 08h', 'RET']
    for i, exp in enumerate(expected):
        actual = lines[i][2]
        assert actual == exp, f'Round-trip line {i}: expected "{exp}", got "{actual}"'
    print('  PASS: round-trip all immediate ALU')


def test_roundtrip_register():
    """Round-trip регистровых ALU: ORA и CMP."""
    source = """    ORG 0100H
        ORA B
        ORA C
        CMP D
        CMP E
        ADD H
        SUB L
        RET"""
    asm = Assembler()
    r = asm.assemble(source)
    assert r.binary, f'Assembly failed: {r.errors}'
    
    dis = Disassembler()
    lines = dis.disassemble(_mem_dict(r.binary), 0x0100, len(r.binary))
    
    expected = ['ORA B', 'ORA C', 'CMP D', 'CMP E', 'ADD H', 'SUB L', 'RET']
    for i, exp in enumerate(expected):
        actual = lines[i][2]
        assert actual == exp, f'Round-trip line {i}: expected "{exp}", got "{actual}"'
    print('  PASS: round-trip register ALU (ORA/CMP)')


if __name__ == '__main__':
    print('Верификация ALUS_IMM по документации 8080/8085:')
    print('=' * 55)
    test_disassembler_immediate_alu()
    test_disassembler_register_alu()
    test_assembler_cpi_ori()
    test_assembler_alu_imm_fallback()
    test_assembler_cmp_imm_rejected()
    test_roundtrip_all_immediate()
    test_roundtrip_register()
    print('=' * 55)
    print('ALL 7 TESTS PASSED')
