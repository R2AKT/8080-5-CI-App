import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
for i, l in enumerate(lines):
    if re.search(r'CPI|ALU_IMM|ALUS_IMM|ORI|0xFE|0xF6|CMP', l):
        print(f"{i+1:5d}: {l}")
