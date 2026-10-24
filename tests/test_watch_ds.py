# -*- coding: utf-8 -*-
"""DS-блоки (резервирование памяти) — это честные переменные и должны попасть в авто watch-list."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import Assembler
from assemble8080.mapfile import generate_map, parse_map
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from i8080_ci.models.watch_model import WatchModel

ok = True
def check(name, cond, info=""):
    global ok
    mark = "\u2705" if cond else "\u274c"
    print(f"{mark} {name}" + ("" if cond else f"  <- {info}"))
    ok = ok and bool(cond)

class DummyEmu:
    def read_mem(self, a): return 0
    def read_mem16(self, a): return 0

def auto_watches(src, tag):
    r = Assembler().assemble(src, tag + ".asm")
    check(f"[{tag}] ассемблировалось", r.success, [str(e) for e in r.errors])
    mf = parse_map(generate_map(r, source_name=tag + ".asm"))
    m = WatchModel(DummyEmu())
    m.set_auto_watches_from_map(mf)
    return {it["name"]: it for it in m.items}

# 1) DS единственный блок
w = auto_watches("ORG 0x0100\nBUF: DS 16", "only")
check("DS-only в watch", "BUF" in w, list(w))

# 2) DS в середине (между кодом)
w = auto_watches("ORG 0x0100\nSTART: RET\nBUF: DS 10\nEND: RET", "mid")
check("DS mid в watch", "BUF" in w, list(w))
check("DS mid не путается с кодом", "START" not in w and "END" not in w, list(w))

# 3) DS в конце (нет следующей метки)
w = auto_watches("ORG 0x0100\nSTART: RET\nBUF: DS 5", "tail")
check("DS tail в watch", "BUF" in w, list(w))

# 4) DS с fill-значением
w = auto_watches("ORG 0x0100\nSTART: RET\nBUF: DS 8, 0x5A", "fill")
check("DS fill в watch", "BUF" in w, list(w))

# 5) размерность: DS>1 -> word, DS 1 -> byte
w = auto_watches("ORG 0x0100\nBIG: DS 4\nONE: DS 1\nEND: RET", "size")
check("DS>1 => word", w.get("BIG", {}).get("type") == WatchModel.TYPE_MEM_WORD, w.get("BIG"))
check("DS 1 => byte", w.get("ONE", {}).get("type") == WatchModel.TYPE_MEM_BYTE, w.get("ONE"))

# 6) адрес корректен (смещение от ORIGIN)
w = auto_watches("ORG 0x0100\nSTART: RET\nBUF: DS 4", "addr")
check("DS адрес = ORIGIN+1", w.get("BUF", {}).get("target") == 0x0101, w.get("BUF"))

print("RESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
