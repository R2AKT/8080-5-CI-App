"""Precise diagnostic: separate real bugs from test errors."""
import sys
sys.path.insert(0, '.')
from assemble8080.assembler import Assembler

print("=== 1. ALU: one-operand vs two-operand form ===")
a = Assembler()
# One-operand form (standard 8080)
for src, expected in [("add b", "80"), ("add c", "81"), ("add d", "82"),
                       ("sub b", "90"), ("ana b", "a0"), ("ora b", "b0"),
                       ("cmp b", "b8"), ("xra b", "a8"), ("sbb b", "98"),
                       ("adc b", "88")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 2. ALU: two-operand form ===")
for src, expected in [("add a,b", "80"), ("add a,c", "81"), ("sub a,b", "90"),
                       ("ana a,b", "a0"), ("ora a,b", "b0"), ("cmp a,b", "b8")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 3. INR/DCR all registers ===")
# INR: B=04 C=0C D=14 E=1C H=24 L=2C SP=34 A=3C M=3E
# DCR: B=05 C=0D D=15 E=1D H=25 L=2D SP=35 A=3D M=3F
for src, expected in [("inr b","04"),("inr c","0c"),("inr d","14"),("inr e","1c"),
                       ("inr h","24"),("inr l","2c"),("inr sp","34"),("inr a","3c"),("inr m","3e"),
                       ("dcr b","05"),("dcr c","0d"),("dcr d","15"),("dcr e","1d"),
                       ("dcr h","25"),("dcr l","2d"),("dcr sp","35"),("dcr a","3d"),("dcr m","3f")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 4. Conditional jumps ===")
# JC=C2 JNC=D2 JZ=C8 JNZ=D8 JM=DA JP=DB CM=CA CP=DA? 
# Actually: C0=RNZ C2=JC C8=JZ CA=CM D0=RZ D2=JNC D8=JNZ DA=JM DB=JP
for src, expected in [("jc 0x1234","c23412"),("jnc 0x1234","d23412"),
                       ("jz 0x1234","c83412"),("jnz 0x1234","d83412"),
                       ("jm 0x1234","da3412"),("jp 0x1234","db3412"),
                       ("cm 0x1234","ca3412"),("cp 0x1234","da3412")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 5. RAL/RAR/RLC/RRC/DAA/CMA/CMC/STC ===")
for src, expected in [("rlc","07"),("rrc","0f"),("ral","67"),("rar","6f"),
                       ("daa","27"),("cma","2f"),("cmc","3f"),("stc","37")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 6. PUSH/POP PSW variants ===")
for src, expected in [("push ps","f5"),("push psw","f5"),("push f","f5"),
                       ("pop ps","f1"),("pop psw","f1"),("pop f","f1")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 7. 8085 mnemonics (cpu_type=8085) ===")
a85 = Assembler()
a85.cpu_type = '8085'
for src, expected in [("rim","20"),("sim","30"),("dsub","18"),("arhl","28"),
                       ("adi 5","c605"),("aci 5","ce05"),("sbi 5","de05"),
                       ("ani 5","e605"),("xri 5","ee05"),("ori 5","f605"),
                       ("cpi 5","fe05")]:
    r = a85.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 8. 8085 in 8080 mode (should fail) ===")
a80 = Assembler()
r = a80.assemble('org 0x100\nrim\nret')
print(f"  rim in 8080 mode: errors={len(r.errors)} (expected >0)")

print("\n=== 9. DAD/INX/DCX register pairs ===")
for src, expected in [("dad b","09"),("dad d","19"),("dad h","29"),("dad sp","39"),
                       ("inx b","03"),("inx d","13"),("inx h","23"),("inx sp","33"),
                       ("dcx b","0b"),("dcx d","1b"),("dcx h","2b"),("dcx sp","3b")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\n=== 10. PCHL/SPHL/XTHL/XCHG ===")
for src, expected in [("pchl","e9"),("sphl","f9"),("xthl","eb"),("xchg","eb")]:
    r = a.assemble(f'org 0x100\n{src}\nret')
    actual = r.binary.hex()[:-2] if r.binary else 'ERR:' + str(r.errors)
    status = "OK" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{src}' -> {actual} (expected {expected})")

print("\nDone.")
