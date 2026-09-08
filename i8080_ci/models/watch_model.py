"""Watch variables table model."""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from ..i18n import LANGS

class WatchModel(QAbstractTableModel):
    """Модель для Watch-окна (наблюдение за памятью и регистрами)"""
    
    # Форматы отображения
    FORMATS = ["hex", "dec", "signed", "bin", "ascii"]
    
    # Типы наблюдения
    TYPE_MEM_BYTE = "mem_byte"
    TYPE_MEM_WORD = "mem_word"
    TYPE_REG = "reg"
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.lang = "en"
        self.items = []  # Список элементов наблюдения
        self.prev_values = {}  # Предыдущие значения для подсветки
        
    # =============================================
    # УПРАВЛЕНИЕ ЭЛЕМЕНТАМИ
    # =============================================
    
    def add_watch(self, name, watch_type, target, fmt="hex"):
        """Добавить элемент наблюдения"""
        item = {
            "name": name,
            "type": watch_type,
            "target": target,
            "format": fmt
        }
        self.beginInsertRows(QModelIndex(), len(self.items), len(self.items))
        self.items.append(item)
        self.endInsertRows()
        
    def remove_watch(self, row):
        """Удалить элемент наблюдения"""
        if 0 <= row < len(self.items):
            self.beginRemoveRows(QModelIndex(), row, row)
            self.items.pop(row)
            self.endRemoveRows()
            
    def clear(self):
        """Очистить все элементы"""
        self.beginResetModel()
        self.items.clear()
        self.prev_values.clear()
        self.endResetModel()
        
    # =============================================
    # ПОЛУЧЕНИЕ И ФОРМАТИРОВАНИЕ ЗНАЧЕНИЙ
    # =============================================
    
    def get_value(self, item):
        """Получить текущее значение элемента"""
        try:
            if item["type"] == self.TYPE_MEM_BYTE:
                return self.emulator.read_byte(item["target"])
            elif item["type"] == self.TYPE_MEM_WORD:
                return self.emulator.read_word(item["target"])
            elif item["type"] == self.TYPE_REG:
                reg = item["target"].upper()
                if reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
                    return self.emulator.get_reg(reg)
                elif reg == 'BC': return self.emulator.get_reg_pair('BC')
                elif reg == 'DE': return self.emulator.get_reg_pair('DE')
                elif reg == 'HL': return self.emulator.get_reg_pair('HL')
                elif reg == 'SP': return self.emulator.sp
                elif reg == 'PC': return self.emulator.pc
                elif reg == 'FLAGS':
                    return (int(self.emulator.flag_s) << 7) | \
                           (int(self.emulator.flag_z) << 6) | \
                           (int(self.emulator.flag_ac) << 4) | \
                           (int(self.emulator.flag_p) << 2) | \
                           int(self.emulator.flag_cy)
        except Exception:
            return 0
        return 0
        
    def format_value(self, value, fmt, is_word=False):
        """Форматировать значение"""
        try:
            if fmt == "hex":
                return f"{value:04X}" if is_word else f"{value:02X}"
            elif fmt == "dec":
                return str(value)
            elif fmt == "signed":
                if is_word:
                    if value >= 0x8000:
                        return str(value - 0x10000)
                else:
                    if value >= 0x80:
                        return str(value - 0x100)
                return str(value)
            elif fmt == "bin":
                return f"{value:016b}" if is_word else f"{value:08b}"
            elif fmt == "ascii":
                if is_word:
                    chars = []
                    for i in range(2):
                        b = (value >> (i * 8)) & 0xFF
                        chars.append(chr(b) if 32 <= b < 127 else '.')
                    return ''.join(chars)
                else:
                    return chr(value) if 32 <= value < 127 else '.'
        except Exception:
            return "?"
        return str(value)
        
    def get_display_value(self, item):
        """Получить отформатированное значение"""
        value = self.get_value(item)
        is_word = item["type"] == self.TYPE_MEM_WORD or \
                  (item["type"] == self.TYPE_REG and item["target"].upper() in ['BC', 'DE', 'HL', 'SP', 'PC'])
        return self.format_value(value, item["format"], is_word)
        
    # =============================================
    # СОХРАНЕНИЕ/ЗАГРУЗКА ПРЕСЕТА
    # =============================================
    
    def save_preset(self, filepath):
        """Сохранить пресет в JSON файл"""
        data = {
            "version": 1,
            "watches": [
                {
                    "name": item["name"],
                    "type": item["type"],
                    "target": item["target"],
                    "format": item["format"]
                }
                for item in self.items
            ]
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
            
    def load_preset(self, filepath):
        """Загрузить пресет из JSON файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.beginResetModel()
            self.items.clear()
            self.prev_values.clear()
            
            for watch in data.get("watches", []):
                self.items.append({
                    "name": watch.get("name", "watch"),
                    "type": watch.get("type", self.TYPE_MEM_BYTE),
                    "target": watch.get("target", 0),
                    "format": watch.get("format", "hex")
                })
            
            self.endResetModel()
            return True
        except Exception:
            return False
            
    # =============================================
    # ОБНОВЛЕНИЕ
    # =============================================
    
    def save_prev_values(self):
        """Сохранить текущие значения для подсветки изменений"""
        self.prev_values = {}
        for i, item in enumerate(self.items):
            key = f"{item['type']}_{item['target']}"
            self.prev_values[key] = self.get_value(item)
            
    def refresh(self):
        """Обновить данные модели"""
        if self.items:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self.items) - 1, 3)
            )
    
    # =============================================
    # QAbstractTableModel INTERFACE
    # =============================================
    
    def rowCount(self, parent=None):
        return len(self.items)
        
    def columnCount(self, parent=None):
        return 4  # Имя | Адрес/Регистр | Значение | Формат
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("watch_col_name", "Name"),
                L.get("watch_col_target", "Addr/Reg"),
                L.get("watch_col_value", "Value"),
                L.get("watch_col_format", "Format"),
            ]
            return headers[section]
        return None
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self.items):
            return None
            
        item = self.items[row]
        
        if role == Qt.DisplayRole:
            if col == 0:
                return item["name"]
            elif col == 1:
                if item["type"] == self.TYPE_REG:
                    return item["target"].upper()
                return f"0x{item['target']:04X}"
            elif col == 2:
                return self.get_display_value(item)
            elif col == 3:
                return item["format"]
                
        elif role == Qt.BackgroundRole:
            # Подсветка изменённых значений
            if col == 2:
                current = self.get_value(item)
                key = f"{item['type']}_{item['target']}"
                if key in self.prev_values and self.prev_values[key] != current:
                    return QColor("#ffcccc")  # Красный фон
                    
        elif role == Qt.TextAlignmentRole:
            if col in [1, 2]:
                return Qt.AlignCenter
                
        return None


