"""Hex memory table model."""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QFont
from ..i18n import LANGS

class HexModel(QAbstractTableModel):
    dataEdited = Signal()
    
    def __init__(self, mem_dict=None):
        super().__init__()
        self.mem = mem_dict if mem_dict is not None else {}
        self.min_addr = 0
        self.max_addr = 0
        self.lang = "en"  # ← Добавлено для локализации заголовков
        self.update_range()

    def update_data(self, new_mem):
        self.mem.update(new_mem)
        self.update_range()
        self.layoutChanged.emit()

    def update_range(self):
        if self.mem:
            self.min_addr = min(self.mem.keys())
            self.max_addr = max(self.mem.keys())
            self.min_addr &= ~0x0F
        else:
            self.min_addr = 0; self.max_addr = 0

    def rowCount(self, parent=QModelIndex()):
        if not self.mem: return 0
        return ((self.max_addr - self.min_addr) >> 4) + 1

    def columnCount(self, parent=QModelIndex()):
        return 18

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Заголовки колонок"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return LANGS.get(self.lang, LANGS['en']).get('addr_column', 'Addr')
            elif 1 <= section <= 16:
                return f"{section - 1:X}"  # 0, 1, 2, ... F
            elif section == 17:
                return LANGS.get(self.lang, LANGS['en']).get('text_column', 'Text')
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = index.row(); col = index.column()
        addr = self.min_addr + (row * 16)
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0: return f"{addr:04X}"
            elif 1 <= col <= 16:
                byte_addr = addr + col - 1
                if byte_addr in self.mem: return f"{self.mem[byte_addr]:02X}"
            elif col == 17:
                ascii_str = ""
                for c in range(16):
                    b = self.mem.get(addr + c, -1)
                    if 32 <= b <= 126: ascii_str += chr(b)
                    else: ascii_str += "."
                return ascii_str
        elif role == Qt.FontRole:
            return QFont("Consolas", 10)
        return None

    def flags(self, index):
        flags = super().flags(index)
        if 1 <= index.column() <= 16:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and 1 <= index.column() <= 16:
            try:
                val = int(value, 16)
                if 0 <= val <= 255:
                    addr = self.min_addr + (index.row() * 16) + index.column() - 1
                    old_val = self.mem.get(addr, 0)
                    if old_val != val:  # Только если значение изменилось
                        self.mem[addr] = val
                        self.last_edit = (addr, old_val, val)  # ← Сохраняем для undo
                        self.dataChanged.emit(index, index, [Qt.DisplayRole])
                        self.dataEdited.emit()
                    return True
            except ValueError: pass
        return False

# ==================== КАСТОМНАЯ ТАБЛИЦА HEX-РЕДАКТОРА С ПОДСКАЗКАМИ ====================

