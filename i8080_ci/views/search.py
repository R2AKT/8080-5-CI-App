"""Search dialog for hex editor."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLineEdit, QLabel, QListWidget, QListWidgetItem,
                                QComboBox)
from PySide6.QtCore import Qt, Signal

class SearchDialog(QDialog):
    searchRequested = Signal(str, str)  # pattern, mode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Memory")
        self.resize(400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Поле ввода паттерна
        input_layout = QHBoxLayout()
        self.lbl_pattern = QLabel(self.tr("search_pattern"))
        self.txt_pattern = QLineEdit()
        self.txt_pattern.setPlaceholderText("C3 00 10 or HELLO")
        input_layout.addWidget(self.lbl_pattern)
        input_layout.addWidget(self.txt_pattern)
        layout.addLayout(input_layout)
        
        # Режим поиска
        mode_layout = QHBoxLayout()
        self.lbl_mode = QLabel(self.tr("search_mode"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            self.tr("search_mode_hex"),
            self.tr("search_mode_ascii"),
            self.tr("search_mode_mask")
        ])
        mode_layout.addWidget(self.lbl_mode)
        mode_layout.addWidget(self.cmb_mode)
        layout.addLayout(mode_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_find = QPushButton(self.tr("search_find_next"))
        self.btn_find_all = QPushButton(self.tr("search_find_all"))
        self.btn_close = QPushButton(self.tr("search_close"))
        self.btn_find.clicked.connect(self.on_find)
        self.btn_find_all.clicked.connect(self.on_find_all)
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_find)
        btn_layout.addWidget(self.btn_find_all)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
        
        # Результаты
        self.lbl_results = QLabel(self.tr("search_results"))
        layout.addWidget(self.lbl_results)
        
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_result_double_click)
        layout.addWidget(self.results_list)
        
    def tr(self, key):
        if self.parent() and hasattr(self.parent(), 'tr'):
            return self.parent().tr(key)
        return key
        
    def retranslate(self):
        self.setWindowTitle(self.tr("search_title"))
        self.lbl_pattern.setText(self.tr("search_pattern"))
        self.lbl_mode.setText(self.tr("search_mode"))
        self.btn_find.setText(self.tr("search_find_next"))
        self.btn_find_all.setText(self.tr("search_find_all"))
        self.btn_close.setText(self.tr("search_close"))
        self.lbl_results.setText(self.tr("search_results"))
        # Обновляем пункты combo (не меняем текущий выбор)
        current = self.cmb_mode.currentIndex()
        self.cmb_mode.clear()
        self.cmb_mode.addItems([
            self.tr("search_mode_hex"),
            self.tr("search_mode_ascii"),
            self.tr("search_mode_mask")
        ])
        self.cmb_mode.setCurrentIndex(current)
        
    def on_find(self):
        pattern = self.txt_pattern.text().strip()
        mode = self.cmb_mode.currentText()
        if pattern:
            self.searchRequested.emit(pattern, mode)
            
    def on_find_all(self):
        pattern = self.txt_pattern.text().strip()
        mode = self.cmb_mode.currentText()
        if pattern:
            self.searchRequested.emit(pattern, mode)
            
    def on_result_double_click(self, item):
        # Извлекаем адрес из текста элемента
        text = item.text()
        if":" in text:
            addr_str = text.split(":")[0].strip()
            try:
                addr = int(addr_str, 16)
                self.parent().goto_address(addr)
            except ValueError:
                pass
                
    def show_results(self, results):
        """Отображает результаты поиска"""
        self.results_list.clear()
        for addr, matched_bytes in results:
            bytes_str = " ".join(f"{b:02X}" for b in matched_bytes)
            self.results_list.addItem(QListWidgetItem(f"{addr:04X}: {bytes_str}"))


