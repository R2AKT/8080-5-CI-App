import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from assemble8080.assembler import Assembler
def t(src, label, expect=None):
    r = Assembler().assemble(src)
    if r.success:
        ok = "" if expect is None else ("  OK" if r.binary.hex()==expect else f"  MISMATCH expect {expect}")
        print(f"  {label:14s} -> {r.binary.hex()}{ok}")
    else:
        print(f"  {label:14s} -> ERR {r.errors[0] if r.errors else '?'}")
print("PUSH/POP single-letter convention:")
t("ORG 0100H\npush b\nret","push b","c5c9")
t("ORG 0100H\npush d\nret","push d","d5c9")
t("ORG 0100H\npush h\nret","push h","e5c9")
t("ORG 0100H\npush psw\nret","push psw","f5c9")
t("ORG 0100H\npop b\nret","pop b","c1c9")
t("ORG 0100H\npop psw\nret","pop psw","f1c9")
# show rpsw handler
s = open('assemble8080/assembler.py', encoding='utf-8').read().splitlines()
for i,l in enumerate(s):
    if "'rpsw'" in l or 'rpsw' in l:
        print(f"  [{i+1}] {l.strip()}")
