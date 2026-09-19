"""Hex table view with context menu."""
from PySide6.QtWidgets import QApplication, QTableView, QInputDialog, QMenu, QToolTip
from PySide6.QtCore import QEvent, Signal

class HexTableView(QTableView):
    editOperation = Signal(list)  # ← Добавлено: [(addr, old_val, new_val), ...]
    statusUpdate = Signal(str, str, str)
    gotoAddress = Signal(int)
    
    def __init__(self, disassembler, mem_data, parent=None):
        super().__init__(parent)
        self.disassembler = disassembler
        self.mem_data = mem_data
        self.setMouseTracking(True)
    
    def tr(self, key):
        if self.parent() and hasattr(self.parent(), 'tr'):
            return self.parent().tr(key)
        return key
    
    def event(self, event):
        if event.type() == QEvent.ToolTip:
            viewport_pos = self.viewport().mapFrom(self, event.pos())
            index = self.indexAt(viewport_pos)
            if index.isValid() and 1 <= index.column() <= 16:
                row = index.row()
                col = index.column()
                model = self.model()
                if model and hasattr(model, 'min_addr'):
                    addr = model.min_addr + (row * 16) + col - 1
                    if addr in self.mem_data:
                        byte_val = self.mem_data[addr]
                        mnemonic = self.disassembler.get_mnemonic(byte_val)
                        QToolTip.showText(event.globalPos(), f"0x{byte_val:02X}: {mnemonic}", self)
                        return True
                        
        elif event.type() == QEvent.HoverMove:
            viewport_pos = self.viewport().mapFrom(self, event.pos())
            index = self.indexAt(viewport_pos)
            if index.isValid() and 1 <= index.column() <= 16:
                row = index.row()
                col = index.column()
                model = self.model()
                if model and hasattr(model, 'min_addr'):
                    addr = model.min_addr + (row * 16) + col - 1
                    if addr in self.mem_data:
                        byte_val = self.mem_data[addr]
                        mnemonic = self.disassembler.get_mnemonic(byte_val)
                        self.statusUpdate.emit(f"0x{addr:04X}", f"0x{byte_val:02X}", mnemonic)
                        
        return super().event(event)
        
    def contextMenuEvent(self, event):
        """Контекстное меню при правом клике"""
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
            
        menu = QMenu(self)
        
        # Определяем адрес ячейки
        addr = None
        if 1 <= index.column() <= 16:
            model = self.model()
            if model and hasattr(model, 'min_addr'):
                row = index.row()
                col = index.column()
                addr = model.min_addr + (row * 16) + col - 1
        
        if addr is not None and addr in self.mem_data:
            byte_val = self.mem_data[addr]
            
            # Копировать адрес
            act_copy_addr = menu.addAction(f"{self.tr('ctx_copy_addr')} (0x{addr:04X})")
            act_copy_addr.triggered.connect(lambda: self.copy_to_clipboard(f"{addr:04X}"))
            
            # Копировать значение
            act_copy_val = menu.addAction(f"{self.tr('ctx_copy_val')} (0x{byte_val:02X})")
            act_copy_val.triggered.connect(lambda: self.copy_to_clipboard(f"{byte_val:02X}"))
            
            menu.addSeparator()
            
            # Инвертировать байт
            act_invert = menu.addAction(f"{self.tr('ctx_invert')} (0x{~byte_val & 0xFF:02X})")
            act_invert.triggered.connect(lambda: self.invert_byte(addr))
            
            # Заполнить диапазон
            act_fill = menu.addAction(self.tr("ctx_fill"))
            act_fill.triggered.connect(lambda: self.fill_range(addr))
            
            menu.addSeparator()
            
            # Дизассемблировать отсюда
            act_disasm = menu.addAction(f"{self.tr('ctx_disasm')}0x{addr:04X}")
            act_disasm.triggered.connect(lambda: self.disasm_from(addr))
            
            # Перейти к адресу
            act_goto = menu.addAction(self.tr("ctx_goto"))
            act_goto.triggered.connect(lambda: self.goto_dialog())
            
        menu.exec(event.globalPos())
        
    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)
        
    def invert_byte(self, addr):
        """Инвертирует байт по адресу"""
        if addr in self.mem_data:
            old_val = self.mem_data[addr]
            new_val = ~old_val & 0xFF
            self.mem_data[addr] = new_val
            self.editOperation.emit([(addr, old_val, new_val)])  # ← Для undo
            model = self.model()
            if model:
                model.update_data({addr: new_val})
                
    def fill_range(self, start_addr):
        """Заполняет диапазон значением"""
        text, ok = QInputDialog.getText(self, self.tr("fill_title"), self.tr("fill_value"))
        if not ok: return
        try:
            val = int(text, 16)
        except ValueError:
            return
            
        size, ok2 = QInputDialog.getInt(self, self.tr("fill_title"), self.tr("fill_size"), 16, 1, 4096)
        if not ok2: return
        
        changes = []
        for i in range(size):
            addr = start_addr + i
            old_val = self.mem_data.get(addr, 0)
            self.mem_data[addr] = val
            changes.append((addr, old_val, val))
            
        self.editOperation.emit(changes)  # ← Для undo
        model = self.model()
        if model:
            model.update_data({start_addr + i: val for i in range(size)})
            
    def disasm_from(self, addr):
        """Дизассемблировать от указанного адреса"""
        self.parent().parent().parent().parent().disasm_from_address(addr)
        
    def goto_dialog(self):
        """Диалог перехода к адресу"""
        text, ok = QInputDialog.getText(self, self.tr("goto_title"), self.tr("bp_addr"))
        if not ok: return
        try:
            addr = int(text, 16)
            self.gotoAddress.emit(addr)
        except ValueError:
            pass


