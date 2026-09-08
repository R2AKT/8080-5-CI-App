"""
Виджеты визуализации дисплеев.
Итерация 12: Визуализация дисплеев.

Поддерживаемые устройства:
- LCD1602 / LCD2004 — символьные дисплеи
- TFT8080 — графический дисплей (16-бит цвет)
- I8275 / I8276 — символьные CRT-дисплеи с атрибутами
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QImage


# =============================================
# LCD1602 / LCD2004
# =============================================
class LCDWidget(QWidget):
    """Виджет для символьных дисплеев LCD1602/LCD2004"""

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.cols = getattr(device, 'cols', 16)
        self.rows = getattr(device, 'rows', 2)

        # Размер ячейки символа
        self.cell_w = 22
        self.cell_h = 30
        
        # Масштаб для увеличения
        self.scale = 1
        
        w = self.cols * self.cell_w * self.scale + 20
        h = self.rows * self.cell_h * self.scale + 20
        self.setMinimumSize(w, h)
        self.resize(w, h)
        
        self.setFont(QFont("Courier New", 13, QFont.Bold))

    def refresh(self):
        self._recalc_size()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Зелёный фон (классический LCD)
        p.fillRect(self.rect(), QColor(0x9E, 0xD4, 0x4B))

        lines = self.device.get_display_text()
        cursor_x = getattr(self.device, 'cursor_x', -1)
        cursor_y = getattr(self.device, 'cursor_y', -1)
        cursor_on = getattr(self.device, 'cursor_on', False)

        for row in range(self.rows):
            text = lines[row] if row < len(lines) else ""
            for col in range(self.cols):
                x = 6 + col * self.cell_w
                y = 6 + row * self.cell_h

                # Ячейка
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0x8A, 0xC4, 0x3A))
                p.drawRect(x, y, self.cell_w - 2, self.cell_h - 2)

                # Символ
                ch = text[col] if col < len(text) else ' '
                p.setPen(QColor(0x1A, 0x3A, 0x0A))
                p.drawText(x + 1, y + 1, self.cell_w - 4, self.cell_h - 4,
                           Qt.AlignCenter, ch)

                # Курсор (подчёркивание)
                if cursor_on and col == cursor_x and row == cursor_y:
                    p.setPen(QPen(QColor(0x1A, 0x3A, 0x0A), 2))
                    p.drawLine(x + 2, y + self.cell_h - 5,
                               x + self.cell_w - 5, y + self.cell_h - 5)

    def _recalc_size(self):
        """Пересчёт размера виджета при изменении параметров устройства"""
        cols = getattr(self.device, 'cols', 16)
        rows = getattr(self.device, 'rows', 2)
        w = cols * self.cell_w * self.scale + 20
        h = rows * self.cell_h * self.scale + 20
        self.setMinimumSize(w, h)
        self.resize(w, h)

# =============================================
# TFT8080
# =============================================
class TFTWidget(QWidget):
    """Виджет для графического дисплея TFT8080 (RGB565)"""

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.dev_w = getattr(device, 'width', 320)
        self.dev_h = getattr(device, 'height', 240)

        # Масштаб 2× для лучшего отображения
        self.scale = 2
        
        w = self.dev_w * self.scale + 20
        h = self.dev_h * self.scale + 20
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def refresh(self):
        self._recalc_size()
        self.update()

    @staticmethod
    def _rgb565_to_rgb888(pixel):
        """Конвертация RGB565 → (R, G, B)"""
        r = ((pixel >> 11) & 0x1F) << 3
        g = ((pixel >> 5) & 0x3F) << 2
        b = (pixel & 0x1F) << 3
        return r, g, b

    def paintEvent(self, event):
        p = QPainter(self)
        fb = self.device.framebuffer

        if not fb:
            p.fillRect(self.rect(), Qt.black)
            return

        img = QImage(self.dev_w, self.dev_h, QImage.Format_RGB32)
        img.fill(Qt.black)

        for y in range(self.dev_h):
            row_offset = y * self.dev_w
            for x in range(self.dev_w):
                idx = row_offset + x
                if idx < len(fb):
                    r, g, b = self._rgb565_to_rgb888(fb[idx])
                    img.setPixel(x, y, (255 << 24) | (r << 16) | (g << 8) | b)

        target = QRect(0, 0, self.dev_w * self.scale, self.dev_h * self.scale)
        p.drawImage(target, img)

    def _recalc_size(self):
        """Пересчёт размера виджета при изменении параметров устройства"""
        dev_w = getattr(self.device, 'width', 320)
        dev_h = getattr(self.device, 'height', 240)
        w = dev_w * self.scale + 20
        h = dev_h * self.scale + 20
        self.setMinimumSize(w, h)
        self.resize(w, h)

# =============================================
# I8275 / I8276
# =============================================
class CRTWidget(QWidget):
    ATTR_BLINK, ATTR_INVERSE, ATTR_UNDERLINE, ATTR_BRIGHT = 0x01, 0x02, 0x04, 0x08

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.scale = 2
        self.blink_state = False
        t = QTimer(self); t.timeout.connect(self._blink); t.start(500)
        self._recalc_size()

    def _recalc_size(self):
        cols = getattr(self.device, 'chars_per_line', 80)
        rows = getattr(self.device, 'lines_per_screen', 16)
        ch_h = getattr(self.device, 'char_height', 8)
        ch_w = getattr(self.device, 'char_width', 8)
        self.setFixedSize(cols*ch_w*self.scale, rows*ch_h*self.scale)
        dev_type = type(self.device).__name__
        if dev_type in ("I8275", "DiscreteVideo"):
            self.char_cell_height = 8
            self.display_scale_v = max(1, getattr(self.device, 'char_height', 8) // 8)
        else:
            self.char_cell_height = getattr(self.device, 'char_height', 8)
            self.display_scale_v = 1

    def _blink(self):
        self.blink_state = not self.blink_state
        self.update()

    def refresh(self):
        self._recalc_size()
        self.update()
        
        # Обновление из памяти для дискретного видео
        if hasattr(self.device, 'refresh_from_memory'):
            self.device.refresh_from_memory()
        self._recalc_size()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.black)
        dev = self.device
        cols = dev.chars_per_line
        rows = dev.lines_per_screen
        ch_h = getattr(dev, 'char_height', 8)
        ch_w = getattr(dev, 'char_width', 8)  # ← ширина знакоместа
        s = self.scale
        cg = dev.char_gen

        for y in range(rows):
            for x in range(cols):
                off = y*cols + x
                entry = None
                if hasattr(dev, 'display_buffer'):
                    entry = dev.display_buffer.get(off)
                elif hasattr(dev, 'video_ram'):
                    entry = dev.video_ram.get(off)
                code, attr = (entry if entry else (0x20, 0))
                fg = QColor(0x66,0xFF,0x66) if (attr & self.ATTR_BRIGHT) else QColor(0x33,0xFF,0x33)
                bg = QColor(0,0,0)
                if attr & self.ATTR_INVERSE:
                    fg, bg = bg, fg
                if (attr & self.ATTR_BLINK) and not self.blink_state:
                    fg = bg

                cx, cy = x*ch_w*s, y*ch_h*s
                p.fillRect(cx, cy, ch_w*s, ch_h*s, bg)

                if type(dev).__name__ in ("I8275", "DiscreteVideo"):
                    bm = cg.get_bitmap(code, 8)
                    for r in range(8):
                        bits = bm[r]
                        if (attr & self.ATTR_UNDERLINE) and r == 7:
                            bits = (1 << ch_w) - 1
                        if bits == 0:
                            continue
                        for b in range(ch_w):  # ← по ширине знакоместа
                            if bits & (0x01 << b):
                                for vs in range(self.display_scale_v):
                                    p.fillRect(cx + b*s, cy + (r * self.display_scale_v + vs)*s, s, s, fg)
                else:
                    bm = cg.get_bitmap(code, ch_h)
                    for r in range(ch_h):
                        bits = bm[r]
                        if (attr & self.ATTR_UNDERLINE) and r == ch_h-1:
                            bits = 0xFF
                        if bits == 0:
                            continue
                        for b in range(ch_w):
                            if bits & (0x01 << b):
                                p.fillRect(cx + b*s, cy + r*s, s, s, fg)

        # Курсор
        if getattr(dev, 'cursor_enabled', False):
            cx = dev.cursor_x*ch_w*s
            cy = dev.cursor_y*ch_h*s + (ch_h-1)*s
            p.fillRect(cx, cy, ch_w*s, s, QColor(0x33,0xFF,0x33))

# =============================================
# BitmapVideo (графика)
# =============================================
class GraphicsWidget(QWidget):
    """Виджет для графических машин (битмап, без знакогенератора)"""

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.scale = 2  # Масштаб отображения
        self._recalc_size()

    def _recalc_size(self):
        w = getattr(self.device, 'width', 256)
        h = getattr(self.device, 'height', 256)
        self.setFixedSize(w * self.scale + 20, h * self.scale + 20)

    def refresh(self):
        self._recalc_size()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.black)

        dev = self.device
        w = dev.width
        h = dev.height
        s = self.scale

        if dev.memory_bus is None:
            return

        # Читаем кадр целиком и рисуем пиксели
        frame = dev.get_frame_bytes()
        bpl = dev.bytes_per_line()

        # Цвета (монохром: зелёный на чёрном, как ЭЛТ)
        fg = QColor(0x33, 0xFF, 0x33)
        bg = QColor(0x00, 0x00, 0x00)

        for y in range(h):
            row_offset = y * bpl
            for byte_idx in range(bpl):
                byte = frame[row_offset + byte_idx]
                if byte == 0:
                    continue  # Пустой байт — пропускаем
                for bit_pos in range(8):
                    if dev.bit0_left:
                        on = (byte >> bit_pos) & 1
                        x = byte_idx * 8 + bit_pos
                    else:
                        on = (byte >> (7 - bit_pos)) & 1
                        x = byte_idx * 8 + bit_pos
                    if on and x < w:
                        p.fillRect(10 + x * s, 10 + y * s, s, s, fg)

# =============================================
# ФАБРИКА ВИДЖЕТОВ
# =============================================
def create_display_widget(device):
    """Создать виджет дисплея для устройства.
    Возвращает None, если устройство не является дисплеем."""
    cls_name = type(device).__name__
    if cls_name in ('LCD1602', 'LCD2004'):
        return LCDWidget(device)
    elif cls_name == 'TFT8080':
        return TFTWidget(device)
    elif cls_name in ('I8275', 'I8276', 'DiscreteVideo'):
        return CRTWidget(device)
    elif cls_name == 'BitmapVideo':
        return GraphicsWidget(device)
    return None