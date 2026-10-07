# -*- coding: utf-8 -*-
"""
HeadlessHost — «утка» под MainWindow для MCP-сервера без GUI.

Предоставляет ровно тот подмножество интерфейса MainWindow, которое
используют MCPServerManager (mcp_server.py) и AutomationAPI (automation.py):

  * ядро (реальные объекты): emulator, disassembler, mem_data, system, memory_bus
  * GUI no-op: log, safe_call, sync_breakpoints, update_emulator_ui,
    update_emu_disasm_view, update_range_label, auto_disasm
  * GUI-заглушки: hex_model, disasm_start/len, disasm_view, tabs, tab_disasm,
    auto_disasm_check
  * аппаратка (не подключена): is_connected, bus_active, send_command,
    sync_send_and_recv, max_block_size
  * трассировка: _get_trace_mnemonic, _export_trace_csv/json/txt

Никаких виджетов PySide6 не создаётся. QObject (I8080Emulator) работает
headless — сигналы не требуют QApplication. Для полной изоляции от GUI
запускайте процесс с QT_QPA_PLATFORM=offscreen (см. mcp_headless.py).

Один экземпляр, без параллельных сессий.
"""
from __future__ import annotations

import os
import sys
import json
import csv

# --- Гарантируем, что корень проекта в sys.path ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from i8080_emulator import I8080Emulator
from i8080_ci.disassembler import I8080Disassembler
from i8080_ci.automation import AutomationAPI
from modules.system import ComputerSystem
from modules.memory import RAMRegion
from modules.memory.memory_bus import ROMRegion


# =============================================================
# GUI-заглушки (duck-typing под Qt-виджеты)
# =============================================================
class _NoOpLineEdit:
    """Заглушка QLineEdit (disasm_start / disasm_len)."""
    def setText(self, text):  # noqa: N802
        pass
    def text(self):
        return ""


class _NoOpDisasmView:
    """Заглушка DisasmView."""
    def set_lines(self, lines):
        pass
    def set_symbols(self, symbols):
        pass
    def set_breakpoints(self, bps):
        pass
    def set_bp_conditions(self, conds):
        pass
    def update(self):
        pass


class _NoOpTabs:
    """Заглушка QTabWidget."""
    def setCurrentWidget(self, w):
        pass


class _NoOpHexModel:
    """Заглушка HexModel (QAbstractItemModel)."""
    class _Signal:
        def emit(self, *a, **k):
            pass
    layoutChanged = _Signal()

    def update_data(self, data):
        pass


class _NoOpCheck:
    """Заглушка QCheckBox."""
    def isChecked(self):  # noqa: N802
        return False


# =============================================================
# HeadlessHost
# =============================================================
class HeadlessHost:
    """Duck-types подмножество MainWindow для MCP-сервера без GUI."""

    def __init__(self, project_root: str | None = None):
        self.project_root = project_root or _PROJECT_ROOT
        self._current_profile: str | None = None
        self.current_cpu: str = "i8080"

        # --- Ядро (реальные объекты) ---
        self.mem_data: dict = {}
        self.emulator = I8080Emulator(self.mem_data)
        self.disassembler = I8080Disassembler()
        self.emulator.disassembler = self.disassembler
        self.system = ComputerSystem()
        self.memory_bus = None

        # --- GUI-заглушки ---
        self.disasm_start = _NoOpLineEdit()
        self.disasm_len = _NoOpLineEdit()
        self.disasm_view = _NoOpDisasmView()
        self.tabs = _NoOpTabs()
        self.tab_disasm = None
        self.hex_model = _NoOpHexModel()
        self.auto_disasm_check = _NoOpCheck()

        # --- Аппаратка (не подключена) ---
        self.is_connected = False
        self.bus_active = False
        self.max_block_size = 0x100

        # --- AutomationAPI (как в MainWindow.__init__, L216) ---
        # Важно: _get_api() в mcp_server.py проверяет hasattr(mw, '_automation_api').
        # Если атрибут отсутствует, он пытается `from i8080_CI import AutomationAPI`
        # (мёртвый путь). Поэтому ставим реальный экземпляр, как MainWindow.
        self._automation_api = AutomationAPI(self)

    # ---------------------------------------------------------
    # Логирование
    # ---------------------------------------------------------
    def log(self, msg) -> None:
        print(f"[i8080-ci] {msg}", flush=True)

    # ---------------------------------------------------------
    # GUI no-op
    # ---------------------------------------------------------
    def safe_call(self, func, *args, **kwargs) -> None:
        # GUI-потока нет — обновления интерфейса не выполняем
        pass

    def sync_breakpoints(self) -> None:
        pass

    def update_emulator_ui(self) -> None:
        pass

    def update_emu_disasm_view(self) -> None:
        pass

    def update_range_label(self) -> None:
        pass

    def auto_disasm(self) -> None:
        pass

    # ---------------------------------------------------------
    # Аппаратка (не подключена в headless-режиме)
    # ---------------------------------------------------------
    def send_command(self, *a, **k):
        raise RuntimeError("Device not connected (headless mode)")

    def sync_send_and_recv(self, *a, **k):
        raise RuntimeError("Device not connected (headless mode)")

    # ---------------------------------------------------------
    # Загрузка профиля (не-GUI часть MainWindow.load_profile)
    # ---------------------------------------------------------
    def load_profile(self, profile_name: str) -> str:
        """Загружает профиль системы. Возвращает тип CPU."""
        if getattr(self.emulator, "running", False):
            self.emulator.stop()

        # Загружаем профиль (внутри создаётся НОВАЯ шина)
        self.system.load_profile(profile_name)
        self._current_profile = profile_name

        # Проверка файлов образов
        errors = self.system.validate_profile_files()
        if errors:
            raise ValueError("Ошибки загрузки профиля:\n" + "\n".join(errors))

        # Тип процессора из профиля (по умолчанию i8080)
        self.current_cpu = self.system.config.cpu if self.system.config.cpu else "i8080"

        # Обновляем эмулятор
        self.emulator.cpu_type = self.current_cpu
        self.emulator.reset()

        # Обновляем дизассемблер (таблица опкодов зависит от CPU)
        self.disassembler.set_cpu_type(self.current_cpu)
        self.emulator.disassembler = self.disassembler

        # Переподключаем CPU к НОВОЙ шине
        self.system.connect_cpu(self.emulator)
        self.memory_bus = self.system.bus

        # Заменяем RAM из TOML на RAM с mem_data
        self.memory_bus.memory_regions = [
            r for r in self.memory_bus.memory_regions
            if not isinstance(r, RAMRegion)
        ]
        ram = RAMRegion(0x0000, 0xFFFF, data=self.mem_data, name="RAM")
        self.memory_bus.register_memory(ram)
        self.emulator.memory_bus = self.memory_bus

        # Копируем данные из ПЗУ в mem_data
        for region in self.memory_bus.memory_regions:
            if isinstance(region, ROMRegion) and hasattr(region, "data"):
                for addr, byte in region.data.items():
                    self.mem_data[addr] = byte

        # Сбрасываем состояние эмулятора
        self.emulator.halted = False
        self.emulator.wait_signal = False
        if self.mem_data:
            self.emulator.set_pc_to_memory_start()

        return self.current_cpu

    # ---------------------------------------------------------
    # Загрузка бинарного образа
    # ---------------------------------------------------------
    def load_binary(self, data: bytes, origin: int = 0x0000) -> int:
        """Загружает бинарный образ в память. Возвращает размер."""
        origin &= 0xFFFF
        for i, b in enumerate(data):
            self.mem_data[origin + i] = b & 0xFF
        self.emulator.set_pc(origin)
        return len(data)

    # ---------------------------------------------------------
    # Трассировка (для emu_trace_get / emu_trace_export)
    # ---------------------------------------------------------
    def _get_trace_mnemonic(self, rec) -> str:
        """Определяет мнемонику для записи трассировки."""
        try:
            temp_mem = {rec["pc"] + i: b for i, b in enumerate(rec["bytes"])}
            lines = self.disassembler.disassemble(temp_mem, rec["pc"], len(rec["bytes"]))
            if lines:
                return lines[0][2]  # asm
        except Exception:
            pass
        return f"DB {rec['opcode']:02X}h"

    def _export_trace_csv(self, path, records) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["seq", "pc", "bytes", "mnemonic", "A", "BC", "DE", "HL", "SP",
                 "flags", "IFF1", "IFF2", "I", "cycles", "cycles_total"]
            )
            for rec in records:
                flags = rec["flags"]
                flags_str = (
                    f"{'S' if flags[0] else '-'}{'Z' if flags[1] else '-'}"
                    f"{'A' if flags[2] else '-'}{'P' if flags[3] else '-'}"
                    f"{'C' if flags[4] else '-'}"
                )
                writer.writerow([
                    rec["seq"], f"{rec['pc']:04X}",
                    " ".join(f"{b:02X}" for b in rec["bytes"]),
                    self._get_trace_mnemonic(rec),
                    f"{rec['A']:02X}", f"{rec['BC']:04X}", f"{rec['DE']:04X}",
                    f"{rec['HL']:04X}", f"{rec['SP']:04X}", flags_str,
                    int(rec.get("IFF1", False)), int(rec.get("IFF2", False)),
                    f"{rec.get('I', 0):02X}", rec["cycles"], rec["cycles_total"],
                ])

    def _export_trace_json(self, path, records) -> None:
        out = []
        for rec in records:
            flags = rec["flags"]
            out.append({
                "seq": rec["seq"], "pc": f"{rec['pc']:04X}",
                "bytes": " ".join(f"{b:02X}" for b in rec["bytes"]),
                "mnemonic": self._get_trace_mnemonic(rec),
                "A": f"{rec['A']:02X}", "BC": f"{rec['BC']:04X}",
                "DE": f"{rec['DE']:04X}", "HL": f"{rec['HL']:04X}",
                "SP": f"{rec['SP']:04X}",
                "flags": {"S": flags[0], "Z": flags[1], "AC": flags[2],
                          "P": flags[3], "CY": flags[4]},
                "IFF1": rec.get("IFF1", False), "IFF2": rec.get("IFF2", False),
                "I": f"{rec.get('I', 0):02X}",
                "cycles": rec["cycles"], "cycles_total": rec["cycles_total"],
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    def _export_trace_txt(self, path, records) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                flags = rec["flags"]
                flags_str = (
                    f"S={flags[0]} Z={flags[1]} AC={flags[2]} "
                    f"P={flags[3]} CY={flags[4]}"
                )
                f.write(
                    f"{rec['seq']:6d}  {rec['pc']:04X}  "
                    f"{' '.join(f'{b:02X}' for b in rec['bytes']):<12}  "
                    f"{self._get_trace_mnemonic(rec):<16}  {flags_str}\n"
                )

    # ---------------------------------------------------------
    # Статус
    # ---------------------------------------------------------
    def get_status(self) -> dict:
        return {
            "profile": self._current_profile,
            "cpu": self.current_cpu,
            "pc": self.emulator.pc,
            "halted": self.emulator.halted,
            "mem_size": len(self.mem_data),
            "connected": self.is_connected,
        }
