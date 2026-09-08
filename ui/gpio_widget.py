"""
Виджет GPIO для 8255.
Индикаторы = выходные линии.
Чекбоксы = входные линии.
Двунаправленный режим (порт A, режим 2) — оба активны и разделены.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class BitIndicator(QWidget):
    """Один бит: индикатор (выход) + чекбокс (вход)"""

    # Режимы отображения
    MODE_OUTPUT = 'output'      # Только индикатор
    MODE_INPUT = 'input'        # Только чекбокс
    MODE_BIDIR = 'bidir'        # Оба активны

    def __init__(self, bit_num, parent=None):
        super().__init__(parent)
        self.bit_num = bit_num
        self.on_toggle = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)

        # Индикатор (выход)
        self.led = QLabel()
        self.led.setFixedSize(18, 18)
        self.led.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.led, alignment=Qt.AlignCenter)

        # Подпись бита
        lbl = QLabel(str(bit_num))
        lbl.setFont(QFont("Consolas", 7))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        # Чекбокс (вход)
        self.chk = QCheckBox()
        self.chk.setFixedSize(16, 16)
        self.chk.toggled.connect(self._on_toggled)
        layout.addWidget(self.chk, alignment=Qt.AlignCenter)

        # Начальное состояние: только индикатор
        self.set_mode(self.MODE_OUTPUT)
        self._update_led(False)

    def set_mode(self, mode):
        """Установить режим отображения"""
        if mode == self.MODE_OUTPUT:
            self.led.setEnabled(True)
            self.chk.setVisible(False)
        elif mode == self.MODE_INPUT:
            self.led.setEnabled(False)  # Индикатор неактивен (серый)
            self.led.setStyleSheet(
                "background-color: #1a1a1a; border-radius: 9px; "
                "border: 1px solid #333;"
            )
            self.chk.setVisible(True)
        elif mode == self.MODE_BIDIR:
            self.led.setEnabled(True)
            self.chk.setVisible(True)

    def set_led(self, state):
        """Установить индикатор (выходной регистр)"""
        self._update_led(state)

    def set_checkbox(self, state):
        """Установить чекбокс (внешний сигнал) без генерации события"""
        self.chk.blockSignals(True)
        self.chk.setChecked(state)
        self.chk.blockSignals(False)

    def _update_led(self, state):
        if self.led.isEnabled():
            color = "#00cc00" if state else "#333333"
        else:
            color = "#1a1a1a"  # Неактивный индикатор
        self.led.setStyleSheet(
            f"background-color: {color}; border-radius: 9px; "
            f"border: 1px solid #666;"
        )

    def _on_toggled(self, checked):
        if self.on_toggle:
            self.on_toggle(self.bit_num, checked)


class PortGroup(QGroupBox):
    """Группа из 8 бит одного порта"""

    def __init__(self, port_name, parent=None):
        super().__init__(port_name, parent)
        self.bits = []
        self.on_bit_toggle = None
        self._port_id = 0

        grid = QGridLayout(self)
        grid.setSpacing(2)

        for i in range(8):
            bit = BitIndicator(i)
            bit.on_toggle = self._bit_toggled
            self.bits.append(bit)
            grid.addWidget(bit, 0, 7 - i)

    def set_port_id(self, port_id):
        self._port_id = port_id

    def set_mode(self, mode):
        """Установить режим для всех битов"""
        for bit in self.bits:
            bit.set_mode(mode)

    def set_leds(self, value):
        """Индикаторы: выходной регистр"""
        for i in range(8):
            self.bits[i].set_led(bool(value & (1 << i)))

    def set_checkboxes(self, value):
        """Чекбоксы: внешний входной сигнал"""
        for i in range(8):
            self.bits[i].set_checkbox(bool(value & (1 << i)))

    def _bit_toggled(self, bit_num, state):
        if self.on_bit_toggle:
            self.on_bit_toggle(self._port_id, bit_num, state)


class GPIO8255Widget(QWidget):
    """Виджет GPIO для 8255"""

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self._init_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(200)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("<b>GPIO 8255</b>")
        header.setFont(QFont("Segoe UI", 9))
        layout.addWidget(header)

        self.port_a = PortGroup("Port A")
        self.port_a.set_port_id(0)
        self.port_a.on_bit_toggle = self._on_bit_toggle
        layout.addWidget(self.port_a)

        self.port_b = PortGroup("Port B")
        self.port_b.set_port_id(1)
        self.port_b.on_bit_toggle = self._on_bit_toggle
        layout.addWidget(self.port_b)

        self.port_c = PortGroup("Port C")
        self.port_c.set_port_id(2)
        self.port_c.on_bit_toggle = self._on_bit_toggle
        layout.addWidget(self.port_c)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        self.lbl_direction = QLabel("")
        self.lbl_direction.setFont(QFont("Consolas", 8))
        layout.addWidget(self.lbl_direction)

        self._auto_refresh()

    def _auto_refresh(self):
        """Автообновление состояния портов"""
        if not hasattr(self.device, 'port_a'):
            return

        # === Определяем режимы портов ===
        try:
            modes = self.device.get_port_modes()
        except Exception:
            modes = {
                'a_mode': 0, 'a_direction': 'in',
                'b_mode': 0, 'b_direction': 'in',
                'c_low_direction': 'in', 'c_high_direction': 'in',
            }

        # === Порт A ===
        a_dir = modes['a_direction']
        if a_dir == 'bidir':
            # Двунаправленный: индикаторы И чекбоксы активны
            self.port_a.set_mode(BitIndicator.MODE_BIDIR)
            self.port_a.set_leds(self.device.port_a)
            self.port_a.set_checkboxes(self.device.external_input[0])
        elif a_dir == 'out':
            # Выход: только индикаторы
            self.port_a.set_mode(BitIndicator.MODE_OUTPUT)
            self.port_a.set_leds(self.device.port_a)
        else:
            # Вход: только чекбоксы, индикаторы неактивны
            self.port_a.set_mode(BitIndicator.MODE_INPUT)
            self.port_a.set_checkboxes(self.device.external_input[0])

        # === Порт B ===
        b_dir = modes['b_direction']
        if b_dir == 'out':
            self.port_b.set_mode(BitIndicator.MODE_OUTPUT)
            self.port_b.set_leds(self.device.port_b)
        else:
            self.port_b.set_mode(BitIndicator.MODE_INPUT)
            self.port_b.set_checkboxes(self.device.external_input[1])

        # === Порт C: половины могут быть разными ===
        cl_dir = modes['c_low_direction']
        ch_dir = modes['c_high_direction']
        
        # Устанавливаем режим для каждой половины
        for i in range(8):
            if i < 4:  # Нижняя половина
                if cl_dir == 'out':
                    self.port_c.bits[i].set_mode(BitIndicator.MODE_OUTPUT)
                else:
                    self.port_c.bits[i].set_mode(BitIndicator.MODE_INPUT)
            else:  # Верхняя половина
                if ch_dir == 'out':
                    self.port_c.bits[i].set_mode(BitIndicator.MODE_OUTPUT)
                else:
                    self.port_c.bits[i].set_mode(BitIndicator.MODE_INPUT)
        
        self.port_c.set_leds(self.device.port_c)
        self.port_c.set_checkboxes(self.device.external_input[2])

        # === Метка режимов ===
        a_mode_str = f"режим {modes['a_mode']}"
        b_mode_str = f"режим {modes['b_mode']}"
        dirs = [
            f"A[{a_mode_str}]:{a_dir.upper()}",
            f"B[{b_mode_str}]:{b_dir.upper()}",
            f"CL:{cl_dir.upper()}",
            f"CH:{ch_dir.upper()}",
        ]
        self.lbl_direction.setText("  ".join(dirs))

    def _on_bit_toggle(self, port_id, bit_num, state):
        """Пользователь переключил чекбокс → меняем внешний сигнал"""
        if not hasattr(self.device, 'set_external_input'):
            return
        current = self.device.external_input[port_id]
        if state:
            current |= (1 << bit_num)
        else:
            current &= ~(1 << bit_num)
        self.device.set_external_input(port_id, current)

    def refresh(self):
        self._auto_refresh()

    def closeEvent(self, event):
        self.refresh_timer.stop()
        event.accept()
