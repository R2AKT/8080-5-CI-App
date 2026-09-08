"""Custom disassembly view with syntax highlighting."""
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, QEvent, QRect, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from ..i18n import LANGS
from ..disassembler import JUMP_OPCODES

class DisasmView(QWidget):
    toggleBreakpoint = Signal(int)  # Сигнал для установки/удаления breakpoint
    cursorChanged = Signal(int)             # Одинарный клик по строке
    runToCursorRequested = Signal(int)      # Контекстное меню: Run to Cursor
    runFromHereRequested = Signal(int)      # Контекстное меню: Run from Here
    jumpToCursorRequested = Signal(int)     # Контекстное меню: Jump to Cursor
    setConditionalBreakpointRequested = Signal(int)  # ИТЕРАЦИЯ C
    
    def __init__(self, mem_data, parent=None):
        super().__init__(parent)
        self.lines = []
        self.mem_data = mem_data
        self.line_height = 22
        self.addr_to_index = {}
        self.font_size = 10
        self.setFont(QFont("Consolas", self.font_size))
        self.setMinimumWidth(700)
        self.arrow_margin = 30
        self.is_dark_theme = False
        self.setup_colors()
        self.highlight_addr = None  # Адрес для подсветки (PC эмулятора)
        
        # === ИТЕРАЦИЯ B: Интерактивный режим (курсор + контекстное меню) ===
        self.interactive = False       # По умолчанию выключено
        self.cursor_addr = None        # Адрес курсора Run to Cursor
        
        self.breakpoints = set()  # Точки останова для отрисовки
        self.bp_conditions = {}  # ← ИТЕРАЦИЯ C: условия для отрисовки
        
        self.lang = "en"
        
    def set_bp_conditions(self, conditions):
        """Установить условия BP для отрисовки"""
        self.bp_conditions = conditions
        self.update()
        
    def set_highlight(self, addr):
        """Установить подсветку строки (PC эмулятора)"""
        self.highlight_addr = addr
        self.update()
        
    def setup_colors(self):
        """Настраивает цвета в зависимости от темы"""
        if self.is_dark_theme:
            # Тёмная тема
            self.colors = {
                "bg": QColor("#1e1e1e"),
                "addr": QColor("#858585"),
                "bytes": QColor("#6a6a6a"),
                "jump": QColor("#569cd6"),      # Синий
                "memory": QColor("#6bcf7f"),    # Зелёный
                "io": QColor("#c586c0"),        # Фиолетовый
                "control": QColor("#858585"),   # Серый
                "register": QColor("#ce9178"),  # Оранжевый
                "alu": QColor("#dcdcaa"),       # Жёлтый
                "stack": QColor("#4ec9b0"),     # Бирюзовый
                "undoc": QColor("#ff6b6b"),     # Красный
                "comment": QColor("#569cd6"),   # Голубой
                "text": QColor("#d4d4d4"),      # Основной текст
            }
        else:
            # Светлая тема (яркие, контрастные цвета на белом фоне)
            self.colors = {
                "bg": QColor("#ffffff"),        # Белый фон
                "addr": QColor("#808080"),      # Серый
                "bytes": QColor("#666666"),     # Тёмно-серый
                "jump": QColor("#0055cc"),      # Тёмно-синий
                "memory": QColor("#007700"),    # Тёмно-зелёный
                "io": QColor("#8800aa"),        # Фиолетовый
                "control": QColor("#666666"),   # Серый
                "register": QColor("#cc5500"),  # Тёмно-оранжевый
                "alu": QColor("#886600"),       # Тёмно-жёлтый
                "stack": QColor("#008888"),     # Тёмно-бирюзовый
                "undoc": QColor("#cc0000"),     # Красный
                "comment": QColor("#0055cc"),   # Голубой
                "text": QColor("#000000"),      # Чёрный текст
            }
        
    def set_theme(self, is_dark):
        """Устанавливает тему"""
        self.is_dark_theme = is_dark
        self.setup_colors()
        self.update()
        
    def set_lines(self, lines):
        self.lines = lines
        self.addr_to_index = {line[0]: i for i, line in enumerate(lines)}
        self.setFixedHeight(len(lines) * self.line_height + 10)
        self.repaint()
        if self.parent():
            self.parent().update()
            
    def get_instruction_color(self, asm):
        """Возвращает цвет для команды в зависимости от её типа"""
        parts = asm.split()
        if not parts:
            return self.colors["text"]
            
        mnemonic = parts[0].upper()
        
        # Недокументированные команды
        if asm.endswith("*"):
            return self.colors["undoc"]
        
        # Переходы: JMP, CALL, Jcc, Ccc, RST
        if mnemonic in ["JMP", "CALL", "RST"]:
            return self.colors["jump"]
        if len(mnemonic) > 1:
            suffix = mnemonic[1:]
            if mnemonic[0] == 'J' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
            if mnemonic[0] == 'C' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
        
        # Память
        if mnemonic in ["LDA", "STA", "LHLD", "SHLD", "LDAX", "STAX", "XCHG", "XTHL"]:
            return self.colors["memory"]
        if mnemonic == "MOV" and len(parts) > 1 and "M" in parts[1]:
            return self.colors["memory"]
        
        # Ввод-вывод
        if mnemonic in ["IN", "OUT"]:
            return self.colors["io"]
        
        # Управление
        if mnemonic in ["NOP", "HLT", "DI", "EI", "RET", "PCHL", "SPHL"]:
            return self.colors["control"]
        
        # Регистры и данные
        if mnemonic in ["MVI", "LXI", "INR", "DCR", "MOV", "INX", "DCX"]:
            return self.colors["register"]
        
        # Арифметика и логика (включая DAD)
        if mnemonic in ["ADD", "ADC", "SUB", "SBB", "ANA", "XRA", "ORA", "CMP",
                        "RLC", "RRC", "RAL", "RAR", "DAA", "CMA", "STC", "CMC",
                        "ADI", "ACI", "SUI", "SBI", "ANI", "XRI", "ORI", "CPI",
                        "DAD"]:
            return self.colors["alu"]
        
        # Стек
        if mnemonic in ["PUSH", "POP"]:
            return self.colors["stack"]
        
        return self.colors["text"]
        
    def wheelEvent(self, event):
        """Ctrl + колесо мыши для изменения размера шрифта"""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(self.font_size + 1, 36)
            else:
                self.font_size = max(self.font_size - 1, 8)
                
            self.setFont(QFont("Consolas", self.font_size))
            self.line_height = self.font_size + 12
            self.setFixedHeight(len(self.lines) * self.line_height + 10)
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font())
        
        # Фон (белый для светлой темы)
        painter.fillRect(self.rect(), self.colors["bg"])
        
        # Получаем ширину символа для выравнивания
        font_metrics = painter.fontMetrics()
        char_width = font_metrics.averageCharWidth()
        
        # Фиксированные позиции колонок
        addr_x = self.arrow_margin + 10
        bytes_x = addr_x + 6 * char_width
        asm_x = bytes_x + 14 * char_width
        
        # Рисуем строки
        for i, (addr, size, asm, undoc, target) in enumerate(self.lines):
            y = i * self.line_height + self.line_height // 2 + 5
            
            # === ИТЕРАЦИЯ B: Отрисовка курсора (зелёная стрелка ▷) ===
            if self.interactive and self.cursor_addr is not None and addr == self.cursor_addr:
                # Зелёная стрелка слева от адреса
                painter.setPen(QColor("#4CAF50"))  # Зелёный
                cursor_font = QFont("Consolas", 10, QFont.Bold)
                painter.setFont(cursor_font)
                painter.drawText(5, y, "▷")
                
                # Лёгкая зелёная подсветка строки (если нет PC-подсветки)
                if self.highlight_addr != addr:
                    cursor_rect = QRect(
                        self.arrow_margin + 5,
                        i * self.line_height + 2,
                        self.width() - self.arrow_margin - 10,
                        self.line_height - 4
                    )
                    painter.fillRect(cursor_rect, QColor("#E8F5E9"))  # Бледно-зелёный
                   
            # === Подсветка текущей инструкции (PC эмулятора) ===
            if self.highlight_addr is not None and addr == self.highlight_addr:
                # Жёлтый фон для текущей инструкции
                highlight_rect = QRect(
                    self.arrow_margin + 5,
                    i * self.line_height + 2,
                    self.width() - self.arrow_margin - 10,
                    self.line_height - 4
                )
                painter.fillRect(highlight_rect, QColor("#fff3cd"))  # Светло-жёлтый
                
                # Стрелка слева
                painter.setPen(QColor("#ff9800"))
                painter.drawText(5, y, "►")
                
            # === Точки останова (красные/оранжевые кружки) ===
            if addr in self.breakpoints:
                bp_x = self.arrow_margin + 2
                bp_y = i * self.line_height + self.line_height // 2
                # Проверяем, условная ли это BP
                is_conditional = (
                    hasattr(self, 'bp_conditions') and 
                    addr in self.bp_conditions and 
                    self.bp_conditions[addr]
                )
                if is_conditional:
                    painter.setBrush(QColor("#ff9800"))  # Оранжевый для условных
                else:
                    painter.setBrush(QColor("#f44336"))  # Красный для обычных
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(bp_x - 4, bp_y - 4, 8, 8)
				
            # Адрес
            painter.setPen(self.colors["addr"])
            painter.drawText(addr_x, y, f"{addr:04X}")
            
            # Байты
            bytes_str = " ".join(f"{self.mem_data.get(addr+k, 0):02X}" for k in range(size))
            painter.setPen(self.colors["bytes"])
            painter.drawText(bytes_x, y, bytes_str)
            
            # Команда
            asm_text = f"{asm} {undoc}".strip()
            color = self.get_instruction_color(asm_text)
            painter.setPen(color)
            painter.drawText(asm_x, y, asm_text)
            
            # Комментарий перехода
            if target is not None:
                comment = f"; -> {target:04X}h"
                comment_x = asm_x + len(asm_text) * char_width + 3 * char_width
                painter.setPen(self.colors["comment"])
                painter.drawText(comment_x, y, comment)
                
        # Рисуем стрелки переходов
        self.draw_arrows(painter)
        
    def draw_arrows(self, painter):
        arrow_x_start = 5
        arrow_colors = [QColor("#ff6b6b"), QColor("#4ecdc4"), QColor("#ffe66d"), 
                        QColor("#a8e6cf"), QColor("#ffd93d"), QColor("#6bcf7f")]
        color_idx = 0
        
        for i, (addr, size, asm, undoc, target) in enumerate(self.lines):
            if target is not None and target in self.addr_to_index:
                target_idx = self.addr_to_index[target]
                y1 = i * self.line_height + self.line_height // 2 + 5
                y2 = target_idx * self.line_height + self.line_height // 2 + 5
                
                color = arrow_colors[color_idx % len(arrow_colors)]
                color_idx += 1
                
                pen = QPen(color, 2)
                painter.setPen(pen)
                
                x_offset = arrow_x_start + (color_idx % 5) * 4
                
                painter.drawLine(x_offset, y1, x_offset, y2)
                painter.drawLine(x_offset, y2, self.arrow_margin + 5, y2)
                
                if y2 > y1:
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 - 4)
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 + 4)
                else:
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 - 4)
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 + 4)
                    
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x_offset - 2, y1 - 2, 4, 4)
                painter.setPen(pen)
				
    def mouseDoubleClickEvent(self, event):
        """Двойной ЛЕВЫЙ клик — установить/удалить точку останова"""
        # === Обрабатываем только левую кнопку ===
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        
        y = event.position().y()
        line_idx = int((y - 5) / self.line_height)
        
        if 0 <= line_idx < len(self.lines):
            addr = self.lines[line_idx][0]
            self.toggleBreakpoint.emit(addr)
        
        super().mouseDoubleClickEvent(event)
        
    def set_breakpoints(self, breakpoints):
        """Установить точки останова для отрисовки"""
        self.breakpoints = breakpoints
        self.update()
        
    def set_interactive(self, enabled):
        """Включает/выключает интерактивный режим (курсор + меню)"""
        self.interactive = enabled
        
    def set_cursor(self, addr):
        """Установить курсор Run to Cursor"""
        self.cursor_addr = addr
        self.update()
        
    def get_line_addr_at(self, y):
        """Возвращает адрес строки по Y-координате мыши"""
        if not hasattr(self, 'lines') or not self.lines:
            return None
        line_idx = int((y - 5) / self.line_height)
        if 0 <= line_idx < len(self.lines):
            return self.lines[line_idx][0]
        return None
        
    def mousePressEvent(self, event):
        """Одинарный ЛЕВЫЙ клик — установка курсора"""
        if self.interactive and event.button() == Qt.LeftButton:
            addr = self.get_line_addr_at(event.position().y())
            if addr is not None:
                self.cursor_addr = addr
                self.cursorChanged.emit(addr)
                self.update()
            # НЕ вызываем super() для левого клика в интерактивном режиме,
            # чтобы избежать конфликта с mouseDoubleClickEvent
            event.accept()
            return
        super().mousePressEvent(event)
        
    def contextMenuEvent(self, event):
        """Контекстное меню (только в интерактивном режиме)"""
        if not self.interactive:
            super().contextMenuEvent(event)
            return
        addr = self.get_line_addr_at(event.pos().y())
        if addr is None:
            super().contextMenuEvent(event)
            return
        self.cursor_addr = addr
        self.update()
        L = LANGS.get(self.lang, LANGS["en"])
        menu = QMenu(self)
        act_run_to = menu.addAction(f"⥗ {L.get('ctx_run_to', 'Run to Cursor')} (0x{addr:04X})  [Ctrl+F10]")
        act_run_from = menu.addAction(f"⥟ {L.get('ctx_run_from', 'Run from Here')} (0x{addr:04X})")
        act_jump = menu.addAction(f"⤼ {L.get('ctx_jump', 'Jump to Cursor')} (0x{addr:04X})")
        menu.addSeparator()
        act_toggle_bp = menu.addAction(f"● {L.get('ctx_toggle_bp', 'Toggle Breakpoint')} (0x{addr:04X})")
        act_cond_bp = menu.addAction(f"◉ {L.get('ctx_cond_bp', 'Set Conditional BP...')} (0x{addr:04X})")
        selected = menu.exec(event.globalPos())
        if selected == act_run_to:
            self.runToCursorRequested.emit(addr)
        elif selected == act_run_from:
            self.runFromHereRequested.emit(addr)
        elif selected == act_jump:
            self.jumpToCursorRequested.emit(addr)
        elif selected == act_toggle_bp:
            self.toggleBreakpoint.emit(addr)
        elif selected == act_cond_bp:
            self.setConditionalBreakpointRequested.emit(addr)

# ==================== МОДЕЛЬ ДАННЫХ HEX-РЕДАКТОРА ====================

