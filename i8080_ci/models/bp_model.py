"""Breakpoints table model."""
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtGui import QColor
from ..i18n import LANGS

class BreakpointModel(QAbstractTableModel):
    """Модель для панели точек останова"""
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.lang = "en"
    
    def get_bp_list(self):
        """Отсортированный список адресов BP"""
        return sorted(self.emulator.breakpoints)
    
    def refresh(self):
        """Полный сброс модели для пересчёта строк"""
        self.beginResetModel()
        self.endResetModel()
    
    # QAbstractTableModel interface
    def rowCount(self, parent=None):
        return len(self.emulator.breakpoints)
    
    def columnCount(self, parent=None):
        return 4  # Адрес | Условие | Вкл | Срабатываний
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("bp_col_addr", "Address"),
                L.get("bp_col_cond", "Condition"),
                L.get("bp_col_enabled", "On"),
                L.get("bp_col_hits", "Hits"),
            ]
            return headers[section]
        return None
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        bps = self.get_bp_list()
        row, col = index.row(), index.column()
        if row >= len(bps):
            return None
        addr = bps[row]
        
        if role == Qt.DisplayRole:
            if col == 0:
                return f"0x{addr:04X}"
            elif col == 1:
                return self.emulator.get_bp_condition(addr) or "—"
            elif col == 2:
                return "✓" if self.emulator.bp_enabled.get(addr, True) else "✗"
            elif col == 3:
                return str(self.emulator.bp_hit_count.get(addr, 0))
        elif role == Qt.ForegroundRole:
            if not self.emulator.bp_enabled.get(addr, True):
                return QColor("#999999")
            if col == 1 and self.emulator.get_bp_condition(addr):
                return QColor("#0066cc")
        elif role == Qt.TextAlignmentRole:
            if col in [0, 2, 3]:
                return Qt.AlignCenter
        return None


