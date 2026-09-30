"""Custom disassembly view with syntax highlighting, jump arrows, and map symbols."""
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPen
from ..i18n import LANGS


class DisasmView(QWidget):
    toggleBreakpoint = Signal(int)
    cursorChanged = Signal(int)
    runToCursorRequested = Signal(int)
    runFromHereRequested = Signal(int)
    jumpToCursorRequested = Signal(int)
    setConditionalBreakpointRequested = Signal(int)

    def __init__(self, mem_data, parent=None):
        super().__init__(parent)
        self.lines = []           # raw lines: (addr, size, asm, undoc, target)
        self.mem_data = mem_data
        self.line_height = 22
        self.addr_to_index = {}   # addr -> display line index (instruction line)
        self.font_size = 10
        self.setFont(QFont("Consolas", self.font_size))
        self.setMinimumWidth(700)
        self.arrow_margin = 38    # was 30, expanded 25%
        self.is_dark_theme = False
        self.setup_colors()
        self.highlight_addr = None
        self.symbols = None       # MapFile for symbol display

        # Display lines: (addr, size, asm, undoc, target, is_label, sym_name)
        self._display_lines = []

        # Interactive mode
        self.interactive = False
        self.cursor_addr = None
        self.breakpoints = set()
        self.bp_conditions = {}
        self.lang = "en"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_bp_conditions(self, conditions):
        self.bp_conditions = conditions
        self.update()

    def set_highlight(self, addr):
        self.highlight_addr = addr
        self.update()

    def set_symbols(self, map_file):
        """Set the map file for symbol display. Rebuilds display lines."""
        self.symbols = map_file
        self._rebuild_display_lines()
        self.update()

    def set_lines(self, lines):
        self.lines = lines
        self._rebuild_display_lines()
        self.setFixedHeight(len(self._display_lines) * self.line_height + 10)
        self.repaint()
        if self.parent():
            self.parent().update()

    def set_theme(self, is_dark):
        self.is_dark_theme = is_dark
        self.setup_colors()
        self.update()

    def set_breakpoints(self, breakpoints):
        self.breakpoints = breakpoints
        self.update()

    def set_interactive(self, enabled):
        self.interactive = enabled

    # ------------------------------------------------------------------
    # Internal: build display lines (label + instruction split)
    # ------------------------------------------------------------------

    def _rebuild_display_lines(self):
        """Split lines with symbols into label-line + instruction-line."""
        self._display_lines = []
        self.addr_to_index = {}

        for (addr, size, asm, undoc, target) in self.lines:
            sym = None
            if self.symbols is not None:
                sym = self.symbols.get_symbol_exact(addr)

            if sym:
                # Label line (no instruction)
                self._display_lines.append((addr, 0, "", False, None, True, sym))
                # Instruction line (indented)
                self._display_lines.append((addr, size, asm, undoc, target, False, None))
            else:
                # Normal single line
                self._display_lines.append((addr, size, asm, undoc, target, False, None))

        # addr_to_index maps to the LABEL line if it exists (arrows point to label)
        for i, dl in enumerate(self._display_lines):
            if dl[5]:  # label line - prefer this for arrows
                self.addr_to_index[dl[0]] = i
            elif dl[0] not in self.addr_to_index:
                self.addr_to_index[dl[0]] = i

    # ------------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------------

    def setup_colors(self):
        if self.is_dark_theme:
            self.colors = {
                "bg": QColor("#1e1e1e"),
                "addr": QColor("#858585"),
                "bytes": QColor("#6a6a6a"),
                "jump": QColor("#569cd6"),
                "memory": QColor("#6bcf7f"),
                "io": QColor("#c586c0"),
                "control": QColor("#858585"),
                "register": QColor("#ce9178"),
                "alu": QColor("#dcdcaa"),
                "stack": QColor("#4ec9b0"),
                "undoc": QColor("#ff6b6b"),
                "comment": QColor("#569cd6"),
                "text": QColor("#d4d4d4"),
                "symbol": QColor("#dcdcaa"),
            }
        else:
            self.colors = {
                "bg": QColor("#ffffff"),
                "addr": QColor("#808080"),
                "bytes": QColor("#666666"),
                "jump": QColor("#0055cc"),
                "memory": QColor("#007700"),
                "io": QColor("#8800aa"),
                "control": QColor("#666666"),
                "register": QColor("#cc5500"),
                "alu": QColor("#886600"),
                "stack": QColor("#008888"),
                "undoc": QColor("#cc0000"),
                "comment": QColor("#0055cc"),
                "text": QColor("#000000"),
                "symbol": QColor("#0066cc"),
            }

    # ------------------------------------------------------------------
    # Instruction color
    # ------------------------------------------------------------------

    def get_instruction_color(self, asm):
        parts = asm.split()
        if not parts:
            return self.colors["text"]
        mnemonic = parts[0].upper()
        if asm.endswith("*"):
            return self.colors["undoc"]
        if mnemonic in ["JMP", "CALL", "RST"]:
            return self.colors["jump"]
        if len(mnemonic) > 1:
            suffix = mnemonic[1:]
            if mnemonic[0] == 'J' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
            if mnemonic[0] == 'C' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
        if mnemonic in ["LDA", "STA", "LHLD", "SHLD", "LDAX", "STAX", "XCHG", "XTHL"]:
            return self.colors["memory"]
        if mnemonic == "MOV" and len(parts) > 1 and "M" in parts[1]:
            return self.colors["memory"]
        if mnemonic in ["IN", "OUT"]:
            return self.colors["io"]
        if mnemonic in ["NOP", "HLT", "DI", "EI", "RET", "PCHL", "SPHL"]:
            return self.colors["control"]
        if mnemonic in ["MVI", "LXI", "INR", "DCR", "MOV", "INX", "DCX"]:
            return self.colors["register"]
        if mnemonic in ["ADD", "ADC", "SUB", "SBB", "ANA", "XRA", "ORA", "CMP",
                        "RLC", "RRC", "RAL", "RAR", "DAA", "CMA", "STC", "CMC",
                        "ADI", "ACI", "SUI", "SBI", "ANI", "XRI", "ORI", "CPI",
                        "DAD"]:
            return self.colors["alu"]
        if mnemonic in ["PUSH", "POP"]:
            return self.colors["stack"]
        return self.colors["text"]

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font())

        painter.fillRect(self.rect(), self.colors["bg"])

        font_metrics = painter.fontMetrics()
        char_width = font_metrics.horizontalAdvance("0")  # exact monospace width
        tab_width = 4 * char_width  # one tab stop

        # Column positions
        addr_x = self.arrow_margin + 10
        content_x = addr_x + 6 * char_width       # where bytes / symbol starts
        bytes_x = content_x                        # bytes position (normal lines)
        asm_x = content_x + 12 * char_width        # instruction position (fixed column)
        asm_x_indented = content_x + tab_width + 12 * char_width  # indented instruction

        for i, (addr, size, asm, undoc, target, is_label, sym_name) in enumerate(self._display_lines):
            y = i * self.line_height + self.line_height // 2 + 5

            # === Cursor arrow (interactive mode) ===
            if self.interactive and self.cursor_addr is not None and addr == self.cursor_addr and not is_label:
                painter.setPen(QColor("#4CAF50"))
                cursor_font = QFont("Consolas", 10, QFont.Bold)
                painter.setFont(cursor_font)
                painter.drawText(5, y, "\u25B6")
                if self.highlight_addr != addr:
                    cursor_rect = QRect(
                        self.arrow_margin + 5,
                        i * self.line_height + 2,
                        self.width() - self.arrow_margin - 10,
                        self.line_height - 4
                    )
                    painter.fillRect(cursor_rect, QColor("#E8F5E9"))
                painter.setFont(self.font())

            # === PC highlight ===
            if self.highlight_addr is not None and addr == self.highlight_addr and not is_label:
                highlight_rect = QRect(
                    self.arrow_margin + 5,
                    i * self.line_height + 2,
                    self.width() - self.arrow_margin - 10,
                    self.line_height - 4
                )
                painter.fillRect(highlight_rect, QColor("#fff3cd"))
                painter.setPen(QColor("#ff9800"))
                painter.drawText(5, y, "\u25BA")

            # === Breakpoints ===
            if addr in self.breakpoints and not is_label:
                bp_x = self.arrow_margin + 2
                bp_y = i * self.line_height + self.line_height // 2
                is_conditional = (
                    hasattr(self, 'bp_conditions') and
                    addr in self.bp_conditions and
                    self.bp_conditions[addr]
                )
                if is_conditional:
                    painter.setBrush(QColor("#ff9800"))
                else:
                    painter.setBrush(QColor("#f44336"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(bp_x - 4, bp_y - 4, 8, 8)

            # === Address (always drawn) ===
            painter.setPen(self.colors["addr"])
            painter.drawText(addr_x, y, f"{addr:04X}")

            if is_label:
                # Label line: just the symbol name
                painter.setPen(self.colors["symbol"])
                sym_font = QFont("Consolas", self.font_size, QFont.Bold)
                painter.setFont(sym_font)
                painter.drawText(content_x, y, sym_name)
                painter.setFont(self.font())
            else:
                # Instruction line
                b_x = content_x
                a_x = content_x + 12 * char_width

                # Bytes
                if size > 0:
                    bytes_str = " ".join(f"{self.mem_data.get(addr + k, 0):02X}" for k in range(size))
                    painter.setPen(self.colors["bytes"])
                    painter.drawText(b_x, y, bytes_str)

                # Instruction
                asm_text = f"{asm} {undoc}".strip()
                color = self.get_instruction_color(asm_text)
                painter.setPen(color)
                painter.drawText(a_x, y, asm_text)

                # Jump target comment
                if target is not None:
                    comment = f"; -> {target:04X}h"
                    comment_x = a_x + len(asm_text) * char_width + 2 * char_width
                    painter.setPen(self.colors["comment"])
                    painter.drawText(comment_x, y, comment)

        # Draw jump arrows
        self.draw_arrows(painter)

    # ------------------------------------------------------------------
    # Arrows
    # ------------------------------------------------------------------

    def draw_arrows(self, painter):
        arrow_colors = [QColor("#ff6b6b"), QColor("#4ecdc4"), QColor("#ffe66d"),
                        QColor("#a8e6cf"), QColor("#ffd93d"), QColor("#6bcf7f")]
        color_idx = 0

        for i, (addr, size, asm, undoc, target, is_label, sym_name) in enumerate(self._display_lines):
            if is_label or target is None:
                continue
            if target not in self.addr_to_index:
                continue

            target_idx = self.addr_to_index[target]
            y1 = i * self.line_height + self.line_height // 2 + 5
            y2 = target_idx * self.line_height + self.line_height // 2 + 5

            color = arrow_colors[color_idx % len(arrow_colors)]
            color_idx += 1

            pen = QPen(color, 2)
            painter.setPen(pen)

            x_offset = 5 + (color_idx % 5) * 5

            painter.drawLine(x_offset, y1, x_offset, y2)
            painter.drawLine(x_offset, y2, self.arrow_margin + 5, y2)

            # Arrowhead
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

    # ------------------------------------------------------------------
    # Mouse / interaction
    # ------------------------------------------------------------------

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(self.font_size + 1, 36)
            else:
                self.font_size = max(self.font_size - 1, 8)
            self.setFont(QFont("Consolas", self.font_size))
            self.line_height = self.font_size + 12
            self.setFixedHeight(len(self._display_lines) * self.line_height + 10)
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)

    def get_line_addr_at(self, y):
        if not self._display_lines:
            return None
        line_idx = int((y - 5) / self.line_height)
        if 0 <= line_idx < len(self._display_lines):
            return self._display_lines[line_idx][0]
        return None

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        y = event.position().y()
        line_idx = int((y - 5) / self.line_height)
        if 0 <= line_idx < len(self._display_lines):
            addr = self._display_lines[line_idx][0]
            self.toggleBreakpoint.emit(addr)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if self.interactive and event.button() == Qt.LeftButton:
            addr = self.get_line_addr_at(event.position().y())
            if addr is not None:
                self.cursor_addr = addr
                self.cursorChanged.emit(addr)
                self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
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
        act_run_to = menu.addAction(f"\u2957 {L.get('ctx_run_to', 'Run to Cursor')} (0x{addr:04X})  [Ctrl+F10]")
        act_run_from = menu.addAction(f"\u295F {L.get('ctx_run_from', 'Run from Here')} (0x{addr:04X})")
        act_jump = menu.addAction(f"\u293C {L.get('ctx_jump', 'Jump to Cursor')} (0x{addr:04X})")
        menu.addSeparator()
        act_toggle_bp = menu.addAction(f"\u25CF {L.get('ctx_toggle_bp', 'Toggle Breakpoint')} (0x{addr:04X})")
        act_cond_bp = menu.addAction(f"\u25C9 {L.get('ctx_cond_bp', 'Set Conditional BP...')} (0x{addr:04X})")
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
