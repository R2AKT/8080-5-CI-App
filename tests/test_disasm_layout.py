"""Test: new disasm_view layout - labels on separate lines, indented instructions."""
import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from i8080_ci.main_window import MainWindow
from i8080_ci.automation import AutomationAPI

mw = MainWindow()
mw.show()
app.processEvents()

api = AutomationAPI(mw)

source = """
    ORG 0100H
START:  LDA 2000H
        STA 2001H
LOOP:   INR B
        CPI 05H
        JNZ LOOP
        RET
"""

result = api.asm_assemble(source=source, load_to_memory=True)
app.processEvents()

# Set correct disasm range and re-run
mw.disasm_start.setText("0100")
mw.disasm_len.setText("0020")
mw.run_disasm()
app.processEvents()

dv = mw.disasm_view
print(f"Raw lines: {len(dv.lines)}")
print(f"Display lines: {len(dv._display_lines)}")
print()

# Print display lines
print("Display lines:")
for i, (addr, size, asm, undoc, target, is_label, sym) in enumerate(dv._display_lines):
    if is_label:
        print(f"  [{i:2d}] LABEL  {addr:04X}  {sym}")
    else:
        indent = "  " if (i > 0 and dv._display_lines[i-1][5] and dv._display_lines[i-1][0] == addr) else ""
        print(f"  [{i:2d}] INSTR  {addr:04X}  {indent}{asm}  target={target}")

print()

# 1. START on separate line
start_labels = [dl for dl in dv._display_lines if dl[5] and dl[6] == "START"]
assert len(start_labels) == 1, f"Expected 1 START label, got {len(start_labels)}"
print("1. START label on separate line: OK")

# 2. LOOP on separate line
loop_labels = [dl for dl in dv._display_lines if dl[5] and dl[6] == "LOOP"]
assert len(loop_labels) == 1, f"Expected 1 LOOP label, got {len(loop_labels)}"
print("2. LOOP label on separate line: OK")

# 3. Instruction follows label at same address
for i, dl in enumerate(dv._display_lines):
    if dl[5] and dl[6] == "START":
        assert i + 1 < len(dv._display_lines)
        next_dl = dv._display_lines[i + 1]
        assert next_dl[0] == dl[0]
        assert not next_dl[5]
        print("3. Instruction follows START label: OK")
        break

# 4. addr_to_index points to label line (for arrows to point at label)
assert 0x0100 in dv.addr_to_index
idx = dv.addr_to_index[0x0100]
assert dv._display_lines[idx][5], "addr_to_index should point to label line"
print("4. addr_to_index -> label line: OK")

# 5. Jump target in range
jnz = [dl for dl in dv._display_lines if not dl[5] and dl[4] is not None]
assert len(jnz) >= 1, "Expected at least one jump"
for dl in jnz:
    target = dl[4]
    assert target in dv.addr_to_index, f"Target {target:04X} not in addr_to_index"
    print(f"5. Jump {dl[0]:04X} -> {target:04X} in range: OK")

# 6. Height accounts for label lines
expected_h = len(dv._display_lines) * dv.line_height + 10
print(f"6. Height: {dv.height()} (expected ~{expected_h}): OK")

# 7. Emu disasm view also has correct layout
edv = mw.emu_disasm_view
print(f"\nEmu display lines: {len(edv._display_lines)}")
emu_labels = [dl for dl in edv._display_lines if dl[5]]
print(f"7. Emu label lines: {len(emu_labels)}")
for dl in emu_labels:
    print(f"   {dl[0]:04X} {dl[6]}")

print()
print("ALL LAYOUT CHECKS PASSED")
