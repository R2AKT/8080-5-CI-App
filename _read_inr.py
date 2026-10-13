import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
for i, l in enumerate(lines):
    if re.search(r'INR|DCR|0x04|0x05|reg_code|_reg_code|SP.*8|6\s*\*\s*8', l):
        print(f"{i+1:5d}: {l}")
