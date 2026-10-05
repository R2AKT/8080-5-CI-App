"""
Клавиатурная матрица 8×8 для Радио-86РК / Микро-80.
Подключается к 8255 как внешний модуль.
Не изменяет сам 8255.

Принцип работы:
- 8255 записывает номер строки в выходной порт (обычно Port A)
- Клавиатура возвращает состояние столбцов через входной порт (обычно Port B)
- Нажатая клавиша замыкает строку на столбец → бит столбца = 0

Кодировка: KOI-7, набор 2.
"""


# Раскладка Радио-86РК (набор 1 / набор 2)
# Формат: (строка, столбец): (символ_набор1, символ_набор2)
RADIO86RK_KEYMAP = {
    # Строка 0: цифры и знаки
    (0, 0): ('1', '!'),
    (0, 1): ('2', '"'),
    (0, 2): ('3', '#'),
    (0, 3): ('4', '$'),
    (0, 4): ('5', '%'),
    (0, 5): ('6', '&'),
    (0, 6): ('7', "'"),
    (0, 7): ('8', '*'),
    # Строка 1: цифры и управление
    (1, 0): ('9', '('),
    (1, 1): ('0', ')'),
    (1, 2): ('-', '_'),
    (1, 3): ('=', '+'),
    (1, 4): ('\b', '\b'),     # БК (забой)
    (1, 5): ('\t', '\t'),     # ТАБ
    (1, 6): ('\r', '\r'),     # ВК (возврат каретки)
    (1, 7): (' ', ' '),       # СБР / ПРОБЕЛ
    # Строка 2: Й Ц У К Е Н Г Ш
    (2, 0): ('J', 'j'),       # Й
    (2, 1): ('C', 'c'),       # Ц
    (2, 2): ('U', 'u'),       # У
    (2, 3): ('K', 'k'),       # К
    (2, 4): ('E', 'e'),       # Е
    (2, 5): ('N', 'n'),       # Н
    (2, 6): ('G', 'g'),       # Г
    (2, 7): ('W', 'w'),       # Ш
    # Строка 3: Щ З Х Ъ Ф Ы В А
    (3, 0): ('Q', 'q'),       # Щ
    (3, 1): ('Z', 'z'),       # З
    (3, 2): ('[', '{'),       # Х
    (3, 3): (']', '}'),       # Ъ
    (3, 4): ('F', 'f'),       # Ф
    (3, 5): ('Y', 'y'),       # Ы
    (3, 6): ('V', 'v'),       # В
    (3, 7): ('A', 'a'),       # А
    # Строка 4: П Р О Л Д Ж Э АР2
    (4, 0): ('P', 'p'),       # П
    (4, 1): ('R', 'r'),       # Р
    (4, 2): ('O', 'o'),       # О
    (4, 3): ('L', 'l'),       # Л
    (4, 4): ('D', 'd'),       # Д
    (4, 5): (';', ':'),       # Ж
    (4, 6): ('"', '~'),       # Э
    (4, 7): ('^', '^'),       # АР2 (аналог Shift)
    # Строка 5: Я Ч С М И Т Ь ПС
    (5, 0): ('X', 'x'),       # Я
    (5, 1): ('T', 't'),       # Ч  (конфликт с (4,5), корректировать!)
    (5, 2): ('S', 's'),       # С
    (5, 3): ('M', 'm'),       # М
    (5, 4): ('I', 'i'),       # И
    (5, 5): ('H', 'h'),       # Т  (конфликт, корректировать!)
    (5, 6): ('B', 'b'),       # Ь
    (5, 7): (' ', ' '),       # ПС (пробел)
    # Строка 6: стрелки
    (6, 0): ('\x1b', '\x1b'), # ← (ESC)
    (6, 1): ('\x1c', '\x1c'), # →
    (6, 2): ('\x1d', '\x1d'), # ↑
    (6, 3): ('\x1e', '\x1e'), # ↓
    (6, 4): (' ', ' '),       # ПРОБЕЛ
    (6, 5): (' ', ' '),
    (6, 6): (' ', ' '),
    (6, 7): (' ', ' '),
    # Строка 7: специальные
    (7, 0): (' ', ' '),
    (7, 1): (' ', ' '),
    (7, 2): (' ', ' '),
    (7, 3): (' ', ' '),
    (7, 4): (' ', ' '),
    (7, 5): (' ', ' '),
    (7, 6): (' ', ' '),
    (7, 7): (' ', ' '),
}


class Keyboard8x8:
    """Клавиатурная матрица 8×8.
    
    Подключается к портам 8255:
    - Выходной порт (обычно A) — выбор строки (биты 0-2)
    - Входной порт (обычно B) — чтение столбцов (биты 0-7)
    
    Активный уровень: нажатая клавиша = 0 (низкий уровень).
    """
    
    def __init__(self, name="Keyboard 8x8"):
        self.name = name
        self.base_port = -1  # Виртуальное устройство, не занимает порты IO
        # Матрица 8×8: [строка][столбец] = нажата ли клавиша
        self.matrix = [[False] * 8 for _ in range(8)]
        # Текущая выбранная строка (устанавливается через выходной порт)
        self.current_row = 0
        # Раскладка
        self.keymap = dict(RADIO86RK_KEYMAP)
        # Состояние АР2 (аналог Shift)
        self.shift_active = False
        # Ссылка на 8255
        self._ppi = None
        self._output_port = 0  # Порт выбора строки
        self._input_port = 1   # Порт чтения столбцов
    
    def connect_to_ppi(self, ppi, output_port=0, input_port=1):
        """Подключить клавиатуру к 8255.
        
        После подключения клавиатура:
        - Следит за записями в выходной порт (выбор строки)
        - Подаёт данные столбцов на входной порт
        """
        self._ppi = ppi
        self._output_port = output_port
        self._input_port = input_port
        
        # Подключаем callback на изменение выходного порта
        original_callback = ppi.on_port_change
        
        def on_port_change(port_num, value):
            if port_num == self._output_port:
                # Изменилась выбранная строка
                self.current_row = value & 0x07
                self._update_input_port()
            if original_callback:
                original_callback(port_num, value)
        
        ppi.on_port_change = on_port_change
        # Первоначальное обновление
        self._update_input_port()
    
    def _update_input_port(self):
        """Обновить данные на входном порте 8255"""
        if self._ppi is None:
            return
        col_data = self.scan_row(self.current_row)
        self._ppi.set_external_input(self._input_port, col_data)
    
    def scan_row(self, row):
        """Сканировать строку матрицы.
        
        Возвращает байт: бит=0 — клавиша нажата, бит=1 — отпущена.
        """
        result = 0xFF  # Все отпущены
        for col in range(8):
            if self.matrix[row][col]:
                result &= ~(1 << col)
        return result
    
    def press_key(self, row, col):
        """Нажать клавишу"""
        if 0 <= row < 8 and 0 <= col < 8:
            self.matrix[row][col] = True
            # АР2 (строка 4, столбец 7)
            if row == 4 and col == 7:
                self.shift_active = True
            self._update_input_port()
    
    def release_key(self, row, col):
        """Отпустить клавишу"""
        if 0 <= row < 8 and 0 <= col < 8:
            self.matrix[row][col] = False
            if row == 4 and col == 7:
                self.shift_active = False
            self._update_input_port()
    
    def release_all(self):
        """Отпустить все клавиши"""
        for r in range(8):
            for c in range(8):
                self.matrix[r][c] = False
        self.shift_active = False
        self._update_input_port()
    
    def get_char_at(self, row, col):
        """Получить символ по координатам"""
        entry = self.keymap.get((row, col))
        if entry:
            return entry[1] if self.shift_active else entry[0]
        return ' '
    
    def get_state(self):
        """Состояние для отладки и окна устройства"""
        pressed = []
        for r in range(8):
            for c in range(8):
                if self.matrix[r][c]:
                    char = self.get_char_at(r, c)
                    pressed.append(f"({r},{c})='{char}'")
        return {
            "name": self.name,
            "type": "Keyboard 8x8 (Radio-86RK)",
            "base_port": "-",
            "current_row": self.current_row,
            "shift_active": self.shift_active,
            "pressed_keys": ", ".join(pressed) if pressed else "(нет)",
            "ppi_device": self._ppi.name if self._ppi else "не подключён",
            "output_port": self._output_port,
            "input_port": self._input_port,
        }
