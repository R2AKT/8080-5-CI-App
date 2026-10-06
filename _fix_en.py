import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
base = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis'

# Fix EN i18n key - find asm_link in EN section
i18n_path = os.path.join(base, 'common', 'i18n.py')
f = open(i18n_path, 'r', encoding='utf-8')
i18n = f.read()
f.close()

# Find all occurrences of asm_link
for m in re.finditer(r'"asm_link"\s*:\s*"[^"]*"', i18n):
    print(f"  Found: {m.group()}")

# The EN section is the first one. Find asm_link in the first section (before "ru":)
ru_start = i18n.find('"ru":')
en_section = i18n[:ru_start]
# Find asm_link in EN section
m = re.search(r'("asm_link"\s*:\s*"[^"]*")', en_section)
if m:
    pos = m.end()
    # Check if asm_processor already exists in EN
    if '"asm_processor"' not in en_section:
        i18n = i18n[:pos] + ',\n        "asm_processor": "Processor:",' + i18n[pos:]
        print("Added EN asm_processor")
    else:
        print("EN asm_processor already exists")
else:
    print("WARNING: asm_link not found in EN section")

f = open(i18n_path, 'w', encoding='utf-8')
f.write(i18n)
f.close()

# Verify syntax
import py_compile
try:
    py_compile.compile(i18n_path, doraise=True)
    print("i18n.py syntax OK")
except py_compile.PyCompileError as e:
    print(f"i18n.py SYNTAX ERROR: {e}")

# Verify assembler_widget.py still compiles
try:
    py_compile.compile(os.path.join(base, 'i8080_ci', 'assembler_widget.py'), doraise=True)
    print("assembler_widget.py syntax OK")
except py_compile.PyCompileError as e:
    print(f"assembler_widget.py SYNTAX ERROR: {e}")

print("Done")
