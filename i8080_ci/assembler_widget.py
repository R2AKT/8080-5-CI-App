"""
Assembler tab — editor, assembly, load to memory.
Uses assemble8080 and number parser with 0x... and ...H support.

Features:
- Syntax highlighting (global labels :: in extra bold)
- Line numbering
- Autocomplete (mnemonics, registers, directives, labels)
- Error panel (double-click — goto line)
- Label address list (double-click — goto line)
- Jump arrows (like in disassembler)
- Ctrl+Click on label — goto label definition
- Multi-file tabs (Notepad++ style)
- Workspace support (.ws JSON)
- Auto-load map file after assembly
"""

import os
import re
import json
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QGroupBox,
    QSplitter, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QPlainTextDocumentLayout,
    QHeaderView, QCompleter, QAbstractItemView, QLabel, QComboBox,
    QTabWidget, QToolButton, QToolTip
)
from PySide6.QtGui import (
    QFont, QFontMetrics, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter,
    QPen, QTextCursor, QTextFormat
)
from PySide6.QtCore import QRectF, QSizeF, Qt, QRegularExpression, QRect, QSize, QStringListModel, QEvent, QTimer

from assemble8080.assembler import Assembler
from assemble8080.objfile import obj_from_asm_result, save_obj, load_obj
from assemble8080.linker import link, link_from_script
from assemble8080.mapfile import parse_map
from common.i18n import LANGS, get_system_language, get_mnemonic_info
from common.encoding import read_text_auto
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



# =============================================
# FOLDING MARGIN (NPP-style) + CHANGE TRACKING
# =============================================

class FoldingArea(QWidget):
    """Vertical strip: fold +/- buttons + change indicators (yellow/green)."""

    WIDTH = 16

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.WIDTH, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.editor._on_fold_margin_click(event.pos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        self.editor._paint_fold_margin(event)


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
# CODE EDITOR WITH LINE NUMBERS, ARROWS, AUTOCOMPLETE, CTRL+CLICK
# =============================================

class FoldableDocumentLayout(QPlainTextDocumentLayout):
    """Layout that can hide specific blocks (code folding)."""

    def __init__(self, document):
        super().__init__(document)
        self._hidden = set()

    def set_hidden(self, blocks):
        self._hidden = set(blocks)
        self.requestUpdate()

    def _lh(self):
        doc = self.document()
        if doc is None:
            return 15.0
        return QFontMetrics(doc.defaultFont()).height()

    def documentSize(self):
        base = super().documentSize()
        if not self._hidden:
            return base
        return QSizeF(base.width(), max(0.0, base.height() - len(self._hidden) * self._lh()))

    def draw(self, painter, option):
        doc = self.document()
        if doc is None or not self._hidden:
            super().draw(painter, option)
            return
        total = doc.blockCount()
        segments, start, off = [], 0, 0.0
        for b in range(total):
            if b in self._hidden:
                if b > start:
                    segments.append((start, b - 1, off))
                off += self._lh()
                start = b + 1
        if start < total:
            segments.append((start, total - 1, off))
        for (a, z, o) in segments:
            painter.save()
            painter.translate(0, -o)
            top = self.blockBoundingRect(doc.findBlockByNumber(a)).top()
            bot = self.blockBoundingRect(doc.findBlockByNumber(z)).bottom()
            opt = QPlainTextDocumentLayout.PaintContext(option)
            opt.clip = QRectF(option.clip.left(), top, option.clip.width(), bot - top + 1)
            super().draw(painter, opt)
            painter.restore()


class CodeEditor(QPlainTextEdit):
    """Assembler editor: line numbers, jump arrows, autocomplete, Ctrl+Click."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.folding_area = FoldingArea(self)
        self.line_number_area = LineNumberArea(self)
        self.jumps = []  # [(src_line, dst_line), ...]
        self._is_dark = True
        self._label_lines = {}  # {LABEL: line_number} for Ctrl+Click
        # Folding state
        self._fold_regions = []  # [(start_line, end_line, name), ...]
        self._collapsed = set()  # NAMES of collapsed regions
        self._fold_saved = {}  # {name: text} saved content of collapsed regions
        # Change tracking
        self._saved_lines = []  # lines at last save/load
        self._changed_lines = set()  # currently modified line numbers
        self._saved_flash = set()  # lines to flash green after save

        self.blockCountChanged.connect(self._updateMargins)
        self.updateRequest.connect(self._updateMarginsUpdate)
        self.cursorPositionChanged.connect(self._highlightCurrentLine)
        self.textChanged.connect(self._on_text_changed)

        self._suppress_change = False
        self._cpu_type = "i8080"
        self._updateMargins(0)
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

    def set_label_lines(self, label_lines: dict):
        """Set label lines for Ctrl+Click navigation."""
        self._label_lines = label_lines

    # --- Line numbering ---

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 8 + digits * self.fontMetrics().horizontalAdvance('9')
        return LineNumberArea.ARROWS_WIDTH + space

    def _updateMargins(self, _):
        total_left = FoldingArea.WIDTH + self.lineNumberAreaWidth()
        self.setViewportMargins(total_left, 0, 0, 0)

    def _updateMarginsUpdate(self, rect, dy):
        if dy:
            self.folding_area.scroll(0, dy)
            self.line_number_area.scroll(0, dy)
        else:
            self.folding_area.update(0, rect.y(), FoldingArea.WIDTH, rect.height())
            self.line_number_area.update(0, rect.y(),
                                         self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._updateMargins(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.folding_area.setGeometry(
            QRect(cr.left(), cr.top(), FoldingArea.WIDTH, cr.height()))
        self.folding_area.raise_()
        ln_x = cr.left() + FoldingArea.WIDTH
        self.line_number_area.setGeometry(
            QRect(ln_x, cr.top(), self.lineNumberAreaWidth(), cr.height()))
        self.line_number_area.raise_()

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
                self._updateMargins(0)
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

    def _is_collapsed_marker_line(self, line_num: int) -> bool:
        """Check if the given line is a .block/.endblock marker of a collapsed region."""
        for st, en, name in self._fold_regions:
            if name in self._collapsed:
                if line_num == st or line_num == en:
                    return True
        return False

    def keyPressEvent(self, event):
        # Prohibit editing of collapsed block markers
        cursor = self.textCursor()
        line_num = cursor.blockNumber()
        if self._is_collapsed_marker_line(line_num):
            key = event.key()
            ctrl = event.modifiers() & Qt.ControlModifier
            nav_keys = (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                        Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown,
                        Qt.Key_Escape)
            if key in nav_keys:
                pass
            elif ctrl and key == Qt.Key_C:
                pass
            elif ctrl and key in (Qt.Key_V, Qt.Key_X):
                event.accept()
                return
            elif event.text() or key in (Qt.Key_Backspace, Qt.Key_Delete,
                                         Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                event.accept()
                return

        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape,
                               Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        # Tab / Shift+Tab: indent/unindent
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            sel = self.textCursor()
            if sel.hasSelection():
                # Indent all selected lines
                sel.select(QTextCursor.LineUnderCursor)
                start_block = sel.selectionStart().blockNumber()
                end_block = sel.selectionEnd().blockNumber()
                for block_num in range(start_block, end_block + 1):
                    c = QTextCursor(self.document().findBlockByNumber(block_num))
                    c.insertText('\t')
                event.accept()
                return
            # No selection: let default tab behavior happen (insert tab)
        elif event.key() == Qt.Key_Backtab or (event.key() == Qt.Key_Tab and (event.modifiers() & Qt.ShiftModifier)):
            # Shift+Tab: unindent
            sel = self.textCursor()
            if sel.hasSelection():
                # Unindent all selected lines
                start_block = sel.selectionStart().blockNumber()
                end_block = sel.selectionEnd().blockNumber()
                for block_num in range(start_block, end_block + 1):
                    c2 = QTextCursor(self.document().findBlockByNumber(block_num))
                    c2.movePosition(QTextCursor.StartOfLine)
                    c2.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    if c2.selectedText() == '\t':
                        c2.removeSelectedText()
                event.accept()
                return
            else:
                # Single line: remove one leading tab
                c = self.textCursor()
                c.movePosition(QTextCursor.StartOfLine)
                c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                if c.selectedText() == '\t':
                    c.removeSelectedText()
                    event.accept()
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

    # --- Ctrl+Click: goto label ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            cursor = self.cursorForPosition(event.pos())
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText().strip()
            if word and word.upper() in self._label_lines:
                target_line = self._label_lines[word.upper()]
                block = self.document().findBlockByNumber(target_line)
                if block.isValid():
                    new_cursor = QTextCursor(block)
                    self.setTextCursor(new_cursor)
                    self.ensureCursorVisible()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def insertFromMimeData(self, source):
        """Block paste on collapsed block marker lines."""
        cursor = self.textCursor()
        line_num = cursor.blockNumber()
        if self._is_collapsed_marker_line(line_num):
            return  # reject paste
        super().insertFromMimeData(source)

    # ------------------------------------------------------------------
    # Hover: tooltip на мнемонику + такты выделенного блока
    # ------------------------------------------------------------------



    # ------------------------------------------------------------------
    # NPP-style Code Folding
    # ------------------------------------------------------------------

    def set_cpu_type(self, cpu_type: str):
        self._cpu_type = cpu_type

    def parse_fold_regions(self):
        """Parse .block/.endblock directives using regex.
        Handles: .block, BLOCK, .endblock, ENDBLOCK, mixed case,
        trailing comments, leading whitespace, optional dot prefix.
        """
        import re as _re
        text = self.toPlainText()
        ln_list = text.split('\n')
        new_regions = []
        stack = []
        
        # Regex patterns (case-insensitive, optional dot prefix)
        re_block = _re.compile(r'^\s*\.?BLOCK\b\s*(.*)$', _re.IGNORECASE)
        re_endblock = _re.compile(r'^\s*\.?ENDBLOCK\b\s*(.*)$', _re.IGNORECASE)
        
        for i, line in enumerate(ln_list):
            # Strip trailing comment (find ; not in quotes)
            code_part = line
            in_quote = False
            quote_char = ''
            cut_pos = -1
            for ci, ch in enumerate(code_part):
                if in_quote:
                    if ch == quote_char:
                        in_quote = False
                else:
                    if ch in ('"', "'"):
                        in_quote = True
                        quote_char = ch
                    elif ch == ';':
                        cut_pos = ci
                        break
            if cut_pos >= 0:
                code_part = code_part[:cut_pos]
            
            # Check ENDBLOCK first (must be before BLOCK since ENDBLOCK contains BLOCK)
            m_end = re_endblock.match(code_part)
            if m_end:
                if stack:
                    start, name = stack.pop()
                    new_regions.append((start, i, name))
                continue

            # Check for collapsed indicator: 	{N} (replaces .endblock when collapsed)
            # Only recognized if the block is actually in collapsed state (name in self._collapsed)
            # This prevents false positives when 	{N} appears as content in expanded blocks
            m_collapsed = _re.match(r'^\{\d+\}$', code_part.strip()) if line.startswith('\t') else None
            if m_collapsed and stack:
                top_start, top_name = stack[-1]
                if top_name in self._collapsed:
                    stack.pop()
                    new_regions.append((top_start, i, top_name))
                    continue
                # Otherwise it is just content - fall through
            
            m_blk = re_block.match(code_part)
            if m_blk:
                name = m_blk.group(1).strip().strip('"').strip("'")
                if not name:
                    name = f"block_{i}"
                stack.append((i, name))
        
        # Close any unclosed blocks at end of file
        while stack:
            start, name = stack.pop()
            new_regions.append((start, len(ln_list) - 1, name))
        
        # If a saved region's marker was deleted, force-restore its text
        old_saved = dict(self._fold_saved)
        for name, saved_text in old_saved.items():
            # Check if the .block marker still exists in current text
            import re as _re2
            pattern = _re2.compile(r'^\s*\.?BLOCK\b\s*' + _re2.escape(name) + r'\b', _re2.IGNORECASE | _re2.MULTILINE)
            if not pattern.search(self.toPlainText()):
                # Marker deleted - insert saved text back at end of document
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.End)
                cursor.insertText(saved_text)
                del self._fold_saved[name]
                self._collapsed.discard(name)

        self._fold_regions = new_regions
        # Preserve collapsed state by name (regions that still exist)
        valid_names = set(r[2] for r in new_regions)
        self._collapsed = self._collapsed & valid_names
        # Clean up saved text for regions that no longer exist
        for name in list(self._fold_saved.keys()):
            if name not in valid_names:
                del self._fold_saved[name]

    def _collapse_region(self, region_idx: int):
        """Physically remove inner lines + .endblock, replace with \t{N}."""
        st, en, name = self._fold_regions[region_idx]
        if st + 1 >= en:
            return  # nothing to hide
        # Expand any inner collapsed blocks first (so their text is included)
        for inner_idx in range(len(self._fold_regions) - 1, -1, -1):
            i_st, i_en, i_name = self._fold_regions[inner_idx]
            if i_name != name and i_st > st and i_en < en and i_name in self._collapsed:
                self._expand_region(inner_idx)
                # Re-parse after expand (line numbers changed)
                self.parse_fold_regions()
                # Re-find this region (index may have changed)
                for ri in range(len(self._fold_regions)):
                    if self._fold_regions[ri][2] == name:
                        region_idx = ri
                        break
                st, en, name = self._fold_regions[region_idx]
                if st + 1 >= en:
                    return
        # Number of collapsed lines (between .block and .endblock, exclusive)
        n_lines = en - st - 1
        # Select from start of line (st+1) to END of line en (including .endblock)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        for _ in range(st + 1):
            cursor.movePosition(QTextCursor.Down)
        start_pos = cursor.position()
        # Move to start of line en, then to end of that line
        cursor.movePosition(QTextCursor.Start)
        for _ in range(en):
            cursor.movePosition(QTextCursor.Down)
        cursor.movePosition(QTextCursor.EndOfLine)
        end_pos = cursor.position()
        # Select and remove
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        removed_text = cursor.selectedText()
        cursor.removeSelectedText()
        # Insert the collapsed indicator: \t{N}
        cursor.insertText("\t{" + str(n_lines) + "}")
        self._fold_saved[name] = removed_text
        self._collapsed.add(name)

    def _expand_region(self, region_idx: int):
        """Replace the \t{N} indicator line with saved text (including .endblock)."""
        st, en, name = self._fold_regions[region_idx]
        if name not in self._fold_saved:
            return
        saved_text = self._fold_saved[name]
        # Select the \t{N} line (line en) and replace with saved text
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        for _ in range(en):
            cursor.movePosition(QTextCursor.Down)
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.insertText(saved_text)
        del self._fold_saved[name]
        self._collapsed.discard(name)

    def toggle_fold(self, region_idx: int):
        """Toggle a fold region by physically removing/inserting its inner lines."""
        if region_idx >= len(self._fold_regions):
            return
        st, en, name = self._fold_regions[region_idx]
        self._suppress_change = True
        try:
            if name in self._collapsed:
                self._expand_region(region_idx)
            else:
                self._collapse_region(region_idx)
        finally:
            self._suppress_change = False
        self.document().setModified(False)
        self.parse_fold_regions()
        self.folding_area.update()

    def collapse_all(self):
        # Collapse from bottom to top; re-check length each iteration
        # since toggle_fold() re-parses regions (list shrinks)
        while self._fold_regions:
            idx = len(self._fold_regions) - 1
            _, _, name = self._fold_regions[idx]
            if name not in self._collapsed:
                self.toggle_fold(idx)
            else:
                break

    def expand_all(self):
        # Expand from top to bottom
        for idx in range(len(self._fold_regions)):
            _, _, name = self._fold_regions[idx]
            if name in self._collapsed:
                self.toggle_fold(idx)

    def expand_all_folds(self):
        """Expand all folds (use before saving to restore full text)."""
        self.expand_all()

    def _on_fold_margin_click(self, pos):
        """Handle click in folding margin - toggle fold at clicked line."""
        y = pos.y()
        from PySide6.QtCore import QPoint
        vp_pos = QPoint(0, y)
        cursor = self.cursorForPosition(vp_pos)
        line_num = cursor.blockNumber()
        # Find fold region starting at this line
        for idx, (start, end, name) in enumerate(self._fold_regions):
            if start == line_num:
                self.toggle_fold(idx)
                return

    def _paint_fold_margin(self, event):
        """Paint folding margin: +/- buttons + change indicators."""
        painter = QPainter(self.folding_area)
        c = EDITOR_DARK if self._is_dark else EDITOR_LIGHT
        bg = c.get("line_number_bg", "#2D2D2D")
        painter.fillRect(event.rect(), QColor(bg))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = block_number
                h = round(self.blockBoundingRect(block).height())

                # Change indicator (3px right edge)
                if line_num in self._changed_lines:
                    painter.fillRect(FoldingArea.WIDTH - 3, top, 3, h, QColor("#E8C840"))
                elif line_num in self._saved_flash:
                    painter.fillRect(FoldingArea.WIDTH - 3, top, 3, h, QColor("#4CAF50"))

                # Fold button
                for idx, (start, end, name) in enumerate(self._fold_regions):
                    if start == line_num:
                        cx = FoldingArea.WIDTH // 2
                        cy = top + h // 2
                        painter.setPen(QColor("#AAAAAA"))
                        # Always draw horizontal line
                        painter.drawLine(cx - 4, cy, cx + 4, cy)
                        # If collapsed, draw vertical (making +)
                        if name in self._collapsed:
                            painter.drawLine(cx, cy - 4, cx, cy + 4)
                        break

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()

    # ------------------------------------------------------------------
    # Change Tracking
    # ------------------------------------------------------------------

    def set_saved_text(self, text: str):
        """Call after loading/saving. Resets change tracking + parses folds."""
        self._saved_lines = text.split('\n')
        self._changed_lines = set()
        self._saved_flash = set()
        self.parse_fold_regions()
        self.folding_area.update()

    def mark_saved(self):
        """Call after save. Show green on changed lines (persistent until next edit)."""
        self._saved_flash = set(self._changed_lines)
        self._changed_lines = set()
        self._saved_lines = self.toPlainText().split('\n')
        self.folding_area.update()

    def _on_text_changed(self):
        """Update change tracking (difflib-based) + re-parse folds."""
        if self._suppress_change:
            return
        import difflib
        current_lines = self.toPlainText().split('\n')
        # Use SequenceMatcher to find only actually changed/added lines
        sm = difflib.SequenceMatcher(None, self._saved_lines, current_lines, autojunk=False)
        new_changed = set()
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                # Mark lines in the new text that were replaced
                for j in range(j1, j2):
                    new_changed.add(j)
            elif tag == 'insert':
                # Mark inserted lines
                for j in range(j1, j2):
                    new_changed.add(j)
            # 'delete' and 'equal' - no marking needed
        self._changed_lines = new_changed
        self.parse_fold_regions()
        self.folding_area.update()


    def event(self, event):
        if event.type() == QEvent.ToolTip:
            try:
                pos = event.pos()

                # 1) Priority: mnemonic under cursor
                cursor = self.cursorForPosition(pos)
                block = cursor.block()
                line_text = block.text()
                char_pos = cursor.positionInBlock()
                # Manual word extraction (reliable with syntax highlighting)
                w_start = char_pos
                while w_start > 0 and (line_text[w_start - 1].isalnum() or line_text[w_start - 1] == '_'):
                    w_start -= 1
                w_end = char_pos
                while w_end < len(line_text) and (line_text[w_end].isalnum() or line_text[w_end] == '_'):
                    w_end += 1
                word = line_text[w_start:w_end].upper()

                if word:
                    lang = get_system_language()
                    info = get_mnemonic_info(word, lang, self._cpu_type)
                    if info:
                        desc, opcode, cycles = info
                        tip = f"<b>{word}</b> \u2014 {desc}<br/>"
                        tip += f"Opcode: <code>{opcode}</code> | Cycles: {cycles}"
                        QToolTip.showText(event.globalPos(), tip, self)
                        event.accept()
                        return True

                # 2) Selection: only if mouse is within selection area
                tc = self.textCursor()
                if tc.hasSelection():
                    pos_cursor = self.cursorForPosition(pos)
                    if tc.selectionStart() <= pos_cursor.position() <= tc.selectionEnd():
                        sel_text = tc.selectedText()
                        total_cycles, instr_count = self._count_selection_cycles(sel_text)
                        if instr_count > 0:
                            lang = get_system_language()
                            L = LANGS.get(lang, LANGS["en"])
                            tip = f"<b>{L.get('sel_cycles', 'Selected code')}</b>: {instr_count} instr, {total_cycles} cycles"
                            QToolTip.showText(event.globalPos(), tip, self)
                            event.accept()
                            return True

            except Exception:
                pass

            event.accept()
            return True
        return super().event(event)

    def _count_selection_cycles(self, text: str):
        """Подсчитывает количество инструкций и суммарные такты в выделенном тексте."""
        total = 0
        count = 0
        text = text.replace('\u2029', '\n')
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            # Убираем метку (первое слово + :)
            m = re.match(r'^[A-Za-z_@][A-Za-z0-9_@]*\s*::?\s*(.*)', line)
            if m:
                line = m.group(1).strip()
            if not line:
                continue
            mnemonic = line.split()[0].upper() if line.split() else ''
            info = get_mnemonic_info(mnemonic, get_system_language())
            if info:
                cycles = info[2]
                # "5/12" → берём минимальное (условие не выполнено)
                if isinstance(cycles, str) and '/' in cycles:
                    cycles = int(cycles.split('/')[0])
                total += cycles
                count += 1
        return total, count


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
        directives = r'\b(ORG|DB|DW|DS|EQU|END|INCLUDE|INPUT|OUTPUT|ORIGIN|SIZE|FILL|BLOCK|ENDBLOCK)\b'
        numbers = r'\b(0[xX][0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|[0-9]+[dD]?|[01]+[bB]|[0-7]+[qoQo])\b'
        # Global labels (::) — checked FIRST so they take priority
        global_labels = r'^([A-Za-z_][A-Za-z0-9_$]*)::'
        # Local labels (:) — single colon
        local_labels = r'^([A-Za-z_][A-Za-z0-9_$]*)\s*:(?!:)'
        registers = r'\b(A|B|C|D|E|H|L|M|PSW|SP|BC|DE|HL)\b'
        comments = r';.*$'

        colors = get_syntax_colors(self._is_dark)

        def fmt(color, bold=False, italic=False, extra_bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold or extra_bold:
                f.setFontWeight(QFont.Bold)
            if extra_bold:
                # Extra bold: use heavier weight
                f.setFontWeight(QFont.Black)
            if italic:
                f.setFontItalic(True)
            return f

        # Global label color: bright orange/yellow for dark theme, dark orange for light
        global_label_color = "#FFD700" if self._is_dark else "#CC6600"

        self._rules = [
            (QRegularExpression(comments), fmt(colors["comment"], italic=True)),
            (QRegularExpression(mnemonics, QRegularExpression.CaseInsensitiveOption),
             fmt(colors["mnemonic"], bold=True)),
            (QRegularExpression(directives, QRegularExpression.CaseInsensitiveOption),
             fmt(colors["directive"])),
            (QRegularExpression(numbers), fmt(colors["number"])),
            # Global labels (::) — extra bold + special color
            (QRegularExpression(global_labels, QRegularExpression.MultilineOption),
             fmt(global_label_color, extra_bold=True)),
            # Local labels (:) — normal bold
            (QRegularExpression(local_labels, QRegularExpression.MultilineOption),
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
# MAIN ASSEMBLER WIDGET (Notepad++ style with tabs)
# =============================================
class AssemblerWidget(QWidget):
    """Assembler tab: multi-file editor with tabs, errors, labels."""

    def __init__(self, main_window=None, is_dark=True, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_dark = is_dark
        
        self.assembler = Assembler()
        self._workspace_path = None  # Path to .ws workspace file
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- Button panel ---
        ctrl_layout = QHBoxLayout()

        #self.btn_new = QPushButton(_tr("asm_new"))
        #self.btn_new.clicked.connect(self.on_new)
        #ctrl_layout.addWidget(self.btn_new)

        self.btn_load_file = QPushButton(_tr("asm_load"))
        self.btn_load_file.clicked.connect(self.on_load_file)
        ctrl_layout.addWidget(self.btn_load_file)

        self.btn_save_file = QPushButton(_tr("asm_save"))
        self.btn_save_file.clicked.connect(self.on_save_file)
        ctrl_layout.addWidget(self.btn_save_file)

        # Workspace buttons
        self.btn_open_ws = QPushButton(_tr("asm_open_ws"))
        self.btn_open_ws.clicked.connect(self.on_open_workspace)
        ctrl_layout.addWidget(self.btn_open_ws)

        self.btn_save_ws = QPushButton(_tr("asm_save_ws"))
        self.btn_save_ws.clicked.connect(self.on_save_workspace)
        ctrl_layout.addWidget(self.btn_save_ws)

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

        ctrl_layout.addSpacing(8)
        self.btn_collapse_all = QPushButton("⚞")
        self.btn_collapse_all.setToolTip(_tr("fold_collapse_all"))
        self.btn_collapse_all.setFixedWidth(28)
        self.btn_collapse_all.clicked.connect(self._on_collapse_all)
        ctrl_layout.addWidget(self.btn_collapse_all)
        self.btn_expand_all = QPushButton("⚟")
        self.btn_expand_all.setToolTip(_tr("fold_expand_all"))
        self.btn_expand_all.setFixedWidth(28)
        self.btn_expand_all.clicked.connect(self._on_expand_all)
        ctrl_layout.addWidget(self.btn_expand_all)


        # === CPU type selector ===
        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(QLabel(_tr("asm_processor")))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(["i8080", "i8085"])
        self.cpu_combo.setCurrentText("i8080")
        self.cpu_combo.currentTextChanged.connect(self._on_cpu_changed)
        ctrl_layout.addWidget(self.cpu_combo)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # --- Horizontal splitter: editor+errors | labels ---
        h_splitter = QSplitter(Qt.Horizontal)

        # Left: tab widget + error panel
        v_splitter = QSplitter(Qt.Vertical)

        # Tab widget for multiple files
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabBar().tabMoved.connect(self._on_tab_move)
        
        # "+" button for new tab
        self.btn_add_tab = QToolButton()
        self.btn_add_tab.setText("+")
        self.btn_add_tab.setToolTip(_tr("asm_new_tab"))
        self.btn_add_tab.clicked.connect(self._add_tab)
        self.tab_widget.setCornerWidget(self.btn_add_tab, Qt.TopRightCorner)
        
        v_splitter.addWidget(self.tab_widget)

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
        self.label_table.setSortingEnabled(True)
        self.label_table.cellDoubleClicked.connect(self._on_label_double_clicked)
        lbl_layout.addWidget(self.label_table)
        self.label_group.setLayout(lbl_layout)
        h_splitter.addWidget(self.label_group)

        h_splitter.setSizes([600, 200])
        layout.addWidget(h_splitter, 1)

        # Create initial tab
        self._add_tab()

    # =============================================
    # TAB MANAGEMENT
    # =============================================

    def _add_tab(self, file_path=None, content=None, encoding=None):
        """Add a new tab with optional file path and content."""
        editor = CodeEditor(self)
        editor.setFont(QFont("Consolas", 11))
        editor.setPlaceholderText(_tr("asm_placeholder"))
        editor.set_dark(self.is_dark)
        editor.setStyleSheet(get_editor_style(self.is_dark))
        highlighter = AsmHighlighter(editor.document(), self.is_dark)
        editor.textChanged.connect(lambda: self._on_text_changed(editor))
        
        if content is not None:
            editor._suppress_change = True
            editor.setPlainText(content)
            editor._suppress_change = False
            editor.set_saved_text(content)
        
        # Track tab state
        tab_info = {
            'editor': editor,
            'highlighter': highlighter,
            'file_path': file_path,
            'modified': False,
            'encoding': encoding,  # original file encoding (None = new/UTF-8)
        }
        
        # Connect modified tracking
        editor.document().modificationChanged.connect(
            lambda m, ti=tab_info: self._on_tab_modified(ti, m))
        
        # Add to tab widget
        tab_index = self.tab_widget.addTab(editor, self._tab_title(file_path))
        self.tab_widget.setCurrentIndex(tab_index)
        
        # Store tab info
        self._tab_infos = getattr(self, '_tab_infos', [])
        self._tab_infos.append(tab_info)
        
        # Update label lines and jumps
        self._update_tab_labels(editor)
        
        return tab_index

    def _on_tab_close(self, index):
        """Close a tab."""
        if not hasattr(self, '_tab_infos') or index >= len(self._tab_infos):
            return
        
        tab_info = self._tab_infos[index]
        editor = tab_info['editor']
        
        # Check for unsaved changes
        if editor.document().isModified():
            title = self._tab_title(tab_info['file_path'])
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(_tr("asm_unsaved_title"))
            msg_box.setText(_tr("asm_unsaved_msg").format(file=title))
            btn_save = msg_box.addButton(_tr("btn_save"), QMessageBox.AcceptRole)
            btn_discard = msg_box.addButton(_tr("btn_discard"), QMessageBox.DestructiveRole)
            btn_cancel = msg_box.addButton(_tr("btn_cancel"), QMessageBox.RejectRole)
            msg_box.exec()
            reply = msg_box.clickedButton()
            if reply == btn_save:
                reply = QMessageBox.Save
            elif reply == btn_cancel:
                reply = QMessageBox.Cancel
            else:
                reply = QMessageBox.Discard
            if reply == QMessageBox.Save:
                self._save_tab(index)
            elif reply == QMessageBox.Cancel:
                return
        
        # Remove from tab widget
        self.tab_widget.removeTab(index)
        editor.deleteLater()
        
        # Remove from tab infos
        self._tab_infos.pop(index)
        
        # If no tabs left, add a new one
        if self.tab_widget.count() == 0:
            self._add_tab()

    def _on_tab_changed(self, index):
        """Handle tab change: update label table + label lines + jumps."""
        if not hasattr(self, '_tab_infos') or index < 0 or index >= len(self._tab_infos):
            return
        tab_info = self._tab_infos[index]
        editor = tab_info['editor']
        # Update label lines and jumps for the new current tab
        self._update_tab_labels(editor)
        # Update label table from stored assembly result
        last_result = tab_info.get('last_result')
        if last_result:
            self._update_labels_table(
                last_result.get('symbols', {}),
                last_result.get('global_labels'),
                last_result.get('equ_symbols'))
        else:
            self._update_labels_table({})

    def _on_tab_move(self, from_idx, to_idx):
        if not hasattr(self, '_tab_infos'):
            return
        if 0 <= from_idx < len(self._tab_infos) and 0 <= to_idx < len(self._tab_infos):
            item = self._tab_infos.pop(from_idx)
            self._tab_infos.insert(to_idx, item)

    def _on_tab_modified(self, tab_info, modified):
        """Handle tab modification."""
        tab_info['modified'] = modified
        # Update tab title
        for i, ti in enumerate(self._tab_infos):
            if ti is tab_info:
                self.tab_widget.setTabText(i, self._tab_title(ti['file_path'], ti['modified']))
                break

    def _tab_title(self, file_path, modified=False):
        """Generate tab title from file path."""
        if file_path:
            name = os.path.basename(file_path)
        else:
            name = _tr("asm_untitled")
        if modified:
            name += " ●"
        return name

    def _current_editor(self):
        """Get the current tab's editor."""
        index = self.tab_widget.currentIndex()
        if 0 <= index < len(self._tab_infos):
            return self._tab_infos[index]['editor']
        return None

    def _current_tab_info(self):
        """Get the current tab's info dict."""
        index = self.tab_widget.currentIndex()
        if 0 <= index < len(self._tab_infos):
            return self._tab_infos[index]
        return None

    def _save_tab(self, index):
        """Save a specific tab."""
        if index < 0 or index >= len(self._tab_infos):
            return
        tab_info = self._tab_infos[index]
        editor = tab_info['editor']
        file_path = tab_info['file_path']
        
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, _tr("asm_save_title"), "",
                _tr("asm_file_filter_save"))
            if not file_path:
                return
            tab_info['file_path'] = file_path
        
        editor.expand_all_folds()
        try:
            # Always save as UTF-8 (no BOM). If the file was opened in
            # another encoding, this is the moment it gets converted on disk.
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(editor.toPlainText())
            editor.mark_saved()
            editor.document().setModified(False)
            self.tab_widget.setTabText(index, self._tab_title(file_path, False))
            if self.main_window is not None:
                self.main_window.log(_tr("asm_saved").format(path=file_path))
                orig_enc = tab_info.get('encoding')
                if orig_enc and not orig_enc.startswith('utf-8'):
                    self.main_window.log(_tr("asm_saved_utf8").format(path=file_path))
                    tab_info['encoding'] = 'utf-8'
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_err_title"),
                                 _tr("asm_save_err").format(e=e))

    # =============================================
    # WORKSPACE SUPPORT
    # =============================================

    def on_open_workspace(self):
        """Open a workspace file (.ws)."""
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("asm_open_ws_title"), "",
            _tr("asm_ws_filter"))
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                ws = json.load(f)
            self._workspace_path = path
            ws_dir = os.path.dirname(path)
            
            # Close ALL existing tabs
            while self.tab_widget.count() > 0:
                idx2 = self.tab_widget.count() - 1
                self.tab_widget.removeTab(idx2)
                if idx2 < len(self._tab_infos):
                    self._tab_infos[idx2]['editor'].deleteLater()
                    self._tab_infos.pop(idx2)
            
            # Open files from workspace
            files = ws.get('files', [])
            for i, fpath in enumerate(files):
                full_path = os.path.join(ws_dir, fpath) if not os.path.isabs(fpath) else fpath
                if os.path.exists(full_path):
                    try:
                        content, enc, converted = read_text_auto(full_path)
                        self._add_tab(full_path, content, encoding=enc)
                    except Exception:
                        pass
                else:
                    # File doesn't exist, create empty tab
                    self._add_tab(full_path, "")
            
            # Set active tab
            active = ws.get('active', 0)
            if 0 <= active < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(active)
            
            if self.main_window is not None:
                self.main_window.log(_tr("asm_ws_loaded").format(path=path, n=len(files)))
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_err_title"),
                                 _tr("asm_ws_err").format(e=e))

    def on_save_workspace(self):
        """Save workspace file (.ws)."""
        if self._workspace_path:
            path = self._workspace_path
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, _tr("asm_save_ws_title"), "",
                _tr("asm_ws_filter_save"))
            if not path:
                return
        
        # Collect file paths from tabs
        files = []
        for ti in self._tab_infos:
            if ti['file_path']:
                # Store relative path if possible
                if self._workspace_path:
                    ws_dir = os.path.dirname(self._workspace_path)
                    try:
                        rel = os.path.relpath(ti['file_path'], ws_dir)
                        files.append(rel)
                    except ValueError:
                        files.append(ti['file_path'])
                else:
                    files.append(ti['file_path'])
        
        ws = {
            'version': 1,
            'files': files,
            'active': self.tab_widget.currentIndex(),
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ws, f, indent=2)
            self._workspace_path = path
            if self.main_window is not None:
                self.main_window.log(_tr("asm_ws_saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_err_title"),
                                 _tr("asm_ws_save_err").format(e=e))

    # =============================================
    # NAVIGATION
    # =============================================

    def _goto_line(self, line_num):
        """Goto line (0-based) in current editor."""
        editor = self._current_editor()
        if editor:
            block = editor.document().findBlockByNumber(line_num)
            if block.isValid():
                cursor = QTextCursor(block)
                editor.setTextCursor(cursor)
                editor.ensureCursorVisible()
                editor.setFocus()

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

    # =============================================
    # LABEL AND JUMP COLLECTION
    # =============================================

    def _collect_label_lines(self, editor=None):
        """Collect {LABEL: line_number} from editor text."""
        if editor is None:
            editor = self._current_editor()
        if editor is None:
            return {}
        lines = editor.toPlainText().split('\n')
        label_lines = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Global label (::)
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_$]*)::', stripped)
            if m:
                label_lines[m.group(1).upper()] = i
                continue
            # Local label (:)
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_$]*)\s*:(?!:)', stripped)
            if m:
                label_lines[m.group(1).upper()] = i
        return label_lines

    def _compute_jumps(self, editor=None):
        """Compute jumps [(src_line, dst_line), ...]."""
        if editor is None:
            editor = self._current_editor()
        if editor is None:
            return
        lines = editor.toPlainText().split('\n')
        label_lines = self._collect_label_lines(editor)
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

        editor.set_jumps(jumps)

    def _update_tab_labels(self, editor):
        """Update label lines and jumps for a specific editor."""
        label_lines = self._collect_label_lines(editor)
        editor.set_label_lines(label_lines)
        self._compute_jumps(editor)
        labels = list(label_lines.keys())
        editor.set_completions(KEYWORDS + labels)

    def _on_text_changed(self, editor):
        """On text change — recompute jumps and update autocomplete."""
        self._update_tab_labels(editor)

        # Real-time validation for .lnk files
        ti = self._current_tab_info()
        if ti and (ti.get('file_path') or '').lower().endswith('.lnk'):
            errors = self._validate_lnk_file(editor)
            self._update_errors(errors)

    # =============================================
    # LNK FILE VALIDATION
    # =============================================

    def _validate_lnk_file(self, editor):
        """Validate .lnk file in real-time. Returns list of (line, message) errors."""
        errors = []
        try:
            from assemble8080.linker import parse_link_script
            text = editor.toPlainText()
            config = parse_link_script(text)

            # Check that INPUT files exist
            file_path = self._current_tab_info()['file_path'] if self._current_tab_info() else None
            if file_path:
                import os
                script_dir = os.path.dirname(os.path.abspath(file_path))
                for inp in config.get("inputs", []):
                    inp_path = inp if os.path.isabs(inp) else os.path.join(script_dir, inp)
                    if not os.path.exists(inp_path):
                        # Find the line number
                        for i, line in enumerate(text.split('\n')):
                            if line.strip().upper().startswith('INPUT') and inp in line:
                                errors.append((i + 1, f"Input file not found: {inp}"))
                                break
                        else:
                            errors.append((1, f"Input file not found: {inp}"))

            # Check that OUTPUT is specified (non-default)
            if config.get("output") == "output.bin":
                # Check if OUTPUT line exists
                has_output = False
                for line in text.split('\n'):
                    if line.strip().upper().startswith('OUTPUT'):
                        has_output = True
                        break
                if not has_output:
                    errors.append((1, "OUTPUT not specified"))
        except Exception:
            pass
        return errors

    # =============================================
    # ERROR PANEL UPDATE
    # =============================================

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
        editor = self._current_editor()
        if editor:
            editor.highlight_error_lines(error_lines)

    # =============================================
    # LABEL TABLE UPDATE
    # =============================================

    def _update_labels_table(self, symbols, global_labels=None, equ_symbols=None):
        """Fill label table with color coding.
        symbols: {label: address}, global_labels: set, equ_symbols: set
        Labels: default color, EQU/DEFINE: orange, Global: bold+gold
        """
        self.label_table.setSortingEnabled(False)
        self.label_table.setRowCount(0)
        editor = self._current_editor()
        label_lines = self._collect_label_lines(editor) if editor else {}
        sorted_symbols = sorted(symbols.items(), key=lambda x: x[1])
        
        # Colors
        color_label = QColor("#FFFFFF") if self.is_dark else QColor("#000000")
        color_equ = QColor("#FFA500") if self.is_dark else QColor("#CC6600")
        color_global = QColor("#FFD700") if self.is_dark else QColor("#996600")
        
        for label, addr in sorted_symbols:
            row = self.label_table.rowCount()
            self.label_table.insertRow(row)
            
            is_equ = equ_symbols and label in equ_symbols
            is_global = global_labels and label in global_labels
            
            # Label name with color coding
            label_item = QTableWidgetItem(label)
            if is_global:
                label_item.setFont(QFont("Consolas", 10, QFont.Bold))
                label_item.setForeground(color_global)
            elif is_equ:
                label_item.setForeground(color_equ)
                label_item.setFont(QFont("Consolas", 10, QFont.Bold))
            else:
                label_item.setForeground(color_label)
            self.label_table.setItem(row, 0, label_item)
            
            # Address (with numeric sort key)
            addr_item = QTableWidgetItem(f"0x{addr:04X}")
            addr_item.setData(Qt.UserRole, addr)
            self.label_table.setItem(row, 1, addr_item)
            
            # Line number (with numeric sort key)
            ln = label_lines.get(label, -1)
            line_item = QTableWidgetItem(str(ln + 1) if ln >= 0 else "-")
            line_item.setData(Qt.UserRole, ln + 1 if ln >= 0 else 999999)
            self.label_table.setItem(row, 2, line_item)
        
        self.label_table.setSortingEnabled(True)

    # =============================================
    # BUTTON HANDLERS
    # =============================================

    def _on_cpu_changed(self, cpu_type: str):
        for ti in getattr(self, '_tab_infos', []):
            ti['editor'].set_cpu_type(cpu_type)

    def retranslate(self):
        """Update all translatable strings (called on language change)."""
        self.btn_collapse_all.setToolTip(_tr("fold_collapse_all"))
        self.btn_expand_all.setToolTip(_tr("fold_expand_all"))
        self.btn_assemble.setText(_tr("asm_assemble"))
        self.btn_assemble_load.setText(_tr("asm_assemble_load"))
        self.btn_assemble_obj.setText(_tr("asm_assemble_obj"))
        self.btn_link.setText(_tr("asm_link"))
        # Update folding area tooltips
        if hasattr(self, 'folding_area'):
            self.folding_area.update()

    def _on_collapse_all(self):
        editor = self._current_editor()
        if editor:
            editor.collapse_all()

    def _on_expand_all(self):
        editor = self._current_editor()
        if editor:
            editor.expand_all()

    def on_new(self):
        """New program: add a new empty tab."""
        self._add_tab()

    def on_assemble(self):
        self._do_assemble(load_to_memory=False)

    def on_assemble_load(self):
        self._do_assemble(load_to_memory=True)

    def on_assemble_obj(self):
        """Assemble and save object file (.obj)."""
        self.assembler.cpu_type = self.cpu_combo.currentText()
        editor = self._current_editor()
        if not editor:
            return
        editor.expand_all_folds()
        source = editor.toPlainText()
        if not source.strip():
            if self.main_window is not None:
                self.main_window.log(_tr("asm_no_code"))
            return
        try:
            file_path = self._current_tab_info()['file_path'] if self._current_tab_info() else None
            result = self.assembler.assemble(source, file_path or '')
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
        self._apply_cpu_from_source()

        # Save map file
        file_path = self._current_tab_info()['file_path'] if self._current_tab_info() else None
        if result.map_text and file_path:
            map_path = os.path.splitext(file_path)[0] + '.map'
            try:
                from assemble8080.mapfile import save_map_file
                save_map_file(map_path, result.map_text)
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_saved").format(path=map_path))
            except Exception as e:
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_map_save_err").format(e=e))
        
        # Determine default obj path
        if file_path:
            default = os.path.splitext(file_path)[0] + '.obj'
        else:
            default = 'output.obj'
        path, _ = QFileDialog.getSaveFileName(
            self, _tr("asm_obj_title"), default, _tr("asm_obj_filter"))
        if not path:
            return
        try:
            obj = obj_from_asm_result(result, file_path or '')
            save_obj(path, obj)
            if self.main_window is not None:
                self.main_window.log(_tr("asm_obj_saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, _tr("asm_err_title"),
                                 _tr("asm_obj_err").format(e=e))

    def on_link(self):
        """Link object files using a linker script (.lnk) or selected .obj files."""
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
        """Load a file into a new tab."""
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("asm_load_title"), "",
            _tr("asm_file_filter"))
        if path:
            try:
                content, enc, converted = read_text_auto(path)
                self._add_tab(path, content, encoding=enc)
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_loaded").format(path=path))
                    if converted:
                        self.main_window.log(_tr("asm_encoding_converted").format(enc=enc))
            except Exception as e:
                QMessageBox.critical(self, _tr("asm_err_title"),
                                     _tr("asm_load_err").format(e=e))

    def on_save_file(self):
        """Save the current tab's file."""
        self._save_tab(self.tab_widget.currentIndex())

    # =============================================
    # ASSEMBLY
    # =============================================

    def _do_assemble(self, load_to_memory=False):
        """Assemble the current tab's source code."""
        self.assembler.cpu_type = self.cpu_combo.currentText()
        
        if self.main_window is not None:
            self.main_window.log(_tr("asm_assembling"))

        editor = self._current_editor()
        if not editor:
            return
        editor.expand_all_folds()
        source = editor.toPlainText()
        if not source.strip():
            if self.main_window is not None:
                self.main_window.log(_tr("asm_no_code"))
            return

        file_path = self._current_tab_info()['file_path'] if self._current_tab_info() else None

        # Variant D: auto-detect .lnk files
        if file_path and file_path.lower().endswith('.lnk'):
            self._do_link_from_current_tab()
            return

        try:
            result = self.assembler.assemble(source, file_path or '')
        except Exception:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_exception").format(tb=traceback.format_exc()))
            return

        self._compute_jumps(editor)

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
            ti = self._current_tab_info()
            if ti:
                ti['last_result'] = None
            return

        # Success
        self._update_errors([])
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

        # Update labels table with global label info
        self._update_labels_table(result.symbols, result.global_labels,
                                  getattr(result, 'equ_symbols', None))
        # Store result in tab info for tab-switch restore
        ti = self._current_tab_info()
        if ti:
            ti['last_result'] = {
                'symbols': result.symbols,
                'global_labels': result.global_labels,
                'equ_symbols': getattr(result, 'equ_symbols', None),
            }

        # Save map file
        if result.map_text and file_path:
            map_path = os.path.splitext(file_path)[0] + '.map'
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
            # Auto-load map into disassembler (only on assemble+load)
            # Extract EQU constants for disassembler substitution
            if self.main_window is not None and hasattr(result, 'equ_symbols'):
                self.main_window.equ_dict = {
                    result.symbols[n]: n for n in result.equ_symbols
                    if n in result.symbols
                }
            self._auto_load_map(result)

    def _auto_load_map(self, result):
        """Auto-load map file into disassembler and emulator."""
        if not result.map_text or self.main_window is None:
            return
        try:
            mf = parse_map(result.map_text)
            self.main_window.map_file = mf
            # Set map on disassembler (same as manual load)
            self.main_window.disassembler.set_map(mf)
            # Set EQU constants for value substitution
            if hasattr(self.main_window, 'equ_dict') and self.main_window.equ_dict:
                self.main_window.disassembler.set_equ(self.main_window.equ_dict)
            # Update main disassembler view with symbols
            if hasattr(self.main_window, 'disasm_view') and hasattr(self.main_window.disasm_view, 'set_symbols'):
                self.main_window.disasm_view.set_symbols(mf)
            # Update emulator disasm view with symbols
            if hasattr(self.main_window, 'emu_disasm_view') and hasattr(self.main_window.emu_disasm_view, 'set_symbols'):
                self.main_window.emu_disasm_view.set_symbols(mf)
            # Update disasm range to match actual binary size (like emulator does)
            if result.binary:
                origin = result.origin
                size = len(result.binary)
                mw = self.main_window
                if hasattr(mw, 'disasm_start'):
                    mw.disasm_start.setText(f"{origin:04X}")
                if hasattr(mw, 'disasm_len'):
                    mw.disasm_len.setText(f"{size:04X}")
            # Re-run main disassembly to show resolved symbols in text
            if hasattr(self.main_window, 'run_disasm'):
                self.main_window.run_disasm()
            # Re-run emulator disassembly to show resolved symbols in text
            if hasattr(self.main_window, 'update_emu_disasm_view'):
                self.main_window.update_emu_disasm_view()
            if self.main_window is not None:
                self.main_window.log(_tr("asm_map_auto_loaded").format(n=len(mf.entries)))
        except Exception as e:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_map_auto_err").format(e=e))

    def _do_link_from_current_tab(self):
        """Link using the current .lnk tab as linker script."""
        editor = self._current_editor()
        if not editor:
            return
        file_path = self._current_tab_info()['file_path']
        try:
            from assemble8080.linker import link_from_script
            result = link_from_script(file_path)
            if not result.success:
                if self.main_window is not None:
                    self.main_window.log(_tr("asm_link_errors").format(n=len(result.errors)))
                    for err in result.errors:
                        self.main_window.log(_tr("asm_link_err").format(msg=err.message))
                return
            if self.main_window is not None:
                self.main_window.log(_tr("asm_link_success").format(n=len(result.binary), path=file_path))
            # Load binary to memory
            if result.binary:
                self._load_to_memory(result.binary, result.origin)
        except Exception as e:
            if self.main_window is not None:
                self.main_window.log(_tr("asm_link_fail").format(e=e))

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
        """Auto-detect CPU type from source directives."""
        cpu_from_source = self.assembler.cpu_set_by_directive
        cpu_type = self.assembler.cpu_type

        if cpu_from_source:
            if self.main_window is not None and hasattr(self.main_window, '_set_cpu_type'):
                self.main_window._set_cpu_type(cpu_type, source='assembler')
            self.cpu_combo.blockSignals(True)
            self.cpu_combo.setCurrentText(cpu_type)
            self.cpu_combo.blockSignals(False)
            self.cpu_combo.setEnabled(False)
            if self.main_window is not None:
                if hasattr(self.main_window, 'emu_cpu_combo'):
                    self.main_window.emu_cpu_combo.setEnabled(False)
                if hasattr(self.main_window, 'disasm_cpu_combo'):
                    self.main_window.disasm_cpu_combo.setEnabled(False)
        else:
            self.cpu_combo.setEnabled(True)
            if self.main_window is not None:
                if hasattr(self.main_window, 'emu_cpu_combo'):
                    self.main_window.emu_cpu_combo.setEnabled(True)
                if hasattr(self.main_window, 'disasm_cpu_combo'):
                    self.main_window.disasm_cpu_combo.setEnabled(True)

    # =============================================
    # THEME
    # =============================================

    def set_theme(self, is_dark: bool):
        """Update assembler widget theme."""
        self.is_dark = is_dark
        for ti in self._tab_infos:
            ti['highlighter'].set_theme(is_dark)
            ti['editor'].set_dark(is_dark)
            ti['editor'].setStyleSheet(get_editor_style(is_dark))
        # Update button labels for new language
        #self.btn_new.setText(_tr("asm_new"))
        self.btn_load_file.setText(_tr("asm_load"))
        self.btn_save_file.setText(_tr("asm_save"))
        self.btn_open_ws.setText(_tr("asm_open_ws"))
        self.btn_save_ws.setText(_tr("asm_save_ws"))
        self.btn_assemble.setText(_tr("asm_assemble"))
        self.btn_assemble_load.setText(_tr("asm_assemble_load"))
        self.btn_assemble_obj.setText(_tr("asm_assemble_obj"))
        self.btn_link.setText(_tr("asm_link"))
        self.error_group.setTitle(_tr("asm_errors"))
        self.error_table.setHorizontalHeaderLabels([_tr("asm_col_line"), _tr("asm_col_msg")])
        self.label_group.setTitle(_tr("asm_labels"))
        self.label_table.setHorizontalHeaderLabels(
            [_tr("asm_col_label"), _tr("asm_col_addr"), _tr("asm_col_line2")])
        for ti in self._tab_infos:
            ti['editor'].setPlaceholderText(_tr("asm_placeholder"))

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
        editor = self._current_editor()
        if editor:
            editor.setPlainText('\n'.join(text_lines))
