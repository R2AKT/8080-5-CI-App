import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
# Find lines about case, upper, symbols storage, exports
for i, l in enumerate(lines):
    if re.search(r'\.upper\(\)|case|_sym_key|self\.symbols\[|self\.exports|_exports|case_sensitive', l, re.I):
        print(f"{i+1:5d}: {l}")
