"""
Виджет клавиатуры 8×8 для Радио-86РК / Микро-80.
Сетка кнопок, соответствующая физической раскладке.
Нажатие кнопки мыши → пресс/релиз клавиши в матрице.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class KeyboardWidget(QWidget):
    """Виджет клавиатуры: сетка кнопок 8×8"""

    def __init__(self, keyboard, parent=None):
        super().__init__(parent)
        self.keyboard = keyboard
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle(f"Клавиатура — {keyboard.name}")
        self.setMinimumSize(420, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Заголовок
        header = QLabel(f"<b>{self.keyboard.name}</b> — Радио-86РК / Микро-80 (КОИ-7, набор 2)")
        header.setFont(QFont("Segoe UI", 9))
        layout.addWidget(header)

        hint = QLabel("Набор 1 = прописные, Набор 2 (АР2) = строчные/знаки")
        hint.setFont(QFont("Segoe UI", 8))
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        # Сетка кнопок 8×8
        grid = QGridLayout()
        grid.setSpacing(3)
        self.buttons = {}

        for row in range(8):
            for col in range(8):
                # Определяем подпись кнопки
                entry = self.keyboard.keymap.get((row, col))
                if entry:
                    char1, char2 = entry
                    # Отображаем символ набора 1 (или спец. название)
                    label = self._format_label(char1, char2, row, col)
                else:
                    label = ""

                btn = QPushButton(label)
                btn.setFixedSize(48, 40)
                btn.setFont(QFont("Consolas", 9))

                # Для клавиши АР2 — особый стиль
                if row == 4 and col == 7:
                    btn.setStyleSheet("background-color: #4a4a2a;")

                # Подключение событий нажатия/отпускания
                btn.pressed.connect(lambda r=row, c=col: self._on_press(r, c))
                btn.released.connect(lambda r=row, c=col: self._on_release(r, c))

                grid.addWidget(btn, row, col)
                self.buttons[(row, col)] = btn

        layout.addLayout(grid)

        # Индикатор состояния
        self.lbl_status = QLabel("Нет нажатых клавиш")
        self.lbl_status.setFont(QFont("Consolas", 8))
        self.lbl_status.setStyleSheet("color: #6a6;")
        layout.addWidget(self.lbl_status)

    def _format_label(self, char1, char2, row, col):
        """Форматировать подпись кнопки"""
        # Специальные клавиши
        special = {
            (1, 4): "БК",      # Забой
            (1, 5): "ТАБ",     # Табуляция
            (1, 6): "ВК",      # Возврат каретки
            (1, 7): "СБР",     # Сброс
            (4, 7): "АР2",     # Аналог Shift
            (5, 7): "ПС",      # Пробел
            (6, 0): "←",
            (6, 1): "→",
            (6, 2): "↑",
            (6, 3): "↓",
            (6, 4): "ПРОБЕЛ",
        }
        if (row, col) in special:
            return special[(row, col)]
        # Обычный символ
        if char1 == ' ':
            return "ПРОБЕЛ" if (row, col) == (5, 7) else ""
        if char1 == '\b':
            return "БК"
        if char1 == '\t':
            return "ТАБ"
        if char1 == '\r':
            return "ВК"
        if char1 == '\x1b':
            return "←"
        return char1

    def _on_press(self, row, col):
        """Кнопка мыши нажата"""
        self.keyboard.press_key(row, col)
        self._update_status()

    def _on_release(self, row, col):
        """Кнопка мыши отпущена"""
        self.keyboard.release_key(row, col)
        self._update_status()

    def _update_status(self):
        """Обновить индикатор состояния"""
        pressed = []
        for r in range(8):
            for c in range(8):
                if self.keyboard.matrix[r][c]:
                    pressed.append(self.keyboard.get_char_at(r, c))
        if pressed:
            self.lbl_status.setText("Нажато: " + " ".join(pressed))
        else:
            self.lbl_status.setText("Нет нажатых клавиш")

    def closeEvent(self, event):
        # При закрытии отпускаем все клавиши
        self.keyboard.release_all()
        event.accept()

    def showEvent(self, event):
        """Получить фокус при показе окна"""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def set_always_on_top(self, enabled):
        """Установить/снять флаг поверх всех окон"""
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()  # Нужно после setWindowFlags
