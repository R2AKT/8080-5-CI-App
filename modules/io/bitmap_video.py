"""
BitmapVideo — графический видеоконтроллер (битмап).
Для Специалиста и других графических машин без знакогенератора.

Принцип работы:
- Видеопамять находится в RAM (не в устройстве)
- Устройство читает видеопамять из шины при обновлении
- Пиксели хранятся как битмап (1 бит = 1 пиксель для монохрома)
- Не занимает портов ввода-вывода
"""


class BitmapVideo:
    """Графический видеоконтроллер (битмап)"""

    def __init__(self, name="Bitmap Video"):
        self.name = name
        self.base_port = -1  # Виртуальное устройство

        # Параметры дисплея
        self.width = 256       # Ширина в пикселях
        self.height = 256      # Высота в пикселях
        self.planes = 1        # Кол-во битовых плоскостей (1=моно)

        # Адрес видеопамяти в RAM
        self.video_addr = 0xC000

        # Порядок битов: бит 0 = левый пиксель
        self.bit0_left = True

        # Ссылка на шину памяти
        self.memory_bus = None

        # Состояние
        self.display_enabled = True

        # Кэш кадра (для ускорения отрисовки): {offset: byte}
        self._frame_cache = {}

    def connect_to_bus(self, bus):
        """Подключить к шине памяти"""
        self.memory_bus = bus

    def bytes_per_line(self):
        """Байт в одной строке"""
        return (self.width * self.planes) // 8

    def read_video_byte(self, offset):
        """Прочитать байт из видеопамяти"""
        if self.memory_bus is None:
            return 0x00
        return self.memory_bus.read(self.video_addr + offset) & 0xFF

    def get_pixel(self, x, y):
        """Прочитать пиксель (для монохрома, 1 плоскость).
        Возвращает 0 или 1.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return 0
        bpl = self.bytes_per_line()
        byte_offset = y * bpl + (x // 8)
        byte = self.read_video_byte(byte_offset)
        bit_pos = x % 8
        if self.bit0_left:
            bit = (byte >> bit_pos) & 1
        else:
            bit = (byte >> (7 - bit_pos)) & 1
        return bit

    def get_frame_bytes(self):
        """Прочитать весь кадр как список байт (для виджета)."""
        total = self.bytes_per_line() * self.height
        frame = []
        for offset in range(total):
            frame.append(self.read_video_byte(offset))
        return frame

    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": "-",
            "type": "Графика (битмап)",
            "width": self.width,
            "height": self.height,
            "planes": self.planes,
            "video_addr": f"0x{self.video_addr:04X}",
            "bytes_per_line": self.bytes_per_line(),
            "bit0_left": self.bit0_left,
            "display_enabled": self.display_enabled,
            "memory_bus": "подключена" if self.memory_bus else "НЕ подключена",
        }
