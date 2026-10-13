import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from assemble8080.assembler import Assembler

def t(src, label):
    asm = Assembler()
    r = asm.assemble(src)
    if r.success:
        print(f"  OK   {label:14s} -> {r.binary.hex()}")
    else:
        print(f"  ERR  {label:14s} -> {r.errors[0] if r.errors else '?'}")

print("INR/DCR register set (expect B..M,A valid; SP invalid):")
for reg in ['B','C','D','E','H','L','M','A','SP']:
    t(f"ORG 0100H\nINR {reg}\nRET", f"INR {reg}")
    t(f"ORG 0100H\nDCR {reg}\nRET", f"DCR {reg}")

print("\nExpected: INR B=04 C=0C D=14 E=1C H=24 L=2C M=34 A=3C")
print("Expected: DCR B=05 C=0D D=15 E=1D H=25 L=2D M=35 A=3D")
print("Expected: INR SP / DCR SP -> ERR (no such instruction)")
