# -*- coding: utf-8 -*-
"""Test: verify map auto-load only on assemble+load, and matches manual load behavior."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from i8080_ci.main_window import MainWindow
from i8080_ci.automation import AutomationAPI

mw = MainWindow()
api = AutomationAPI(mw)

src = "ORG 0100H\nSTART:: MVI A, 0x55\nOUT 01H\nJMP START\n"
api.asm_set_source(src)

# Test 1: Simple assemble (load_to_memory=False) should NOT set map_file
res = api.asm_assemble(load_to_memory=False)
assert not res.errors, f"Assemble errors: {res.errors}"
print(f"1. Simple assemble: map_file = {mw.map_file}")
assert mw.map_file is None, f"map_file should be None after simple assemble, got {mw.map_file}"
print("   ✅ map_file is None (no auto-load on simple assemble)")

# Test 2: Assemble+Load (load_to_memory=True) SHOULD set map_file
res2 = api.asm_assemble(load_to_memory=True)
assert not res2.errors, f"Assemble+Load errors: {res2.errors}"
print(f"2. Assemble+Load: map_file = {mw.map_file is not None}")
assert mw.map_file is not None, "map_file should be set after assemble+load"
print("   ✅ map_file is set (auto-load on assemble+load)")

# Test 3: disasm_view.symbols should be set
assert mw.disasm_view.symbols is not None, "disasm_view.symbols should be set"
print(f"3. disasm_view.symbols = {mw.disasm_view.symbols is not None}")
print("   ✅ disasm_view.symbols is set")

# Test 4: disassembler should have the map (same as manual load)
has_disasm_map = hasattr(mw.disassembler, '_map') and mw.disassembler._map is not None
print(f"4. disassembler._map = {has_disasm_map}")
assert has_disasm_map, "disassembler._map should be set (same as manual load)"
print("   ✅ disassembler has map (matches manual load behavior)")

# Test 5: Symbol lookup works
sym = mw.disasm_view.symbols.get_symbol_exact(0x0100)
assert sym == "START", f"Expected START, got {sym}"
print(f"5. get_symbol_exact(0x0100) = {sym}")
print("   ✅ Symbol lookup works")

print("\n✅ ALL TESTS PASSED: auto-load only on assemble+load, matches manual load")
