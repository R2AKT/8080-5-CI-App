# -*- coding: utf-8 -*-
"""GUI-тест: загрузка меньшего образа поверх большего — хвост исчезает (не 0xFF)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = True
def check(name, cond, info=""):
    global ok
    print(("\u2705 " if cond else "\u274c ") + name + ((" - " + str(info)) if (info and not cond) else ""))
    ok = ok and bool(cond)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from i8080_ci.main_window import MainWindow
from i8080_ci.assembler_widget import AssemblerWidget

mw = MainWindow()
w = AssemblerWidget(mw)
w.main_window = mw

ORIGIN = 0x0100
big = bytes(range(0x10, 0x20))          # 16 байт
small = bytes([0x76, 0xC9])             # 2 байта

# 1) Загружаем БОЛЬШОЙ образ
w._load_to_memory(big, ORIGIN)
check("Большой образ загружен", max(mw.mem_data.keys()) == ORIGIN + 15, max(mw.mem_data.keys()))
check("hex_model.mem — тот же словарь", mw.hex_model.mem is mw.mem_data)

# 2) Загружаем МЕНЬШИЙ образ по тому же origin
w._load_to_memory(small, ORIGIN)
tail = [a for a in range(ORIGIN + 2, ORIGIN + 16) if a in mw.mem_data]
check("Хвост удалён из mem_data", not tail, tail)
check("Хвост удалён из hex_model.mem", not any(a in mw.hex_model.mem for a in range(ORIGIN + 2, ORIGIN + 16)))
check("hex max_addr = конец нового образа", mw.hex_model.max_addr == ORIGIN + 1, hex(mw.hex_model.max_addr))
check("Новый образ на месте", mw.mem_data.get(ORIGIN) == 0x76 and mw.mem_data.get(ORIGIN + 1) == 0xC9)

# 3) Повторная загрузка того же размера — ничего не ломается
w._load_to_memory(small, ORIGIN)
check("Повторная загрузка", mw.mem_data.get(ORIGIN) == 0x76 and mw.hex_model.max_addr == ORIGIN + 1)

# 4) Загрузка БОЛЬШЕГО после МЕНЬШЕГО — расширение работает
w._load_to_memory(big, ORIGIN)
check("Расширение работает", max(mw.mem_data.keys()) == ORIGIN + 15)

print("RESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
