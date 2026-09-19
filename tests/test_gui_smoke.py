# -*- coding: utf-8 -*-
"""Headless smoke test: GUI imports + AutomationAPI assembler methods."""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1) Импорт всех GUI-модулей
import i8080_ci.main_window  # noqa
import i8080_ci.assembler_widget  # noqa
import i8080_ci.automation  # noqa
import i8080_ci.bus_worker  # noqa
import i8080_ci.disassembler  # noqa
import i8080_ci.intelhex  # noqa
import i8080_ci.slip  # noqa
import i8080_ci.models.bp_model  # noqa
import i8080_ci.models.hex_model  # noqa
import i8080_ci.models.trace_model  # noqa
import i8080_ci.models.watch_model  # noqa
import i8080_ci.views.disasm_view  # noqa
import i8080_ci.views.hex_view  # noqa
import i8080_ci.views.search  # noqa
import ui.device_manager  # noqa
import ui.device_window  # noqa
import ui.display_widgets  # noqa
import ui.gpio_widget  # noqa
import ui.keyboard_widget  # noqa
import ui.serial_terminal  # noqa
import ui.cube3d_widget  # noqa
print("✅ Импорт всех GUI-модулей")

# 2) Создание главного окна (offscreen)
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
from i8080_ci.main_window import MainWindow
mw = MainWindow()
print("✅ MainWindow создан")

# 3) Виджет ассемблера существует
assert hasattr(mw, 'assembler_widget') and mw.assembler_widget is not None, \
    "Виджет ассемблера не создан"
print("✅ Виджет ассемблера создан")

# 4) AutomationAPI: методы ассемблера
from i8080_ci.automation import AutomationAPI
api = AutomationAPI(mw)
for m in ('asm_get_source', 'asm_set_source', 'asm_load_file',
          'asm_assemble', 'asm_get_binary', 'asm_get_symbols'):
    assert callable(getattr(api, m, None)), f"Нет метода {m}"
print("✅ AutomationAPI: методы asm_* присутствуют")

# 5) Функциональный тест: ассемблирование через API
src = "ORG 0100H\nSTART: MVI A, 0x55\nOUT 01H\nJMP START\n"
api.asm_set_source(src)
res = api.asm_assemble()
assert not res.errors, f"Ошибки: {res.errors}"
assert len(res.binary) == 7, f"Ожидалось 7 байт, получено {len(res.binary)}"
assert res.binary == bytes.fromhex('3E55D301C30001'), f"Неверный код: {res.binary.hex()}"
b = api.asm_get_binary()
assert b == res.binary
syms = api.asm_get_symbols()
assert syms.get('START') == 0x0100, f"START = {syms.get('START')}"
print(f"✅ asm_assemble: {len(res.binary)} байт, START=0x{syms['START']:04X}")

# 6) asm_load_file
test_asm = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'ASM_FOR_TEST', 'macros.asm')
api.asm_load_file(test_asm)
res2 = api.asm_assemble()
assert not res2.errors, f"Ошибки: {res2.errors}"
print(f"✅ asm_load_file + asm_assemble: {len(res2.binary)} байт")

# 7) run_script namespace содержит asm_*
import inspect
code = inspect.getsource(mw.run_script)
for name in ('asm_get_source', 'asm_set_source', 'asm_load_file',
             'asm_assemble', 'asm_get_binary', 'asm_get_symbols'):
    assert name in code, f"run_script: нет {name}"
print("✅ run_script: namespace содержит asm_*")

print("\nВСЕ SMOKE-ТЕСТЫ ПРОЙДЕНЫ")
