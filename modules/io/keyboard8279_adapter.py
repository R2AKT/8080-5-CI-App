"""
Адаптер клавиатуры для 8279.
Реализует тот же интерфейс, что и Keyboard8x8.
Виджет клавиатуры работает с обоими адаптерами одинаково.
"""
from .keyboard8x8 import RADIO86RK_KEYMAP


class Keyboard8279Adapter:
    """Адаптер клавиатуры для 8279.
    
    Преобразует нажатия кнопок виджета (row, col) в коды клавиш для 8279.
    Код клавиши формируется как (строка << 3) | столбец.
    """
    
    def __init__(self, name="Keyboard 8279"):
        self.name = name
        self.base_port = -1  # Виртуальное устройство
        self._i8279 = None
        self.keymap = dict(RADIO86RK_KEYMAP)
        self.matrix = [[False] * 8 for _ in range(8)]
        self.shift_active = False
    
    def connect_to_8279(self, i8279):
        """Подключить адаптер к 8279"""
        self._i8279 = i8279
    
    def press_key(self, row, col):
        """Нажать клавишу — отправить код в 8279"""
        if 0 <= row < 8 and 0 <= col < 8:
            self.matrix[row][col] = True
            if row == 4 and col == 7:
                self.shift_active = True
            # Код клавиши для 8279: (строка << 3) | столбец
            key_data = (row << 3) | col
            if self._i8279:
                self._i8279.key_press(key_data)
    
    def release_key(self, row, col):
        """Отпустить клавишу"""
        if 0 <= row < 8 and 0 <= col < 8:
            self.matrix[row][col] = False
            if row == 4 and col == 7:
                self.shift_active = False
            # 8279 сам обрабатывает отпускание
    
    def release_all(self):
        """Отпустить все клавиши"""
        for r in range(8):
            for c in range(8):
                self.matrix[r][c] = False
        self.shift_active = False
    
    def get_char_at(self, row, col):
        """Получить символ по координатам"""
        entry = self.keymap.get((row, col))
        if entry:
            return entry[1] if self.shift_active else entry[0]
        return ' '
    
    def get_state(self):
        """Состояние для отладки"""
        pressed = []
        for r in range(8):
            for c in range(8):
                if self.matrix[r][c]:
                    char = self.get_char_at(r, c)
                    pressed.append(f"({r},{c})='{char}'")
        return {
            "name": self.name,
            "type": "Keyboard 8279 Adapter",
            "base_port": "-",
            "shift_active": self.shift_active,
            "pressed_keys": ", ".join(pressed) if pressed else "(нет)",
            "i8279_device": self._i8279.name if self._i8279 else "не подключён",
        }
