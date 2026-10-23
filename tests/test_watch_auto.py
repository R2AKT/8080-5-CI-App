# -*- coding: utf-8 -*-
"""Тест автозагрузки watch-list из map-файла + сортировка + preset-исключение auto."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import assemble
from assemble8080.objfile import obj_from_asm_result
from assemble8080.linker import link
from assemble8080.mapfile import parse_map

from PySide6.QtCore import Qt
from i8080_ci.models.watch_model import WatchModel

SRC = """\
ORG 0x0100
START:   JMP LOOP
LOOP:    NOP
         RET
MYS:     DB 0x42
MYSUM:   DW 0x1234
"""

ok = True
def check(name, cond, info=""):
    global ok
    print(("\u2705 " if cond else "\u274c ") + name + ((" - " + info) if (info and not cond) else ""))
    ok = ok and bool(cond)

r = assemble(SRC)
obj = obj_from_asm_result(r)
res = link([obj], origin=obj.org)
mf = parse_map(res.map_text)

types = {e.name.upper(): e.entry_type for e in mf.entries}
check("map: MYS -> DATA", types.get("MYS") == "DATA", str(types))
check("map: MYSUM -> DATA", types.get("MYSUM") == "DATA", str(types))
check("map: START -> CODE", types.get("START") == "CODE", str(types))
check("map: LOOP -> CODE", types.get("LOOP") == "CODE", str(types))
sizes = {e.name.upper(): e.size for e in mf.entries}
check("map: MYS size 1", sizes.get("MYS") == 1, str(sizes))
check("map: MYSUM size 2", sizes.get("MYSUM") == 2, str(sizes))

class FakeEmu:
    def __init__(self):
        self.mem = {0x0105: 0x42, 0x0106: 0x34, 0x0107: 0x12}
    def read_byte(self, a): return self.mem.get(a, 0)
    def read_word(self, a): return self.mem.get(a, 0) | (self.mem.get(a + 1, 0) << 8)
    def get_reg(self, *a): return 0
    def get_reg_pair(self, *a): return 0
    sp = 0; pc = 0x0100
    flag_s = flag_z = flag_ac = flag_p = flag_cy = 0

m = WatchModel(FakeEmu())
n = m.set_auto_watches_from_map(mf)
check("auto count == 2", n == 2, str(n))
auto = [it for it in m.items if it["auto"]]
check("2 auto items", len(auto) == 2, str(m.items))
by_name = {it["name"].upper(): it for it in auto}
check("MYS byte @0x0105", by_name.get("MYS", {}).get("type") == "mem_byte" and by_name.get("MYS", {}).get("target") == 0x0105)
check("MYSUM word @0x0106", by_name.get("MYSUM", {}).get("type") == "mem_word" and by_name.get("MYSUM", {}).get("target") == 0x0106)
check("no CODE labels in watch", not any(x in by_name for x in ("START", "LOOP")))
check("value MYSUM == 0x1234", m.get_value(by_name["MYSUM"]) == 0x1234, hex(m.get_value(by_name["MYSUM"])))

m.add_watch("manual", WatchModel.TYPE_REG, "PC")
n2 = m.set_auto_watches_from_map(mf)
check("re-run: auto regenerated, manual kept", n2 == 2 and len(m.items) == 3, f"n2={n2} total={len(m.items)}")

pf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_watch_preset.json")
m.save_preset(pf)
import json
data = json.load(open(pf, encoding="utf-8"))
check("preset excludes auto", len(data["watches"]) == 1 and data["watches"][0]["name"] == "manual", str(data))
m2 = WatchModel(FakeEmu())
m2.load_preset(pf)
check("load_preset: manual added, no auto", any(it["name"] == "manual" and not it["auto"] for it in m2.items) and not any(it.get("auto") for it in m2.items))
os.remove(pf)

m.sort(0, Qt.AscendingOrder)
names = [it["name"] for it in m.items]
check("sort by name asc", names == sorted(names, key=str.lower), str(names))
m.sort(0, Qt.DescendingOrder)
check("sort by name desc", [it["name"] for it in m.items] == list(reversed(names)))
m.sort(1, Qt.AscendingOrder)
targets = [it["target"] for it in m.items if it["type"] != "reg"]
check("sort by addr asc", targets == [0x0105, 0x0106], str(targets))

print("RESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
