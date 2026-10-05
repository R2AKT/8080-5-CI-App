"""Test: auto-load map updates disasm range to actual binary size."""
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

# Set default disasm range (simulating user not changing it)
mw.disasm_start.setText("0100")
mw.disasm_len.setText("0064")  # 100 bytes default
print(f"Before: disasm_start={mw.disasm_start.text()}, disasm_len={mw.disasm_len.text()}")

# Assemble a program larger than 100 bytes
# 200 bytes of NOP + RET at the end
source_lines = ["    ORG 0100H"]
for i in range(49):
    source_lines.append("        NOP")
source_lines.append("        RET")
source = "\n".join(source_lines)

# Expected size: 50 bytes (49 NOP + 1 RET)
expected_size = 50
print(f"Expected binary size: {expected_size} bytes")

result = api.asm_assemble(source=source, load_to_memory=True)
app.processEvents()

# Check that disasm range was updated
actual_start = mw.disasm_start.text()
actual_len = mw.disasm_len.text()
print(f"After: disasm_start={actual_start}, disasm_len={actual_len}")

assert actual_start == "0100", f"Expected start 0100, got {actual_start}"
assert actual_len == f"{expected_size:04X}", f"Expected len {expected_size:04X}, got {actual_len}"
print(f"1. Disasm range updated to actual size: OK")

# Verify disassembler actually shows all instructions
mw.run_disasm()
app.processEvents()
dv = mw.disasm_view
lines = dv.lines
print(f"2. Disasm lines: {len(lines)} (expected {expected_size})")
assert len(lines) == expected_size, f"Expected {expected_size} lines, got {len(lines)}"
print(f"   All {len(lines)} instructions visible: OK")

# Test with a larger program (>100 bytes)
source_lines2 = ["    ORG 0200H"]
for i in range(150):
    source_lines2.append("        NOP")
source_lines2.append("        RET")
source2 = "\n".join(source_lines2)
expected_size2 = 151

result2 = api.asm_assemble(source=source2, load_to_memory=True)
app.processEvents()

actual_start2 = mw.disasm_start.text()
actual_len2 = mw.disasm_len.text()
print(f"\nLarge program: disasm_start={actual_start2}, disasm_len={actual_len2}")
assert actual_start2 == "0200", f"Expected start 0200, got {actual_start2}"
assert actual_len2 == f"{expected_size2:04X}", f"Expected len {expected_size2:04X}, got {actual_len2}"
print(f"3. Large program range updated: OK")

mw.run_disasm()
app.processEvents()
lines2 = mw.disasm_view.lines
print(f"4. Large program lines: {len(lines2)} (expected {expected_size2})")
assert len(lines2) == expected_size2, f"Expected {expected_size2} lines, got {len(lines2)}"
print(f"   All {len(lines2)} instructions visible: OK")

print()
print("ALL CHECKS PASSED")
