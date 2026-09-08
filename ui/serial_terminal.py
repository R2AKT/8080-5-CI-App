"""
Виджет последовательного терминала для 8251/16550.
Итерация 13: Терминал для USART/UART.

Возможности:
- Отображение данных, переданных устройством (через on_transmit)
- Ввод данных пользователем (через receive_data)
- Режимы: эхо, CR+LF, hex-ввод
- Потокобезопасность через Qt Signal
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor, QColor


class SerialTerminalWidget(QWidget):
    """Виджет терминала для последовательных портов 8251/16550"""

    # Сигнал для потокобезопасной передачи данных из любого потока
    data_received = Signal(int)

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self._rx_count = 0
        self._tx_count = 0

        self._init_ui()
        self._connect_device()

        # Подключение сигнала
        self.data_received.connect(self._display_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Заголовок
        dev_type = type(self.device).__name__
        base_port = getattr(self.device, 'base_port', 0)
        header = QLabel(f"<b>Терминал</b> — {dev_type} @ 0x{base_port:02X}")
        header.setFont(QFont("Segoe UI", 9))
        layout.addWidget(header)

        # Область отображения (как консоль)
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setFont(QFont("Courier New", 10))
        self.display.setStyleSheet(
            "QTextEdit { background-color: #0a0a0a; color: #00cc00; "
            "border: 1px solid #333; }"
        )
        self.display.setMinimumHeight(150)
        layout.addWidget(self.display, 1)

        # Строка ввода
        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setFont(QFont("Courier New", 10))
        self.input.setPlaceholderText("Введите текст и нажмите Enter...")
        self.input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input, 1)

        self.btn_send = QPushButton("Отправить")
        self.btn_send.clicked.connect(self._on_send)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

        # Настройки
        settings_layout = QHBoxLayout()

        self.chk_echo = QCheckBox("Локальное эхо")
        self.chk_echo.setChecked(False)
        settings_layout.addWidget(self.chk_echo)

        self.chk_cr_lf = QCheckBox("CR+LF")
        self.chk_cr_lf.setChecked(False)
        settings_layout.addWidget(self.chk_cr_lf)

        self.chk_hex_mode = QCheckBox("HEX-ввод")
        self.chk_hex_mode.setChecked(False)
        self.chk_hex_mode.setToolTip("Ввод в формате: 48 65 6C 6C 6F")
        settings_layout.addWidget(self.chk_hex_mode)

        settings_layout.addStretch()

        self.lbl_counters = QLabel("TX: 0  RX: 0")
        self.lbl_counters.setStyleSheet("color: #666;")
        settings_layout.addWidget(self.lbl_counters)

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self._on_clear)
        settings_layout.addWidget(self.btn_clear)

        layout.addLayout(settings_layout)

    # =============================================
    # ПОДКЛЮЧЕНИЕ К УСТРОЙСТВУ
    # =============================================
    def _connect_device(self):
        """Подключение к callback устройства"""
        if hasattr(self.device, 'on_transmit'):
            self.device.on_transmit = self._on_device_transmit

    def _disconnect_device(self):
        """Отключение от устройства"""
        if hasattr(self.device, 'on_transmit'):
            self.device.on_transmit = None

    # =============================================
    # ПРИЁМ ОТ УСТРОЙСТВА (может вызываться из любого потока)
    # =============================================
    def _on_device_transmit(self, data):
        """Получены данные от устройства — эмитим сигнал (потокобезопасно)"""
        self._rx_count += 1
        self.data_received.emit(data & 0xFF)

    def _display_data(self, data):
        """Отображение данных в виджете (в UI-потоке)"""
        # Специальные символы
        if data == 10:  # LF — новая строка
            self.display.insertPlainText("\n")
        elif data == 13:  # CR — возврат каретки
            pass  # Игнорируем отдельно, ждём LF
        elif data == 9:  # TAB
            self.display.insertPlainText("    ")
        elif 32 <= data <= 126:  # Печатаемые
            self.display.insertPlainText(chr(data))
        else:  # Непечатаемые — показываем как hex
            self.display.insertPlainText(f"[{data:02X}]")

        # Автопрокрутка
        cursor = self.display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.display.setTextCursor(cursor)

        self._update_counters()

    # =============================================
    # ОТПРАВКА К УСТРОЙСТВУ
    # =============================================
    def _on_send(self):
        """Отправка данных пользователем"""
        text = self.input.text()
        if not text:
            return
        self.input.clear()

        # Определяем список байтов для отправки
        if self.chk_hex_mode.isChecked():
            # HEX-режим: "48 65 6C 6C 6F"
            try:
                hex_str = text.replace(" ", "").replace(",", "")
                if len(hex_str) % 2 != 0:
                    hex_str = "0" + hex_str
                data_list = bytes.fromhex(hex_str)
            except ValueError:
                self.display.insertPlainText("\n[Ошибка: неверный HEX-формат]\n")
                return
        else:
            # Текстовый режим
            data_list = text.encode('ascii', errors='replace')

        # Локальное эхо (до отправки)
        if self.chk_echo.isChecked():
            if self.chk_hex_mode.isChecked():
                echo_str = " ".join(f"{b:02X}" for b in data_list)
                self.display.insertPlainText(echo_str)
            else:
                self.display.insertPlainText(text)
            if self.chk_cr_lf.isChecked():
                self.display.insertPlainText("\n")

        # Отправка данных
        for byte in data_list:
            self._send_byte(byte)
            self._tx_count += 1

        # CR+LF
        if self.chk_cr_lf.isChecked():
            self._send_byte(13)  # CR
            self._send_byte(10)  # LF
            self._tx_count += 2
            if not self.chk_echo.isChecked():
                self.display.insertPlainText("\n")

        self._update_counters()

        # Автопрокрутка
        cursor = self.display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.display.setTextCursor(cursor)

    def _send_byte(self, byte):
        """Отправка одного байта в устройство через порт данных"""
        base_port = getattr(self.device, 'base_port', 0)
        cls_name = type(self.device).__name__
        if cls_name == 'I16550':
            # Для 16550: убедимся, что DLAB сброшен
            self.device.lcr &= ~0x80
        elif cls_name == 'I8251':
            # Для 8251: убедимся, что устройство в состоянии READY
            if self.device.state != self.device.STATE_READY:
                self.device.state = self.device.STATE_READY
        if hasattr(self.device, 'io_write'):
            self.device.io_write(base_port, byte)

    # =============================================
    # УТИЛИТЫ
    # =============================================
    def _on_clear(self):
        """Очистка терминала"""
        self.display.clear()
        self._rx_count = 0
        self._tx_count = 0
        self._update_counters()

    def _update_counters(self):
        """Обновление счётчиков TX/RX"""
        self.lbl_counters.setText(f"TX: {self._tx_count}  RX: {self._rx_count}")

    def append_text(self, text):
        """Программное добавление текста (для скриптов)"""
        self.display.insertPlainText(text)
        cursor = self.display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.display.setTextCursor(cursor)

    def closeEvent(self, event):
        """Отключение от устройства при закрытии"""
        self._disconnect_device()
        event.accept()


def create_terminal_widget(device):
    """Создать виджет терминала для устройства.
    Возвращает None, если устройство не является последовательным портом."""
    cls_name = type(device).__name__
    if cls_name in ('I8251', 'I16550'):
        return SerialTerminalWidget(device)
    return None
