# -*- coding: utf-8 -*-
"""Test: full auto-load map flow into disasm_view."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from i8080_ci.main_window import MainWindow
from i8080_ci.automation import AutomationAPI
from assemble8080.mapfile import parse_map

mw = MainWindow()
api = AutomationAPI(mw)

# 1. Assemble code with a global label
src = "ORG 0100H\nSTART:: MVI A, 0x55\nOUT 01H\nJMP START\n"
api.asm_set_source(src)
res = api.asm_assemble()
assert not res.errors, f"Assemble errors: {res.errors}"
print(f"1. Assemble OK: {len(res.binary)} bytes")

# 2. Verify map_file is None before auto-load
assert mw.map_file is None, "map_file should be None initially"
print("2. map_file is None before auto-load")

# 3. Simulate _auto_load_map (what assembler_widget does)
mf = parse_map(res.map_text)
assert mf is not None, "parse_map returned None"
assert len(mf.entries) == 1, f"Expected 1 entry, got {len(mf.entries)}"
print(f"3. MapFile parsed: {len(mf.entries)} entries")

# 4. Set symbols on disasm_view
mw.map_file = mf
mw.disasm_view.set_symbols(mf)
assert mw.disasm_view.symbols is not None, "set_symbols did not store the map file"
print("4. disasm_view.set_symbols() OK")

# 5. Verify symbol lookup
sym = mw.disasm_view.symbols.get_symbol_exact(0x0100)
assert sym == "START", f"Expected START, got {sym}"
print(f"5. get_symbol_exact(0x0100) = {sym}")

# 6. Load binary into memory, set disasm params, then run disasm
for i, b in enumerate(res.binary):
    mw.mem_data[0x0100 + i] = b
mw.disasm_start.setText("0100")
mw.disasm_len.setText("10")
mw.run_disasm()
assert len(mw.disasm_view.lines) > 0, "No disasm lines"
print(f"6. run_disasm OK: {len(mw.disasm_view.lines)} lines")

# 7. Verify the assembler widget's _auto_load_map method exists
assert hasattr(mw.assembler_widget, '_auto_load_map'), "Missing _auto_load_map"
print("7. assembler_widget._auto_load_map exists")

print("\n✅ FULL AUTO-LOAD MAP FLOW: ALL PASSED")
