"""
Assembler tab — editor, assembly, load to memory.
Uses assemble8080 and number parser with 0x... and ...H support.

Features:
- Syntax highlighting
- Line numbering
- Autocomplete (mnemonics, registers, directives, labels)
- Error panel (double-click — goto line)
- Label address list (double-click — goto line)
- Jump arrows (like in disassembler)
"""

import os
import re
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QGroupBox,
    QSplitter, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QCompleter, QAbstractItemView, QLabel, QComboBox
)
from PySide6.QtGui import (
    QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter,
    QPen, QTextCursor, QTextFormat
)
from PySide6.QtCore import Qt, QRegularExpression, QRect, QSize, QStringListModel

from assemble8080.assembler import Assembler
from assemble8080.objfile import obj_from_asm_result, save_obj, load_obj
from assemble8080.linker import link, link_from_script
from assemble8080.mapfile import load_map_file
from common.i18n import LANGS, get_system_language
from common.themes import (
    get_editor_style, get_syntax_colors, ARROW_COLORS,
    EDITOR_DARK, EDITOR_LIGHT,
)


# =============================================
# KEYWORDS FOR AUTOCOMPLETE
# =============================================

MNEMONICS = [
    "MOV", "MVI", "LXI", "LDA", "STA", "LHLD", "SHLD", "LDAX", "STAX", "XCHG",
    "ADD", "ADC", "SUB", "SBB", "ANA", "XRA", "ORA", "CMP",
    "ADI", "ACI", "SUI", "SBI", "ANI", "XRI", "ORI", "CPI",
    "INR", "DCR", "INX", "DCX", "DAD",
    "RLC", "RRC", "RAL", "RAR", "CMA", "CMC", "STC",
    "JMP", "JNZ", "JZ", "JNC", "JC", "JPO", "JPE", "JP", "JM",
    "CALL", "CNZ", "CZ", "CNC", "CC", "CPO", "CPE", "CP", "CM",
    "RET", "RNZ", "RZ", "RNC", "RC", "RPO", "RPE", "RP", "RM",
    "RST", "PUSH", "POP", "IN", "OUT", "EI", "DI", "HLT", "NOP",
    "PCHL", "SPHL", "XTHL", "SIM", "RIM",
]

REGISTERS = ["A", "B", "C", "D", "E", "H", "L", "M", "PSW", "SP", "BC", "DE", "HL"]

DIRECTIVES = ["ORG", "EQU", "DB", "DW", "DS", "END", "INCLUDE"]

KEYWORDS = MNEMONICS + REGISTERS + DIRECTIVES

# Jump mnemonics (for arrows)
JUMP_MNEMONICS = {
    "JMP", "JNZ", "JZ", "JNC", "JC", "JPO", "JPE", "JP", "JM",
    "CALL", "CNZ", "CZ", "CNC", "CC", "CPO", "CPE", "CP", "CM",
}


def _tr(key: str) -> str:
    """Get translated string for current language."""
    lang = get_system_language()
    return LANGS.get(lang, LANGS["en"]).get(key, key)


# =============================================
# LINE NUMBER AREA + JUMP ARROWS
# =============================================

class LineNumberArea(QWidget):
    """Area to the left of the editor: jump arrows + line numbers."""

    ARROWS_WIDTH = 32

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


# =============================================
# CODE EDITOR WITH LINE NUMBERS, ARROWS, AUTOCOMPLETE
# =============================================

class CodeEditor(QPlainTextEdit):
    """Assembler editor: line numbers, jump arrows, autocomplete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.jumps = []  # [(src_line, dst_line), ...]
        self._is_dark = True

        self.blockCountChanged.connect(self._updateLineNumberAreaWidth)
        self.updateRequest.connect(self._updateLineNumberArea)
        self.cursorPositionChanged.connect(self._highlightCurrentLine)

        self._updateLineNumberAreaWidth(0)
        self._highlightCurrentLine()

        # Autocomplete
        self._completer = QCompleter(KEYWORDS, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchStartsWith)
        self._completer.activated.connect(self._insert_completion)

    def set_dark(self, is_dark: bool):
        """Update editor colors for theme."""
        self._is_dark = is_dark
        self.line_number_area.update()

    # --- Line numbering ---

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 8 + digits * self.fontMetrics().horizontalAdvance('9')
        return LineNumberArea.ARROWS_WIDTH + space

    def _updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def _updateLineNumberArea(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(),
                                         self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        c = EDITOR_DARK if self._is_dark else EDITOR_LIGHT
        painter.fillRect(event.rect(), QColor(c["line_number_bg"]))

        # Jump arrows
        self._paintArrows(painter)

        # Line numbers
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block)
                    .translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        painter.setFont(self.font())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(c["line_number_fg"]))
                painter.drawText(
                    LineNumberArea.ARROWS_WIDTH, top,
                    self.line_number_area.width() - LineNumberArea.ARROWS_WIDTH - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight | Qt.AlignVCenter, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _paintArrows(self, painter):
        """Draw jump arrows — same algorithm as disassembler."""
        if not self.jumps:
            return
        content_offset = self.contentOffset()
        view_h = self.line_number_area.height()
        color_idx = 0

        for src, dst in self.jumps:
            src_block = self.document().findBlockByNumber(src)
            dst_block = self.document().findBlockByNumber(dst)
            if not src_block.isValid() or not dst_block.isValid():
                continue

            src_top = round(self.blockBoundingGeometry(src_block)
                            .translated(content_offset).top())
            src_h = round(self.blockBoundingRect(src_block).height())
            dst_top = round(self.blockBoundingGeometry(dst_block)
                            .translated(content_offset).top())
            dst_h = round(self.blockBoundingRect(dst_block).height())

            src_y = src_top + src_h // 2
            dst_y = dst_top + dst_h // 2

            if (src_y < -50 and dst_y < -50) or (src_y > view_h + 50 and dst_y > view_h + 50):
                continue

            color = QColor(ARROW_COLORS[color_idx % len(ARROW_COLORS)])
            color_idx += 1
            pen = QPen(color, 2)
            painter.setPen(pen)

            x = 4 + (color_idx % 5) * 5

            painter.drawLine(x, src_y, x, dst_y)

            if dst_y > src_y:
                painter.drawLine(x, dst_y, x - 3, dst_y - 4)
                painter.drawLine(x, dst_y, x + 3, dst_y - 4)
            else:
                painter.drawLine(x, dst_y, x - 3, dst_y + 4)
                painter.drawLine(x, dst_y, x + 3, dst_y + 4)

            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x - 2, src_y - 2, 4, 4)

    def set_jumps(self, jumps):
        """Set jump list [(src, dst), ...] and repaint."""
        self.jumps = jumps
        self.line_number_area.update()

    # --- Font size (Ctrl+wheel) ---
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            current_size = self.font().pointSize()
            if event.angleDelta().y() > 0:
                new_size = min(current_size + 1, 36)
            else:
                new_size = max(current_size - 1, 8)
            if new_size != current_size:
                self.setFont(QFont("Consolas", new_size))
                self._updateLineNumberAreaWidth(0)
                self.line_number_area.update()
            event.accept()
        else:
            super().wheelEvent(event)

    # --- Current line highlight ---
    def _highlightCurrentLine(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            c = EDITOR_DARK if self._is_dark else EDITOR_LIGHT
            sel.format.setBackground(QColor(c["current_line_bg"]))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        self.setExtraSelections(extra)

    def highlight_error_lines(self, error_lines):
        """Highlight error lines in red."""
        extra = []
        for ln in error_lines:
            block = self.document().findBlockByNumber(ln)
            if block.isValid():
                sel = QTextEdit.ExtraSelection()
                c = EDITOR_DARK if self._is_dark else EDITOR_LIGHT
                sel.format.setBackground(QColor(c["error_line_bg"]))
                sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                sel.cursor = QTextCursor(block)
                sel.cursor.clearSelection()
                extra.append(sel)
        self.setExtraSelections(extra)

    # --- Autocomplete ---
    def set_completions(self, words):
        self._completer.setModel(QStringListModel(words, self._completer))

    def _insert_completion(self, completion):
        tc = self.textCursor()
        tc.movePosition(QTextCursor.PreviousWord, QTextCursor.KeepAnchor)
        tc.insertText(completion)
        self.setTextCursor(tc)

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape,
                               Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        super().keyPressEvent(event)

        tc = self.textCursor()
        tc.movePosition(QTextCursor.PreviousWord, QTextCursor.KeepAnchor)
        word = tc.selectedText()

        if len(word) >= 2:
            self._completer.setCompletionPrefix(word)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            cr = self.cursorRect()
            cr.setWidth(popup.sizeHintForColumn(0)
                        + popup.verticalScrollBar().sizeHint().width())
            self._completer.complete(cr)
        else:
            self._completer.popup().hide()


# =============================================
# SYNTAX HIGHLIGHTING
# =============================================
class AsmHighlighter(QSyntaxHighlighter):

    def __init__(self, document, is_dark=True):
        super().__init__(document)
        self._is_dark = is_dark
        self._rules = []
        self._setup_rules()

    def _setup_rules(self):
        mnemonics = (
            r'\b(MOV|MVI|LXI|LDA|STA|LHLD|SHLD|LDAX|STAX|XCHG|'
            r'ADD|ADC|SUB|SBB|ANA|XRA|ORA|CMP|ADI|ACI|SUI|SBI|'
            r'ANI|XRI|ORI|CPI|INR|DCR|INX|DCX|DAD|'
            r'RLC|RRC|RAL|RAR|CMA|CMC|STC|'
            r'JMP|JNZ|JZ|JNC|JC|JPO|JPE|JP|JM|'
            r'CALL|CNZ|CZ|CNC|CC|CPO|CPE|CP|CM|'
            r'RET|RNZ|RZ|RNC|RC|RPO|RPE|RP|RM|'
            r'RST|PUSH|POP|IN|OUT|EI|DI|HLT|NOP|PCHL|SPHL|XTHL)\b'
        )
        directives = r'\b(ORG|DB|DW|DS|EQU|END|INCLUDE)\b'
        numbers = r'\b(0[xX][0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|[0-9]+[dD]?|[01]+[bB]|[0-7]+[qoQo])\b'
        labels = r'^[A-Za-z_][A-Za-z0-9_]*:'
        registers = r'\b(A|B|C|D|E|H|L|M|PSW|SP|BC|DE|HL)\b'
        comments = r';.*$'

        colors = get_syntax_colors(self._is_dark)

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        self._rules = [
            (QRegularExpression(comments), fmt(colors["comment"], italic=True)),
            (QRegularExpression(mnemonics, QRegularExpression.CaseInsensitiveOption),
             fmt(colors["mnemonic"], bold=True)),
            (QRegularExpression(directives, QRegularExpression.CaseInsensitiveOption),
             fmt(colors["directive"])),
            (QRegularExpression(numbers), fmt(colors["number"])),
            (QRegularExpression(labels, QRegularExpression.MultilineOption),
             fmt(colors["label"], bold=True)),
            (QRegularExpression(registers, QRegularExpression.CaseInsensitiveOption),
             fmt(colors["register"])),
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

    def set_theme(self, is_dark):
        """Reconfigure highlighting for new theme."""
        self._is_dark = is_dark
        self._rules = []
        self._setup_rules()
        self.rehighlight()


# =============================================
# MAIN ASSEMBLER WIDGET
# =============================================
class AssemblerWidget(QWidget):
    """Assembler tab: editor, errors, labels."""

    def __init__(self, main_window=None, is_dark=True, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_dark = is_dark
        
        self.assembler = Assembler()
        self._current_file = None  # Путь к загруженному .asm файлу
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- Button panel ---
        ctrl_layout = QHBoxLayout()

        self.btn_new = QPushButton(_tr("asm_new"))
        self.btn_new.clicked.connect(self.on_new)
        ctrl_layout.addWidget(self.btn_new)

        self.btn_load_file = QPushButton(_tr("asm_load"))
        self.btn_load_file.clicked.connect(self.on_load_file)
        ctrl_layout.addWidget(self.btn_load_file)

        self.btn_save_file = QPushButton(_tr("asm_save"))
        self.btn_save_file.clicked.connect(self.on_save_file)
        ctrl_layout.addWidget(self.btn_save_file)

        self.btn_assemble = QPushButton(_tr("asm_assemble"))
        self.btn_assemble.clicked.connect(self.on_assemble)
        ctrl_layout.addWidget(self.btn_assemble)

        self.btn_assemble_load = QPushButton(_tr("asm_assemble_load"))
        self.btn_assemble_load.clicked.connect(self.on_assemble_load)
        ctrl_layout.addWidget(self.btn_assemble_load)

        self.btn_assemble_obj = QPushButton(_tr("asm_assemble_obj"))
        self.btn_assemble_obj.clicked.connect(self.on_assemble_obj)
        ctrl_layout.addWidget(self.btn_assemble_obj)

        self.btn_link = QPushButton(_tr("asm_link"))
        self.btn_link.clicked.connect(self.on_link)
        ctrl_layout.addWidget(self.btn_link)

        # === Выбор типа процессора ===
        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(QLabel("Процессор:"))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(["i8080", "i8085"])
        self.cpu_combo.setCurrentText("i8080")
        ctrl_layout.addWidget(self.cpu_combo)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # --- Horizontal splitter: editor+errors | labels ---
        h_splitter = QSplitter(Qt.Horizontal)

        # Left: editor + error panel
        v_splitter = QSplitter(Qt.Vertical)

        # Code editor
        self.editor = CodeEditor(self)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setPlaceholderText(_tr("asm_placeholder"))
        self.editor.set_dark(self.is_dark)
        self.highlighter = AsmHighlighter(self.editor.document(), self.is_dark)
        self.editor.textChanged.connect(self._on_text_changed)
        v_splitter.addWidget(self.editor)

        # Error panel
        self.error_group = QGroupBox(_tr("asm_errors"))
        err_layout = QVBoxLayout()
        self.error_table = QTableWidget()
        self.error_table.setColumnCount(2)
        self.error_table.setHorizontalHeaderLabels([_tr("asm_col_line"), _tr("asm_col_msg")])
        self.error_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.error_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.error_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.error_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.error_table.setAlternatingRowColors(True)
        self.error_table.cellDoubleClicked.connect(self._on_error_double_clicked)
        err_layout.addWidget(self.error_table)
        self.error_group.setLayout(err_layout)
        v_splitter.addWidget(self.error_group)

        v_splitter.setSizes([500, 150])
        h_splitter.addWidget(v_splitter)

        # Right: label list
        self.label_group = QGroupBox(_tr("asm_labels"))
        lbl_layout = QVBoxLayout()
        self.label_table = QTableWidget()
        self.label_table.setColumnCount(3)
        self.label_table.setHorizontalHeaderLabels(
            [_tr("asm_col_label"), _tr("asm_col_addr"), _tr("asm_col_line2")])
        self.label_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.label_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.label_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.label_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.label_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.label_table.setAlternatingRowColors(True)
        self.label_table.cellDoubleClicked.connect(self._on_label_double_clicked)
        lbl_layout.addWidget(self.label_table)
        self.label_group.setLayout(lbl_layout)
        h_splitter.addWidget(self.label_group)

        h_splitter.setSizes([600, 200])
        layout.addWidget(h_splitter, 1)

    # --- Navigation ---

    def _goto_line(self, line_num):
        """Goto line (0-based) in editor."""
        block = self.editor.document().findBlockByNumber(line_num)
        if block.isValid():
            cursor = QTextCursor(block)
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
            self.editor.setFocus()

    def _on_error_double_clicked(self, row, column):
        item = self.error_table.item(row, 0)
        if item:
            self._goto_line(int(item.text()) - 1)

    def _on_label_double_clicked(self, row, column):
        item = self.label_table.item(row, 2)
        if item:
            txt = item.text()
            if txt.isdigit():
                self._goto_line(int(txt) - 1)

    # --- Label and jump collection ---
    def _collect_label_lines(self):
        """Collect {LABEL: line_number} from editor text."""
        lines = self.editor.toPlainText().split('\n')
        label_lines = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:', stripped)
            if m:
                label_lines[m.group(1).upper()] = i
        return label_lines

    def _compute_jumps(self):
        """Compute jumps [(src_line, dst_line), ...]."""
        lines = self.editor.toPlainText().split('\n')
        label_lines = self._collect_label_lines()
        jumps = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if ';' in stripped:
                stripped = stripped.split(';')[0].strip()
            if not stripped:
                continue

            parts = stripped.split()
            if not parts:
                continue

            mnemonic = parts[0].upper()

            if mnemonic.endswith(':'):
                rest = stripped[len(parts[0]):].strip()
                if rest:
                    parts = rest.split()
                    mnemonic = parts[0].upper()
                else:
                    continue

            if mnemonic not in JUMP_MNEMONICS:
                continue
            if len(parts) < 2:
                continue

            operand = parts[1].strip().rstrip(',').upper()
            if operand in label_lines:
                jumps.append((i, label_lines[operand]))

        self.editor.set_jumps(jumps)

    def _on_text_changed(self):
        """On text change — recompute jumps and update autocomplete."""
        self._compute_jumps()
        labels = list(self._collect_label_lines().keys())
        self.editor.set_completions(KEYWORDS + labels)

    # --- Error panel update ---

    def _update_errors(self, errors):
        """Fill error panel. errors: [(line, message), ...]"""
        self.error_table.setRowCount(0)
        error_lines = []
        for line, msg in errors:
            row = self.error_table.rowCount()
            self.error_table.insertRow(row)
            self.error_table.setItem(row, 0, QTableWidgetItem(str(line)))
            self.error_table.setItem(row, 1, QTableWidgetItem(msg))
            error_lines.append(line - 1)
        self.editor.highlight_error_lines(error_lines)

    # --- Label table update ---

    def _update_labels_table(self, symbols):
        """Fill label table. symbols: {label: address}"""
        self.label_table.setRowCount(0)
        label_lines = self._collect_label_lines()
        sorted_symbols = sorted(symbols.items(), key=lambda x: x[1])
        for label, addr in sorted_symbols:
            row = self.label_table.rowCount()
            self.label_table.insertRow(row)
            self.label_table.setItem(row, 0, QTableWidgetItem(label))
            self.label_table.setItem(row, 1, QTableWidgetItem(f"0x{addr:04X}"))
            ln = label_lines.get(label, -1)
            self.label_table.setItem(row, 2,
                                     QTableWidgetItem(str(ln + 1) if ln >= 0 else "-"))

    # --- Button handlers ---
    def on_new(self):
        """New program: clear editor and log."""
        self.editor.clear()
        self._current_file = None
        self.editor.jumps = []
        self.editor.line_number_area.update()
        self.error_table.setRowCount(0)
        self.label_table.setRowCount(0)

    def on_assemble(self):
        self._do_assemble(load_to_memory=False)

    def on_assemble_load(self):
        self._do_assemble(load_to_memory=True)

    def on_assemble_obj(self):
        """Assemble and save object file (.obj)."""
        # Передаём тип процессора в ассемблер
        self.assembler.cpu_type = self.cpu_combo.currentText()
        source = self.editor.toPlainText()
        if not source.strip():
            if self.main_window is not None:
                self.main_window.log(_tr("asm_no_code"))
            return
        try:
            result = self.assembler.assemble(source, self._current_file or '')
        except Exception:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_exception").format(tb=traceback.format_exc()))
            return
        if result.errors:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_errors_found").format(n=len(result.errors)))
                for err in result.errors:
                    self.main_window.log(_tr("asm_err_line").format(line=err.line, msg=err.message))
            return
        # Сохранение map-файла рядом с исходным (map создаётся при любом ассемблировании)
        # === Автоопределение CPU из директивы ===
        self._apply_cpu_from_source()

        if result.map_text and self._current_file:
            map_path = os.path.splitext(self._current_file)[0] + '.map'
            try:
                from assemble8080.mapfile import save_map_file
                save_map_file(map_path, result.map_text)
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_saved").format(path=map_path))
            except Exception as e:
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_save_err").format(e=e))
        # Determine default obj path
        if self._current_file:
            default = os.path.splitext(self._current_file)[0] + '.obj'
        else:
            default = 'output.obj'
        path, _ = QFileDialog.getSaveFileName(
            self, _tr("asm_obj_title"), default, _tr("asm_obj_filter"))
        if not path:
            return
        try:
            obj = obj_from_asm_result(result, self._current_file or '')
            save_obj(path, obj)
            if self.main_window is not None:
                self.main_window.log(_tr("asm_obj_saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_err_title"),
                                 _tr("asm_obj_err").format(e=e))

    def on_link(self):
        """Link object files using a linker script (.lnk) or selected .obj files."""
        # Try to open a linker script first
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("asm_link_title"), "", _tr("asm_link_filter"))
        if not path:
            return
        if self.main_window is not None:
            self.main_window.log(_tr("asm_linking"))
        try:
            if path.lower().endswith('.lnk'):
                result = link_from_script(path)
            else:
                # Single .obj file: link it alone
                obj = load_obj(path)
                result = link([obj])
            if not result.success:
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_link_errors").format(n=len(result.errors)))
                    for err in result.errors:
                        self.main_window.log(_tr("asm_link_err").format(msg=err.message))
                return
            if self.main_window is not None:
                self.main_window.log(_tr("asm_link_success").format(n=len(result.binary), path=path))
                if result.map_text:
                    self.main_window.log(_tr("asm_link_map").format(path='(generated)'))
                for w in result.warnings:
                    self.main_window.log(_tr("asm_warning").format(w=w))
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_link_err_title"),
                                 _tr("asm_link_fail").format(e=e))

    def on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("asm_load_title"), "",
            _tr("asm_file_filter"))
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self._current_file = path
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_loaded").format(path=path))
            except Exception as e:
                QMessageBox.critical(self, _tr("asm_err_title"),
                                     _tr("asm_load_err").format(e=e))

    def on_save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, _tr("asm_save_title"), "",
            _tr("asm_file_filter_save"))
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_saved").format(path=path))
            except Exception as e:
                QMessageBox.critical(self, _tr("asm_err_title"),
                                     _tr("asm_save_err").format(e=e))

    # --- Assembly ---

    def _do_assemble(self, load_to_memory=False):
        # Передаём тип процессора в ассемблер
        self.assembler.cpu_type = self.cpu_combo.currentText()
        
        if self.main_window is not None:
            self.main_window.log(_tr("asm_assembling"))

        source = self.editor.toPlainText()
        if not source.strip():
            if self.main_window is not None:
                self.main_window.log(_tr("asm_no_code"))
            return

        try:
            result = self.assembler.assemble(source, self._current_file or '')
        except Exception:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_exception").format(tb=traceback.format_exc()))
            return

        self._compute_jumps()

        if result.errors:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_errors_found").format(n=len(result.errors)))
            err_list = []
            if self.main_window is not None:
                for err in result.errors:
                    self.main_window.log(_tr("asm_err_line").format(line=err.line, msg=err.message))
                    err_list.append((err.line, err.message))
            self._update_errors(err_list)
            self._update_labels_table({})
            return

        # Success
        self._update_errors([])

        # === Автоопределение CPU из директивы ===
        self._apply_cpu_from_source()


        if result.warnings:
            if self.main_window is not None:
                for w in result.warnings:
                    self.main_window.log(_tr("asm_warning").format(w=w))

        if self.main_window is not None:
            self.main_window.log(_tr("asm_success").format(n=len(result.binary)))
            self.main_window.log(_tr("asm_origin").format(addr=result.origin))
            self.main_window.log(_tr("asm_symbols").format(n=len(result.symbols)))

        if self.main_window is not None:
            for name, addr in sorted(result.symbols.items(), key=lambda x: x[1]):
                self.main_window.log(f"    {name}: 0x{addr:04X}")

        self._update_labels_table(result.symbols)

        # Сохранение map-файла рядом с исходным файлом
        if result.map_text and self._current_file:
            map_path = os.path.splitext(self._current_file)[0] + '.map'
            try:
                from assemble8080.mapfile import save_map_file
                save_map_file(map_path, result.map_text)
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_saved").format(path=map_path))
            except Exception as e:
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_save_err").format(e=e))

        # Load to memory
        if load_to_memory and result.binary:
            self._load_to_memory(result.binary, result.origin)

    def _load_to_memory(self, binary, origin):
        """Load assembled binary into emulator memory."""
        if not self.main_window:
            return
        try:
            mw = self.main_window
            changes = {}
            for i, byte in enumerate(binary):
                mw.mem_data[origin + i] = byte & 0xFF
                changes[origin + i] = byte & 0xFF
            mw.hex_model.update_data(changes)
            if hasattr(mw, 'update_range_label'):
                mw.update_range_label()
            if hasattr(mw, 'update_emu_disasm_view'):
                mw.update_emu_disasm_view()
            if hasattr(mw, 'emulator') and mw.emulator:
                mw.emulator.set_pc(origin)
                if hasattr(mw, 'update_emu_disasm_view'):
                    mw.update_emu_disasm_view()
            mw.log(_tr("asm_loaded_mem").format(n=len(binary), addr=origin))
        except Exception:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_load_mem_err").format(tb=traceback.format_exc()))

    def _apply_cpu_from_source(self):
        """Автоопределение типа CPU из директивы в исходном коде.
        Если директива найдена — блокируем combo и синхронизируем эмулятор.
        Если нет — разблокируем combo (пользователь выбирает вручную)."""
        cpu_from_source = self.assembler.cpu_set_by_directive
        cpu_type = self.assembler.cpu_type

        if cpu_from_source:
            # Директива найдена — блокируем combo и синхронизируем
            self.cpu_combo.blockSignals(True)
            self.cpu_combo.setCurrentText(cpu_type)
            self.cpu_combo.blockSignals(False)
            self.cpu_combo.setEnabled(False)
            # Синхронизируем эмулятор и дизассемблер
            if self.main_window is not None:
                if hasattr(self.main_window, 'emulator') and self.main_window.emulator:
                    self.main_window.emulator.cpu_type = cpu_type
                if hasattr(self.main_window, 'emu_cpu_combo'):
                    self.main_window.emu_cpu_combo.blockSignals(True)
                    self.main_window.emu_cpu_combo.setCurrentText(cpu_type)
                    self.main_window.emu_cpu_combo.blockSignals(False)
                    self.main_window.emu_cpu_combo.setEnabled(False)
                if hasattr(self.main_window, 'disassembler') and self.main_window.disassembler:
                    self.main_window.disassembler.set_cpu_type(cpu_type)
                self.main_window.current_cpu = cpu_type
        else:
            # Директивы нет — разблокируем combo
            self.cpu_combo.setEnabled(True)
            if self.main_window is not None:
                if hasattr(self.main_window, 'emu_cpu_combo'):
                    self.main_window.emu_cpu_combo.setEnabled(True)

    def set_theme(self, is_dark: bool):
        """Update assembler widget theme."""
        self.is_dark = is_dark
        if hasattr(self, 'highlighter') and self.highlighter is not None:
            self.highlighter.set_theme(is_dark)
        if hasattr(self, 'editor') and self.editor is not None:
            self.editor.set_dark(is_dark)
            self.editor.setStyleSheet(get_editor_style(is_dark))
            # Update button labels for new language
            self.btn_new.setText(_tr("asm_new"))
            self.btn_load_file.setText(_tr("asm_load"))
            self.btn_save_file.setText(_tr("asm_save"))
            self.btn_assemble.setText(_tr("asm_assemble"))
            self.btn_assemble_load.setText(_tr("asm_assemble_load"))
            self.btn_assemble_obj.setText(_tr("asm_assemble_obj"))
            self.btn_link.setText(_tr("asm_link"))
            self.error_group.setTitle(_tr("asm_errors"))
            self.error_table.setHorizontalHeaderLabels([_tr("asm_col_line"), _tr("asm_col_msg")])
            self.label_group.setTitle(_tr("asm_labels"))
            self.label_table.setHorizontalHeaderLabels(
                [_tr("asm_col_label"), _tr("asm_col_addr"), _tr("asm_col_line2")])
            self.editor.setPlaceholderText(_tr("asm_placeholder"))

    def sync_from_memory(self):
        """Sync from emulator memory (disassembly)."""
        if self.main_window is None:
            return
        mw = self.main_window
        if not mw.mem_data:
            return
        disasm = mw.disassembler
        mn = min(mw.mem_data.keys())
        mx = max(mw.mem_data.keys())
        lines = disasm.disassemble(mw.mem_data, mn, mx - mn + 1)
        text_lines = [f"        ORG {mn:04X}H"]
        for addr, size, asm, undoc, target in lines:
            text_lines.append(f"{asm}")
        self.editor.setPlainText('\n'.join(text_lines))
