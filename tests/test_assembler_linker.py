# -*- coding: utf-8 -*-
"""
Тест новых функций: map file, object file, linker.
"""
import os
import sys
import tempfile
import shutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import assemble, Assembler
from assemble8080.mapfile import generate_map, parse_map, MapFile
from assemble8080.objfile import ObjectFile, save_obj, load_obj, obj_from_asm_result
from assemble8080.linker import link, parse_link_script, LinkResult

passed = 0
failed = 0

def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}: {msg}")


def main():
    global passed, failed
    tmpdir = tempfile.mkdtemp(prefix="asm_link_test_")
    
    try:
        # === Test 1: Map file generation ===
        print("Тест 1: Генерация map файла")
        source = """
ORG 0x0100
start:
    MVI A, 0x42
    CALL sub
    HLT
sub:
    ADD B
    RET
my_data:
    DB 0x11, 0x22, 0x33
"""
        result = assemble(source)
        check("Сборка без ошибок", result.success, str(result.errors))
        
        map_text = generate_map(result, source_name="test.asm")
        check("Map текст сгенерирован", len(map_text) > 0)
        check("Map содержит 'START'", 'START' in map_text)
        check("Map содержит 'SUB'", 'SUB' in map_text)
        check("Map содержит 'MY_DATA'", 'MY_DATA' in map_text)
        check("Map содержит ORG", '0x0100' in map_text)
        
        # Parse back
        mf = parse_map(map_text)
        check("Parse: entries > 0", len(mf.entries) > 0)
        check("Parse: source", mf.source == "test.asm")
        check("Parse: get_symbol_at", mf.get_symbol_at(0x0100) == 'START')
        check("Parse: get_symbol_exact", mf.get_symbol_exact(0x0100) == 'START')
        
        # === Test 2: Object file ===
        print("Тест 2: Объектный файл")
        source2 = """
ORG 0x0200
EXPORT main
IMPORT helper
main:
    MVI A, 0x01
    CALL helper
    HLT
"""
        result2 = assemble(source2)
        check("Сборка без ошибок", result2.success, str(result2.errors))
        check("Exports содержит MAIN", 'MAIN' in result2.exports, str(result2.exports))
        check("Imports содержит HELPER", 'HELPER' in result2.imports, str(result2.imports))
        
        # Save and load
        obj_path = os.path.join(tmpdir, "test.obj")
        obj = obj_from_asm_result(result2, source_name="test2.asm")
        save_obj(obj_path, obj)
        check("Файл создан", os.path.exists(obj_path))
        
        obj2 = load_obj(obj_path)
        check("Load: name", obj2.name == "test2")
        check("Load: org", obj2.org == 0x0200)
        check("Load: exports", 'MAIN' in obj2.exports)
        check("Load: imports", 'HELPER' in obj2.imports)
        check("Load: data size", len(obj2.data) == result2.binary.__len__())
        
        # === Test 3: Linker ===
        print("Тест 3: Линковщик")
        # Create two object files
        # Module 1: main at 0x0100, calls helper
        src1 = """
ORG 0x0100
EXPORT main
IMPORT helper
main:
    MVI A, 0x01
    CALL helper
    HLT
"""
        # Module 2: helper at 0x0200
        src2 = """
ORG 0x0200
EXPORT helper
helper:
    INR B
    RET
"""
        r1 = assemble(src1)
        r2 = assemble(src2)
        check("Module 1 assembled", r1.success)
        check("Module 2 assembled", r2.success)
        
        obj1 = obj_from_asm_result(r1, "main.asm")
        obj2 = obj_from_asm_result(r2, "helper.asm")
        
        # Save to disk
        obj1_path = os.path.join(tmpdir, "main.obj")
        obj2_path = os.path.join(tmpdir, "helper.obj")
        save_obj(obj1_path, obj1)
        save_obj(obj2_path, obj2)
        
        # Link
        result_link = link([obj1, obj2], origin=0, size=0x10000, fill=0xFF)
        check("Link success", result_link.success, str(result_link.errors))
        check("Link: binary size", len(result_link.binary) == 0x10000)
        check("Link: symbols has MAIN", 'MAIN' in result_link.symbols)
        check("Link: symbols has HELPER", 'HELPER' in result_link.symbols)
        check("Link: MAIN at 0x0100", result_link.symbols.get('MAIN') == 0x0100)
        check("Link: HELPER at 0x0200", result_link.symbols.get('HELPER') == 0x0200, f"got {result_link.symbols.get('HELPER')}")
        
        # Verify binary layout
        # main at 0x0100: MVI A, 0x01 (0x0E, 0x01)
        #                  CALL helper (0xCD, 0x00, 0x00) - not relocated yet
        # helper at 0x0200: INR B (0x04), RET (0xC9)
        check("MVI A at 0x0100", result_link.binary[0x0100] == 0x3E, f"got 0x{result_link.binary[0x0100]:02X}")
        check("CALL at 0x0102", result_link.binary[0x0102] == 0xCD, f"got 0x{result_link.binary[0x0102]:02X}")
        check("INR B at 0x0200", result_link.binary[0x0200] == 0x04, f"got 0x{result_link.binary[0x0200]:02X}")
        check("RET at 0x0201", result_link.binary[0x0201] == 0xC9, f"got 0x{result_link.binary[0x0201]:02X}")
        check("Fill 0xFF elsewhere", result_link.binary[0x0300] == 0xFF)
        
        # === Test 4: Linker script ===
        print("Тест 4: Linker script")
        lnk_content = """
INPUT main.obj helper.obj
OUTPUT output.bin
MAP output.map
ORIGIN 0x0000
SIZE 0x10000
FILL 0xFF
"""
        lnk_path = os.path.join(tmpdir, "test.lnk")
        with open(lnk_path, 'w') as f:
            f.write(lnk_content)
        
        config = parse_link_script(lnk_content)
        check("Config: inputs", config["inputs"] == ["main.obj", "helper.obj"])
        check("Config: output", config["output"] == "output.bin")
        check("Config: map", config["map"] == "output.map")
        check("Config: origin", config["origin"] == 0)
        check("Config: size", config["size"] == 0x10000)
        check("Config: fill", config["fill"] == 0xFF)
        
        # === Test 5: Disassembler with map ===
        print("Тест 5: Дизассемблер с map")
        from i8080_ci.disassembler import I8080Disassembler
        
        disasm = I8080Disassembler()
        # Without map
        mem = {0x0100: 0x0E, 0x0101: 0x42, 0x0102: 0xC3, 0x0103: 0x04, 0x0104: 0x01}
        lines = disasm.disassemble(mem, 0x0100, 5)
        check("Disasm без map: нет имён", ':' not in lines[0][2], lines[0][2])
        check("Disasm: 2 инструкции", len(lines) == 2, f"got {len(lines)}")
        
        # With map
        mf = MapFile()
        from assemble8080.mapfile import MapEntry
        mf.entries.append(MapEntry(0x0100, 2, "CODE", "my_func"))
        mf.entries.append(MapEntry(0x0104, 1, "CODE", "target"))
        disasm.set_map(mf)
        lines = disasm.disassemble(mem, 0x0100, 5)
        check("Disasm с map: имя функции", 'my_func' in lines[0][2], lines[0][2])
        check("Disasm с map: имя target в JMP", 'target' in lines[1][2], lines[1][2])
        
        # === Test 6: Relocation tracking ===
        print("Тест 6: Отслеживание переносов (relocations)")
        # Local label: no relocation
        src_local = """
ORG 0x100
START:
    MVI A, 5
    JMP START
    HLT
END
"""
        r = assemble(src_local)
        check("Local: success", r.success, str(r.errors))
        check("Local: no relocations", r.relocations == [], str(r.relocations))
        
        # Import symbol: relocations generated
        src_imp = """
ORG 0x100
IMPORT HELPER
START:
    MVI A, 5
    CALL HELPER
    JMP HELPER
    LHLD HELPER
    HLT
END
"""
        r = assemble(src_imp)
        check("Import: success", r.success, str(r.errors))
        check("Import: 3 relocations", len(r.relocations) == 3, str(r.relocations))
        expected = [(3, 2, 'HELPER'), (6, 2, 'HELPER'), (9, 2, 'HELPER')]
        check("Import: correct offsets", r.relocations == expected, str(r.relocations))
        
        # DW with import
        src_dw = """
ORG 0x200
IMPORT TBL
    DW TBL, 5
    HLT
END
"""
        r = assemble(src_dw)
        check("DW: success", r.success, str(r.errors))
        check("DW: 1 relocation", r.relocations == [(0, 2, 'TBL')], str(r.relocations))
        
        # LXI with import
        src_lxi = """
ORG 0x300
IMPORT PTR
    LXI H, PTR
    HLT
END
"""
        r = assemble(src_lxi)
        check("LXI: success", r.success, str(r.errors))
        check("LXI: 1 relocation", r.relocations == [(1, 2, 'PTR')], str(r.relocations))
        
        # Full link: relocation applied correctly
        srcA = """
ORG 0x200
EXPORT HELPER
HELPER:
    MVI A, 42
    RET
END
"""
        srcB = """
ORG 0x100
IMPORT HELPER
START:
    CALL HELPER
    HLT
END
"""
        rA = assemble(srcA)
        rB = assemble(srcB)
        check("Link A: success", rA.success, str(rA.errors))
        check("Link B: success", rB.success, str(rB.errors))
        objA = obj_from_asm_result(rA, 'a.asm')
        objB = obj_from_asm_result(rB, 'b.asm')
        res = link([objA, objB], origin=0, size=0x10000)
        check("Link: success", res.success, str(res.errors))
        check("Link: HELPER at 0x200", res.symbols.get('HELPER') == 0x200, str(res.symbols.get('HELPER')))
        call_bytes = res.binary[0x100:0x103]
        check("Link: CALL patched to 0x0200", call_bytes == bytes([0xCD, 0x00, 0x02]), call_bytes.hex())
        helper_bytes = res.binary[0x200:0x203]
        check("Link: HELPER code intact", helper_bytes == bytes([0x3E, 0x2A, 0xC9]), helper_bytes.hex())
        
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
