import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
s = open('assemble8080/assembler.py', encoding='utf-8').read()
lines = s.splitlines()
# Find REGISTERS and REG_PAIRS definitions
for i, l in enumerate(lines):
    if re.search(r'^REGISTERS|^REG_PAIRS|^REG_PAIRS_PSW|REGISTERS\s*=|REG_PAIRS\s*=', l):
        # print this and next ~12 lines
        for j in range(i, min(i+14, len(lines))):
            print(f"{j+1:5d}: {lines[j]}")
        print("...")
