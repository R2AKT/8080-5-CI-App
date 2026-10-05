"""
LCD2004 — символьный дисплей 20×4.
Контроллер: HD44780.
Итерация 8: Дисплеи.

Наследует логику от LCD1602, отличается только размером и адресами строк.

Регистры (2 порта):
  offset 0 (Data):    Чтение/запись данных
  offset 1 (Control): Запись команд / чтение статуса
"""
from .lcd1602 import LCD1602


class LCD2004(LCD1602):
    """LCD2004 — символьный дисплей 20×4"""

    # Адреса строк для 20×4
    LINE_ADDRS = [0x00, 0x40, 0x14, 0x54]

    def __init__(self, base_port, name="LCD2004"):
        super().__init__(base_port, name)
        self.cols = 20
        self.rows = 4

    def reset(self):
        """Сброс контроллера"""
        super().reset()
        self.cols = 20
        self.rows = 4

    def _update_cursor_from_addr(self):
        """Обновить позицию курсора из адреса (для 20×4)"""
        addr = self.ddram_addr
        for i, line_addr in enumerate(self.LINE_ADDRS):
            if line_addr <= addr < line_addr + self.cols:
                self.cursor_y = i
                self.cursor_x = (addr - line_addr) % self.cols
                return
        # Если адрес не в диапазоне, определяем по модулю
        self.cursor_y = (addr // self.cols) % self.rows
        self.cursor_x = addr % self.cols

    def get_display_text(self):
        """Получить текст дисплея 20×4"""
        lines = []
        for row in range(self.rows):
            line = ""
            base = self.LINE_ADDRS[row] if row < len(self.LINE_ADDRS) else row * 0x40
            for col in range(self.cols):
                ch = self.ddram[(base + col) & 0x7F]
                line += chr(ch) if 32 <= ch <= 126 else "."
            lines.append(line)
        return lines
