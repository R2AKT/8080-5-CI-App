"""Test: ORI disassembly + EQU substitution."""
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

# Test 1: ORI should show as ORI, not ORA
source = """
    ORG 0100H
COUNT EQU 5
MAXV  EQU 255
START:  ORI 05H
        CPI COUNT
        ANA MAXV
        XRA 00H
        ADD 01H
        RET
"""

result = api.asm_assemble(source=source, load_to_memory=True)
app.processEvents()

# Set correct disasm range
mw.disasm_start.setText("0100")
mw.disasm_len.setText("0020")
mw.run_disasm()
app.processEvents()

dv = mw.disasm_view
print("=== Disassembly output ===")
for i, (addr, size, asm, undoc, target) in enumerate(dv.lines):
    print(f"  {addr:04X}  {asm}")
print()

# Check ORI
ori_lines = [l for l in dv.lines if 'ORI' in l[2]]
ora_lines = [l for l in dv.lines if 'ORA' in l[2]]
print(f"ORI lines: {len(ori_lines)} (expected 1)")
print(f"ORA lines: {len(ora_lines)} (expected 0)")

assert len(ori_lines) == 1, f"Expected 1 ORI, got {len(ori_lines)}"
assert len(ora_lines) == 0, f"Expected 0 ORA, got {len(ora_lines)}"
print("1. ORI correctly decoded: OK")

# Check EQU substitution
cpi_lines = [l for l in dv.lines if 'CPI' in l[2]]
print(f"\nCPI line: {cpi_lines[0][2] if cpi_lines else 'NOT FOUND'}")
assert 'COUNT' in cpi_lines[0][2], f"EQU name COUNT not substituted: {cpi_lines[0][2]}"
print("2. CPI COUNT (EQU substitution): OK")

ani_lines = [l for l in dv.lines if 'ANI' in l[2]]
print(f"ANI line: {ani_lines[0][2] if ani_lines else 'NOT FOUND'}")
assert 'MAXV' in ani_lines[0][2], f"EQU name MAXV not substituted: {ani_lines[0][2]}"
print("3. ANI MAXV (EQU substitution): OK")

# Check that non-EQU values are NOT substituted
xri_lines = [l for l in dv.lines if 'XRI' in l[2]]
print(f"XRI line: {xri_lines[0][2] if xri_lines else 'NOT FOUND'}")
assert '00h' in xri_lines[0][2], f"XRI should show hex value: {xri_lines[0][2]}"
print("4. XRI 00h (no EQU, shows hex): OK")

adi_lines = [l for l in dv.lines if 'ADI' in l[2]]
print(f"ADI line: {adi_lines[0][2] if adi_lines else 'NOT FOUND'}")
assert '01h' in adi_lines[0][2], f"ADI should show hex value: {adi_lines[0][2]}"
print("5. ADI 01h (no EQU, shows hex): OK")

# Check emu disasm view too
edv = mw.emu_disasm_view
emu_ori = [l for l in edv.lines if 'ORI' in l[2]]
print(f"\nEmu ORI lines: {len(emu_ori)}")
assert len(emu_ori) == 1, "Emu should also show ORI"
print("6. Emu ORI correct: OK")

print()
print("ALL CHECKS PASSED")
