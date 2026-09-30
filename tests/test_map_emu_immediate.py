"""Test: map auto-load must immediately update emu_disasm_view with symbols."""
import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from i8080_ci.main_window import MainWindow
from i8080_ci.automation import AutomationAPI

mw = MainWindow()
mw.show()
app.processEvents()

api = AutomationAPI(mw)

# Source with a label
source = """
    ORG 0100H
START:  LDA 2000H
        STA 2001H
        JMP START
"""

# Assemble + load
result = api.asm_assemble(source=source, load_to_memory=True)
app.processEvents()

print(f"1. map_file set: {mw.map_file is not None}")
assert mw.map_file is not None, "map_file should be set after assemble+load"

print(f"2. disassembler._map set: {mw.disassembler._map is not None}")
assert mw.disassembler._map is not None, "disassembler._map should be set"

print(f"3. disasm_view.symbols set: {mw.disasm_view.symbols is not None}")
assert mw.disasm_view.symbols is not None, "disasm_view.symbols should be set"

print(f"4. emu_disasm_view.symbols set: {mw.emu_disasm_view.symbols is not None}")
assert mw.emu_disasm_view.symbols is not None, "emu_disasm_view.symbols should be set"

# Check that emu_disasm_view has lines with symbol names
print(f"5. emu_disasm_view has lines: {len(mw.emu_disasm_view.lines) > 0}")
assert len(mw.emu_disasm_view.lines) > 0, "emu_disasm_view should have lines"

# Check that the disassembly text contains the label name
lines_text = "\n".join(str(l) for l in mw.emu_disasm_view.lines)
print(f"6. 'START' in emu disasm text: {'START' in lines_text}")
assert 'START' in lines_text, f"emu_disasm_view text should contain 'START', got: {lines_text[:200]}"

# Check symbol lookup
sym = mw.emu_disasm_view.symbols.get_symbol_exact(0x0100)
print(f"7. get_symbol_exact(0x0100) = {sym}")
assert sym == "START", f"Expected 'START', got '{sym}'"

print()
print("ALL 7 CHECKS PASSED")
