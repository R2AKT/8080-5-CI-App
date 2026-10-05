import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from i8080_ci.main_window import MainWindow
from i8080_ci.automation import AutomationAPI
from assemble8080.mapfile import parse_map

mw = MainWindow()
mw.show()
app.processEvents()
api = AutomationAPI(mw)

# Source with EQU constants and labels
source = """
    ORG 0100H
COUNT EQU 10
SIZE  EQU 255
START:  LDA 2000H
        STA 2001H
LOOP:   INR B
        CPI COUNT
        JNZ LOOP
        RET
"""

result = api.asm_assemble(source=source, load_to_memory=True)
app.processEvents()

print("=== Map text ===")
print(result.map_text)
print()

# Parse the map and check that EQU symbols are NOT in it
mf = parse_map(result.map_text)
print("=== Map entries ===")
for e in mf.entries:
    print(f"  {e.address:04X}  {e.name}")
print()

# Check: COUNT and SIZE should NOT be in the map
names = [e.name for e in mf.entries]
print(f"COUNT in map: {'COUNT' in names} (should be False)")
print(f"SIZE in map: {'SIZE' in names} (should be False)")
print(f"START in map: {'START' in names} (should be True)")
print(f"LOOP in map: {'LOOP' in names} (should be True)")
print()

# Check equ_symbols tracking
print(f"equ_symbols: {result.equ_symbols}")

# Verify assertions
assert 'COUNT' not in names, "COUNT (EQU) should not be in map"
assert 'SIZE' not in names, "SIZE (EQU) should not be in map"
assert 'START' in names, "START (label) should be in map"
assert 'LOOP' in names, "LOOP (label) should be in map"
print()
print("ALL EQU FILTER CHECKS PASSED")
