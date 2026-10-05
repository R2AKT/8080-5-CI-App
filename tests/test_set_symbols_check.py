# -*- coding: utf-8 -*-
"""Verify set_symbols is accessible on both DisasmView instances."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from i8080_ci.main_window import MainWindow
mw = MainWindow()

# Check disasm_view
dv = mw.disasm_view
print(f"disasm_view: type={type(dv).__name__}, module={type(dv).__module__}")
print(f"  has set_symbols: {hasattr(dv, 'set_symbols')}")
print(f"  has symbols attr: {hasattr(dv, 'symbols')}")

# Check emu_disasm_view
edv = mw.emu_disasm_view
print(f"emu_disasm_view: type={type(edv).__name__}, module={type(edv).__module__}")
print(f"  has set_symbols: {hasattr(edv, 'set_symbols')}")
print(f"  has symbols attr: {hasattr(edv, 'symbols')}")

# Check the class itself
from i8080_ci.views.disasm_view import DisasmView
print(f"\nDisasmView class: {DisasmView}")
print(f"  class has set_symbols: {hasattr(DisasmView, 'set_symbols')}")
print(f"  file: {DisasmView.__module__}")
import i8080_ci.views.disasm_view as dv_mod
print(f"  module file: {dv_mod.__file__}")

# Simulate the exact call from _auto_load_map
from assemble8080.mapfile import parse_map
mf = parse_map("ADDRESS   SIZE  TYPE    NAME\n0100      0007  CODE    START\n")
print(f"\nMapFile entries: {len(mf.entries)}")

# The exact call that fails:
try:
    mw.disasm_view.set_symbols(mf)
    print("✅ mw.disasm_view.set_symbols(mf) — OK")
except AttributeError as e:
    print(f"❌ AttributeError: {e}")

try:
    mw.emu_disasm_view.set_symbols(mf)
    print("✅ mw.emu_disasm_view.set_symbols(mf) — OK")
except AttributeError as e:
    print(f"❌ AttributeError: {e}")

print("\nDONE")
