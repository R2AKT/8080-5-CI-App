import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
# print lines 1786-1830
for i in range(1785, min(1835, len(lines))):
    print(f"{i+1:5d}: {lines[i]}")
