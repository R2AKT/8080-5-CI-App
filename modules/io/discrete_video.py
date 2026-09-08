"""
DiscreteVideo — видеоконтроллер на дискретной логике.
Для Микро-80 и других машин без программируемого CRT-контроллера.

Принцип работы:
- Видеопамять находится в RAM (не в устройстве)
- Устройство читает видеопамять из шины при обновлении
- Знакогенератор преобразует коды символов в пиксели
- Не занимает портов ввода-вывода (как Keyboard8x8)
"""


class DiscreteVideo:
    """Видеоконтроллер на дискретной логике"""

    # Таблица КОИ-7 → Unicode (набор 2)
    KOI7_TO_UNICODE = {
        0x60: 'Ю', 0x61: 'А', 0x62: 'Б', 0x63: 'Ц', 0x64: 'Д', 0x65: 'Е',
        0x66: 'Ф', 0x67: 'Г', 0x68: 'Х', 0x69: 'И', 0x6A: 'Й', 0x6B: 'К',
        0x6C: 'Л', 0x6D: 'М', 0x6E: 'Н', 0x6F: 'О', 0x70: 'П', 0x71: 'Я',
        0x72: 'Р', 0x73: 'С', 0x74: 'Т', 0x75: 'У', 0x76: 'Ж', 0x77: 'В',
        0x78: 'Ь', 0x79: 'Ы', 0x7A: 'З', 0x7B: 'Ш', 0x7C: 'Э', 0x7D: 'Щ',
        0x7E: 'Ч', 0x7F: 'Ъ',
    }
    UNICODE_TO_KOI7 = {v: k for k, v in KOI7_TO_UNICODE.items()}

    def __init__(self, name="Discrete Video"):
        self.name = name
        self.base_port = -1  # Виртуальное устройство

        # Параметры дисплея
        self.chars_per_line = 64
        self.lines_per_screen = 32
        self.char_width = 6       # Ширина знакоместа (пиксели)
        self.char_height = 8      # Высота знакоместа (пиксели)

        # Адреса видеопамяти
        self.video_addr = 0xE800  # Видеопамять символов
        self.attr_addr = 0xE000   # Видеопамять атрибутов/курсора

        # Курсор
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_enabled = False

        # Буфер отображения: {offset: (char, attr)}
        self.display_buffer = {}

        # Ссылка на шину памяти
        self.memory_bus = None

        # Знакогенератор
        from .chargen import CharGenerator
        self.char_gen = CharGenerator()

        # Состояние
        self.display_enabled = True

    @classmethod
    def unicode_to_koi7(cls, text):
        """Преобразовать текст из Unicode в коды KOI-7"""
        codes = []
        for ch in text:
            if ch in cls.UNICODE_TO_KOI7:
                codes.append(cls.UNICODE_TO_KOI7[ch])
            elif 32 <= ord(ch) <= 126:
                codes.append(ord(ch))
            else:
                codes.append(0x3F)  # '?'
        return codes

    def connect_to_bus(self, bus):
        """Подключить к шине памяти"""
        self.memory_bus = bus

    def refresh_from_memory(self):
        """Обновить буфер отображения из видеопамяти.
        Вызывается из виджета при автообновлении.
        """
        if self.memory_bus is None:
            return

        total_chars = self.chars_per_line * self.lines_per_screen
        self.display_buffer.clear()

        for i in range(total_chars):
            # Код символа из видеопамяти символов
            char = self.memory_bus.read(self.video_addr + i)
            # Атрибут из видеопамяти атрибутов (если задана)
            attr = 0x00
            if self.attr_addr is not None:
                attr = self.memory_bus.read(self.attr_addr + i)
            self.display_buffer[i] = (char & 0xFF, attr & 0xFF)

    def load_font_from_file(self, path, char_width=6, num_chars=128,
                            invert=False, bit_reverse=False):
        """Загрузить шрифт знакогенератора из файла"""
        self.char_width = char_width
        return self.char_gen.load_from_file(path, height=8,
                                            width=char_width,
                                            num_chars=num_chars,
                                            invert=invert,
                                            bit_reverse=bit_reverse)

    def get_display_text(self):
        """Получить текст дисплея (с КОИ-7 кириллицей)"""
        lines = []
        for y in range(self.lines_per_screen):
            line = ""
            for x in range(self.chars_per_line):
                idx = y * self.chars_per_line + x
                if idx in self.display_buffer:
                    char, attr = self.display_buffer[idx]
                    if char in self.KOI7_TO_UNICODE:
                        line += self.KOI7_TO_UNICODE[char]
                    elif 32 <= char <= 126:
                        line += chr(char)
                    else:
                        line += "."
                else:
                    line += " "
            lines.append(line)
        return lines

    def set_character(self, x, y, char, attr=0x00):
        """Установить символ в буфер (для тестов)"""
        idx = y * self.chars_per_line + x
        self.display_buffer[idx] = (char & 0xFF, attr & 0xFF)

    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": "-",
            "type": "Дискретная логика (Микро-80)",
            "chars_per_line": self.chars_per_line,
            "lines_per_screen": self.lines_per_screen,
            "char_width": self.char_width,
            "char_height": self.char_height,
            "video_addr": f"0x{self.video_addr:04X}",
            "attr_addr": f"0x{self.attr_addr:04X}" if self.attr_addr else "-",
            "display_enabled": self.display_enabled,
            "memory_bus": "подключена" if self.memory_bus else "НЕ подключена",
        }
