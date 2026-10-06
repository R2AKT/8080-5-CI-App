import sys
sys.stdout.reconfigure(encoding='utf-8')

# Verify the fixes
path = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\assembler_widget.py'
f = open(path, 'r', encoding='utf-8')
c = f.read()
f.close()

# Check fix 2 - fold marker
idx = c.find('m_collapsed')
print("=== FOLD MARKER LINE ===")
print(c[idx:idx+200])
print()

# Check fix 1 - retranslate method
idx2 = c.find('def retranslate')
print("=== RETRANSLATE METHOD ===")
print(c[idx2:idx2+500])
print()

# Syntax check
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX OK: assembler_widget.py")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")

path2 = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\main_window.py'
try:
    py_compile.compile(path2, doraise=True)
    print("SYNTAX OK: main_window.py")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")

# Check main_window retranslate call
f2 = open(path2, 'r', encoding='utf-8')
mw = f2.read()
f2.close()
idx3 = mw.find('assembler_widget.retranslate')
print("\n=== MAIN WINDOW RETRANSLATE CALL ===")
print(mw[max(0,idx3-100):idx3+200])
