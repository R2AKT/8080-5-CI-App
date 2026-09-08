"""
3D-куб 8×8×8 — виртуальное устройство-периферия.
Подключается к 8255: порт A = X, порт B = Y, порт C = Z.
Не занимает собственных портов ввода-вывода.

Аналогично Keyboard8x8: устройство подключается к 8255 через on_port_change.
"""


class Cube3D:
    """3D-куб 8×8×8 (512 светодиодов).
    
    Управление:
    - Через порты 8255 (A=X, B=Y, C=Z) — мультиплексирование
    - Прямое: set_led(), set_layer(), clear(), fill_all()
    """
    
    def __init__(self, name="Cube3D"):
        self.name = name
        self.base_port = -1  # Виртуальное устройство, без портов
        
        # Состояние 512 светодиодов: [z][y][x] = 0.0..1.0
        self.brightness = [[[0.0] * 8 for _ in range(8)] for _ in range(8)]
        
        # Подключение к 8255
        self._ppi = None
        self._port_x = 0
        self._port_y = 1
        self._port_z = 2
        
        # Режим мультиплексирования (инерционность зрения)
        self.persist_mode = True
    
    def connect_to_ppi(self, ppi, port_x=0, port_y=1, port_z=2):
        """Подключить куб к 8255.

        Светодиод зажигается ТОЛЬКО при записи в порт Z.
        Порты X и Y лишь задают координату (стробирование).
        Это устраняет посторонние пиксели при мультиплексировании.
        """
        self._ppi = ppi
        self._port_x = port_x
        self._port_y = port_y
        self._port_z = port_z

        original = ppi.on_port_change

        def on_port_change(port_num, value):
            # Зажигаем только при записи в порт Z (строб)
            if port_num == self._port_z:
                x = ppi.port_a & 0x07
                y = ppi.port_b & 0x07
                z = ppi.port_c & 0x07
                self.brightness[z][y][x] = 1.0
            if original:
                original(port_num, value)

        ppi.on_port_change = on_port_change
    
    # =============================================
    # УПРАВЛЕНИЕ СВЕТОДИОДАМИ
    # =============================================
    def set_led(self, x, y, z, state):
        """Установить состояние одного светодиода"""
        if 0 <= x < 8 and 0 <= y < 8 and 0 <= z < 8:
            self.brightness[z][y][x] = 1.0 if state else 0.0
    
    def get_led(self, x, y, z):
        """Получить состояние светодиода"""
        if 0 <= x < 8 and 0 <= y < 8 and 0 <= z < 8:
            return self.brightness[z][y][x] > 0.05
        return False
    
    def set_layer(self, z, pattern):
        """Установить слой из битовой карты (8 байт, бит 0 = левый пиксель)"""
        if 0 <= z < 8 and len(pattern) == 8:
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = \
                        1.0 if (pattern[y] & (1 << x)) else 0.0
    
    def clear(self):
        """Погасить все светодиоды"""
        for z in range(8):
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = 0.0
    
    def fill_all(self, state=True):
        """Заполнить весь куб"""
        v = 1.0 if state else 0.0
        for z in range(8):
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = v
    
    def set_persist(self, enabled):
        """Режим мультиплексирования"""
        self.persist_mode = bool(enabled)
    
    def lit_count(self):
        """Количество горящих светодиодов"""
        return sum(1 for z in range(8) for y in range(8) for x in range(8)
                   if self.brightness[z][y][x] > 0.05)
    
    def get_state(self):
        """Состояние для отладки и окна устройства"""
        return {
            "name": self.name,
            "base_port": "-",
            "leds_on": self.lit_count(),
            "total_leds": 512,
            "persist_mode": self.persist_mode,
            "ppi_device": self._ppi.name if self._ppi else "не подключён",
            "port_x": self._port_x,
            "port_y": self._port_y,
            "port_z": self._port_z,
        }

    def set_always_on_top(self, enabled):
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()
