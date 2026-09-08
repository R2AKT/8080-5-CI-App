"""Execution trace table model."""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from ..i18n import LANGS
from ..disassembler import JUMP_OPCODES

class TraceModel(QAbstractTableModel):
    """Виртуальная модель трассировки с поддержкой фильтра"""
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.disassembler = None
        self._filter = None
        self._filtered_indices = None  # Индексы отфильтрованных записей
        self.lang = "en"
    
    def set_filter(self, filter_dict):
        """Установить фильтр и обновить модель"""
        self._filter = filter_dict
        self.refresh()
    
    def refresh(self):
        """Уведомить Qt об изменении данных"""
        self._apply_filter()
        self.beginResetModel()
        self.endResetModel()
    
    def _apply_filter(self):
        """Применить фильтр и сохранить индексы подходящих записей"""
        if self._filter is None:
            self._filtered_indices = None
            return
        buf = self.emulator.trace_buffer
        self._filtered_indices = []
        f = self._filter
        if f["type"] == "addr":
            for i, rec in enumerate(buf):
                if rec["pc"] == f["value"]:
                    self._filtered_indices.append(i)
        elif f["type"] == "reg":
            reg = f["reg"]
            op = f.get("op", "==")  # ← По умолчанию равенство
            value = f["value"]
            flag_map = {'S': 0, 'Z': 1, 'AC': 2, 'P': 3, 'CY': 4}
            for i, rec in enumerate(buf):
                # Получаем значение регистра
                if reg == 'A': val = rec["A"]
                elif reg == 'B': val = rec["B"]
                elif reg == 'C': val = rec["C"]
                elif reg == 'D': val = rec["D"]
                elif reg == 'E': val = rec["E"]
                elif reg == 'H': val = rec["H"]
                elif reg == 'L': val = rec["L"]
                elif reg == 'BC': val = rec["BC"]
                elif reg == 'DE': val = rec["DE"]
                elif reg == 'HL': val = rec["HL"]
                elif reg == 'SP': val = rec["SP"]
                elif reg == 'PC': val = rec["pc"]
                elif reg in flag_map:
                    val = rec["flags"][flag_map[reg]]
                else:
                    continue
                
                # Сравниваем с учётом оператора
                if op == '==' and val == value:
                    self._filtered_indices.append(i)
                elif op == '!=' and val != value:
                    self._filtered_indices.append(i)
                elif op == '>' and val > value:
                    self._filtered_indices.append(i)
                elif op == '<' and val < value:
                    self._filtered_indices.append(i)
                elif op == '>=' and val >= value:
                    self._filtered_indices.append(i)
                elif op == '<=' and val <= value:
                    self._filtered_indices.append(i)
        elif f["type"] == "mnemonic":
            for i, rec in enumerate(buf):
                mnemonic = self._get_mnemonic(rec)
                if f["value"] in mnemonic.upper():
                    self._filtered_indices.append(i)
    
    def _get_record(self, row):
        """Получить запись по строке (с учётом фильтра)"""
        buf = self.emulator.trace_buffer
        if self._filtered_indices is not None:
            if row >= len(self._filtered_indices):
                return None
            idx = self._filtered_indices[row]
            if idx >= len(buf):
                return None
            return buf[idx]
        else:
            if row >= len(buf):
                return None
            return buf[row]
    
    def rowCount(self, parent=None):
        if self._filtered_indices is not None:
            return len(self._filtered_indices)
        return self.emulator.trace_count()
    
    def columnCount(self, parent=None):
        return 10
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("trace_col_seq", "#"),
                L.get("trace_col_pc", "PC"),
                L.get("trace_col_bytes", "Bytes"),
                L.get("trace_col_mnem", "Mnemonic"),
                "A", "BC", "DE", "HL", "SP",
                L.get("trace_col_flags", "Flags")
            ]
            return headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._get_record(index.row())
        if rec is None:
            return None
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == 0:
                return str(rec["seq"])
            elif col == 1:
                return f"{rec['pc']:04X}"
            elif col == 2:
                return " ".join(f"{b:02X}" for b in rec["bytes"])
            elif col == 3:
                return self._get_mnemonic(rec)
            elif col == 4:
                return f"{rec['A']:02X}"
            elif col == 5:
                return f"{rec['BC']:04X}"
            elif col == 6:
                return f"{rec['DE']:04X}"
            elif col == 7:
                return f"{rec['HL']:04X}"
            elif col == 8:
                return f"{rec['SP']:04X}"
            elif col == 9:
                f = rec["flags"]
                return (f"{'S' if f[0] else '-'}{'Z' if f[1] else '-'}"
                        f"{'A' if f[2] else '-'}{'P' if f[3] else '-'}"
                        f"{'C' if f[4] else '-'}")
        elif role == Qt.TextAlignmentRole:
            if col in [0, 1, 4, 5, 6, 7, 8]:
                return Qt.AlignCenter
        elif role == Qt.BackgroundRole:
            # === Подсветка переходов (JMP/CALL/RET/RST) ===
            if rec["opcode"] in JUMP_OPCODES:
                return QColor("#FFE0B2")  # Оранжевый фон для переходов
            # === Подсветка изменённых регистров ===
            prev_rec = self._get_record(index.row() - 1)
            if prev_rec is not None:
                if col == 4 and rec["A"] != prev_rec["A"]:
                    return QColor("#FFCDD2")  # Красный фон
                elif col == 5 and rec["BC"] != prev_rec["BC"]:
                    return QColor("#FFCDD2")
                elif col == 6 and rec["DE"] != prev_rec["DE"]:
                    return QColor("#FFCDD2")
                elif col == 7 and rec["HL"] != prev_rec["HL"]:
                    return QColor("#FFCDD2")
                elif col == 8 and rec["SP"] != prev_rec["SP"]:
                    return QColor("#FFCDD2")
                elif col == 9 and rec["flags"] != prev_rec["flags"]:
                    return QColor("#FFCDD2")
        return None
    
    def _get_mnemonic(self, rec):
        """Определить мнемонику для записи"""
        if not self.disassembler:
            return f"DB {rec['opcode']:02X}h"
        temp_mem = {rec["pc"] + i: b for i, b in enumerate(rec["bytes"])}
        lines = self.disassembler.disassemble(temp_mem, rec["pc"], len(rec["bytes"]))
        if lines:
            return lines[0][2]
        return f"DB {rec['opcode']:02X}h"

# ==================== ГЛАВНОЕ ОКНО ====================

