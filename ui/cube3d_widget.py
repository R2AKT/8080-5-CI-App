"""
Виджет 3D-куба 8×8×8 — ЧЕСТНЫЙ 3D.
Итерация 12.3: демонстрационная визуализация.

- Реальная 3D-проекция с перспективой
- Вращение мышью (ЛКМ), зум (колесо), сброс вида (двойной клик)
- Сортировка по глубине (алгоритм художника) — дальние светодиоды
  рисуются первыми, ближние перекрывают их
- Режим мультиплексирования (инерционность зрения): светодиоды
  зажигаются при смене портов и плавно гаснут
- Управление: set_led, set_layer, clear, fill_all, set_persist

Подключение к 8255: порт A = X, порт B = Y, порт C = Z (биты 0-2)
"""
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QRadialGradient, QLinearGradient, QFont
)


class Cube3DWidget(QWidget):
    """3D-куб 8×8×8 (512 светодиодов) с реальной 3D-проекцией"""

    def __init__(self, cube, parent=None):
        """
        Args:
            cube: устройство Cube3D (новый вариант)
                  или 8255 (обратная совместимость)
        """
        super().__init__(parent)

        # Определяем тип: устройство Cube3D или 8255
        if type(cube).__name__ == 'Cube3D':
            self.cube = cube
            self.device = cube._ppi
            # Используем яркость устройства (общая ссылка)
            self.brightness = cube.brightness
        else:
            # Обратная совместимость: передан 8255
            self.cube = None
            self.device = cube
            self.brightness = [[[0.0]*8 for _ in range(8)] for _ in range(8)]

        # Параметры вида
        self.yaw = -32.0
        self.pitch = -26.0
        self.zoom = 1.0
        self.focal = 14.0

        # Цвета
        self.color_on = QColor(255, 70, 50)
        self.color_off = QColor(72, 74, 82)

        # Мультиплексирование
        self.persist_mode = True
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_tick)
        self._fade_timer.start(25)

        # Мышь
        self._dragging = False
        self._last_pos = None

        self.setMinimumSize(480, 480)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowFlags(Qt.Window)

        # Подключение к 8255 только если нет устройства Cube3D
        if self.cube is None and self.device is not None:
            self._connect_to_8255()

    # =============================================
    # УПРАВЛЕНИЕ КЛАВИАТУРОЙ
    # =============================================
    def keyPressEvent(self, event):
        """Клавиатурное управление видом"""
        key = event.key()
        if key == Qt.Key_Space:
            # Мгновенный переворот на 180°
            self.pitch = (self.pitch + 180) % 360 - 180
            self.update()
        elif key == Qt.Key_Left:
            self.yaw -= 10
            self.update()
        elif key == Qt.Key_Right:
            self.yaw += 10
            self.update()
        elif key == Qt.Key_Up:
            self.pitch -= 10
            self.update()
        elif key == Qt.Key_Down:
            self.pitch += 10
            self.update()
        elif key == Qt.Key_R:
            # Сброс вида
            self.yaw, self.pitch, self.zoom = -32.0, -26.0, 1.0
            self.update()
        else:
            super().keyPressEvent(event)

    # =============================================
    # УПРАВЛЕНИЕ СВЕТОДИОДАМИ
    # =============================================
    def set_led(self, x, y, z, state):
        """Установить состояние одного светодиода"""
        if 0 <= x < 8 and 0 <= y < 8 and 0 <= z < 8:
            self.brightness[z][y][x] = 1.0 if state else 0.0
            if not self.persist_mode:
                self.update()

    def get_led(self, x, y, z):
        """Получить состояние светодиода"""
        if 0 <= x < 8 and 0 <= y < 8 and 0 <= z < 8:
            return self.brightness[z][y][x] > 0.05
        return False

    def set_layer(self, z, pattern):
        """Установить слой из битовой карты.

        Args:
            z: номер слоя (0-7)
            pattern: 8 байт, каждый байт = строка, бит 0 = левый пиксель
        """
        if 0 <= z < 8 and len(pattern) == 8:
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = \
                        1.0 if (pattern[y] & (1 << x)) else 0.0
            if not self.persist_mode:
                self.update()

    def clear(self):
        """Погасить все светодиоды"""
        for z in range(8):
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = 0.0
        self.update()

    def fill_all(self, state=True):
        """Заполнить весь куб"""
        v = 1.0 if state else 0.0
        for z in range(8):
            for y in range(8):
                for x in range(8):
                    self.brightness[z][y][x] = v
        self.update()

    def set_persist(self, enabled):
        """Режим мультиплексирования: светодиоды гаснут после зажигания.

        True  — честная эмуляция сканирования (для управления через 8255)
        False — статичное изображение (для анимаций из скриптов)
        """
        self.persist_mode = bool(enabled)
        self.update()

    def set_color(self, r, g, b):
        """Цвет включённых светодиодов"""
        self.color_on = QColor(r, g, b)
        self.update()

    def lit_count(self):
        """Количество горящих светодиодов"""
        return sum(1 for z in range(8) for y in range(8) for x in range(8)
                   if self.brightness[z][y][x] > 0.05)

    def get_state(self):
        """Состояние для отладки"""
        return {
            "leds_on": self.lit_count(),
            "total_leds": 512,
            "persist_mode": self.persist_mode,
            "yaw": round(self.yaw, 1),
            "pitch": round(self.pitch, 1),
            "zoom": round(self.zoom, 2),
        }

    # =============================================
    # МУЛЬТИПЛЕКСИРОВАНИЕ ЧЕРЕЗ 8255
    # =============================================
    def _connect_to_8255(self):
        """Порты 8255 задают координату: A=X, B=Y, C=Z.
        Светодиод зажигается ТОЛЬКО при записи в порт Z (строб).
        """
        original = self.device.on_port_change

        def on_port_change(port_num, value):
            # Зажигаем только при записи в порт C (Z = строб)
            if port_num == 2:
                x = self.device.port_a & 0x07
                y = self.device.port_b & 0x07
                z = self.device.port_c & 0x07
                self.brightness[z][y][x] = 1.0
            if original:
                original(port_num, value)

        self.device.on_port_change = on_port_change

    def _fade_tick(self):
        """Инерционность зрения: плавное затухание светодиодов"""
        if not self.persist_mode:
            return
        changed = False
        for z in range(8):
            for y in range(8):
                row = self.brightness[z][y]
                for x in range(8):
                    b = row[x]
                    if b > 0:
                        b *= 0.88
                        if b < 0.03:
                            b = 0.0
                        row[x] = b
                        changed = True
        if changed:
            self.update()

    # =============================================
    # 3D-МАТЕМАТИКА
    # =============================================
    def _project(self, x, y, z, cx, cy, scale):
        """Мировые координаты -> экранные + глубина + масштаб.

        Возвращает (sx, sy, depth, k):
            sx, sy — экранные координаты
            depth  — глубина (больше = дальше от наблюдателя)
            k      — коэффициент масштаба (перспективное сжатие)
        """
        # Центрируем куб в начале координат
        px, py, pz = x - 3.5, y - 3.5, z - 3.5
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        # Вращение вокруг оси Y (рыскание)
        x1 = px * math.cos(yaw) + pz * math.sin(yaw)
        z1 = -px * math.sin(yaw) + pz * math.cos(yaw)
        # Вращение вокруг оси X (тангаж)
        y2 = py * math.cos(pitch) - z1 * math.sin(pitch)
        z2 = py * math.sin(pitch) + z1 * math.cos(pitch)
        # Перспективная проекция
        d = self.focal + z2
        if d < 1.0:
            d = 1.0
        k = (self.focal / d) * scale * self.zoom
        return cx + x1 * k, cy - y2 * k, z2, k

    # =============================================
    # ОТРИСОВКА
    # =============================================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Фон-градиент
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(26, 28, 36))
        bg.setColorAt(1.0, QColor(8, 8, 12))
        p.fillRect(self.rect(), QBrush(bg))

        cx = self.width() / 2
        cy = self.height() / 2
        scale = min(self.width(), self.height()) / 11.5

        # ---------- Каркас куба ----------
        c0, c1 = -0.5, 7.5
        corners = [
            (c0, c0, c0), (c1, c0, c0), (c1, c0, c1), (c0, c0, c1),
            (c0, c1, c0), (c1, c1, c0), (c1, c1, c1), (c0, c1, c1),
        ]
        edges = [(0,1),(1,2),(2,3),(3,0),
                 (4,5),(5,6),(6,7),(7,4),
                 (0,4),(1,5),(2,6),(3,7)]
        proj = [self._project(*c, cx, cy, scale) for c in corners]
        p.setPen(QPen(QColor(100, 105, 120, 130), 1))
        for a, b in edges:
            p.drawLine(QPointF(proj[a][0], proj[a][1]),
                       QPointF(proj[b][0], proj[b][1]))

        # ---------- Оси координат ----------
        axis_len = 5.2
        axes = [
            ((axis_len, 3.5, 3.5), QColor(220, 90, 90),  "X"),
            ((3.5, axis_len, 3.5), QColor(90, 200, 120), "Y"),
            ((3.5, 3.5, axis_len), QColor(90, 140, 230), "Z"),
        ]
        center = self._project(3.5, 3.5, 3.5, cx, cy, scale)
        p.setFont(QFont("Consolas", 8))
        for end, color, label in axes:
            pe = self._project(*end, cx, cy, scale)
            p.setPen(QPen(QColor(color.red(), color.green(),
                                 color.blue(), 110), 1))
            p.drawLine(QPointF(center[0], center[1]), QPointF(pe[0], pe[1]))
            p.setPen(color)
            p.drawText(QPointF(pe[0] + 4, pe[1] - 4), label)

        # ---------- Сбор и сортировка светодиодов по глубине ----------
        leds = []
        for z in range(8):
            for y in range(8):
                for x in range(8):
                    sx, sy, depth, k = self._project(x, y, z, cx, cy, scale)
                    leds.append((depth, sx, sy, k, self.brightness[z][y][x]))
        # Алгоритм художника: дальние рисуются первыми
        leds.sort(key=lambda t: t[0], reverse=True)

        # ---------- Отрисовка светодиодов ----------
        p.setPen(Qt.NoPen)
        for depth, sx, sy, k, bright in leds:
            if bright > 0.05:
                # Горящий светодиод: ореол + яркое ядро
                r = 0.40 * k * (0.7 + 0.3 * bright)
                c = self.color_on
                halo = r * (1.6 + 1.4 * bright)
                grad = QRadialGradient(sx, sy, halo)
                grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(),
                                            int(170 * bright)))
                grad.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(),
                                            int(60 * bright)))
                grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
                p.setBrush(QBrush(grad))
                p.drawEllipse(QPointF(sx, sy), halo, halo)
                core = QColor(
                    min(255, c.red() + int(90 * bright)),
                    min(255, c.green() + int(90 * bright)),
                    min(255, c.blue() + int(90 * bright)),
                )
                p.setBrush(core)
                p.drawEllipse(QPointF(sx, sy), r, r)
            else:
                # Погасший светодиод
                r = 0.22 * k
                p.setBrush(self.color_off)
                p.drawEllipse(QPointF(sx, sy), r, r)

        # ---------- HUD ----------
        p.setPen(QColor(150, 155, 170))
        p.setFont(QFont("Consolas", 9))
        hud = (f"LEDs: {self.lit_count()}/512   "
               f"zoom: {self.zoom:.1f}x   "
               f"persist: {'on' if self.persist_mode else 'off'}")
        p.drawText(10, 18, hud)
        p.setPen(QColor(90, 95, 110))
        p.drawText(10, self.height() - 10,
                   "ЛКМ — вращение   колесо — зум   "
                   "Пробел — переворот   стрелки — поворот   "
                   "двойной клик / R — сброс")

    # =============================================
    # МЫШЬ
    # =============================================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_pos is not None:
            pos = event.position()
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            self.yaw += dx * 0.5
            self.pitch += dy * 0.5
            # Свободное вращение: нормализация углов в [-180, 180]
            self.yaw = (self.yaw + 180) % 360 - 180
            self.pitch = (self.pitch + 180) % 360 - 180
            self._last_pos = pos
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._last_pos = None

    def mouseDoubleClickEvent(self, event):
        """Сброс вида"""
        self.yaw, self.pitch, self.zoom = -32.0, -26.0, 1.0
        self.update()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom *= 1.12
        else:
            self.zoom /= 1.12
        self.zoom = max(0.3, min(6.0, self.zoom))
        self.update()

    # =============================================
    # СЛУЖЕБНОЕ
    # =============================================
    def showEvent(self, event):
        """Получить фокус при показе окна"""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def refresh(self):
        self.update()

    def closeEvent(self, event):
        self._fade_timer.stop()
        event.accept()
