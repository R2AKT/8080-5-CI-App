import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from assemble8080.assembler import Assembler

def t(src, label, expect=None):
    asm = Assembler()
    r = asm.assemble(src)
    if r.success:
        ok = "" if expect is None else ("  OK" if r.binary.hex()==expect else f"  MISMATCH expect {expect}")
        print(f"  {label:22s} -> {r.binary.hex()}{ok}")
    else:
        print(f"  {label:22s} -> ERR {r.errors[0] if r.errors else '?'}")

print("ALU two-operand (ASxxxx style 'op reg, #imm'):")
t("ORG 0100H\ncmp a, #5\nret", "cmp a, #5", "fe05c9")
t("ORG 0100H\nadd b, #3\nret", "add b, #3", "c603c9")
t("ORG 0100H\nsub d, #9\nret", "sub d, #9", "d609c9")
t("ORG 0100H\nora e, #1\nret", "ora e, #1", "f601c9")

print("\nPUSH/POP PSW/SP aliases:")
t("ORG 0100H\npush psw\nret", "push psw", "f5c9")
t("ORG 0100H\npush sp\nret", "push sp", "f5c9")
t("ORG 0100H\npop psw\nret", "pop psw", "f1c9")
t("ORG 0100H\npop sp\nret", "pop sp", "f1c9")
t("ORG 0100H\npush bc\nret", "push bc", "c5c9")
t("ORG 0100H\npush de\nret", "push de", "d5c9")
t("ORG 0100H\npush hl\nret", "push hl", "e5c9")
