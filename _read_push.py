import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
for i, l in enumerate(lines):
    if re.search(r"'PUSH'|'POP'|PUSH|POP", l) and 'push' not in l.lower()[:0]:
        if re.search(r"PUSH|POP", l):
            print(f"{i+1:5d}: {l}")
