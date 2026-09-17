"""
Диспетчер устройств.
Итерация 11: Интеграция устройств в GUI.

Отображает список устройств текущего профиля.
Двойной клик или кнопка «Открыть» — открывает окно устройства.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .device_window import DeviceWindow
from .keyboard_widget import KeyboardWidget
from .cube3d_widget import Cube3DWidget

class DeviceManagerDialog(QDialog):
    """Диспетчер устройств: список + открытие индивидуальных окон"""

    def tr(self, key: str, **kwargs) -> str:
        """Translate a key, optionally with format args."""
        from common.i18n import LANGS, get_system_language
        lang = get_system_language()
        text = LANGS.get(lang, {}).get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def retranslate(self):
        """Update all translatable strings (call on language change)."""
        self.setWindowTitle(self.tr("dm_title"))
        if hasattr(self, 'title_label'):
            self.title_label.setText(self.tr("dm_subtitle"))
        if hasattr(self, 'btn_open'):
            self.btn_open.setText(self.tr("dm_open"))
        if hasattr(self, 'btn_close_all'):
            self.btn_close_all.setText(self.tr("dm_close_all"))
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setText(self.tr("dm_refresh"))
        if hasattr(self, 'chk_always_on_top'):
            self.chk_always_on_top.setText(self.tr("dm_always_on_top"))

    def __init__(self, system, parent=None):
        super().__init__()  # Диспетчер без родителя — независим
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self._main_window = parent  # ← Ссылка на ГЛАВНОЕ окно (для виджетов)
        self.system = system
        self.device_windows = {}
        self._always_on_top = False
        
        self.setWindowTitle(self.tr("dm_title"))
        self.setMinimumSize(420, 500)
        self.resize(440, 520)

        self._init_ui()
        self.refresh_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Заголовок
        title = QLabel(self.tr("dm_subtitle"))
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Список устройств
        self.device_list = QListWidget()
        self.device_list.setFont(QFont("Consolas", 10))
        self.device_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.device_list, 1)

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_open = QPushButton(self.tr("dm_open"))
        self.btn_open.clicked.connect(self._open_selected)
        self.btn_close_all = QPushButton(self.tr("dm_close_all"))
        self.btn_close_all.clicked.connect(self.close_all_windows)
        self.btn_refresh = QPushButton(self.tr("dm_refresh"))
        self.btn_refresh.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_close_all)
        btn_layout.addWidget(self.btn_refresh)
        layout.addLayout(btn_layout)

        # Опция "поверх всех"
        self.chk_always_on_top = QCheckBox(self.tr("dm_always_on_top"))
        self.chk_always_on_top.toggled.connect(self._toggle_always_on_top)
        layout.addWidget(self.chk_always_on_top)

    def refresh_devices(self):
        """Обновить список устройств из профиля"""
        self.device_list.clear()
        if not hasattr(self.system, 'list_devices'):
            return
        for dev_info in self.system.list_devices():
            name = dev_info.get('name', '?')
            dev_type = dev_info.get('type', '?')
            base_port = dev_info.get('base_port', '?')
            marker = "●" if name in self.device_windows and self.device_windows[name].isVisible() else "○"
            item = QListWidgetItem(f"{marker} {name}  [{dev_type}] @ {base_port}")
            item.setData(Qt.UserRole, name)
            self.device_list.addItem(item)

        if self.device_list.count() == 0:
            item = QListWidgetItem(self.tr("dm_no_devices"))
            item.setFlags(Qt.NoItemFlags)
            self.device_list.addItem(item)

    def _on_item_double_clicked(self, item):
        name = item.data(Qt.UserRole)
        if name:
            self._open_device_window(name)

    def _open_selected(self):
        item = self.device_list.currentItem()
        if item:
            name = item.data(Qt.UserRole)
            if name:
                self._open_device_window(name)

    def _open_device_window(self, device_name):
        """Открыть/показать окно устройства"""
        device = self.system.get_device(device_name)
        if device is None:
            return

        # Уже открыто — просто поднять
        if device_name in self.device_windows:
            win = self.device_windows[device_name]
            if win.isVisible():
                win.raise_()
                win.activateWindow()
                return
        else:
            if type(device).__name__ == 'Cube3D':
                # Для Cube3D — чистое окно с виджетом, без полей регистров
                win = Cube3DWidget(device, parent=self._main_window)
                win.setWindowTitle(self.tr("dm_cube_title", name=device_name))
                win.resize(640, 600)
                if self._always_on_top:
                    win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)
            elif type(device).__name__ in ('Keyboard8x8', 'Keyboard8279Adapter'):
                # Для клавиатуры — чистое окно с виджетом, без полей
                win = KeyboardWidget(device, parent=self._main_window)
                win.setWindowTitle(self.tr("dm_keyboard_title", name=device_name))
                if self._always_on_top:
                    win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)
            else:
                win = DeviceWindow(
                    device, device_name,
                    always_on_top=self._always_on_top,
                    parent=self._main_window  # ← ГЛАВНОЕ окно
                )
            self.device_windows[device_name] = win

        win.show()
        win.raise_()
        win.activateWindow()
        self.refresh_devices()

    def _toggle_always_on_top(self, checked):
        """Применить флаг ко всем открытым окнам"""
        self._always_on_top = checked
        for win in self.device_windows.values():
            if win.isVisible():
                win.set_always_on_top(checked)

    def close_all_windows(self):
        """Закрыть все окна устройств"""
        for win in self.device_windows.values():
            win.close()
        self.device_windows.clear()
        self.refresh_devices()

    def on_profile_changed(self):
        """Вызывается при смене профиля — закрываем все окна"""
        self.close_all_windows()
        self.refresh_devices()

    def closeEvent(self, event):
        # При закрытии диспетчера — закрываем и окна устройств
        self.close_all_windows()
        event.accept()
