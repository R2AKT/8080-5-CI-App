"""Main application window."""
import sys
import json
import time
import traceback
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QPushButton, QComboBox, QLabel,
                               QLineEdit, QTextEdit, QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QTableView, QHeaderView, QFileDialog,
                               QProgressBar, QSpinBox, QCheckBox, QScrollArea, QInputDialog,
                               QDialog, QListWidget, QListWidgetItem, QMenu, QSplitter,
                               QFormLayout, QStackedWidget)
from PySide6.QtCore import Qt, QTimer, QThread, QSettings

from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence, QAction


from i8080_emulator import I8080Emulator
from ui.device_manager import DeviceManagerDialog
from i8080_ci.assembler_widget import AssemblerWidget

# === MCP Server (optional) ===
try:
    from mcp_server import MCPServerManager
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"MCP Server доступен: {e}")

from common.i18n import LANGS, get_system_language, set_language
from common.themes import THEMES
from .slip import (SlipProtocol, _FEND, CMD_NOP, CMD_HOLD, CMD_UNHOLD,
                   CMD_IO_READ_BYTE, CMD_IO_WRITE_BYTE,
                   CMD_GET_SIZE_SETUP,
                   ACK_NOP, ACK_HOLD_WAIT_LOW, ACK_HOLD_WAIT_HIGH,
                   ACK_HOLD_ACTIVE, ACK_WAIT_UNHOLD, ACK_UNHOLD,
                   ACK_MEM_READ_BYTE,
                   ACK_IO_READ_BYTE, ACK_IO_WRITE_BYTE,
                   ACK_EEPROM_WRITE_BYTE, ACK_EEPROM_WRITE_BLOCK,
                   ACK_ERROR, ACK_GET_SIZE_SETUP)
from .intelhex import IntelHex
from .disassembler import I8080Disassembler
from .bus_worker import BusWorker
from .automation import AutomationAPI
from .models import HexModel, WatchModel, BreakpointModel, TraceModel
from .views import DisasmView, HexTableView, SearchDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Стартовый размер окна (уменьшенный)
        self.resize(1280, 720)
        # Минимальный размер (разумный)
        self.setMinimumSize(1100, 700)
        
        # ============================================================
        # 1. ЗАГРУЗКА НАСТРОЕК
        # ============================================================
        self.settings = QSettings("8080-5 CI", "8080-5 CI application")
        saved_lang = self.settings.value("language", None)
        saved_theme = self.settings.value("theme", None)
        
        # Определение языка: сохранённый -> системный -> английский
        if saved_lang in LANGS:
            self.current_lang = saved_lang
            set_language(self.current_lang)
        else:
            self.current_lang = get_system_language()
            set_language(self.current_lang)
            
        # Определение темы: сохранённая -> светлая
        if saved_theme in THEMES:
            self.current_theme = saved_theme
        else:
            self.current_theme = "Light"
        
        # ============================================================
        # 2. ИНИЦИАЛИЗАЦИЯ ДАННЫХ (до создания UI)
        # ============================================================
        self.serial_port = None
        self.rx_buffer = bytearray()
        self.mem_data = {}
        self.disassembler = I8080Disassembler()
        self.hex_model = HexModel(self.mem_data)
        
        self.worker = None
        self.worker_thread = None
        self.pending_read = None
        self.is_connected = False
        self.bus_active = False
        self.max_block_size = 128
        
        # === Очередь команд ===
        self.command_queue = []
        self.waiting_response = False
        self.worker_active = False
        
        # === Undo/Redo ===
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_depth = 100
        
        # ============================================================
        # 3. ЭМУЛЯТОР i8080 (до init_ui, так как create_tab_emulator 
        #    обращается к self.emulator)
        # ============================================================
        self.emulator = I8080Emulator(self.mem_data)
        self.emulator.state_changed.connect(self.update_emulator_ui)
        self.emulator.log_message.connect(self.log)
        
        # Передаём дизассемблер для трассировки
        self.emulator.disassembler = self.disassembler
        
        # === Шина памяти ===
        from modules.memory import MemoryBus, RAMRegion
        self.memory_bus = MemoryBus()
        # RAM на всё адресное пространство, использует mem_data как хранилище
        ram = RAMRegion(0x0000, 0xFFFF, data=self.mem_data, name="RAM")
        self.memory_bus.register_memory(ram)
        self.emulator.memory_bus = self.memory_bus
        
        # === Интеграция системы профилей ===
        from modules.system import ComputerSystem
        from modules.config.system_profiles import get_profile_names

        # Создаём системный контроллер
        self.system = ComputerSystem()
        
        # Загружаем профиль по умолчанию
        self._current_profile = "empty"
        self.system.load_profile(self._current_profile)
                
        # Меню профилей
        from PySide6.QtGui import QActionGroup  # ← ДОБАВЛЕНО в импорты

        # Меню профилей
        self.profile_menu = self.menuBar().addMenu("Профиль системы")
        
        # Меню устройств
        self.devices_menu = self.menuBar().addMenu(self.tr("menu_devices"))
        self.act_device_manager = self.devices_menu.addAction(self.tr("device_manager"))
        self.act_device_manager.triggered.connect(self.show_device_manager)

        # Меню Справка (F1)
        self.help_menu = self.menuBar().addMenu(self.tr("menu_help"))
        self.act_help_guide = self.help_menu.addAction(self.tr("help_user_guide"))
        self.act_help_guide.triggered.connect(lambda: self._show_doc("USER_GUIDE.md"))
        self.act_help_readme = self.help_menu.addAction(self.tr("help_readme"))
        self.act_help_readme.triggered.connect(lambda: self._show_doc("README.md"))
        self.act_help_changes = self.help_menu.addAction(self.tr("help_changes"))
        self.act_help_changes.triggered.connect(lambda: self._show_doc("CHANGES.md"))
        self.act_help_analysis = self.help_menu.addAction(self.tr("help_analysis"))
        self.act_help_analysis.triggered.connect(lambda: self._show_doc("ANALYSIS.md"))
        self.act_help_mcp = self.help_menu.addAction(self.tr("help_mcp"))
        self.act_help_mcp.triggered.connect(lambda: self._show_doc("MCP_GUIDE.md"))
        self.act_help_scripts = self.help_menu.addAction(self.tr("help_scripts"))
        self.act_help_scripts.triggered.connect(lambda: self._show_doc("SCRIPTS_GUIDE.md"))
        self.help_menu.addSeparator()
        self.act_help_about = self.help_menu.addAction(self.tr("help_about"))
        self.act_help_about.triggered.connect(self._show_about)
        # F1 hotkey
        self._help_shortcut = QShortcut(QKeySequence(Qt.Key_F1), self)
        self._help_shortcut.activated.connect(lambda: self._show_doc("USER_GUIDE.md"))

        # Группа действий: только один профиль одновременно
        self.profile_group = QActionGroup(self)
        self.profile_group.setExclusive(True)  # ← КЛЮЧЕВАЯ СТРОКА

        self.profile_actions = {}
        for profile_name in get_profile_names():
            action = QAction(profile_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, pn=profile_name: self.load_profile(pn))
            self.profile_group.addAction(action)       # ← в группу
            self.profile_menu.addAction(action)        # ← в меню
            self.profile_actions[profile_name] = action

        # Отмечаем текущий профиль
        self.profile_actions[self._current_profile].setChecked(True)
        
        # ============================================================
        # 4. УСТРОЙСТВА
        # ============================================================
        self.device_manager = None  # Диспетчер устройств (ленивая инициализация)
        
        # ============================================================
        # 5. СОЗДАНИЕ UI
        # ============================================================
        self.init_ui()
        
        # ============================================================
        # 6. СТАТУСНАЯ СТРОКА (после init_ui)
        # ============================================================
        self.statusBar = self.statusBar()
        self.status_label_addr = QLabel(self.tr("status_addr") + "-")
        self.status_label_data = QLabel(self.tr("status_data") + "-")
        self.status_label_mnem = QLabel(self.tr("status_mnem") + "-")
        self.status_label_size = QLabel(self.tr("status_size") + "0 " + self.tr("bytes"))
        self.status_label_conn = QLabel(self.tr("disconnected"))
        
        self.statusBar.addWidget(self.status_label_conn)
        self.statusBar.addPermanentWidget(self.status_label_size)
        self.statusBar.addPermanentWidget(self.status_label_addr)
        self.statusBar.addPermanentWidget(self.status_label_data)
        self.statusBar.addPermanentWidget(self.status_label_mnem)
        
        # ============================================================
        # 7. MCP SERVER (после инициализации данных и UI)
        # ============================================================
        self._automation_api = AutomationAPI(self)
        self.mcp_server = None
        if MCP_AVAILABLE:
            try:
                self.mcp_server = MCPServerManager(self, host="127.0.0.1", port=8000)
            except Exception as e:
                self.log(f"MCP Server initialization failed: {e}")
        
        # ============================================================
        # 8. ЛОКАЛИЗАЦИЯ И ТЕМА
        # ============================================================
        self.retranslate_ui()
        QApplication.instance().setStyleSheet(THEMES[self.current_theme])
        
        is_dark = (self.current_theme == "Dark")
        
        # Применяем тему к дизассемблеру
        is_dark = (self.current_theme == "Dark")
        self.disasm_view.set_theme(is_dark)
        
        # ============================================================
        # 9. ТАЙМЕРЫ
        # ============================================================
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.read_serial)
        
        self.disasm_timer = QTimer()
        self.disasm_timer.setSingleShot(True)
        self.disasm_timer.timeout.connect(self.auto_disasm)
        
        # ============================================================
        # 10. ФИНАЛЬНАЯ НАСТРОЙКА
        # ============================================================
        self.update_ui_state()
        self.setup_shortcuts()
        
        # Инициализация окна эмулятора (показывает код с PC=0x0000)
        if hasattr(self, 'update_emu_disasm_view'):
            self.update_emu_disasm_view()
            
        # === ИТЕРАЦИЯ B: Цель для Run to Cursor ===
        self.run_target_addr = None
        
    def tr(self, key):
        return LANGS.get(self.current_lang, LANGS["en"]).get(key, key)
        
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # --- Верхняя панель: Подключение, Язык, Тема ---
        conn_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh_ports)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        
        self.btn_connect = QPushButton()
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        self.lbl_lang = QLabel()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Русский", "English"])
        # Устанавливаем сохранённый язык
        self.lang_combo.setCurrentIndex(0 if self.current_lang == "ru" else 1)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        
        self.lbl_theme = QLabel()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([self.tr("light"), self.tr("dark")])
        # Устанавливаем сохранённую тему
        self.theme_combo.setCurrentIndex(0 if self.current_theme == "Light" else 1)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        conn_layout.addWidget(QLabel("Port:"))  # Будет обновлено в retranslate_ui
        self.lbl_port = conn_layout.itemAt(0).widget()
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(self.btn_refresh)
        conn_layout.addWidget(QLabel("Baud:"))  # Будет обновлено в retranslate_ui
        self.lbl_baud = conn_layout.itemAt(3).widget()
        conn_layout.addWidget(self.baud_combo)
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addStretch()
        conn_layout.addWidget(self.lbl_lang)
        conn_layout.addWidget(self.lang_combo)
        conn_layout.addWidget(self.lbl_theme)
        conn_layout.addWidget(self.theme_combo)
        main_layout.addLayout(conn_layout)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        # === Новый порядок вкладок ===
        self.create_tab_assembler()    # 0. Ассемблер
        self.create_tab_disasm()       # 1. Дизассемблер
        self.create_tab_hex()          # 2. HEX-редактор
        self.create_tab_emulator()     # 3. Эмулятор
        self.create_tab_trace()        # 4. Трассировка
        self.create_tab_scripts()      # 5. Скрипты
        self.create_tab_control()      # 6. Управление
        self.create_tab_data()         # 7. Данные
        self.create_tab_test()         # 8. Тесты
        self.create_tab_io_seq()       # 9. Секвенсор
        self.create_tab_compare()      # 10. Сравнение
        self.lbl_log = QLabel()
        main_layout.addWidget(self.lbl_log)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: Consolas, Courier New, monospace;")
        main_layout.addWidget(self.log_text)
        # Подключаем сигнал изменения данных в hex-редакторе
        self.hex_model.dataEdited.connect(self.on_hex_data_changed)
        
    def update_emulator_ui(self):
        """Обновляет UI эмулятора с подсветкой изменений"""
        state = self.emulator.get_state()
        
        # === РЕГИСТРЫ С ПОДСВЕТКОЙ ИЗМЕНЕНИЙ ===
        current_values = {}
        for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
            current_values[reg] = state[reg]
        for reg in ['SP', 'PC', 'BC', 'DE', 'HL']:
            current_values[reg] = state[reg]
        
        for reg, value in current_values.items():
            lbl = self.reg_labels[reg]
            if reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
                lbl.setText(f"{value:02X}")
            else:
                lbl.setText(f"{value:04X}")
            
            if reg in self.prev_reg_values and self.prev_reg_values[reg] != value:
                lbl.setStyleSheet("background-color: #ffcccc; padding: 2px; border: 1px solid #cc0000; font-weight: bold;")
            else:
                lbl.setStyleSheet("background-color: #f0f0f0; padding: 2px; border: 1px solid #ccc;")
        
        # === ФЛАГИ ===
        for flag in ['S', 'Z', 'AC', 'P', 'CY']:
            val = 1 if state['flags'][flag] else 0
            self.flag_labels[flag].setText(f"{flag}: {val}")
            if val:
                self.flag_labels[flag].setStyleSheet("color: red; font-weight: bold;")
            else:
                self.flag_labels[flag].setStyleSheet("color: black;")

        # 8085: IFF1, IFF2, I-регистр
        is_8085 = state.get('cpu_type', 'i8080') == 'i8085'
        self.iff1_label.setVisible(is_8085)
        self.iff2_label.setVisible(is_8085)
        self.i_reg_label.setVisible(is_8085)
        if is_8085:
            iff1_val = 1 if state['flags'].get('IFF1', False) else 0
            iff2_val = 1 if state['flags'].get('IFF2', False) else 0
            self.iff1_label.setText(f"IFF1: {iff1_val}")
            self.iff2_label.setText(f"IFF2: {iff2_val}")
            self.i_reg_label.setText(f"I: {state.get('I', 0):02X}")
            if iff1_val:
                self.iff1_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.iff1_label.setStyleSheet("color: black;")
            if iff2_val:
                self.iff2_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.iff2_label.setStyleSheet("color: black;")

        # === СТЕК ===
        self.update_stack_view()
        
        # === СТАТИСТИКА ===
        self.cycles_label.setText(f"{self.tr('emu_cycles')}{state['cycles']}")
        status = self.tr('emu_state_halted') if state['halted'] else (self.tr('emu_state_running') if state['running'] else self.tr('emu_state_ready'))
        self.state_label.setText(f"{self.tr('emu_state')}{status}")
        
        # === WATCH-ОКНО ===
        if hasattr(self, 'watch_model'):
            self.watch_model.refresh()
        
        # === ДИЗАССЕМБЛЕР ===
        self.update_emu_disasm_cursor()  # ← ЧАСТИЧНОЕ обновление (быстро)
        
    def _on_emu_cpu_changed(self, cpu_type: str):
        """Переключение типа процессора в эмуляторе""" 
        if self.emulator:
            self.emulator.cpu_type = cpu_type
            self.emulator.reset()
        if hasattr(self, 'disassembler') and self.disassembler:
            self.disassembler.set_cpu_type(cpu_type)
        self.current_cpu = cpu_type
        self.update_emulator_ui()

    def update_stack_view(self):
        """Обновляет панель стека БЕЗ пересоздания элементов"""
        sp = self.emulator.sp
        
        for i in range(8):
            addr = (sp + i * 2) & 0xFFFF
            value = self.emulator.read_word(addr)
            
            if i == 0:
                text = f"► {addr:04X}: {value:04X}  ← SP"
            else:
                text = f"  {addr:04X}: {value:04X}"
            
            # Обновляем существующий элемент или создаём новый
            if i < self.stack_list.count():
                item = self.stack_list.item(i)
                item.setText(text)
            else:
                item = QListWidgetItem(text)
                self.stack_list.addItem(item)
            
            # Стиль для вершины стека
            if i == 0:
                item.setForeground(QColor("#cc0000"))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            else:
                item.setForeground(QColor("#000000"))
                font = item.font()
                font.setBold(False)
                item.setFont(font)
    
    def update_emu_disasm_view(self):
        """ПОЛНОЕ обновление: дизассемблирование всей программы."""
        if not hasattr(self, 'emu_disasm_view'):
            return
        if not self.mem_data:
            return
        
        pc = self.emulator.pc
        min_addr = min(self.mem_data.keys())
        max_mem_addr = max(self.mem_data.keys())
        end_addr = max(max_mem_addr, pc) + 16
        length = end_addr - min_addr
        
        lines = self.disassembler.disassemble(self.mem_data, min_addr, length)
        self.emu_disasm_view.set_lines(lines)
        self.emu_disasm_view.set_highlight(pc)
        
        if hasattr(self.emu_disasm_view, 'set_breakpoints'):
            self.emu_disasm_view.set_breakpoints(self.emulator.breakpoints)
        
        self._scroll_emu_disasm_to_pc()
        
    def update_emu_disasm_cursor(self):
        """ЧАСТИЧНОЕ обновление: только подсветка PC и прокрутка.
        Если строки пустые — автоматически делает полное обновление."""
        if not hasattr(self, 'emu_disasm_view'):
            return
        
        # === ЗАЩИТА: если строки пустые, нужно полное обновление ===
        if not self.emu_disasm_view.lines:
            self.update_emu_disasm_view()
            return
        
        pc = self.emulator.pc
        self.emu_disasm_view.set_highlight(pc)
        self._scroll_emu_disasm_to_pc()
        self.emu_disasm_view.update()
        
    def _scroll_emu_disasm_to_pc(self):
        """Прокрутка встроенного дизассемблера к текущему PC"""
        pc = self.emulator.pc
        if hasattr(self.emu_disasm_view, 'addr_to_index') and pc in self.emu_disasm_view.addr_to_index:
            idx = self.emu_disasm_view.addr_to_index[pc]
            scroll_y = idx * self.emu_disasm_view.line_height
            if hasattr(self, 'emu_disasm_scroll'):
                self.emu_disasm_scroll.verticalScrollBar().setValue(max(0, scroll_y - 100))
        
    def highlight_pc_in_hex(self, pc):
        """Подсвечивает текущий PC в hex-редакторе"""
        model = self.hex_model
        if not model or not model.mem:
            return
            
        offset = pc - model.min_addr
        if offset < 0:
            return
        row = offset // 16
        col = (offset % 16) + 1
        
        index = model.index(row, col)
        if index.isValid():
            self.table.scrollTo(index, QTableView.PositionAtCenter)
            
    def emulator_step(self):
        """Пошаговое выполнение"""
        self.emulator.step()
        self.update_emulator_ui()
        
    def emulator_run(self):
        """Запуск эмулятора (F5)"""
        if self.emulator.halted:
            self.statusBar.showMessage(self.tr("status_cpu_halted"), 3000)
            return
        self.run_target_addr = None
        
        # === Если PC на breakpoint, обходим его (выполняем одну инструкцию) ===
        if self.emulator.pc in self.emulator.breakpoints:
            self._save_watch_prev_values()
            self._save_reg_prev_values()
            self.emulator.step_into()  # step_into обходит BP на текущем PC
        
        self.emulator.running = True
        if not hasattr(self, 'run_timer'):
            self.run_timer = QTimer()
            self.run_timer.timeout.connect(self._run_tick)
        self.run_timer.start(20)
        self.statusBar.showMessage("Running...", 0)
        
    def set_pc_dialog(self):
        """Диалог установки PC"""
        text, ok = QInputDialog.getText(self, self.tr("set_pc_title"), self.tr("bp_addr"))
        if ok:
            try:
                addr = int(text, 16)
                self.emulator.set_pc(addr)
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("bp_err_addr"))
                
    def add_breakpoint_dialog(self):
        """Диалог добавления точки останова"""
        text, ok = QInputDialog.getText(self, self.tr("bp_addr"), self.tr("bp_addr"))
        if ok:
            try:
                addr = int(text, 16)
                self.emulator.add_breakpoint(addr)
                self.sync_breakpoints()
                self.log(f"Breakpoint set: 0x{addr:04X}")
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("bp_err_addr"))
               
    def clear_breakpoints(self):
        """Очистить все точки останова"""
        self.emulator.clear_all_breakpoints()
        self.sync_breakpoints()
        
    def create_tab_control(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.bus_group = QGroupBox()
        bus_layout = QHBoxLayout()
        self.btn_hold = QPushButton()
        self.btn_unhold = QPushButton()
        #self.btn_hold.clicked.connect(lambda: self.send_command(bytes([CMD_HOLD])))
        #self.btn_unhold.clicked.connect(lambda: self.send_command(bytes([CMD_UNHOLD])))
        self.btn_hold.clicked.connect(self.on_hold_clicked)
        self.btn_unhold.clicked.connect(self.on_unhold_clicked)
        #
        bus_layout.addWidget(self.btn_hold)
        bus_layout.addWidget(self.btn_unhold)
        self.bus_group.setLayout(bus_layout)
        layout.addWidget(self.bus_group)
        
        self.file_group = QGroupBox()
        file_layout = QHBoxLayout()
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self.save_dump)
        self.btn_load = QPushButton()
        self.btn_load.clicked.connect(self.load_and_flash)
        file_layout.addWidget(self.btn_save)
        file_layout.addWidget(self.btn_load)
        self.file_group.setLayout(file_layout)
        layout.addWidget(self.file_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "")
        self.tab_control = tab
		
        self.btn_mcp = QPushButton(self.tr("mcp_off"))
        self.btn_mcp.clicked.connect(self.on_mcp_toggle)
        layout.addWidget(self.btn_mcp)

    def create_tab_data(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.mem_group = QGroupBox()
        mem_layout = QGridLayout()
        
        self.mem_data_addr = QLineEdit("0000")
        self.mem_data_bits = QComboBox()
        self.mem_data_bits.addItems(["8", "16", "24", "32"])
        self.mem_data_bits.setCurrentText("8")
        self.mem_data_value = QLineEdit("00")
        self.mem_data_endian = QComboBox()
        self.mem_data_endian.addItem(self.tr("endian_little"), "Little")
        self.mem_data_endian.addItem(self.tr("endian_big"), "Big")
        self.mem_data_endian.setCurrentIndex(0)
        
        self.btn_mem_read = QPushButton()
        self.btn_mem_write = QPushButton()
        self.btn_mem_read.clicked.connect(self.read_memory_data)
        self.btn_mem_write.clicked.connect(self.write_memory_data)
        
        self.lbl_mem_addr = QLabel()
        self.lbl_mem_bits = QLabel()
        self.lbl_mem_value = QLabel()
        self.lbl_mem_endian = QLabel()
        
        mem_layout.addWidget(self.lbl_mem_addr, 0, 0)
        mem_layout.addWidget(self.mem_data_addr, 0, 1)
        mem_layout.addWidget(self.lbl_mem_bits, 1, 0)
        mem_layout.addWidget(self.mem_data_bits, 1, 1)
        mem_layout.addWidget(self.lbl_mem_value, 2, 0)
        mem_layout.addWidget(self.mem_data_value, 2, 1)
        mem_layout.addWidget(self.lbl_mem_endian, 3, 0)
        mem_layout.addWidget(self.mem_data_endian, 3, 1)
        mem_layout.addWidget(self.btn_mem_read, 4, 0)
        mem_layout.addWidget(self.btn_mem_write, 4, 1)
        
        self.mem_group.setLayout(mem_layout)
        layout.addWidget(self.mem_group)
        
        self.io_group = QGroupBox()
        io_layout = QGridLayout()
        
        self.io_data_addr = QLineEdit("00")
        self.io_data_bits = QComboBox()
        self.io_data_bits.addItems(["8", "16", "24", "32"])
        self.io_data_bits.setCurrentText("8")
        self.io_data_value = QLineEdit("00")
        self.io_data_endian = QComboBox()
        self.io_data_endian.addItem(self.tr("endian_little"), "Little")
        self.io_data_endian.addItem(self.tr("endian_big"), "Big")
        self.io_data_endian.setCurrentIndex(0)
        
        self.btn_io_read = QPushButton()
        self.btn_io_write = QPushButton()
        self.btn_io_read.clicked.connect(self.read_io_data)
        self.btn_io_write.clicked.connect(self.write_io_data)
        
        self.lbl_io_addr = QLabel()
        self.lbl_io_bits = QLabel()
        self.lbl_io_value = QLabel()
        self.lbl_io_endian = QLabel()
        
        io_layout.addWidget(self.lbl_io_addr, 0, 0)
        io_layout.addWidget(self.io_data_addr, 0, 1)
        io_layout.addWidget(self.lbl_io_bits, 1, 0)
        io_layout.addWidget(self.io_data_bits, 1, 1)
        io_layout.addWidget(self.lbl_io_value, 2, 0)
        io_layout.addWidget(self.io_data_value, 2, 1)
        io_layout.addWidget(self.lbl_io_endian, 3, 0)
        io_layout.addWidget(self.io_data_endian, 3, 1)
        io_layout.addWidget(self.btn_io_read, 4, 0)
        io_layout.addWidget(self.btn_io_write, 4, 1)
        
        self.io_group.setLayout(io_layout)
        layout.addWidget(self.io_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "")
        self.tab_data = tab

    def create_tab_hex(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        ctrl_layout = QHBoxLayout()
        self.lbl_range = QLabel()
        self.btn_read_block = QPushButton()
        self.btn_read_block.clicked.connect(self.show_read_block_dialog)
        self.btn_search = QPushButton()
        self.btn_search.clicked.connect(self.show_search_dialog)
        ctrl_layout.addWidget(self.lbl_range)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_read_block)
        ctrl_layout.addWidget(self.btn_search)
        layout.addLayout(ctrl_layout)
        
        self.table = HexTableView(self.disassembler, self.mem_data)
        self.table.setModel(self.hex_model)
        
        # === Размеры колонок ===
        # Колонка 0 (Addr): по содержимому
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # Колонки 1-16 (данные): узкие, фиксированные
        for i in range(1, 17):
            self.table.setColumnWidth(i, 32)
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
        
        # Колонка 17 (ASCII/Текст): растягивается на оставшееся место
        self.table.horizontalHeader().setSectionResizeMode(17, QHeaderView.Stretch)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Consolas", 10))
        layout.addWidget(self.table)
        
        # Подключаем сигналы
        self.table.statusUpdate.connect(self.on_status_update)
        self.table.gotoAddress.connect(self.goto_address)
        self.table.editOperation.connect(self.push_undo)
        
        self.tabs.addTab(tab, "")
        self.tab_hex = tab

    def create_tab_assembler(self):
        """Создать вкладку Ассемблер"""
        is_dark = (self.current_theme == "Dark")
        self.assembler_widget = AssemblerWidget(main_window=self, is_dark=is_dark)
        self.tabs.addTab(self.assembler_widget, "")
        self.tab_assembler = self.assembler_widget
        
    def create_tab_disasm(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        ctrl_layout = QHBoxLayout()
        self.lbl_disasm_start = QLabel()
        self.disasm_start = QLineEdit("0000")
        self.lbl_disasm_len = QLabel()
        self.disasm_len = QLineEdit("100")
        self.btn_disasm = QPushButton()
        self.btn_disasm.clicked.connect(self.run_disasm)
        self.auto_disasm_check = QCheckBox()
        self.auto_disasm_check.setChecked(True)
        ctrl_layout.addWidget(self.lbl_disasm_start)
        ctrl_layout.addWidget(self.disasm_start)
        ctrl_layout.addWidget(self.lbl_disasm_len)
        ctrl_layout.addWidget(self.disasm_len)
        ctrl_layout.addWidget(self.btn_disasm)
        ctrl_layout.addWidget(self.auto_disasm_check)
        self.btn_export_disasm = QPushButton("Export")  # Будет переведено в retranslate_ui
        self.btn_export_disasm.clicked.connect(self.export_disasm)
        ctrl_layout.addWidget(self.btn_export_disasm)
        self.btn_load_map = QPushButton("Load Map")  # Будет переведено в retranslate_ui
        self.btn_load_map.clicked.connect(self.on_load_map)
        ctrl_layout.addWidget(self.btn_load_map)
        layout.addLayout(ctrl_layout)
        
        self.disasm_view = DisasmView(self.mem_data)
        self.disasm_scroll = QScrollArea()
        self.disasm_scroll.setWidget(self.disasm_view)
        self.disasm_scroll.setWidgetResizable(True)
        #self.disasm_view.toggleBreakpoint.connect(self.on_toggle_breakpoint)
        layout.addWidget(self.disasm_scroll)
        
        self.tabs.addTab(tab, "")
        self.tab_disasm = tab
		        
    def create_tab_test(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form_layout = QHBoxLayout()
        self.lbl_test_start = QLabel()
        self.test_start = QLineEdit("0000")
        self.lbl_test_end = QLabel()
        self.test_end = QLineEdit("00FF")
        self.lbl_test_pattern = QLabel()
        self.test_pattern = QComboBox()
        self.test_pattern.addItem(self.tr("test_pattern_checker"), "Checker")
        self.test_pattern.addItem(self.tr("test_pattern_zero"), "Zero")
        self.test_pattern.addItem(self.tr("test_pattern_one"), "One")
        self.test_pattern.addItem(self.tr("test_pattern_addr"), "Addr")
        
        form_layout.addWidget(self.lbl_test_start)
        form_layout.addWidget(self.test_start)
        form_layout.addWidget(self.lbl_test_end)
        form_layout.addWidget(self.test_end)
        form_layout.addWidget(self.lbl_test_pattern)
        form_layout.addWidget(self.test_pattern)
        layout.addLayout(form_layout)
        
        self.btn_test = QPushButton()
        self.btn_test.clicked.connect(self.start_mem_test)
        layout.addWidget(self.btn_test)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.tabs.addTab(tab, "")
        self.tab_test = tab

    def create_tab_io_seq(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.single_io_group = QGroupBox()
        single_layout = QHBoxLayout()
        self.io_addr = QLineEdit("00")
        self.io_data = QLineEdit("00")
        self.btn_io_read_single = QPushButton()
        self.btn_io_write_single = QPushButton()
        self.btn_io_read_single.clicked.connect(self.io_read_single)
        self.btn_io_write_single.clicked.connect(self.io_write_single)
        self.lbl_io_seq_port = QLabel()
        self.lbl_io_seq_data = QLabel()
        single_layout.addWidget(self.lbl_io_seq_port)
        single_layout.addWidget(self.io_addr)
        single_layout.addWidget(self.lbl_io_seq_data)
        single_layout.addWidget(self.io_data)
        single_layout.addWidget(self.btn_io_read_single)
        single_layout.addWidget(self.btn_io_write_single)
        self.single_io_group.setLayout(single_layout)
        layout.addWidget(self.single_io_group)
        
        self.seq_group = QGroupBox()
        seq_layout = QVBoxLayout()
        
        seq_ctrl_layout = QHBoxLayout()
        self.btn_seq_load = QPushButton()
        self.btn_seq_load.clicked.connect(self.load_sequence_file)
        self.btn_seq_run = QPushButton()
        self.btn_seq_run.clicked.connect(self.run_io_sequence)
        seq_ctrl_layout.addWidget(self.btn_seq_load)
        seq_ctrl_layout.addWidget(self.btn_seq_run)
        seq_layout.addLayout(seq_ctrl_layout)
        
        self.seq_text = QTextEdit()
        self.seq_text.setPlaceholderText(self.tr("seq_placeholder"))
        self.seq_text.setFont(QFont("Consolas", 10))
        seq_layout.addWidget(self.seq_text)
        
        self.seq_group.setLayout(seq_layout)
        layout.addWidget(self.seq_group)
        
        self.tabs.addTab(tab, "")
        self.tab_io_seq = tab

    # ==================== ЛОКАЛИЗАЦИЯ И ТЕМЫ ====================
    def on_lang_changed(self, index):
        self.current_lang = "ru" if index == 0 else "en"
        set_language(self.current_lang)  # Уведомляем все диалоги
        self.settings.setValue("language", self.current_lang)  # Сохраняем настройку
        self.retranslate_ui()
        
    def on_theme_changed(self, index):
        self.current_theme = "Light" if index == 0 else "Dark"
        self.settings.setValue("theme", self.current_theme)  # Сохраняем настройку
        QApplication.instance().setStyleSheet(THEMES[self.current_theme])
        
        is_dark = (self.current_theme == "Dark")

        # Обновляем тему ассемблера
        if hasattr(self, 'assembler_widget'):
            self.assembler_widget.set_theme(is_dark)

        # Обновляем тему дизассемблера 
        if hasattr(self, 'emu_disasm_view'):
            self.emu_disasm_view.set_theme(is_dark)
        
    def retranslate_ui(self):
        self.setWindowTitle(self.tr("app_title"))
        
        # ============================================================
        # ВЕРХНЯЯ ПАНЕЛЬ
        # ============================================================
        self.lbl_port.setText(self.tr("port"))
        self.lbl_baud.setText(self.tr("baud"))
        self.btn_refresh.setText(self.tr("refresh"))
        self.btn_connect.setText(
            self.tr("connect") if not (self.serial_port and self.serial_port.is_open) 
            else self.tr("disconnect")
        )
        self.lbl_lang.setText(self.tr("language"))
        self.lbl_theme.setText(self.tr("theme"))
        
        # ============================================================
        # ВКЛАДКИ (в порядке создания)
        # ============================================================
        self.tabs.setTabText(0, self.tr("tab_asm"))        # Ассемблер
        self.tabs.setTabText(1, self.tr("tab_disasm"))     # Дизассемблер
        self.tabs.setTabText(2, self.tr("tab_hex"))        # Hex Редактор
        self.tabs.setTabText(3, self.tr("tab_emulator"))   # Эмулятор
        self.tabs.setTabText(4, self.tr("tab_trace"))      # Трассировка
        self.tabs.setTabText(5, self.tr("tab_scripts"))    # Скрипты
        self.tabs.setTabText(6, self.tr("tab_control"))    # Управление
        self.tabs.setTabText(7, self.tr("tab_data"))       # Данные
        self.tabs.setTabText(8, self.tr("tab_test"))       # Тест Памяти
        self.tabs.setTabText(9, self.tr("tab_io_seq"))     # IO Секвенсор
        self.tabs.setTabText(10, self.tr("tab_compare"))   # Сравнение
        
        # ============================================================
        # ВКЛАДКА "УПРАВЛЕНИЕ"
        # ============================================================
        self.bus_group.setTitle(self.tr("bus_control"))
        self.btn_hold.setText(self.tr("hold"))
        self.btn_unhold.setText(self.tr("unhold"))
        self.file_group.setTitle(self.tr("files"))
        self.btn_save.setText(self.tr("save_dump"))
        self.btn_load.setText(self.tr("load_fw"))
        
        # ============================================================
        # ВКЛАДКА "ДАННЫЕ"
        # ============================================================
        self.mem_group.setTitle(self.tr("memory"))
        self.lbl_mem_addr.setText(self.tr("addr_hex"))
        self.lbl_mem_bits.setText(self.tr("bits"))
        self.lbl_mem_value.setText(self.tr("value_hex"))
        self.lbl_mem_endian.setText(self.tr("endian"))
        self.btn_mem_read.setText(self.tr("read"))
        self.btn_mem_write.setText(self.tr("write"))
        
        self.io_group.setTitle(self.tr("io_port"))
        self.lbl_io_addr.setText(self.tr("port_hex"))
        self.lbl_io_bits.setText(self.tr("bits"))
        self.lbl_io_value.setText(self.tr("value_hex"))
        self.lbl_io_endian.setText(self.tr("endian"))
        self.btn_io_read.setText(self.tr("read"))
        self.btn_io_write.setText(self.tr("write"))
        
        # ============================================================
        # ВКЛАДКА "HEX РЕДАКТОР"
        # ============================================================
        self.btn_read_block.setText(self.tr("read_block"))
        self.btn_search.setText(self.tr("search"))
        self.update_range_label()
        
        # ============================================================
        # ВКЛАДКА "ДИЗАССЕМБЛЕР"
        # ============================================================
        self.lbl_disasm_start.setText(self.tr("start"))
        self.lbl_disasm_len.setText(self.tr("len"))
        self.btn_disasm.setText(self.tr("disasm"))
        self.auto_disasm_check.setText(self.tr("auto_disasm"))
        self.btn_export_disasm.setText(self.tr("export"))
        self.btn_load_map.setText(self.tr("asm_load_map"))
        
        # ============================================================
        # ВКЛАДКА "ТЕСТ ПАМЯТИ"
        # ============================================================
        self.lbl_test_start.setText(self.tr("start"))
        self.lbl_test_end.setText(self.tr("end"))
        self.lbl_test_pattern.setText(self.tr("pattern"))
        self.btn_test.setText(self.tr("start_test"))
        
        # ============================================================
        # ВКЛАДКА "IO СЕКВЕНСОР"
        # ============================================================
        self.single_io_group.setTitle(self.tr("single_io"))
        self.lbl_io_seq_port.setText(self.tr("port_hex"))
        self.lbl_io_seq_data.setText(self.tr("value_hex"))
        self.btn_io_read_single.setText(self.tr("read_in"))
        self.btn_io_write_single.setText(self.tr("write_out"))
        self.seq_group.setTitle(self.tr("io_seq"))
        self.btn_seq_load.setText(self.tr("load_file"))
        self.btn_seq_run.setText(self.tr("run_seq"))
        
        # ============================================================
        # ВКЛАДКА "СРАВНЕНИЕ"
        # ============================================================
        self.btn_load_compare.setText(self.tr("load_compare"))
        self.btn_compare.setText(self.tr("btn_compare"))
        self.btn_export_compare.setText(self.tr("export_report"))
        self.lbl_compare_info.setText(self.tr("no_compare_file"))
        
        # Заголовки таблицы сравнения
        self.compare_table.setHorizontalHeaderLabels([
            self.tr("compare_addr"),
            self.tr("compare_current"),
            self.tr("compare_file"),
            self.tr("compare_status")
        ])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # ============================================================
        # ВКЛАДКА "СКРИПТЫ"
        # ============================================================
        self.btn_run_script.setText(self.tr("run_script"))
        self.btn_load_script.setText(self.tr("load_script"))
        self.btn_save_script.setText(self.tr("save_script"))
        self.btn_clear_output.setText(self.tr("clear_output"))
        self.lbl_script_output.setText(self.tr("script_output_label"))
        
        # ============================================================
        # ВКЛАДКА "ЭМУЛЯТОР"
        # ============================================================
        self.emulator_retranslate()
        
        # ============================================================
        # ВКЛАДКА "ТРАССИРОВКА"
        # ============================================================
        if hasattr(self, 'btn_trace_toggle'):
            if self.btn_trace_toggle.isChecked():
                self.btn_trace_toggle.setText(self.tr("trace_off"))
            else:
                self.btn_trace_toggle.setText(self.tr("trace_on"))
            self.lbl_trace_detail.setText(self.tr("trace_detail_hint"))
            self.btn_trace_clear.setText(self.tr("trace_clear"))
            self.btn_trace_export.setText(self.tr("trace_export"))
            self.lbl_trace_depth.setText(self.tr("trace_depth"))
            self.lbl_trace_search.setText(self.tr("trace_search"))
            self.txt_trace_search.setPlaceholderText(self.tr("trace_search_hint"))
            self.trace_detail_group.setTitle(self.tr("trace_detail_title"))
            self.btn_trace_filter_clear.setToolTip(self.tr("trace_filter_clear"))
            
        # ============================================================
        # МЕНЮ ПРОФИЛЕЙ
        # ============================================================
        if hasattr(self, 'profile_menu'):
            self.profile_menu.setTitle(self.tr("menu_profile"))
            
        # ============================================================
        # СТРОКА СТАТУСА
        # ============================================================
        self.status_label_size.setText(f"0 {self.tr('status_size')}")
        
        # ============================================================
        # ЛОГ
        # ============================================================
        self.lbl_log.setText(self.tr("log"))
        
        # ============================================================
        # ОБНОВЛЕНИЕ ЯЗЫКА МОДЕЛИ
        # ============================================================
        self.hex_model.lang = self.current_lang
        self.hex_model.layoutChanged.emit()
        
        # обновление диалога поиска
        if hasattr(self, 'search_dialog'):
            self.search_dialog.retranslate()
        
        # модель трассировки
        if hasattr(self, 'trace_model'):
            self.trace_model.lang = self.current_lang
            self.trace_model.refresh()
        
        # модель Watch  ← ДОБАВЛЕНО
        if hasattr(self, 'watch_model'):
            self.watch_model.lang = self.current_lang
            self.watch_model.layoutChanged.emit()
        
        # модель Breakpoints  ← ДОБАВЛЕНО
        if hasattr(self, 'bp_model'):
            self.bp_model.lang = self.current_lang
            self.bp_model.refresh()
        
        # язык дизассемблера эмулятора
        if hasattr(self, 'emu_disasm_view'):
            self.emu_disasm_view.lang = self.current_lang
            self.emu_disasm_view.update()
        
        # === Тултипы кнопок трассировки ===
        if hasattr(self, 'btn_trace_filter_clear'):
            self.btn_trace_filter_clear.setToolTip(self.tr("trace_filter_clear"))
            
        # === Тултипы кнопок эмулятора ===
        if hasattr(self, 'btn_watch_add'):
            self.btn_watch_add.setToolTip(self.tr("tip_watch_add"))
            self.btn_watch_del.setToolTip(self.tr("tip_watch_del"))
            self.btn_watch_clear.setToolTip(self.tr("tip_watch_clear"))
            self.btn_watch_save_preset.setToolTip(self.tr("tip_watch_save"))
            self.btn_watch_load_preset.setToolTip(self.tr("tip_watch_load"))
            self.btn_bp_add.setToolTip(self.tr("tip_bp_add"))
            self.btn_bp_cond.setToolTip(self.tr("tip_bp_cond"))
            self.btn_bp_toggle.setToolTip(self.tr("tip_bp_toggle"))
            self.btn_bp_del.setToolTip(self.tr("tip_bp_del"))
            self.btn_bp_clear.setToolTip(self.tr("tip_bp_clear"))
            self.btn_bp_save_preset.setToolTip(self.tr("tip_bp_save"))
            self.btn_bp_load_preset.setToolTip(self.tr("tip_bp_load"))
            self.chk_trace_enable.setToolTip(self.tr("tip_trace_enable"))
        
        # === Устройства ===
        if hasattr(self, 'devices_menu'):
            self.devices_menu.setTitle(self.tr("menu_devices"))
        if hasattr(self, 'help_menu'):
            self.help_menu.setTitle(self.tr("menu_help"))
            self.act_help_guide.setText(self.tr("help_user_guide"))
            self.act_help_readme.setText(self.tr("help_readme"))
            self.act_help_changes.setText(self.tr("help_changes"))
            self.act_help_analysis.setText(self.tr("help_analysis"))
            self.act_help_mcp.setText(self.tr("help_mcp"))
            self.act_help_scripts.setText(self.tr("help_scripts"))
            self.act_help_about.setText(self.tr("help_about"))
        if hasattr(self, 'act_device_manager'):
            self.act_device_manager.setText(self.tr("device_manager"))

        # === Status bar ===
        self.status_label_addr.setText(self.tr("status_addr") + "-")
        self.status_label_data.setText(self.tr("status_data") + "-")
        self.status_label_mnem.setText(self.tr("status_mnem") + "-")
        self.status_label_size.setText(self.tr("status_size") + "0 " + self.tr("bytes"))
        self.status_label_conn.setText(self.tr("disconnected"))

        # Theme combo (preserve index)
        idx = self.theme_combo.currentIndex()
        self.theme_combo.clear()
        self.theme_combo.addItems([self.tr("light"), self.tr("dark")])
        self.theme_combo.setCurrentIndex(idx)

        # Endianness combos (preserve index)
        for combo in [self.mem_data_endian, self.io_data_endian]:
            idx = combo.currentIndex()
            combo.clear()
            combo.addItem(self.tr("endian_little"), "Little")
            combo.addItem(self.tr("endian_big"), "Big")
            combo.setCurrentIndex(idx)

        # Test pattern combo (preserve index)
        idx = self.test_pattern.currentIndex()
        self.test_pattern.clear()
        self.test_pattern.addItem(self.tr("test_pattern_checker"), "Checker")
        self.test_pattern.addItem(self.tr("test_pattern_zero"), "Zero")
        self.test_pattern.addItem(self.tr("test_pattern_one"), "One")
        self.test_pattern.addItem(self.tr("test_pattern_addr"), "Addr")
        self.test_pattern.setCurrentIndex(idx)

        # MCP button
        if hasattr(self, 'btn_mcp'):
            if hasattr(self, 'mcp_server') and self.mcp_server and getattr(self.mcp_server, 'running', False):
                self.btn_mcp.setText(self.tr("mcp_on"))
            else:
                self.btn_mcp.setText(self.tr("mcp_off"))

        # Emulator stats
        if hasattr(self, 'cycles_label'):
            self.cycles_label.setText(self.tr("emu_cycles") + "0")
        if hasattr(self, 'state_label'):
            self.state_label.setText(self.tr("emu_state") + self.tr("emu_state_halted"))

        # Trace status
        if hasattr(self, 'lbl_trace_status'):
            self.lbl_trace_status.setText(self.tr("trace_records") + "0 / 10000")
        if hasattr(self, 'txt_trace_search'):
            self.txt_trace_search.setPlaceholderText(self.tr("trace_search_hint"))
            
    # ==================== ЛОГИКА ====================
    def refresh_ports(self):
        self.port_combo.clear()
        for p in serial.tools.list_ports.comports():
            self.port_combo.addItem(f"{p.device} - {p.description}", p.device)

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            # === Отключение ===
            # Очищаем очередь
            self.command_queue.clear()
            self.waiting_response = False
            
            if self.bus_active:
                self.log("Releasing bus before disconnect...")
                try:
                    self.serial_port.write(SlipProtocol.encode(bytes([CMD_UNHOLD])))
                    self.serial_port.flush()
                    time.sleep(0.5)
                except serial.SerialException:
                    pass
            
            self.serial_port.close()
            self.poll_timer.stop()
            self.is_connected = False
            self.bus_active = False
            self.btn_connect.setText(self.tr("connect"))
            self.update_ui_state()
            self.log(self.tr("disconnected"))
        else:
            # === Подключение ===
            port_name = self.port_combo.currentData()
            baud_rate = int(self.baud_combo.currentText())
            if not port_name:
                QMessageBox.warning(self, self.tr("error"), self.tr("err_port"))
                return
            try:
                self.serial_port = serial.Serial(port_name, baud_rate, timeout=0.1, write_timeout=1.0)
                self.serial_port.dtr = False
                self.serial_port.rts = False
                time.sleep(2)
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                self.poll_timer.start(50)
                self.is_connected = True
                self.bus_active = False
                self.btn_connect.setText(self.tr("disconnect"))
                self.update_ui_state()
                self.log(f"{self.tr('connected')} {port_name} ({baud_rate}).")
                
                # Отправляем команды через очередь (последовательно)
                #self.log(self.tr("test_conn"))
                self.send_command(bytes([CMD_NOP]))
                
                #self.log("Requesting max block size...")
                self.send_command(bytes([CMD_GET_SIZE_SETUP]))
                
            except serial.SerialException as e:
                QMessageBox.critical(self, self.tr("err_connect"), f"{self.tr('err_open')} {port_name}:\n{e}")
                self.serial_port = None
                self.is_connected = False
                self.update_ui_state()
            except Exception as e:
                QMessageBox.critical(self, self.tr("error"), str(e))
                self.is_connected = False
                self.update_ui_state()
				
    def log(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def send_command(self, payload):
        """Добавляет команду в очередь отправки"""
        self.command_queue.append(payload)
        self.process_command_queue()
        
    def process_command_queue(self):
        """Обрабатывает очередь команд"""
        if self.waiting_response or not self.command_queue or self.worker_active:
            return
            
        if not self.serial_port or not self.serial_port.is_open:
            self.command_queue.clear()
            return
            
        payload = self.command_queue.pop(0)
        try:
            # Логируем команду при реальной отправке
            cmd_name = self.get_command_name(payload[0] if payload else 0)
            self.log(f"TX [{cmd_name}] -> {payload.hex(' ').upper()}")
            
            self.serial_port.write(SlipProtocol.encode(payload))
            self.serial_port.flush()
            self.waiting_response = True
            
            QTimer.singleShot(2000, self.on_command_timeout)
        except serial.SerialException as e:
            self.log(f"{self.tr('err_send')} {e}")
            self.waiting_response = False
            self.process_command_queue()
            
    def get_command_name(self, cmd):
        """Возвращает имя команды для лога"""
        names = {
            0x00: "NOP",
            0x01: "HOLD",
            0x02: "UNHOLD",
            0x10: "MEM_R",
            0x11: "MEM_R_BLK",
            0x12: "MEM_W",
            0x13: "MEM_W_BLK",
            0x20: "IO_R",
            0x21: "IO_R_BLK",
            0x22: "IO_W",
            0x23: "IO_W_BLK",
            0x32: "EEPROM_W",
            0x33: "EEPROM_W_BLK",
            0x40: "GET_SIZE",
            0x41: "SET_POLARITY",
        }
        return names.get(cmd, f"CMD_{cmd:02X}")
            
    def on_command_timeout(self):
        """Таймаут ожидания ответа на команду"""
        if self.waiting_response:
            self.log("Command timeout!")
            self.waiting_response = False
            self.process_command_queue()
    	
    def read_serial(self):
        if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting:
            try:
                self.rx_buffer.extend(self.serial_port.read(self.serial_port.in_waiting))
            except serial.SerialException as e:
                self.log(f"{self.tr('err_read_port')} {e}")
                return
                
            while _FEND in self.rx_buffer:
                end_idx = self.rx_buffer.index(_FEND)
                packet_raw = self.rx_buffer[:end_idx]
                self.rx_buffer = self.rx_buffer[end_idx+1:]
                if packet_raw:
                    self.process_response(SlipProtocol.decode(packet_raw))

    def process_response(self, data):
        if not data: return
        self.log(f"RX <- {data.hex(' ').upper()}")
        cmd = data[0]
        
        # Определяем, является ли ответ финальным
        is_final = True
        if cmd == CMD_HOLD and len(data) >= 2:
            ack = data[1]
            if ack in [ACK_HOLD_WAIT_LOW, ACK_HOLD_WAIT_HIGH]:
                is_final = False
        elif cmd == CMD_UNHOLD and len(data) >= 2:
            ack = data[1]
            if ack == ACK_WAIT_UNHOLD:
                is_final = False
        
        # === Обработка ответа ===
        if cmd == ACK_NOP:
            self.log(f"  [{self.tr('ok')}] {self.tr('conn_est')}")
        elif cmd == ACK_GET_SIZE_SETUP and len(data) >= 2:
            self.max_block_size = data[1]
            self.log(f"  [{self.tr('ok')}] Max block size: {self.max_block_size}")
        elif cmd == CMD_HOLD and len(data) >= 2:
            ack = data[1]
            if ack == ACK_HOLD_ACTIVE:
                self.bus_active = True
                self.update_ui_state()
                self.log(f"  [{self.tr('ok')}] Bus HOLD active.")
            elif ack == ACK_HOLD_WAIT_LOW:
                self.log("  [WAIT] HLDA low...")
            elif ack == ACK_HOLD_WAIT_HIGH:
                self.log("  [WAIT] HLDA high...")
        elif cmd == CMD_UNHOLD and len(data) >= 2:
            ack = data[1]
            if ack == ACK_UNHOLD:
                self.bus_active = False
                self.update_ui_state()
                self.log(f"  [{self.tr('ok')}] Bus UNHOLD. CPU running.")
            elif ack == ACK_WAIT_UNHOLD:
                self.log("  [WAIT] HLDA high...")
        elif cmd == ACK_MEM_READ_BYTE and len(data) >= 4:
            addr = (data[1] << 8) | data[2]
            self.mem_data[addr] = data[3]
            self.hex_model.update_data(self.mem_data)
            self.update_range_label()
            self.log(f"  [{self.tr('ok')}] 0x{addr:04X}: 0x{data[3]:02X}")
        elif cmd == ACK_IO_READ_BYTE and len(data) >= 4:
            addr = (data[1] << 8) | data[2]
            val = data[3]
            self.log(f"  [{self.tr('ok')}] IO Read 0x{addr:02X}: 0x{val:02X}")
        elif cmd == ACK_IO_WRITE_BYTE:
            self.log(f"  [{self.tr('ok')}] {self.tr('write_io')}.")
        elif cmd == ACK_EEPROM_WRITE_BYTE:
            self.log(f"  [{self.tr('ok')}] EEPROM write complete.")
        elif cmd == ACK_EEPROM_WRITE_BLOCK:
            self.log(f"  [{self.tr('ok')}] EEPROM block write complete.")
        elif cmd == ACK_ERROR:
            self.log(f"  [{self.tr('error')}] {self.tr('err_ack')}")
        
        # === Снимаем флаг и отправляем следующую команду ===
        if is_final:
            self.waiting_response = False
            self.process_command_queue()
        
    def update_range_label(self):
        if self.mem_data:
            mn = min(self.mem_data.keys()); mx = max(self.mem_data.keys())
            self.lbl_range.setText(f"{self.tr('range')} 0x{mn:04X} - 0x{mx:04X} ({len(self.mem_data)} {self.tr('bytes')})")
            self.status_label_size.setText(f"{len(self.mem_data)} {self.tr('bytes')}")  # ← Добавить
        else:
            self.lbl_range.setText(f"{self.tr('range')} -")
            self.status_label_size.setText(f"0 {self.tr('bytes')}")
            
    # ==================== КОНВЕРТАЦИЯ ЗНАЧЕНИЙ ====================
    def value_to_bytes(self, value, bits, endian):
        size = bits // 8
        if endian == "Little":
            return [(value >> (8 * i)) & 0xFF for i in range(size)]
        else:
            return [(value >> (8 * (size - 1 - i))) & 0xFF for i in range(size)]

    def bytes_to_value(self, byte_list, bits, endian):
        size = bits // 8
        value = 0
        if endian == "Little":
            for i in range(size):
                value |= byte_list[i] << (8 * i)
        else:
            for i in range(size):
                value |= byte_list[i] << (8 * (size - 1 - i))
        return value

    # ==================== ЧТЕНИЕ/ЗАПИСЬ ДАННЫХ ====================
    def read_memory_data(self):
        try:
            addr = int(self.mem_data_addr.text(), 16)
            bits = int(self.mem_data_bits.currentText())
            size = bits // 8
            endian = self.mem_data_endian.currentData()
            self.pending_read = {"addr": addr, "bits": bits, "endian": endian, "is_io": False}
            self.start_worker("read_block", (addr, size))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr"))

    def write_memory_data(self):
        try:
            addr = int(self.mem_data_addr.text(), 16)
            bits = int(self.mem_data_bits.currentText())
            endian = self.mem_data_endian.currentData()
            value = int(self.mem_data_value.text(), 16)
            byte_list = self.value_to_bytes(value, bits, endian)
            mem_dict = {addr + i: byte_list[i] for i in range(len(byte_list))}
            self.mem_data.update(mem_dict)
            self.hex_model.update_data(self.mem_data)
            self.update_range_label()
            self.start_worker("write_block", (mem_dict, addr))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr_val"))

    def read_io_data(self):
        try:
            port = int(self.io_data_addr.text(), 16)
            bits = int(self.io_data_bits.currentText())
            size = bits // 8
            endian = self.io_data_endian.currentData()
            self.pending_read = {"addr": port, "bits": bits, "endian": endian, "is_io": True}
            self.start_worker("read_io_block", (port, size))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_port_addr"))

    def write_io_data(self):
        try:
            port = int(self.io_data_addr.text(), 16)
            bits = int(self.io_data_bits.currentText())
            endian = self.io_data_endian.currentData()
            value = int(self.io_data_value.text(), 16)
            byte_list = self.value_to_bytes(value, bits, endian)
            io_dict = {port + i: byte_list[i] for i in range(len(byte_list))}
            self.start_worker("write_io_block", (io_dict, port))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr_val"))

    # ==================== ФАЙЛЫ ====================
    def save_dump(self):
        if not self.mem_data:
            QMessageBox.warning(self, self.tr("err_empty"), self.tr("err_no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("save_as"), "", "Binary (*.bin);;Intel HEX (*.hex)")
        if path:
            if path.endswith(".hex"):
                with open(path, "w") as f: f.write(IntelHex.generate(self.mem_data))
            else:
                mn, mx = min(self.mem_data.keys()), max(self.mem_data.keys())
                with open(path, "wb") as f:
                    for i in range(mn, mx + 1): f.write(bytes([self.mem_data.get(i, 0xFF)]))
            self.log(f"{self.tr('save_as')}: {path}")

    def load_and_flash(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("load_fw_title"), "", "Binary (*.bin);;Intel HEX (*.hex)")
        if not path: return
        
        loaded_mem = {}
        if path.endswith(".hex"):
            with open(path, "r") as f: loaded_mem = IntelHex.parse(f.read())
        else:
            text, ok = QInputDialog.getText(self, self.tr("base_addr"), self.tr("base_addr_hint"))
            if not ok: return
            try:
                base = int(text, 16)
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("err_hex"))
                return
            with open(path, "rb") as f:
                data = f.read()
                for i, b in enumerate(data): loaded_mem[base + i] = b
                
        self.mem_data.update(loaded_mem)
        self.hex_model.update_data(self.mem_data)
        self.update_range_label()
		
        # === Устанавливаем PC на начало загруженного образа ===
        if hasattr(self, 'emulator') and self.emulator:
            self.emulator.set_pc_to_memory_start()
            self.update_emu_disasm_view()  # ← ПОЛНОЕ обновление (дизассемблирует код)
            
        if self.auto_disasm_check.isChecked():
            self.auto_disasm()
        
        self.log(f"{self.tr('loaded')} {len(loaded_mem)} {self.tr('bytes_from_file')}")
        
        # Проверяем состояние перед записью
        if not self.is_connected:
            self.log(self.tr("dev_not_connected"))
            return
            
        if not self.bus_active:
            self.log(self.tr("bus_not_active_log"))
            QMessageBox.information(self, self.tr("info_title"), self.tr("hold_bus_first"))
            return
        
        if QMessageBox.question(self, self.tr("flash_q"), self.tr("flash_msg")) == QMessageBox.Yes:
            self.start_worker("write_block", (loaded_mem, min(loaded_mem.keys())))

    # ==================== ДИЗАССЕМБЛЕР ====================
    def auto_disasm(self):
        if not self.mem_data:
            return
        mn = min(self.mem_data.keys())
        mx = max(self.mem_data.keys())
        length = mx - mn + 1
        
        self.disasm_start.setText(f"{mn:04X}")
        self.disasm_len.setText(f"{length:X}")
        
        lines = self.disassembler.disassemble(self.mem_data, mn, length)
        self.disasm_view.set_lines(lines)

    def run_disasm(self):
        try:
            start = int(self.disasm_start.text(), 16)
            length = int(self.disasm_len.text(), 16)
        except ValueError: return
        
        lines = self.disassembler.disassemble(self.mem_data, start, length)
        self.disasm_view.set_lines(lines)

    def on_load_map(self):
        """Load a map file into the disassembler for symbol resolution."""
        from assemble8080.mapfile import load_map_file
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("asm_load_map_title"), "", self.tr("asm_map_filter"))
        if not path:
            return
        try:
            map_file = load_map_file(path)
            self.disassembler.set_map(map_file)
            self.log(self.tr("asm_map_loaded").format(path=path, n=len(map_file.entries)))
            # Re-run disassembly to show resolved symbols
            if self.mem_data:
                self.run_disasm()
        except Exception as e:
            QMessageBox.critical(self, self.tr("asm_err_title"),
                                 self.tr("asm_map_err").format(e=e))

    def on_hex_data_changed(self):
        """Вызывается при изменении данных в hex-редакторе"""
        # Добавляем операцию в undo stack
        if hasattr(self.hex_model, 'last_edit') and self.hex_model.last_edit:
            addr, old_val, new_val = self.hex_model.last_edit
            self.push_undo([(addr, old_val, new_val)])
            self.hex_model.last_edit = None
        
        if self.auto_disasm_check.isChecked() and self.mem_data:
            self.auto_disasm()

        # Синхронизируем ассемблер с памятью
        # (не перезаписывая редактируемый код)
        self._on_memory_changed()

    # ==================== БЛОКИ, ТЕСТЫ, IO ====================
    def show_read_block_dialog(self):
        text1, ok1 = QInputDialog.getText(self, self.tr("addr_hex"), self.tr("fill_start_addr"))
        if not ok1: return
        try:
            addr = int(text1, 16)
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_hex"))
            return
            
        size, ok2 = QInputDialog.getInt(
            self, self.tr("len"),
            self.tr("fill_size"), 
            self.max_block_size,  # ← Значение по умолчанию
            1, 
            self.max_block_size   # ← Максимальное значение
        )
        if not ok2: return
        self.start_worker("read_block", (addr, size))

    def start_mem_test(self):
        try:
            start = int(self.test_start.text(), 16)
            end = int(self.test_end.text(), 16)
            pat = self.test_pattern.currentData()
            self.start_worker("test_mem", (start, end, pat))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr"))

    def io_read_single(self):
        try:
            port = int(self.io_addr.text(), 16)
            self.send_command(bytes([CMD_IO_READ_BYTE, (port >> 8) & 0xFF, port & 0xFF]))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_port_addr"))

    def io_write_single(self):
        try:
            port = int(self.io_addr.text(), 16)
            data = int(self.io_data.text(), 16)
            self.send_command(bytes([CMD_IO_WRITE_BYTE, (port >> 8) & 0xFF, port & 0xFF, data]))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr_val"))

    def load_sequence_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("load_file"), "", "Text Files (*.txt);;All Files (*)")
        if path:
            with open(path, 'r') as f:
                self.seq_text.setPlainText(f.read())
            self.log(f"{self.tr('load_file')}: {path}")

    def run_io_sequence(self):
        text = self.seq_text.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, self.tr("err_empty"), self.tr("err_no_data"))
            return
        sequence = text.strip().split('\n')
        self.start_worker("run_io_sequence", {'sequence': sequence})

    def start_worker(self, task, params):
        if not self.serial_port or not self.serial_port.is_open:
            self.log(self.tr("err_not_open"))
            QMessageBox.warning(self, self.tr("error"), self.tr("err_not_open"))
            return
            
        bus_required = ["read_block", "write_block", "test_mem", 
                        "read_io_block", "write_io_block", "run_io_sequence"]
        if task in bus_required and not self.bus_active:
            self.log(self.tr("bus_not_active_msg"))
            QMessageBox.warning(self, self.tr("error"), self.tr("bus_not_active_msg"))
            return
            
        # Блокируем очередь на время работы worker
        self.worker_active = True
        self.poll_timer.stop()          # ← ДОБАВЛЕНО: не даём poll_timer читать порт
        self.serial_port.reset_input_buffer()  # ← ДОБАВЛЕНО: очищаем мусор из буфера
            
        self.worker_thread = QThread()
        self.worker = BusWorker(self.serial_port, task, params, 
                                self.current_lang, self.max_block_size)
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self.log)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.worker_thread.start()
		
    def on_worker_finished(self, result):
        # Разблокируем очередь
        self.worker_active = False
        self.poll_timer.start(50)       # ← ДОБАВЛЕНО: возобновляем опрос
        self.process_command_queue()
        
        if isinstance(result, dict) and result:
            if self.pending_read:
                addr = self.pending_read["addr"]
                bits = self.pending_read["bits"]
                endian = self.pending_read["endian"]
                is_io = self.pending_read["is_io"]
                
                byte_list = [result.get(addr + i, 0) for i in range(bits // 8)]
                value = self.bytes_to_value(byte_list, bits, endian)
                hex_digits = (bits // 8) * 2
                
                if is_io:
                    self.io_data_value.setText(f"{value:0{hex_digits}X}")
                else:
                    self.mem_data_value.setText(f"{value:0{hex_digits}X}")
                    self.mem_data.update(result)
                    self.hex_model.update_data(self.mem_data)
                    self.update_range_label()
                
                self.pending_read = None
                
                if self.auto_disasm_check.isChecked() and not is_io:
                    self.auto_disasm()
            else:
                self.mem_data.update(result)
                self.hex_model.update_data(self.mem_data)
                self.update_range_label()
                
                if self.auto_disasm_check.isChecked():
                    self.auto_disasm()
        
        self.log(self.tr("thread_done"))
		
    def on_status_update(self, addr, data, mnemonic):
        """Обновление статусной строки при наведении на ячейку"""
        self.status_label_addr.setText(f"{self.tr('status_addr')} {addr}")
        self.status_label_data.setText(f"{self.tr('status_data')} {data}")
        self.status_label_mnem.setText(f"{self.tr('status_mnem')} {mnemonic}")
	
    def export_disasm(self):
        """Экспорт дизассемблированного листинга в файл"""
        if not self.disasm_view.lines:
            QMessageBox.warning(self, self.tr("err_empty"), self.tr("err_no_data"))
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("export_disasm_title"),
            "", 
            "Assembly Files (*.asm);;Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write("; ============================================\n")
                f.write("; i8080 Disassembly\n")
                f.write("; Generated by i8080-5 CI\n")
                f.write(f"; Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("; ============================================\n\n")
                
                # Тело
                for addr, size, asm, undoc, target in self.disasm_view.lines:
                    # Получаем байты для этой строки
                    bytes_str = " ".join(f"{self.mem_data.get(addr+k, 0):02X}" for k in range(size))
                    
                    # Форматируем строку
                    undoc_mark = " ; undocumented" if undoc else ""
                    target_comment = f" ; -> {target:04X}h" if target is not None else ""
                    
                    f.write(f"{addr:04X}  {bytes_str:<12} {asm}{undoc_mark}{target_comment}\n")
                    
            self.log(f"{self.tr('export_disasm_log')}{path}")
            self.statusBar.showMessage(f"{self.tr('export_disasm_status')}{path}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), str(e))

    def show_search_dialog(self):
        """Показывает диалог поиска"""
        if not hasattr(self, 'search_dialog'):
            self.search_dialog = SearchDialog(self)
            self.search_dialog.searchRequested.connect(self.perform_search)
        self.search_dialog.show()
        
    def perform_search(self, pattern, mode):
        """Выполняет поиск в памяти"""
        results = []
        
        if mode == "HEX Bytes":
            # Парсим HEX-паттерн
            try:
                pattern_bytes = bytes.fromhex(pattern.replace(" ", ""))
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("search_invalid_hex"))
                return
                
            for addr in sorted(self.mem_data.keys()):
                match = True
                matched = []
                for i, b in enumerate(pattern_bytes):
                    if addr + i not in self.mem_data or self.mem_data[addr + i] != b:
                        match = False
                        break
                    matched.append(b)
                if match:
                    results.append((addr, matched))
                    
        elif mode == "ASCII String":
            # Ищем ASCII-строку
            pattern_bytes = pattern.encode('ascii')
            for addr in sorted(self.mem_data.keys()):
                match = True
                matched = []
                for i, b in enumerate(pattern_bytes):
                    if addr + i not in self.mem_data or self.mem_data[addr + i] != b:
                        match = False
                        break
                    matched.append(b)
                if match:
                    results.append((addr, matched))
                    
        elif mode == "HEX with Mask (??)":
            # Парсим паттерн с маской
            parts = pattern.replace(" ", "").upper()
            if len(parts) % 2 != 0:
                QMessageBox.warning(self, self.tr("error"), self.tr("search_invalid_len"))
                return
                
            pattern_list = []
            for i in range(0, len(parts), 2):
                byte_str = parts[i:i+2]
                if byte_str == "??":
                    pattern_list.append(None)
                else:
                    try:
                        pattern_list.append(int(byte_str, 16))
                    except ValueError:
                        QMessageBox.warning(self, self.tr("error"), f"{self.tr('search_invalid_byte')}{byte_str}")
                        return
                        
            for addr in sorted(self.mem_data.keys()):
                match = True
                matched = []
                for i, pb in enumerate(pattern_list):
                    if addr + i not in self.mem_data:
                        match = False
                        break
                    if pb is not None and self.mem_data[addr + i] != pb:
                        match = False
                        break
                    matched.append(self.mem_data[addr + i])
                if match:
                    results.append((addr, matched))
                    
        # Отображаем результаты
        if hasattr(self, 'search_dialog'):
            self.search_dialog.show_results(results)
            
        self.statusBar.showMessage(f"{self.tr('search_found')}{len(results)}{self.tr('search_matches')}", 3000)
        
    def goto_address(self, addr):
        """Переход к адресу в hex-редакторе"""
        model = self.hex_model
        if not model or not model.mem:
            return
            
        # Вычисляем row и col
        offset = addr - model.min_addr
        if offset < 0:
            return
        row = offset // 16
        col = (offset % 16) + 1  # +1 потому что колонка 0 - адрес
        
        index = model.index(row, col)
        if index.isValid():
            self.table.setCurrentIndex(index)
            self.table.scrollTo(index, QTableView.PositionAtCenter)
            self.tabs.setCurrentWidget(self.tab_hex)
            
    def disasm_from_address(self, addr):
        """Дизассемблировать от указанного адреса"""
        self.disasm_start.setText(f"{addr:04X}")
        self.tabs.setCurrentWidget(self.tab_disasm)
        self.run_disasm()
        
    def update_ui_state(self):
        """Обновляет доступность кнопок в зависимости от состояния"""
        connected = self.is_connected
        active = self.bus_active
        
        # Управление шиной
        self.btn_hold.setEnabled(connected and not active)
        self.btn_unhold.setEnabled(connected and active)
        
        # Чтение/запись данных (требуют захвата шины)
        self.btn_mem_read.setEnabled(connected and active)
        self.btn_mem_write.setEnabled(connected and active)
        self.btn_io_read.setEnabled(connected and active)
        self.btn_io_write.setEnabled(connected and active)
        
        # Hex-редактор
        self.btn_read_block.setEnabled(connected and active)
        
        # IO
        self.btn_io_read_single.setEnabled(connected and active)
        self.btn_io_write_single.setEnabled(connected and active)
        self.btn_seq_run.setEnabled(connected and active)
        
        # Тест памяти
        self.btn_test.setEnabled(connected and active)
        
        # Статусная строка
        if not connected:
            self.status_label_conn.setText(self.tr("disconnected"))
        elif active:
            self.status_label_conn.setText(f"{self.tr('connected')} | {self.tr('bus_active')}")
        else:
            self.status_label_conn.setText(f"{self.tr('connected')} | {self.tr('bus_free')}")
			
    def closeEvent(self, event):
        """Принудительное закрытие всех окон и виджетов"""
        # Закрываем диспетчер устройств и все окна устройств
        if hasattr(self, 'device_manager') and self.device_manager is not None:
            try:
                self.device_manager.close_all_windows()
                self.device_manager.close()
            except Exception:
                pass
            self.device_manager = None
        
        # Закрываем виджет 3D-куба (если создан скриптом)
        if hasattr(self, '_cube3d_widget') and self._cube3d_widget is not None:
            try:
                self._cube3d_widget.close()
            except Exception:
                pass
            self._cube3d_widget = None
        """Освобождение шины при закрытии программы"""
        # Очищаем очередь
        self.command_queue.clear()
        self.waiting_response = False
        
        if self.serial_port and self.serial_port.is_open and self.bus_active:
            self.log("Releasing bus before exit...")
            try:
                self.serial_port.write(SlipProtocol.encode(bytes([CMD_UNHOLD])))
                self.serial_port.flush()
                time.sleep(0.5)
            except serial.SerialException:
                pass
                
        if self.serial_port and self.serial_port.is_open:
            self.poll_timer.stop()
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
			
        # Останавливаем MCP Server
        if self.mcp_server is not None and self.mcp_server.running:
            self.mcp_server.stop()
            
        event.accept()
		
    def on_hold_clicked(self):
        if not self.is_connected: 
            self.statusBar.showMessage(self.tr("status_not_connected"), 2000)
            return
        if self.bus_active:
            self.statusBar.showMessage(self.tr("status_bus_active"), 2000)
            return
        self.send_command(bytes([CMD_HOLD]))
        self.btn_hold.setEnabled(False)
        
    def on_unhold_clicked(self):
        if not self.is_connected:
            self.statusBar.showMessage(self.tr("status_not_connected"), 2000)
            return
        if not self.bus_active:
            self.statusBar.showMessage(self.tr("status_bus_not_active"), 2000)
            return
        self.send_command(bytes([CMD_UNHOLD]))
        self.btn_unhold.setEnabled(False)
        
    def toggle_mcp_server(self):
        """Включить/выключить MCP Server"""
        if self.mcp_server.running:
            self.mcp_server.stop()
        else:
            self.mcp_server.start()
        
    def setup_shortcuts(self):		
        """Настройка горячих клавиш"""
        # Файл
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_and_flash)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_dump)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_disasm)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        
        # Поиск и навигация
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_search_dialog)
        QShortcut(QKeySequence("Ctrl+G"), self, self.show_goto_dialog)
        
        # Дизассемблер
        QShortcut(QKeySequence("Ctrl+D"), self, self.run_disasm)
        
        # Устройство
        QShortcut(QKeySequence("Ctrl+H"), self, self.on_hold_clicked)
        QShortcut(QKeySequence("Ctrl+U"), self, self.on_unhold_clicked)
        
        # Обновление
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_all)
		
        # Undo/Redo
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
		
        # Эмулятор (как в CodeWarrior)
        QShortcut(QKeySequence("F5"), self, self.emulator_run)
        QShortcut(QKeySequence("F10"), self, self.emulator_step_over)
        QShortcut(QKeySequence("F11"), self, self.emulator_step_into)
        QShortcut(QKeySequence("F8"), self, self.emulator_stop)
        QShortcut(QKeySequence("Ctrl+F2"), self, self.emulator_reset)
        QShortcut(QKeySequence("Ctrl+F10"), self, self.emulator_run_to_cursor)
		
    def show_goto_dialog(self):
        """Диалог перехода к адресу (Ctrl+G)"""
        text, ok = QInputDialog.getText(self, self.tr("goto_title"), self.tr("bp_addr"))
        if not ok: return
        try:
            addr = int(text, 16)
            self.goto_address(addr)
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_hex"))
            
    def refresh_all(self):
        """Обновление всех данных (F5)"""
        self.hex_model.layoutChanged.emit()
        if self.auto_disasm_check.isChecked():
            self.auto_disasm()
        self.update_range_label()
        self.statusBar.showMessage(self.tr("status_refreshed"), 2000)

    def push_undo(self, changes):
        """Добавляет операцию в стек undo"""
        if not changes: return
        self.undo_stack.append(changes)
        if len(self.undo_stack) > self.max_undo_depth:
            self.undo_stack.pop(0)
        self.redo_stack.clear()  # Очищаем redo при новом изменении
        self.statusBar.showMessage(f"{self.tr('status_undo_depth')}{len(self.undo_stack)}", 2000)
        
    def undo(self):
        """Отмена последнего изменения (Ctrl+Z)"""
        if not self.undo_stack:
            self.statusBar.showMessage(self.tr("status_nothing_undo"), 2000)
            return
        changes = self.undo_stack.pop()
        for addr, old_val, new_val in changes:
            self.mem_data[addr] = old_val
        self.redo_stack.append(changes)
        self.hex_model.update_data(self.mem_data)
        if self.auto_disasm_check.isChecked():
            self.auto_disasm()
        self.statusBar.showMessage(f"{self.tr('status_undo')}{len(changes)}{self.tr('status_undo_bytes')}", 2000)
        
    def redo(self):
        """Повтор последнего изменения (Ctrl+Y)"""
        if not self.redo_stack:
            self.statusBar.showMessage(self.tr("status_nothing_redo"), 2000)
            return
        changes = self.redo_stack.pop()
        for addr, old_val, new_val in changes:
            self.mem_data[addr] = new_val
        self.undo_stack.append(changes)
        self.hex_model.update_data(self.mem_data)
        if self.auto_disasm_check.isChecked():
            self.auto_disasm()
        self.statusBar.showMessage(f"{self.tr('status_redo')}{len(changes)}{self.tr('status_redo_bytes')}", 2000)
		
    def create_tab_compare(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Кнопки управления
        ctrl_layout = QHBoxLayout()
        self.btn_load_compare = QPushButton()
        self.btn_load_compare.clicked.connect(self.load_compare_file)
        self.btn_compare = QPushButton()
        self.btn_compare.clicked.connect(self.run_compare)
        self.btn_export_compare = QPushButton()
        self.btn_export_compare.clicked.connect(self.export_compare_report)
        ctrl_layout.addWidget(self.btn_load_compare)
        ctrl_layout.addWidget(self.btn_compare)
        ctrl_layout.addWidget(self.btn_export_compare)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Информация о сравнении
        self.lbl_compare_info = QLabel()
        layout.addWidget(self.lbl_compare_info)
        
        # Таблица результатов
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(4)
        self.compare_table.setFont(QFont("Consolas", 10))
        layout.addWidget(self.compare_table)
        
        self.compare_data = None
        self.compare_results = []
        
        self.tabs.addTab(tab, "")
        self.tab_compare = tab
	
    def load_compare_file(self):
        """Загружает файл для сравнения"""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("load_compare_title"), "", 
            "Intel HEX (*.hex);;Binary (*.bin);;All Files (*)"
        )
        if not path: return
        
        loaded_mem = {}
        if path.endswith(".hex"):
            with open(path, "r") as f:
                loaded_mem = IntelHex.parse(f.read())
        else:
            text, ok = QInputDialog.getText(self, self.tr("base_addr"), self.tr("base_addr_hint"))
            if not ok: return
            try:
                base = int(text, 16)
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("err_hex"))
                return
            with open(path, "rb") as f:
                data = f.read()
                for i, b in enumerate(data):
                    loaded_mem[base + i] = b
                    
        self.compare_data = loaded_mem
        self.lbl_compare_info.setText(f"{self.tr('compare_loaded')}: {path} ({len(loaded_mem)} {self.tr('bytes')})")
        self.log(f"Compare file loaded: {path} ({len(loaded_mem)} bytes)")
        
    def run_compare(self):
        """Выполняет сравнение текущего дампа с загруженным файлом"""
        if not self.compare_data:
            QMessageBox.warning(self, self.tr("error"), self.tr("load_compare"))
            return
            
        if not self.mem_data:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_no_data"))
            return
        
        # Сравниваем
        all_addrs = set(self.mem_data.keys()) | set(self.compare_data.keys())
        self.compare_results = []
        
        for addr in sorted(all_addrs):
            val_current = self.mem_data.get(addr)
            val_file = self.compare_data.get(addr)
            
            if val_current is None:
                status_key = "status_added"  # ← Ключ для перевода
            elif val_file is None:
                status_key = "status_removed"  # ← Ключ для перевода
            elif val_current != val_file:
                status_key = "status_changed"  # ← Ключ для перевода
            else:
                continue  # Одинаковые — пропускаем
                
            self.compare_results.append((addr, val_current, val_file, status_key))
            
        # Отображаем результаты
        self.show_compare_results()
        
    def show_compare_results(self):
        """Отображает результаты сравнения в таблице"""
        self.compare_table.setRowCount(len(self.compare_results))
        
        for row, (addr, val_cur, val_file, status_key) in enumerate(self.compare_results):
            # Адрес
            item_addr = QTableWidgetItem(f"{addr:04X}")
            self.compare_table.setItem(row, 0, item_addr)
            
            # Текущее значение
            cur_str = f"{val_cur:02X}" if val_cur is not None else "--"
            item_cur = QTableWidgetItem(cur_str)
            self.compare_table.setItem(row, 1, item_cur)
            
            # Значение из файла
            file_str = f"{val_file:02X}" if val_file is not None else "--"
            item_file = QTableWidgetItem(file_str)
            self.compare_table.setItem(row, 2, item_file)
            
            # Статус (переведённый)
            status_text = self.tr(status_key)  # ← Переводим статус
            item_status = QTableWidgetItem(status_text)
            self.compare_table.setItem(row, 3, item_status)
            
            # Подсветка в зависимости от статуса
            if status_key == "status_changed":
                color = QColor("#fff3cd")  # Жёлтый
            elif status_key == "status_added":
                color = QColor("#d4edda")  # Зелёный
            elif status_key == "status_removed":
                color = QColor("#f8d7da")  # Красный
            else:
                color = None
                
            if color:
                for col in range(4):
                    item = self.compare_table.item(row, col)
                    if item:
                        item.setBackground(color)
                        
        self.statusBar.showMessage(
            f"{self.tr('compare_complete')}: {len(self.compare_results)} {self.tr('compare_found')}", 
            3000
        )
        self.log(f"Compare complete: {len(self.compare_results)} differences")
        
    def export_compare_report(self):
        """Экспортирует отчёт о сравнении"""
        if not self.compare_results:
            QMessageBox.warning(self, self.tr("error"), self.tr("run_compare_first"))
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("export_compare_title"), "", 
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        if not path: return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"{self.tr('compare_addr')},{self.tr('compare_current')},"
                        f"{self.tr('compare_file')},{self.tr('compare_status')}\n")
                for addr, val_cur, val_file, status_key in self.compare_results:
                    cur_str = f"{val_cur:02X}" if val_cur is not None else "--"
                    file_str = f"{val_file:02X}" if val_file is not None else "--"
                    status_text = self.tr(status_key)
                    f.write(f"{addr:04X},{cur_str},{file_str},{status_text}\n")
            self.log(f"{self.tr('compare_exported')}: {path}")
            self.statusBar.showMessage(f"{self.tr('compare_exported')}: {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), str(e))

    def create_tab_scripts(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_run_script = QPushButton("▶ Run Script")
        self.btn_run_script.clicked.connect(self.run_script)
        self.btn_load_script = QPushButton("Load Script")
        self.btn_load_script.clicked.connect(self.load_script_file)
        self.btn_save_script = QPushButton("Save Script")
        self.btn_save_script.clicked.connect(self.save_script_file)
        self.btn_clear_output = QPushButton("Clear Output")
        self.btn_clear_output.clicked.connect(lambda: self.script_output.clear())
        btn_layout.addWidget(self.btn_run_script)
        btn_layout.addWidget(self.btn_load_script)
        btn_layout.addWidget(self.btn_save_script)
        btn_layout.addWidget(self.btn_clear_output)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Редактор кода
        self.script_editor = QTextEdit()
        self.script_editor.setFont(QFont("Consolas", 10))
        self.script_editor.setPlaceholderText(
            "# Example script:\n"
            "# Fill memory with pattern\n"
            "api.fill_mem(0x0000, 256, 0x55)\n"
            "# Disassemble\n"
            "for line in api.disassemble(0x0000, 16):\n"
            "    print(line)\n"
            "# Search\n"
            "results = api.search('C3', 'hex')\n"
            "print(f'Found {len(results)} JMP instructions')"
        )
        layout.addWidget(self.script_editor)
        
        # Разделитель
        self.lbl_script_output = QLabel(self.tr("script_output_label"))
        layout.addWidget(self.lbl_script_output)
        
        # Вывод
        self.script_output = QTextEdit()
        self.script_output.setReadOnly(True)
        self.script_output.setMaximumHeight(200)
        self.script_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.script_output)
        
        self.tabs.addTab(tab, "")
        self.tab_scripts = tab

    def run_script(self):
        """Выполняет скрипт из редактора"""
        code = self.script_editor.toPlainText()
        if not code.strip():
            self.script_output.append(self.tr("script_no_code"))
            return
            
        self.script_output.clear()
        self.script_output.append(self.tr("script_running"))
        
        # Создаём API
        api = AutomationAPI(self)
        
        # Пространство имён для скрипта
        namespace = {
            'api': api,
            # Локальная память
            'read_mem': api.read_mem,
            'write_mem': api.write_mem,
            'read_block': api.read_block,
            'write_block': api.write_block,
            'fill_mem': api.fill_mem,
            # Память устройства
            'dev_read_mem': api.dev_read_mem,
            'dev_write_mem': api.dev_write_mem,
            'dev_read_io': api.dev_read_io,
            'dev_write_io': api.dev_write_io,
            # Синхронизация
            'download': api.download,
            'upload': api.upload,
            'download_all': api.download_all,
            'upload_all': api.upload_all,
            # Шина
            'hold_bus': api.hold_bus,
            'unhold_bus': api.unhold_bus,
            'wait_bus': api.wait_bus,
            'wait_unhold': api.wait_unhold,
            # Файлы
            'load_file': api.load_file,
            'save_file': api.save_file,
            # Утилиты
            'disassemble': api.disassemble,
            'refresh': api.refresh,
            'search': api.search,
            'log': api.log,
            'status': api.status,
            'goto': api.goto,
            'dev_write_eeprom_byte': api.dev_write_eeprom_byte,
            'dev_write_eeprom_block': api.dev_write_eeprom_block,
            # Ассемблер
            'asm_get_source': api.asm_get_source,
            'asm_set_source': api.asm_set_source,
            'asm_load_file': api.asm_load_file,
            'asm_assemble': api.asm_assemble,
            'asm_get_binary': api.asm_get_binary,
            'asm_get_symbols': api.asm_get_symbols,
        }
        
        try:
            # Перенаправляем stdout
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            # Выполняем код
            exec(code, namespace)
            
            # Получаем вывод
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            if output:
                self.script_output.append(output.rstrip())
            self.script_output.append(f"\n{self.tr('script_done')}")
            self.statusBar.showMessage(self.tr("script_completed"), 3000)
            
        except Exception as e:
            sys.stdout = old_stdout
            self.script_output.append(f"\n{self.tr('script_err')}{str(e)}")
            self.script_output.append(traceback.format_exc())
            self.statusBar.showMessage(self.tr("script_error"), 3000)
            
    def load_script_file(self):
        """Загружает скрипт из файла"""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("script_load_title"), "",
            "Python Scripts (*.py);;Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.script_editor.setPlainText(f.read())
                self.statusBar.showMessage(f"{self.tr('script_loaded')}{path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, self.tr("error"), str(e))
                
    def save_script_file(self):
        """Сохраняет скрипт в файл"""
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("script_save_title"), "", 
            "Python Scripts (*.py);;Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.script_editor.toPlainText())
                self.statusBar.showMessage(f"{self.tr('script_saved')}{path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, self.tr("error"), str(e))

    def sync_send_and_recv(self, payload, timeout=2.0):
        """Синхронная отправка команды и ожидание ответа"""
        if not self.serial_port or not self.serial_port.is_open:
            return None
            
        # Останавливаем poll_timer, чтобы избежать конфликта
        self.poll_timer.stop()
        
        try:
            self.serial_port.write(SlipProtocol.encode(payload))
            self.serial_port.flush()
            
            buffer = bytearray()
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()  # Обрабатываем события UI
                try:
                    if self.serial_port.in_waiting:
                        buffer.extend(self.serial_port.read(self.serial_port.in_waiting))
                        if _FEND in buffer:
                            end_idx = buffer.index(_FEND)
                            if end_idx > 0:
                                raw = buffer[:end_idx]
                                self.serial_port.reset_input_buffer()
                                return SlipProtocol.decode(raw)
                except serial.SerialException:
                    return None
                time.sleep(0.01)
            return None
        finally:
            # Запускаем poll_timer снова
            self.poll_timer.start(50)
			
    def on_mcp_toggle(self):
        if not MCP_AVAILABLE or self.mcp_server is None:
            QMessageBox.warning(self, self.tr("mcp_err_title"), self.tr("mcp_err_msg"))
            return
            
        if self.mcp_server.running:
            self.mcp_server.stop()
            self.btn_mcp.setText(self.tr("mcp_off"))
        else:
            self.mcp_server.start()
            self.btn_mcp.setText(self.tr("mcp_on"))
			
    def create_tab_emulator(self):
        """Создаёт вкладку эмулятора — трёхколоночный отладчик"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # =============================================
        # ЧЕТЫРЁХКОЛОНОЧНЫЙ SPLITTER
        # =============================================
        self.emu_splitter = QSplitter(Qt.Horizontal)
        
        # === КОЛОНКА 1: Дизассемблер ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_emu_code = QLabel("Код:")
        self.lbl_emu_code.setFont(QFont("Segoe UI", 9, QFont.Bold))
        left_layout.addWidget(self.lbl_emu_code)

        
        self.emu_disasm_view = DisasmView(self.mem_data)
        self.emu_disasm_view.lang = self.current_lang
        self.emu_disasm_view.set_lines([])
        self.emu_disasm_view.set_highlight(None)
        if hasattr(self.emu_disasm_view, 'set_breakpoints'):
            self.emu_disasm_view.set_breakpoints(set())
        
        # === ИТЕРАЦИЯ B: Интерактивный режим ===
        self.emu_disasm_view.set_interactive(True)
        self.emu_disasm_view.toggleBreakpoint.connect(self.on_toggle_breakpoint)  # ← ОДНО подключение
        self.emu_disasm_view.cursorChanged.connect(self.on_emu_cursor_changed)
        self.emu_disasm_view.runToCursorRequested.connect(self.emulator_run_to_cursor)
        self.emu_disasm_view.runFromHereRequested.connect(self.emulator_run_from_here)
        self.emu_disasm_view.jumpToCursorRequested.connect(self.emulator_jump_to_cursor)
        
        self.emu_disasm_scroll = QScrollArea()
        self.emu_disasm_scroll.setWidget(self.emu_disasm_view)
        self.emu_disasm_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.emu_disasm_scroll)
        
        self.emu_splitter.addWidget(left_panel)
        
        # === КОЛОНКА 2: BP ===
        self.emu_disasm_view.setConditionalBreakpointRequested.connect(self.on_set_conditional_bp)
        
        # === КОЛОНКА 3: WATCH ===
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.watch_group = QGroupBox("Watch")
        watch_layout = QVBoxLayout()
        
        # Кнопки управления Watch
        watch_btn_layout1 = QHBoxLayout()
        self.btn_watch_add = QPushButton("+")
        self.btn_watch_add.setToolTip("Добавить элемент наблюдения")
        self.btn_watch_add.clicked.connect(self.watch_add_dialog)
        self.btn_watch_del = QPushButton("❌")
        self.btn_watch_del.setToolTip("Удалить выбранный элемент")
        self.btn_watch_del.clicked.connect(self.watch_delete)
        self.btn_watch_clear = QPushButton("🗑")
        self.btn_watch_clear.setToolTip("Очистить все")
        self.btn_watch_clear.clicked.connect(self.watch_clear)
        watch_btn_layout1.addWidget(self.btn_watch_add)
        watch_btn_layout1.addWidget(self.btn_watch_del)
        watch_btn_layout1.addWidget(self.btn_watch_clear)
        watch_layout.addLayout(watch_btn_layout1)
        
        # Кнопки пресетов
        watch_btn_layout2 = QHBoxLayout()
        self.btn_watch_save_preset = QPushButton("💾")
        self.btn_watch_save_preset.setToolTip("Сохранить пресет")
        self.btn_watch_save_preset.clicked.connect(self.watch_save_preset)
        self.btn_watch_load_preset = QPushButton("📂")
        self.btn_watch_load_preset.setToolTip("Загрузить пресет")
        self.btn_watch_load_preset.clicked.connect(self.watch_load_preset)
        watch_btn_layout2.addWidget(self.btn_watch_save_preset)
        watch_btn_layout2.addWidget(self.btn_watch_load_preset)
        watch_layout.addLayout(watch_btn_layout2)
        
        # Таблица Watch
        self.watch_model = WatchModel(self.emulator)
        self.watch_table = QTableView()
        self.watch_table.setModel(self.watch_model)
        self.watch_table.setSelectionBehavior(QTableView.SelectRows)
        self.watch_table.setSelectionMode(QTableView.SingleSelection)
        self.watch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        watch_layout.addWidget(self.watch_table)
        
        self.watch_group.setLayout(watch_layout)
        middle_layout.addWidget(self.watch_group)
        
        self.emu_splitter.addWidget(middle_panel)
        
        # Кнопки управления BP
        # === КОЛОНКА 3: BREAKPOINTS (ИТЕРАЦИЯ C) ===
        bp_panel = QWidget()
        bp_layout = QVBoxLayout(bp_panel)
        bp_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bp_group = QGroupBox("Breakpoints")
        bp_group_layout = QVBoxLayout()
        
        # Кнопки управления BP
        bp_btn_layout = QHBoxLayout()
        self.btn_bp_add = QPushButton("+")
        self.btn_bp_add.setToolTip("Добавить точку останова")
        self.btn_bp_add.clicked.connect(self.bp_add_dialog)
        self.btn_bp_cond = QPushButton("🔧")
        self.btn_bp_cond.setToolTip("Редактировать условие")
        self.btn_bp_cond.clicked.connect(self.bp_edit_condition)
        self.btn_bp_toggle = QPushButton("🚫")
        self.btn_bp_toggle.setToolTip("Включить/выключить")
        self.btn_bp_toggle.clicked.connect(self.bp_toggle_enabled)
        self.btn_bp_del = QPushButton("❌")
        self.btn_bp_del.setToolTip("Удалить выбранную")
        self.btn_bp_del.clicked.connect(self.bp_delete)
        self.btn_bp_clear = QPushButton("🗑")
        self.btn_bp_clear.setToolTip("Очистить все")
        self.btn_bp_clear.clicked.connect(self.clear_breakpoints)
        bp_btn_layout.addWidget(self.btn_bp_add)
        bp_btn_layout.addWidget(self.btn_bp_cond)
        bp_btn_layout.addWidget(self.btn_bp_toggle)
        bp_btn_layout.addWidget(self.btn_bp_del)
        bp_btn_layout.addWidget(self.btn_bp_clear)
        bp_group_layout.addLayout(bp_btn_layout)
        
        # Кнопки пресетов BP
        bp_preset_layout = QHBoxLayout()
        self.btn_bp_save_preset = QPushButton("💾")
        self.btn_bp_save_preset.setToolTip("Сохранить пресет BP")
        self.btn_bp_save_preset.clicked.connect(self.bp_save_preset)
        self.btn_bp_load_preset = QPushButton("📂")
        self.btn_bp_load_preset.setToolTip("Загрузить пресет BP")
        self.btn_bp_load_preset.clicked.connect(self.bp_load_preset)
        bp_preset_layout.addWidget(self.btn_bp_save_preset)
        bp_preset_layout.addWidget(self.btn_bp_load_preset)
        bp_group_layout.addLayout(bp_preset_layout)
     
        # Таблица BP
        self.bp_model = BreakpointModel(self.emulator)
        self.bp_table = QTableView()
        self.bp_table.setModel(self.bp_model)
        self.bp_table.setSelectionBehavior(QTableView.SelectRows)
        self.bp_table.setSelectionMode(QTableView.SingleSelection)
        self.bp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bp_table.doubleClicked.connect(self.bp_edit_condition)
        bp_group_layout.addWidget(self.bp_table)
        
        self.bp_group.setLayout(bp_group_layout)
        bp_layout.addWidget(self.bp_group)
        
        self.emu_splitter.addWidget(bp_panel)
        
        # === КОЛОНКА 4: Регистры + Флаги + Стек + Статистика ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Регистры
        self.reg_group = QGroupBox("Регистры")
        reg_layout = QGridLayout()
        reg_layout.setSpacing(2)
        
        self.reg_labels = {}
        regs = ['A', 'B', 'C', 'D', 'E', 'H', 'L', 'SP', 'PC']
        for i, reg in enumerate(regs):
            lbl_name = QLabel(f"{reg}:")
            lbl_name.setFont(QFont("Consolas", 10))
            reg_layout.addWidget(lbl_name, i, 0)
            
            lbl_val = QLabel("0000" if reg in ['SP', 'PC'] else "00")
            lbl_val.setFont(QFont("Consolas", 9))
            lbl_val.setMinimumWidth(50)
            lbl_val.setAlignment(Qt.AlignCenter)
            lbl_val.setStyleSheet("background-color: #f0f0f0; padding: 2px; border: 1px solid #ccc;")
            reg_layout.addWidget(lbl_val, i, 1)
            self.reg_labels[reg] = lbl_val
            
        pairs = ['BC', 'DE', 'HL']
        for i, pair in enumerate(pairs):
            lbl_name = QLabel(f"{pair}:")
            lbl_name.setFont(QFont("Consolas", 10))
            reg_layout.addWidget(lbl_name, i + len(regs), 0)
            
            lbl_val = QLabel("0000")
            lbl_val.setFont(QFont("Consolas", 9))
            lbl_val.setMinimumWidth(50)
            lbl_val.setAlignment(Qt.AlignCenter)
            lbl_val.setStyleSheet("background-color: #f0f0f0; padding: 2px; border: 1px solid #ccc;")
            reg_layout.addWidget(lbl_val, i + len(regs), 1)
            self.reg_labels[pair] = lbl_val
            
        self.reg_group.setLayout(reg_layout)
        right_layout.addWidget(self.reg_group)
        
        self.prev_reg_values = {}
        
        # === Выбор типа процессора (эмулятор) ===
        cpu_sel_layout = QHBoxLayout()
        cpu_sel_layout.addWidget(QLabel("Процессор:"))
        self.emu_cpu_combo = QComboBox()
        self.emu_cpu_combo.addItems(["i8080", "i8085"])
        self.emu_cpu_combo.setCurrentText("i8080")
        self.emu_cpu_combo.currentTextChanged.connect(self._on_emu_cpu_changed)
        cpu_sel_layout.addWidget(self.emu_cpu_combo)
        cpu_sel_layout.addStretch()
        right_layout.addLayout(cpu_sel_layout)

        # Флаги
        self.flags_group = QGroupBox("Флаги")
        flags_layout = QHBoxLayout()
        flags_layout.setSpacing(5)
        
        self.flag_labels = {}
        flags = ['S', 'Z', 'AC', 'P', 'CY']
        for flag in flags:
            lbl = QLabel(f"{flag}: 0")
            lbl.setFont(QFont("Consolas", 8))
            flags_layout.addWidget(lbl)
            self.flag_labels[flag] = lbl
            
        # 8085: IFF1, IFF2, I-регистр (скрыты по умолчанию)
        self.iff1_label = QLabel("IFF1: 0")
        self.iff1_label.setFont(QFont("Consolas", 8))
        self.iff1_label.setVisible(False)
        flags_layout.addWidget(self.iff1_label)

        self.iff2_label = QLabel("IFF2: 0")
        self.iff2_label.setFont(QFont("Consolas", 8))
        self.iff2_label.setVisible(False)
        flags_layout.addWidget(self.iff2_label)

        self.i_reg_label = QLabel("I: 00")
        self.i_reg_label.setFont(QFont("Consolas", 8))
        self.i_reg_label.setVisible(False)
        flags_layout.addWidget(self.i_reg_label)

        self.flags_group.setLayout(flags_layout)
        right_layout.addWidget(self.flags_group)

        
        # Стек
        self.stack_group = QGroupBox("Стек")
        stack_layout = QVBoxLayout()
        
        self.stack_list = QListWidget()
        self.stack_list.setFont(QFont("Consolas", 9))
        self.stack_list.setMaximumHeight(120)
        stack_layout.addWidget(self.stack_list)
        
        self.stack_group.setLayout(stack_layout)
        right_layout.addWidget(self.stack_group)
        
        # Статистика
        self.stats_group = QGroupBox("Статистика")
        stats_layout = QVBoxLayout()
        
        self.cycles_label = QLabel(self.tr("emu_cycles") + "0")
        self.state_label = QLabel(self.tr("emu_state") + self.tr("emu_state_halted"))
        stats_layout.addWidget(self.cycles_label)
        stats_layout.addWidget(self.state_label)
        
        self.stats_group.setLayout(stats_layout)
        right_layout.addWidget(self.stats_group)
        
        right_layout.addStretch()
        
        self.emu_splitter.addWidget(right_panel)
        
        # === КОЛОНКИ ОКНА ЭМУЛЯЦИИ ===
        self.emu_splitter.setSizes([300, 200, 200, 200])
        
        main_layout.addWidget(self.emu_splitter)
        
        # =============================================
        # НИЖНЯЯ ПАНЕЛЬ УПРАВЛЕНИЯ
        # =============================================
        ctrl_panel = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(0, 5, 0, 0)
        
        self.btn_reset = QPushButton("⚡ Reset (Ctrl+F2)")
        self.btn_reset.clicked.connect(self.emulator_reset)
        ctrl_layout.addWidget(self.btn_reset)
        
        self.btn_set_pc = QPushButton("📌 Set PC...")
        self.btn_set_pc.clicked.connect(self.set_pc_dialog)
        ctrl_layout.addWidget(self.btn_set_pc)
        
        ctrl_layout.addSpacing(10)
        
        self.btn_step_into = QPushButton("↴ Step Into (F11)")
        self.btn_step_into.clicked.connect(self.emulator_step_into)
        ctrl_layout.addWidget(self.btn_step_into)
        
        self.btn_step_over = QPushButton("➟ Step Over (F10)")
        self.btn_step_over.clicked.connect(self.emulator_step_over)
        ctrl_layout.addWidget(self.btn_step_over)
        
        ctrl_layout.addSpacing(10)
        
        self.btn_run = QPushButton("🚀 Run (F5)")
        self.btn_run.clicked.connect(self.emulator_run)
        ctrl_layout.addWidget(self.btn_run)
        
        self.btn_stop = QPushButton("⛔ Stop (F8)")
        self.btn_stop.clicked.connect(self.emulator_stop)
        ctrl_layout.addWidget(self.btn_stop)
        
        ctrl_layout.addSpacing(20)
        
        # === ИТЕРАЦИЯ D: Чек-бокс трассировки ===
        self.chk_trace_enable = QCheckBox("Трассировка")
        self.chk_trace_enable.setToolTip("Включить запись трассировки выполнения")
        self.chk_trace_enable.setChecked(False)
        self.chk_trace_enable.toggled.connect(self.on_trace_checkbox_toggled)
        ctrl_layout.addWidget(self.chk_trace_enable)
        
        ctrl_layout.addStretch()
        
        main_layout.addWidget(ctrl_panel)
        
        # =============================================
        # ДОБАВЛЯЕМ ВКЛАДКУ
        # =============================================
        self.tabs.addTab(tab, "")
        self.tab_emulator = tab
		
    def emulator_reset(self):
        """Сброс эмулятора"""
        self.emulator.reset()
        self.update_emulator_ui()
        # Обновляем подсветку в дизассемблере
        self.disasm_view.set_highlight(self.emulator.pc)
        
    def emulator_step_into(self):
        """Step Into: одна инструкция (обходит BP на текущем PC)"""
        if self.emulator.halted:
            self.statusBar.showMessage(f"{self.tr('status_cpu_halted_short')}", 3000)
            return
        self._save_watch_prev_values()
        self._save_reg_prev_values()
        self.emulator.step_into()  # ← step_into() обходит BP
        self.update_emulator_ui()
        self.update_disasm_highlight()
        self.refresh_trace_table()  # ← ИТЕРАЦИЯ D
        
    def emulator_step_over(self):
        """Step Over: выполнить CALL как одну инструкцию"""
        if self.emulator.halted:
            self.statusBar.showMessage(f"{self.tr('status_cpu_halted_short')}", 3000) 
            return
        self._save_watch_prev_values()
        self._save_reg_prev_values()  # ← Сохраняем регистры ДО выполнения
        self.emulator.step_over()
        self.update_emulator_ui()
        self.update_disasm_highlight()
        self.refresh_trace_table()  # ← ИТЕРАЦИЯ D

    def _run_tick(self):
        """Один тик выполнения — оптимизирован для скорости"""
        # === Такты для tick-устройств (512ВИ1, 8253, AM9511, CF IDE, CH376S) ===
        if hasattr(self, 'system') and self.emulator.running:
            self.system.tick(cycles=1)
        
        # === ПРОВЕРКА DMA (итерация 10.2) ===
        if hasattr(self, 'system') and self.system.check_dma():
            # CPU приостановлен (эмуляция HOLD/HLDA)
            self.update_emulator_ui()
            return

        # === ПРОВЕРКА WAIT-СИГНАЛА (итерация 10.3) ===
        if getattr(self.emulator, 'wait_signal', False):
            # CPU ждёт устройство (эмуляция READY/WAIT)
            self.update_emulator_ui()
            return
        
        # === ПРОВЕРКА ПРЕРЫВАНИЙ (итерация 10.1) ===
        if hasattr(self, 'system'):
            self.system.check_interrupts()

        # === Проверки остановки ===
        target_reached = (
            self.run_target_addr is not None and
            self.emulator.pc == self.run_target_addr
        )
        if not self.emulator.running or self.emulator.halted or target_reached:
            self.run_timer.stop()
            self.emulator.running = False
            if target_reached:
                self.statusBar.showMessage(f"{self.tr('status_reached_cursor')}{self.run_target_addr:04X}", 3000)
                self.log(f"{self.tr('status_reached_cursor')}{self.run_target_addr:04X}")
            else:
                self.statusBar.showMessage(self.tr("status_emu_stopped"), 3000)
            self.run_target_addr = None
            self.update_emulator_ui()
            self.update_emu_disasm_view()
            self.refresh_trace_table()
            return

        # === Breakpoint имеет приоритет ===
        if self.emulator.should_stop_at_bp(self.emulator.pc):
            self.run_timer.stop()
            self.emulator.running = False
            self.run_target_addr = None
            self.emulator.register_bp_hit(self.emulator.pc)
            self.update_emulator_ui()
            self.update_emu_disasm_view()
            self.sync_breakpoints()
            self.statusBar.showMessage(f"{self.tr('status_bp_hit')}{self.emulator.pc:04X}", 3000)
            self.refresh_trace_table()
            self.log(f"Breakpoint hit: 0x{self.emulator.pc:04X}")
            return

        # === Сохраняем Watch и регистры один раз за тик ===
        self._save_watch_prev_values()
        self._save_reg_prev_values()

        # === ВЫПОЛНЯЕМ ПАКЕТ ИНСТРУКЦИЙ ===
        INSTRUCTIONS_PER_TICK = 300
        executed = 0
        for _ in range(INSTRUCTIONS_PER_TICK):
            # Проверка цели Run to Cursor
            if self.run_target_addr is not None and self.emulator.pc == self.run_target_addr:
                break
            # Проверка BP с учётом условий и enabled
            if self.emulator.should_stop_at_bp(self.emulator.pc):
                break
            # Проверка DMA и WAIT перед каждой инструкцией
            if getattr(self.emulator, 'wait_signal', False):
                break
            if hasattr(self, 'system') and self.system.check_dma():
                break

            # === Обработка прерывания перед инструкцией ===
            if self.emulator.has_pending_interrupt():
                self.emulator._handle_interrupt()

            # Выполняем БЕЗ emit сигнала
            if not self.emulator.execute_instruction(silent=True):
                break
            executed += 1

        # === ОДНО обновление UI за весь тик ===
        self.update_emulator_ui()
        self.refresh_trace_table()
        self.update_emu_disasm_cursor()

    def on_emu_cursor_changed(self, addr):
        """Курсор изменён (одинарный клик в дизассемблере эмулятора)"""
        self.statusBar.showMessage(f"{self.tr('status_cursor')}{addr:04X}{self.tr('status_cursor_hint')}", 3000)
        
    def emulator_run_to_cursor(self, addr=None):
        """Run to Cursor (Ctrl+F10): выполнить до курсора"""
        if self.emulator.halted:
            self.statusBar.showMessage(self.tr("status_cpu_halted"), 3000)
            return
        if addr is None:
            if hasattr(self.emu_disasm_view, 'cursor_addr') and self.emu_disasm_view.cursor_addr is not None:
                addr = self.emu_disasm_view.cursor_addr
            else:
                self.statusBar.showMessage(self.tr("status_cursor_not_set"), 3000)
                return
        if addr == self.emulator.pc:
            self.statusBar.showMessage(self.tr("status_cursor_eq_pc"), 3000)
            return
        
        # === Если PC на breakpoint, обходим его ===
        if self.emulator.pc in self.emulator.breakpoints:
            self._save_watch_prev_values()
            self._save_reg_prev_values()
            self.emulator.step_into()
        
        self.run_target_addr = addr
        self.emulator.running = True
        if not hasattr(self, 'run_timer'):
            self.run_timer = QTimer()
            self.run_timer.timeout.connect(self._run_tick)
        self.run_timer.start(20)
        self.statusBar.showMessage(f"{self.tr('status_running_to')}{addr:04X}...", 0)
        self.log(f"{self.tr('status_running_from')}{addr:04X}")
        
    def emulator_run_from_here(self, addr):
        """Run from Here: установить PC на курсор и запустить"""
        if self.emulator.halted:
            self.statusBar.showMessage(self.tr("status_cpu_halted"), 3000)
            return
        
        # Устанавливаем PC на адрес курсора
        self.emulator.set_pc(addr)
        self.update_emulator_ui()
        self.update_disasm_highlight()
        
        # Запускаем обычный Run (без цели)
        self.run_target_addr = None
        self.emulator.running = True
        
        if not hasattr(self, 'run_timer'):
            self.run_timer = QTimer()
            self.run_timer.timeout.connect(self._run_tick)
        
        self.run_timer.start(20)
        self.statusBar.showMessage(f"{self.tr('status_running_from')}{addr:04X}...", 0)
        self.log(f"{self.tr('status_running_from')}{addr:04X}")
        
    def emulator_jump_to_cursor(self, addr):
        """Jump to Cursor: переместить PC без выполнения"""
        self.emulator.set_pc(addr)
        self.update_emulator_ui()
        self.update_disasm_highlight()
        self.statusBar.showMessage(f"{self.tr('ctx_jump')}{addr:04X}", 3000)
        self.log(f"{self.tr('ctx_jump')}{addr:04X}")
        
    def emulator_stop(self):
        """Остановка выполнения"""
        self.emulator.stop()
        if hasattr(self, 'run_timer'):
            self.run_timer.stop()
        self.update_emulator_ui()
        self.update_disasm_highlight()
        self.disasm_view.set_breakpoints(self.emulator.breakpoints)
        
    def update_disasm_highlight(self):
        """Обновляет подсветку PC во встроенном дизассемблере эмулятора"""
        if not self.mem_data:
            return
        # Используем частичное обновление (быстро)
        self.update_emu_disasm_cursor()
		    
    def on_toggle_breakpoint(self, addr):
        """Установка/удаление точки останова"""
        if addr in self.emulator.breakpoints:
            self.emulator.remove_breakpoint(addr)
            self.log(f"Breakpoint removed: 0x{addr:04X}")
        else:
            self.emulator.add_breakpoint(addr)
            self.log(f"Breakpoint set: 0x{addr:04X}")
        self.disasm_view.update()
        self.sync_breakpoints()  # ← Синхронизация
        
    def sync_breakpoints(self):
        """Синхронизирует breakpoints между всеми UI-компонентами"""
        # === Обновляем модель BP (таблица в панели Breakpoints) ===
        if hasattr(self, 'bp_model'):
            self.bp_model.refresh()
        
        # === Обновляем встроенный дизассемблер эмулятора ===
        if hasattr(self, 'emu_disasm_view'):
            if hasattr(self.emu_disasm_view, 'set_breakpoints'):
                self.emu_disasm_view.set_breakpoints(self.emulator.breakpoints)
            if hasattr(self.emu_disasm_view, 'set_bp_conditions'):
                self.emu_disasm_view.set_bp_conditions(self.emulator.bp_conditions)
            self.emu_disasm_view.update()
            
    def _save_reg_prev_values(self):
        """Сохранить текущие значения регистров ДО выполнения (для подсветки)"""
        state = self.emulator.get_state()
        self.prev_reg_values = {}
        for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
            self.prev_reg_values[reg] = state[reg]
        for reg in ['SP', 'PC', 'BC', 'DE', 'HL']:
            self.prev_reg_values[reg] = state[reg]
            
    def emulator_retranslate(self):
        """Локализация элементов вкладки эмулятора"""
        # Заголовки групп
        self.reg_group.setTitle(self.tr("emulator_registers"))
        self.flags_group.setTitle(self.tr("emulator_flags"))
        self.stack_group.setTitle(self.tr("emulator_stack"))
        self.stats_group.setTitle(self.tr("emulator_stats"))
        # Кнопки управления
        self.btn_reset.setText(self.tr("emulator_reset"))
        self.btn_set_pc.setText(self.tr("emulator_set_pc"))
        self.btn_step_into.setText(self.tr("emulator_step_into"))
        self.btn_step_over.setText(self.tr("emulator_step_over"))
        self.btn_run.setText(self.tr("emulator_run"))
        self.btn_stop.setText(self.tr("emulator_stop"))
        
        # Чек-бокс трассировки
        if hasattr(self, 'chk_trace_enable'):
            self.chk_trace_enable.setText(self.tr("emulator_trace"))
            
        # ← ДОБАВЛЕНО: метка "Код"
        if hasattr(self, 'lbl_emu_code'):
            self.lbl_emu_code.setText(self.tr("emu_code"))
        # ← ДОБАВЛЕНО: группы Watch и Breakpoints
        if hasattr(self, 'watch_group'):
            self.watch_group.setTitle(self.tr("emu_watch"))
        if hasattr(self, 'bp_group'):
            self.bp_group.setTitle(self.tr("emu_bp"))
		
    def safe_call(self, func: callable, *args, **kwargs):
        """Thread-safe function dispatch.
        
        If called from the GUI (main) thread, executes immediately.
        If called from a worker thread, dispatches via Qt event loop.
        """
        from PySide6.QtCore import QThread, QTimer
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None and app.thread() == QThread.currentThread():
            # Already on the GUI thread - execute directly
            func(*args, **kwargs)
        else:
            # Worker thread - dispatch to GUI thread
            QTimer.singleShot(0, lambda: func(*args, **kwargs))
    # =============================================
    # WATCH: Диалоги и управление
    # =============================================
    
    def watch_add_dialog(self):
        """Диалог добавления элемента в Watch с автоименем и автоформатом"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("watch_add_title"))
            dialog.setMinimumWidth(450)
            layout = QFormLayout(dialog)
            
            # === Имя ===
            name_edit = QLineEdit()
            layout.addRow(self.tr("watch_name"), name_edit)
            
            # === Тип наблюдения ===
            type_combo = QComboBox()
            type_combo.addItems([self.tr("watch_type_byte"), self.tr("watch_type_word"), self.tr("watch_type_reg")])
            layout.addRow(self.tr("watch_type"), type_combo)
            
            # === Контейнер для динамического поля ===
            target_stack = QStackedWidget()
            
            # Страница 0: QLineEdit для hex-адреса (память)
            addr_edit = QLineEdit()
            addr_edit.setPlaceholderText(self.tr("watch_addr_hint"))
            addr_edit.setMaxLength(4)
            target_stack.addWidget(addr_edit)
            
            # Страница 1: QComboBox для регистров
            reg_combo = QComboBox()
            reg_combo.addItems([
                "A", "B", "C", "D", "E", "H", "L",
                "BC", "DE", "HL", "SP", "PC", "FLAGS"
            ])
            reg_combo.setEditable(False)
            target_stack.addWidget(reg_combo)
            
            layout.addRow(self.tr("watch_target"), target_stack)
            
            # === Формат ===
            format_combo = QComboBox()
            format_combo.addItems(WatchModel.FORMATS)
            layout.addRow(self.tr("watch_format"), format_combo)
            
            # =============================================
            # АВТОИМЯ: генерация имени по умолчанию
            # =============================================
            
            def generate_auto_name():
                """Генерирует автоимя в зависимости от типа и цели"""
                type_idx = type_combo.currentIndex()
                if type_idx == 0:  # Память (байт)
                    addr_text = addr_edit.text().strip()
                    try:
                        addr = int(addr_text, 16) if addr_text else 0
                        return f"mem_{addr:04X}"
                    except ValueError:
                        return "mem_XXXX"
                elif type_idx == 1:  # Память (слово)
                    addr_text = addr_edit.text().strip()
                    try:
                        addr = int(addr_text, 16) if addr_text else 0
                        return f"word_{addr:04X}"
                    except ValueError:
                        return "word_XXXX"
                else:  # Регистр
                    reg = reg_combo.currentText()
                    return f"reg_{reg.lower()}"
            
            def update_name_placeholder():
                """Обновляет placeholder имени с примером автоимени"""
                name_edit.setPlaceholderText(f"{self.tr('watch_auto_prefix')} {generate_auto_name()}")
            
            # =============================================
            # АВТОФОРМАТ: выбор формата по умолчанию
            # =============================================
            
            def get_auto_format():
                """Возвращает автоформат в зависимости от типа и цели"""
                type_idx = type_combo.currentIndex()
                if type_idx == 2:  # Регистр
                    reg = reg_combo.currentText()
                    if reg == "FLAGS":
                        return "bin"  # Флаги удобно смотреть в двоичном виде
                    return "hex"      # Регистры — в hex
                else:  # Память
                    return "hex"      # Память — в hex
            
            def apply_auto_format():
                """Применяет автоформат к format_combo"""
                format_combo.setCurrentText(get_auto_format())
            
            # =============================================
            # ОБРАБОТЧИКИ СОБЫТИЙ
            # =============================================
            
            def on_reg_changed(reg_name):
                """При смене регистра: обновить формат и placeholder имени"""
                apply_auto_format()
                update_name_placeholder()
            
            def on_addr_changed(text):
                """При изменении адреса: обновить placeholder имени"""
                update_name_placeholder()
            
            def on_type_changed(index):
                """При смене типа: переключить поле, применить автоформат"""
                if index == 2:  # Регистр
                    target_stack.setCurrentIndex(1)
                else:  # Память
                    target_stack.setCurrentIndex(0)
                apply_auto_format()
                update_name_placeholder()
            
            # Подключение сигналов
            type_combo.currentIndexChanged.connect(on_type_changed)
            reg_combo.currentTextChanged.connect(on_reg_changed)
            addr_edit.textChanged.connect(on_addr_changed)
            
            # Инициализация начального состояния
            update_name_placeholder()
            
            # === Кнопки ===
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton(self.tr("dlg_ok"))
            btn_cancel = QPushButton(self.tr("dlg_cancel"))
            btn_ok.clicked.connect(dialog.accept)
            btn_cancel.clicked.connect(dialog.reject)
            btn_layout.addWidget(btn_ok)
            btn_layout.addWidget(btn_cancel)
            layout.addRow(btn_layout)
            
            # =============================================
            # ОБРАБОТКА РЕЗУЛЬТАТА
            # =============================================
            if dialog.exec() == QDialog.Accepted:
                # Автоимя: если поле пустое — используем сгенерированное
                name = name_edit.text().strip() or generate_auto_name()
                fmt = format_combo.currentText()
                type_idx = type_combo.currentIndex()
                
                if type_idx == 0:  # Память (байт)
                    addr_text = addr_edit.text().strip()
                    if not addr_text:
                        QMessageBox.warning(self, self.tr("error"), self.tr("watch_err_addr"))
                        return
                    addr = int(addr_text, 16)
                    self.watch_model.add_watch(name, WatchModel.TYPE_MEM_BYTE, addr, fmt)
                    self.log(f"Watch added: {name} = mem[0x{addr:04X}] byte ({fmt})")
                    
                elif type_idx == 1:  # Память (слово)
                    addr_text = addr_edit.text().strip()
                    if not addr_text:
                        QMessageBox.warning(self, self.tr("error"), self.tr("watch_err_addr"))
                        return
                    addr = int(addr_text, 16)
                    self.watch_model.add_watch(name, WatchModel.TYPE_MEM_WORD, addr, fmt)
                    self.log(f"Watch added: {name} = mem[0x{addr:04X}] word ({fmt})")
                    
                else:  # Регистр
                    reg = reg_combo.currentText()
                    self.watch_model.add_watch(name, WatchModel.TYPE_REG, reg, fmt)
                    self.log(f"Watch added: {name} = {reg} ({fmt})")
                    
        except ValueError as e:
            QMessageBox.warning(
                self.tr("watch_err_fmt_title"),
                f"Неверный формат адреса!\n\n"
                f"Введите HEX-значение без префикса 0x.\n"
                f"Примеры: 0100, 0FF0, FFFF\n\n"
                f"Детали: {e}"
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('watch_err_add')}{e}")
            self.log(f"Watch add error: {e}")
            
    def watch_delete(self):
        """Удалить выбранный элемент Watch"""
        selected = self.watch_table.selectedIndexes()
        if selected:
            row = selected[0].row()
            self.watch_model.remove_watch(row)
        else:
            self.statusBar.showMessage(self.tr("watch_select_del"), 2000)
            
    def watch_clear(self):
        """Очистить все элементы Watch"""
        if self.watch_model.items:
            reply = QMessageBox.question(
                self, self.tr("watch_confirm"),
                self.tr("watch_confirm_del"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.watch_model.clear()
                
    def watch_save_preset(self):
        """Сохранить пресет Watch в файл"""
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("watch_save_preset"),
            "watch_preset.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            if self.watch_model.save_preset(path):
                self.statusBar.showMessage(f"{self.tr('watch_preset_saved')}{path}", 3000)
                self.log(f"Watch preset saved: {path}")
            else:
                QMessageBox.warning(self, self.tr("error"), self.tr("watch_preset_save_err"))
                
    def watch_load_preset(self):
        """Загрузить пресет Watch из файла"""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("watch_load_preset"),
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            if self.watch_model.load_preset(path):
                self.statusBar.showMessage(f"{self.tr('watch_preset_loaded')}{path}", 3000)
                self.log(f"Watch preset loaded: {path}")
                self.watch_model.refresh()
            else:
                QMessageBox.warning(self, self.tr("error"), self.tr("watch_preset_load_err"))
				
    # =============================================
    # BREAKPOINTS: Диалоги и управление (ИТЕРАЦИЯ C)
    # =============================================
    
    def bp_add_dialog(self):
        """Добавить BP через диалог"""
        text, ok = QInputDialog.getText(self, self.tr("bp_add_title"), self.tr("bp_addr"))
        if ok:
            try:
                addr = int(text, 16)
                self.emulator.add_breakpoint(addr)
                self.sync_breakpoints()
                self.log(f"Breakpoint set: 0x{addr:04X}")
            except ValueError:
                QMessageBox.warning(self, self.tr("error"), self.tr("bp_err_addr"))
    
    def bp_edit_condition(self):
        """Редактировать условие выбранной BP"""
        selected = self.bp_table.selectedIndexes()
        if not selected:
            self.statusBar.showMessage(self.tr("bp_select"), 2000)
            return
        row = selected[0].row()
        bps = self.bp_model.get_bp_list()
        if row >= len(bps):
            return
        addr = bps[row]
        existing = self.emulator.get_bp_condition(addr)
        self.bp_condition_dialog(addr, existing)
    
    def bp_toggle_enabled(self):
        """Включить/выключить выбранную BP"""
        selected = self.bp_table.selectedIndexes()
        if not selected:
            self.statusBar.showMessage(self.tr("bp_select"), 2000)
            return
        row = selected[0].row()
        bps = self.bp_model.get_bp_list()
        if row >= len(bps):
            return
        addr = bps[row]
        self.emulator.toggle_bp_enabled(addr)
        self.sync_breakpoints()
    
    def bp_delete(self):
        """Удалить выбранную BP"""
        selected = self.bp_table.selectedIndexes()
        if not selected:
            self.statusBar.showMessage(self.tr("bp_select"), 2000)
            return
        row = selected[0].row()
        bps = self.bp_model.get_bp_list()
        if row >= len(bps):
            return
        addr = bps[row]
        self.emulator.remove_breakpoint(addr)
        self.sync_breakpoints()
        self.log(f"Breakpoint removed: 0x{addr:04X}")
    
    def bp_condition_dialog(self, addr, existing_condition=""):
        """Диалог ввода условия для BP"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.tr('bp_cond_title')} 0x{addr:04X}")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        
        hint = QLabel(self.tr("bp_cond_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(hint)
        
        cond_edit = QLineEdit(existing_condition)
        cond_edit.setPlaceholderText(self.tr("bp_cond_example"))
        layout.addWidget(cond_edit)
        
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton(self.tr("bp_cond_clear"))
        btn_clear.clicked.connect(lambda: cond_edit.setText(""))
        btn_ok = QPushButton(self.tr("dlg_ok"))
        btn_cancel = QPushButton(self.tr("dlg_cancel"))
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            condition = cond_edit.text().strip()
            if condition and not self._validate_bp_condition(condition):
                QMessageBox.warning(self, self.tr("error"), self.tr("bp_cond_err"))
                return
            self.emulator.set_bp_condition(addr, condition)
            self.sync_breakpoints()
            self.log(f"BP 0x{addr:04X} condition: {condition or '(none)'}")
    
    # =============================================
    # BREAKPOINTS: Пресеты (сохранение/загрузка)
    # =============================================
    
    def bp_save_preset(self):
        """Сохранить пресет BP в JSON файл"""
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("bp_save_preset"),
            "bp_preset.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        
        try:
            data = {
                "version": 1,
                "breakpoints": []
            }
            
            for addr in sorted(self.emulator.breakpoints):
                bp_entry = {
                    "addr": addr,
                    "condition": self.emulator.get_bp_condition(addr),
                    "enabled": self.emulator.bp_enabled.get(addr, True),
                    "hit_count": self.emulator.bp_hit_count.get(addr, 0)
                }
                data["breakpoints"].append(bp_entry)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.statusBar.showMessage(f"{self.tr('bp_preset_saved')}{path}", 3000)
            self.log(f"BP preset saved: {path} ({len(data['breakpoints'])} breakpoints)")
        except Exception as e:
            QMessageBox.warning(self, self.tr("error"), f"{self.tr('bp_preset_save_err')}{e}")
    
    def bp_load_preset(self):
        """Загрузить пресет BP из JSON файла"""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("bp_load_preset"),
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Очищаем текущие BP
            self.emulator.clear_all_breakpoints()
           
            # Загружаем новые BP
            loaded_count = 0
            for bp_entry in data.get("breakpoints", []):
                addr = bp_entry.get("addr")
                if addr is None:
                    continue
                
                self.emulator.add_breakpoint(addr)
                
                condition = bp_entry.get("condition", "")
                if condition:
                    self.emulator.set_bp_condition(addr, condition)
                
                enabled = bp_entry.get("enabled", True)
                self.emulator.bp_enabled[addr] = enabled
                
                hit_count = bp_entry.get("hit_count", 0)
                if hit_count > 0:
                    self.emulator.bp_hit_count[addr] = hit_count
                
                loaded_count += 1
            
            self.sync_breakpoints()
            self.statusBar.showMessage(f"{self.tr('bp_preset_loaded')}{path}", 3000)
            self.log(f"BP preset loaded: {path} ({loaded_count} breakpoints)")
        except Exception as e:
            QMessageBox.warning(self, self.tr("error"), f"{self.tr('bp_preset_load_err')}{e}")
        
    def _validate_bp_condition(self, condition):
        """Проверяет синтаксис условия"""
        try:
            compile(condition, '<bp_condition>', 'eval')
            return True
        except SyntaxError:
            return False
    
    def on_set_conditional_bp(self, addr):
        """Обработчик запроса на условный BP из контекстного меню"""
        if addr not in self.emulator.breakpoints:
            self.emulator.add_breakpoint(addr)
        existing = self.emulator.get_bp_condition(addr)
        self.bp_condition_dialog(addr, existing)
        
    def _save_watch_prev_values(self):
        """Сохранить текущие значения Watch перед выполнением"""
        if hasattr(self, 'watch_model'):
            self.watch_model.save_prev_values()
            
    def create_tab_trace(self):
        """Создаёт вкладку трассировки (ИТЕРАЦИЯ D)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === Панель управления трассировкой ===
        ctrl_layout = QHBoxLayout()
        
        self.btn_trace_toggle = QPushButton("🔥 Включить запись")
        self.btn_trace_toggle.setCheckable(True)
        self.btn_trace_toggle.clicked.connect(self.on_trace_toggle)
        ctrl_layout.addWidget(self.btn_trace_toggle)
        
        self.btn_trace_clear = QPushButton("🗑 Очистить")
        self.btn_trace_clear.clicked.connect(self.on_trace_clear)
        ctrl_layout.addWidget(self.btn_trace_clear)
        
        self.btn_trace_export = QPushButton("💾 Экспорт")
        self.btn_trace_export.clicked.connect(self.on_trace_export)
        ctrl_layout.addWidget(self.btn_trace_export)
        
        ctrl_layout.addSpacing(20)
        
        # Глубина буфера
        self.lbl_trace_depth = QLabel("Глубина:")
        ctrl_layout.addWidget(self.lbl_trace_depth)
        self.spin_trace_depth = QSpinBox()
        self.spin_trace_depth.setMinimum(100)
        self.spin_trace_depth.setMaximum(100000)
        self.spin_trace_depth.setValue(10000)
        self.spin_trace_depth.setSingleStep(1000)
        self.spin_trace_depth.valueChanged.connect(self.on_trace_depth_changed)
        ctrl_layout.addWidget(self.spin_trace_depth)
        
        ctrl_layout.addSpacing(20)
        
        # Статус трассировки
        self.lbl_trace_status = QLabel(self.tr("trace_records") + "0 / 10000")
        self.lbl_trace_status.setStyleSheet("color: #666;")
        ctrl_layout.addWidget(self.lbl_trace_status)
        
        ctrl_layout.addStretch()
        
        # Поиск
        self.lbl_trace_search = QLabel("Поиск:")
        ctrl_layout.addWidget(self.lbl_trace_search)
        self.txt_trace_search = QLineEdit()
        self.txt_trace_search.setPlaceholderText(self.tr("trace_search_hint"))
        self.txt_trace_search.setMaximumWidth(250)
        self.txt_trace_search.returnPressed.connect(self.on_trace_search)
        ctrl_layout.addWidget(self.txt_trace_search)
        
        self.btn_trace_search = QPushButton("🔍")
        self.btn_trace_search.clicked.connect(self.on_trace_search)
        ctrl_layout.addWidget(self.btn_trace_search)
        
        self.btn_trace_filter_clear = QPushButton("❌")
        self.btn_trace_filter_clear.setToolTip("Сбросить фильтр")
        self.btn_trace_filter_clear.clicked.connect(self.on_trace_filter_clear)
        ctrl_layout.addWidget(self.btn_trace_filter_clear)
        
        layout.addLayout(ctrl_layout)
        
        # === Таблица трассировки ===
        self.trace_model = TraceModel(self.emulator)
        self.trace_model.disassembler = self.disassembler
        self.trace_table = QTableView()
        self.trace_table.setModel(self.trace_model)
        self.trace_table.setSelectionBehavior(QTableView.SelectRows)
        self.trace_table.setSelectionMode(QTableView.SingleSelection)
        self.trace_table.setAlternatingRowColors(True)
        self.trace_table.setFont(QFont("Consolas", 9))
        self.trace_table.verticalHeader().setVisible(False)
        # Ширина колонок
        self.trace_table.setColumnWidth(0, 60)   # #
        self.trace_table.setColumnWidth(1, 60)   # PC
        self.trace_table.setColumnWidth(2, 90)   # Байты
        self.trace_table.setColumnWidth(3, 180)  # Мнемо
        self.trace_table.setColumnWidth(4, 40)   # A
        self.trace_table.setColumnWidth(5, 60)   # BC
        self.trace_table.setColumnWidth(6, 60)   # DE
        self.trace_table.setColumnWidth(7, 60)   # HL
        self.trace_table.setColumnWidth(8, 60)   # SP
        self.trace_table.setColumnWidth(9, 90)   # Флаги
        # Выбор строки → детали
        self.trace_table.selectionModel().selectionChanged.connect(self.on_trace_selection_changed)
        layout.addWidget(self.trace_table)
        
        # === Панель детального просмотра выбранной записи ===
        self.trace_detail_group = QGroupBox("Детали выбранной записи")
        detail_layout = QHBoxLayout()
        self.lbl_trace_detail = QLabel("Выберите запись для просмотра")
        self.lbl_trace_detail.setFont(QFont("Consolas", 9))
        self.lbl_trace_detail.setWordWrap(True)
        detail_layout.addWidget(self.lbl_trace_detail)
        self.trace_detail_group.setLayout(detail_layout)
        layout.addWidget(self.trace_detail_group)
        
        # === Контекстное меню записи ===
        self.trace_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.trace_table.customContextMenuRequested.connect(self.on_trace_context_menu)
        
        self.tabs.addTab(tab, "")
        self.tab_trace = tab

        # === Инициализация фильтра ===
        self.trace_filter = None
        self.trace_filtered_records = []
        
    # =============================================
    # ИТЕРАЦИЯ D: Трассировка — обработчики
    # =============================================
    
    def on_trace_toggle(self):
        """Включить/выключить запись трассировки"""
        if self.btn_trace_toggle.isChecked():
            self.emulator.trace_start()
            self.btn_trace_toggle.setText(self.tr("trace_off"))
            self.btn_trace_toggle.setStyleSheet("background-color: #ffcccc;")
            self.chk_trace_enable.setChecked(True)
        else:
            self.emulator.trace_stop()
            self.btn_trace_toggle.setText(self.tr("trace_on"))
            self.btn_trace_toggle.setStyleSheet("")
            self.chk_trace_enable.setChecked(False)
        self.update_trace_status()
    
    def on_trace_clear(self):
        """Очистить буфер трассировки"""
        self.emulator.trace_clear()
        if hasattr(self, 'trace_model'):
            self.trace_model.set_filter(None)  # Сбрасываем фильтр при очистке
        self.refresh_trace_table()
        self.log(self.tr("trace_buf_cleared"))
    
    def on_trace_depth_changed(self, value):
        """Изменение глубины буфера"""
        self.emulator.trace_set_depth(value)
        self.update_trace_status()
    
    def update_trace_status(self):
        """Обновить статус трассировки"""
        count = self.emulator.trace_count()
        max_rec = self.emulator.trace_max_records
        self.lbl_trace_status.setText(f"{self.tr('trace_records')}{count} / {max_rec}")
    
    def refresh_trace_table(self):
        """Обновить таблицу трассировки (быстро, через виртуальную модель)"""
        if hasattr(self, 'trace_model'):
            self.trace_model.refresh()
        self.update_trace_status()
        # Автопрокрутка к последней записи
        if hasattr(self, 'trace_table') and self.emulator.trace_count() > 0:
            self.trace_table.scrollToBottom()
    
    def on_trace_selection_changed(self, selected, deselected):
        """Выбор записи — показать детали"""
        indexes = selected.indexes()
        if not indexes:
            return
        row = indexes[0].row()
        if hasattr(self, 'trace_model'):
            rec = self.trace_model._get_record(row)
            if rec is not None:
                self._show_trace_detail(rec)
    
    def _get_trace_mnemonic(self, rec):
        """Определить мнемонику для записи трассировки"""
        if not self.emulator.disassembler:
            return f"DB {rec['opcode']:02X}h"
        
        # Создаём временный mem_dict из сохранённых байтов
        temp_mem = {rec["pc"] + i: b for i, b in enumerate(rec["bytes"])}
        lines = self.disassembler.disassemble(temp_mem, rec["pc"], len(rec["bytes"]))
        if lines:
            return lines[0][2]  # asm
        return f"DB {rec['opcode']:02X}h"
        
    def _show_trace_detail(self, rec):
        """Показать детальную информацию о записи"""
        flags = rec["flags"]
        flags_str = f"S={flags[0]} Z={flags[1]} AC={flags[2]} P={flags[3]} CY={flags[4]}"
        mnemonic = self._get_trace_mnemonic(rec)
        bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
        
        detail = (
            f"#{rec['seq']}  PC={rec['pc']:04X}  {bytes_str}  {mnemonic}\n"
            f"{self.tr('trace_regs_after')}A={rec['A']:02X}  BC={rec['BC']:04X}  DE={rec['DE']:04X}  "
            f"HL={rec['HL']:04X}  SP={rec['SP']:04X}\n"
            f"{self.tr('trace_flags')}{flags_str}\n"
            f"{self.tr('trace_cycles')}{rec['cycles']}{self.tr('trace_cycles_total')}{rec['cycles_total']})"
        )
        self.lbl_trace_detail.setText(detail)
    
    def on_trace_context_menu(self, pos):
        """Контекстное меню записи трассировки"""
        index = self.trace_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        if hasattr(self, 'trace_model'):
            rec = self.trace_model._get_record(row)
            if rec is None:
                return
            menu = QMenu(self)
            act_view = menu.addAction(f"{self.tr('trace_ctx_view')}(#{rec['seq']})")
            act_restore = menu.addAction(self.tr('trace_ctx_restore'))
            act_goto = menu.addAction(f"{self.tr('trace_ctx_goto')}{rec['pc']:04X}{self.tr('trace_ctx_goto_suffix')}")
            selected = menu.exec(self.trace_table.viewport().mapToGlobal(pos))
            if selected == act_view:
                self._show_trace_detail(rec)
            elif selected == act_restore:
                self._restore_trace_state(rec)
            elif selected == act_goto:
                self._goto_trace_address(rec["pc"])
    
    def _restore_trace_state(self, rec):
        """Восстановить состояние эмулятора из записи трассировки"""
        emu = self.emulator
        emu.a = rec["A"]
        emu.b = rec["B"]
        emu.c = rec["C"]
        emu.d = rec["D"]
        emu.e = rec["E"]
        emu.h = rec["H"]
        emu.l = rec["L"]
        emu.sp = rec["SP"]
        # PC устанавливаем на адрес ПОСЛЕ этой инструкции (для продолжения)
        # Но для просмотра — на адрес самой инструкции
        emu.pc = rec["pc"]
        
        flags = rec["flags"]
        emu.flag_s = bool(flags[0])
        emu.flag_z = bool(flags[1])
        emu.flag_ac = bool(flags[2])
        emu.flag_p = bool(flags[3])
        emu.flag_cy = bool(flags[4])
        # 8085: восстановить IFF1/IFF2/I (если есть в записи)
        if "IFF1" in rec:
            emu.iff1 = bool(rec["IFF1"])
        if "IFF2" in rec:
            emu.iff2 = bool(rec["IFF2"])
        if "I" in rec:
            emu.i_reg = rec["I"]
        self.update_emulator_ui()
        self.update_emu_disasm_view()
        self.log(f"{self.tr('status_state_restored')}{rec['pc']:04X}")
        self.statusBar.showMessage(f"{self.tr('status_state_restored')}{rec['pc']:04X}", 3000)
    
    def _goto_trace_address(self, addr):
        """Перейти к адресу в дизассемблере эмулятора"""
        self.emulator.set_pc(addr)
        self.update_emulator_ui()
        self.update_emu_disasm_view()
        self.tabs.setCurrentWidget(self.tab_emulator)
        self.statusBar.showMessage(f"{self.tr('status_pc_set')}{addr:04X}", 3000)
    
    def on_trace_search(self):
        """Поиск в трассировке по адресу, регистру или мнемонике"""
        query = self.txt_trace_search.text().strip()
        filter_dict = self._parse_trace_filter(query)
        if filter_dict is None and query:
            self.statusBar.showMessage(f"{self.tr('status_trace_search_err')}{query}", 3000)
            return
        if hasattr(self, 'trace_model'):
            self.trace_model.set_filter(filter_dict)
        filtered_count = self.trace_model.rowCount() if hasattr(self, 'trace_model') else 0
        total = self.emulator.trace_count()
        self.statusBar.showMessage(f"{self.tr('status_trace_found')}{filtered_count}{self.tr('status_trace_of')}{total}", 3000)
        if query:
            self.log(f"{self.tr('trace_search_log')}{query}{self.tr('trace_search_found')}{filtered_count}")
    
    def on_trace_filter_clear(self):
        """Сбросить фильтр трассировки"""
        self.txt_trace_search.clear()
        if hasattr(self, 'trace_model'):
            self.trace_model.set_filter(None)
        self.refresh_trace_table()
    
    def _parse_trace_filter(self, query):
        """Парсит запрос поиска. Возвращает фильтр или None."""
        query = query.strip()
        if not query:
            return None
         
        # === Операторы сравнения (проверяем в порядке убывания длины) ===
        operators = ['!=', '==', '>=', '<=', '>', '<', '=']
        for op in operators:
            if op in query:
                parts = query.split(op, 1)
                reg = parts[0].strip().upper()
                val_str = parts[1].strip()
                valid_regs = ['A', 'B', 'C', 'D', 'E', 'H', 'L', 'BC', 'DE', 'HL', 'SP', 'PC',
                              'S', 'Z', 'AC', 'P', 'CY']
                if reg not in valid_regs:
                    return None
                try:
                    value = int(val_str, 16) if val_str.lower().startswith('0x') or all(c in '0123456789abcdefABCDEF' for c in val_str) else int(val_str)
                except ValueError:
                    return None
                # Нормализуем оператор: '=' → '=='
                op_normalized = '==' if op == '=' else op
                return {"type": "reg", "reg": reg, "op": op_normalized, "value": value}
         
        # Hex-адрес: 0010, 0x0010
        try:
            addr = int(query, 16)
            if 0 <= addr <= 0xFFFF:
                return {"type": "addr", "value": addr}
        except ValueError:
            pass
         
        # Мнемоника
        return {"type": "mnemonic", "value": query.upper()}
    
    def _apply_trace_filter(self, records):
        """Применяет фильтр к записям трассировки"""
        if not self.trace_filter:
            return records
        filtered = []
        f = self.trace_filter
        if f["type"] == "addr":
            for rec in records:
                if rec["pc"] == f["value"]:
                    filtered.append(rec)
        elif f["type"] == "reg":
            reg = f["reg"]
            op = f.get("op", "==")  # По умолчанию равенство
            value = f["value"]
            flag_map = {'S': 0, 'Z': 1, 'AC': 2, 'P': 3, 'CY': 4}
            
            def get_reg_value(rec):
                if reg == 'A': return rec["A"]
                elif reg == 'B': return rec["B"]
                elif reg == 'C': return rec["C"]
                elif reg == 'D': return rec["D"]
                elif reg == 'E': return rec["E"]
                elif reg == 'H': return rec["H"]
                elif reg == 'L': return rec["L"]
                elif reg == 'BC': return rec["BC"]
                elif reg == 'DE': return rec["DE"]
                elif reg == 'HL': return rec["HL"]
                elif reg == 'SP': return rec["SP"]
                elif reg == 'PC': return rec["pc"]
                elif reg in flag_map:
                    return rec["flags"][flag_map[reg]]
                return 0
            
            for rec in records:
                val = get_reg_value(rec)
                if op == '==' and val == value: filtered.append(rec)
                elif op == '!=' and val != value: filtered.append(rec)
                elif op == '>' and val > value: filtered.append(rec)
                elif op == '<' and val < value: filtered.append(rec)
                elif op == '>=' and val >= value: filtered.append(rec)
                elif op == '<=' and val <= value: filtered.append(rec)
        elif f["type"] == "mnemonic":
            for rec in records:
                mnemonic = self._get_trace_mnemonic(rec)
                if f["value"] in mnemonic.upper():
                    filtered.append(rec)
        return filtered
    
    def on_trace_export(self):
        """Экспорт трассировки в TXT / CSV / JSON"""
        records = self.emulator.trace_get()
        if not records:
            QMessageBox.warning(self, self.tr("trace_export_title"), self.tr("trace_no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("trace_export_title"),
            "trace.txt",
            "Text Files (*.txt);;CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            if path.endswith('.csv'):
                self._export_trace_csv(path, records)
            elif path.endswith('.json'):
                self._export_trace_json(path, records)
            else:
                self._export_trace_txt(path, records)
            self.statusBar.showMessage(f"{self.tr('trace_exported')}{path}", 3000)
            self.log(f"Trace exported to {path} ({len(records)} records)")
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('trace_export_err')}{e}")
    
    def _export_trace_txt(self, path, records):
        """Экспорт в TXT"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("# i8080 Trace Export\n")
            f.write(f"# Records: {len(records)}\n")
            f.write(f"{'#':>6}  {'PC':>4}  {'Bytes':<12}  {'Mnemonic':<20}  {'A':>2}  {'BC':>4}  {'DE':>4}  {'HL':>4}  {'SP':>4}  {'Flags':<5}  {'IFF1':>4}  {'IFF2':>4}  {'I':>2}  {'Cyc':>5}\n")
            f.write("-" * 110 + "\n")
            for rec in records:
                mnemonic = self._get_trace_mnemonic(rec)
                bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
                flags = rec["flags"]
                flags_str = f"{'S' if flags[0] else '-'}{'Z' if flags[1] else '-'}{'A' if flags[2] else '-'}{'P' if flags[3] else '-'}{'C' if flags[4] else '-'}"
                f.write(f"{rec['seq']:>6}  {rec['pc']:04X}  {bytes_str:<12}  {mnemonic:<20}  "
                        f"{rec['A']:>2}  {rec['BC']:04X}  {rec['DE']:04X}  {rec['HL']:04X}  "
                        f"{rec['SP']:04X}  {flags_str:<5}  {int(rec.get('IFF1', False)):>4}  {int(rec.get('IFF2', False)):>4}  {rec.get('I', 0):02X}  {rec['cycles']:>5}\n")

    def _export_trace_csv(self, path, records):
        """Экспорт в CSV"""
        import csv
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['seq', 'pc', 'bytes', 'mnemonic', 'A', 'BC', 'DE', 'HL', 'SP', 'flags', 'IFF1', 'IFF2', 'I', 'cycles', 'cycles_total'])
            for rec in records:
                mnemonic = self._get_trace_mnemonic(rec)
                bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
                flags = rec["flags"]
                flags_str = f"{'S' if flags[0] else '-'}{'Z' if flags[1] else '-'}{'A' if flags[2] else '-'}{'P' if flags[3] else '-'}{'C' if flags[4] else '-'}"
                writer.writerow([
                    rec['seq'], f"{rec['pc']:04X}", bytes_str, mnemonic,
                    f"{rec['A']:02X}", f"{rec['BC']:04X}", f"{rec['DE']:04X}",
                    f"{rec['HL']:04X}", f"{rec['SP']:04X}", flags_str,
                    int(rec.get('IFF1', False)), int(rec.get('IFF2', False)),
                    f"{rec.get('I', 0):02X}", rec['cycles'], rec['cycles_total']
                ])

    def _export_trace_json(self, path, records):
        """Экспорт в JSON"""
        data = {
            "version": 1,
            "records": []
        }
        for rec in records:
            mnemonic = self._get_trace_mnemonic(rec)
            bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
            flags = rec["flags"]
            data["records"].append({
                "seq": rec['seq'],
                "pc": rec['pc'],
                "bytes": bytes_str,
                "mnemonic": mnemonic,
                "A": rec['A'], "BC": rec['BC'], "DE": rec['DE'],
                "HL": rec['HL'], "SP": rec['SP'],
                "flags": {"S": flags[0], "Z": flags[1], "AC": flags[2], "P": flags[3], "CY": flags[4]},
                "IFF1": rec.get("IFF1", False),
                "IFF2": rec.get("IFF2", False),
                "I": rec.get("I", 0),
                "cycles": rec['cycles'],
                "cycles_total": rec['cycles_total']
            })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def on_trace_checkbox_toggled(self, checked):
        """Чек-бокс трассировки в эмуляторе"""
        if checked:
            self.emulator.trace_start()
            self.log(f"{self.tr('emulator_trace_on')}")
        else:
            self.emulator.trace_stop()
            self.log(f"{self.tr('emulator_trace_off')}")
        # Синхронизируем с кнопкой на вкладке трассировки
        if hasattr(self, 'btn_trace_toggle'):
            self.btn_trace_toggle.setChecked(checked)
            if checked:
                self.btn_trace_toggle.setText(self.tr("trace_off"))
                self.btn_trace_toggle.setStyleSheet("background-color: #ffcccc;")
            else:
                self.btn_trace_toggle.setText(self.tr("trace_on"))
                self.btn_trace_toggle.setStyleSheet("")
        self.update_trace_status()

    def load_profile(self, profile_name):
        """Загрузка профиля системы (итерация 10.4)"""
        try:
            if self.emulator.running:
                self.emulator_stop()

            # Загружаем профиль (внутри создаётся НОВАЯ шина)
            self.system.load_profile(profile_name)
            self._current_profile = profile_name
            
            # === ПРОВЕРКА ФАЙЛОВ ОБРАЗОВ (ИТЕРАЦИЯ 10.4.1) ===
            errors = self.system.validate_profile_files()
            if errors:
                raise ValueError("Ошибки загрузки профиля:\n" + "\n".join(errors))

            # Читаем тип процессора из профиля (по умолчанию 8080)
            self.current_cpu = self.system.config.cpu if self.system.config.cpu else "i8080"
            
            # Обновляем эмулятор
            if hasattr(self, 'emulator') and self.emulator:
                self.emulator.cpu_type = self.current_cpu
                # Обновляем combo в GUI
                if hasattr(self, 'emu_cpu_combo'):
                    self.emu_cpu_combo.blockSignals(True)
                    self.emu_cpu_combo.setCurrentText(self.current_cpu)
                    self.emu_cpu_combo.blockSignals(False)
                self.emulator.reset()
            
            # Обновляем дизассемблер (таблица опкодов зависит от типа CPU)
            if hasattr(self, 'disassembler') and self.disassembler:
                self.disassembler.set_cpu_type(self.current_cpu)

            # Переподключаем CPU к НОВОЙ шине
            self.system.connect_cpu(self.emulator)

            # Обновляем ссылку на шину в MainWindow
            self.memory_bus = self.system.bus

            # Заменяем RAM из TOML на RAM с mem_data
            from modules.memory import RAMRegion
            self.memory_bus.memory_regions = [
                r for r in self.memory_bus.memory_regions
                if not isinstance(r, RAMRegion)
            ]
            ram = RAMRegion(0x0000, 0xFFFF, data=self.mem_data, name="RAM")
            self.memory_bus.register_memory(ram)

            # Эмулятор видит правильный bus
            self.emulator.memory_bus = self.memory_bus
            
            # === Копируем данные из ПЗУ в mem_data для HEX-редактора ===
            from modules.memory.memory_bus import ROMRegion
            for region in self.memory_bus.memory_regions:
                if isinstance(region, ROMRegion) and hasattr(region, 'data'):
                    for addr, byte in region.data.items():
                        self.mem_data[addr] = byte
            self.hex_model.update_data(self.mem_data)
            self.update_range_label()
            
            # Сбрасываем состояние эмулятора
            self.emulator.halted = False
            self.emulator.wait_signal = False
            if self.mem_data:
                self.emulator.set_pc_to_memory_start()
                self.update_emu_disasm_view()

            if profile_name in self.profile_actions:
                self.profile_actions[profile_name].setChecked(True)
            self._update_device_panels()
            self.statusBar.showMessage(
                f"{self.tr('status_profile_loaded')}{self.system.config.system_name}", 3000
            )
            self.log(f"{self.tr('status_profile_loaded')}{self.system.config.system_name}")
            
            # Закрываем окна устройств при смене профиля
            if self.device_manager is not None:
                self.device_manager.on_profile_changed()
                
        except ValueError as e:
            QMessageBox.critical(self, self.tr("status_profile_err"), str(e))

    def _update_device_panels(self):
        """Обновление панелей устройств после загрузки профиля"""
        # Обновляем список устройств в отладчике (если есть)
        if hasattr(self, 'device_list_widget'):
            self.device_list_widget.clear()
            for dev_info in self.system.list_devices():
                item = QListWidgetItem(
                    f"{dev_info['name']} @ {dev_info['base_port']}"
                )
                self.device_list_widget.addItem(item)    
    
    def show_device_manager(self):
        if self.device_manager is None or not self.device_manager.isVisible():
            self.device_manager = DeviceManagerDialog(self.system, parent=self)
        self.device_manager.show()
        self.device_manager.raise_()
        self.device_manager.activateWindow()

    def _on_memory_changed(self):
        """Вызывается при изменении памяти из любого источника."""
        if hasattr(self, 'assembler_widget'):
            # Не перезаписываем, если пользователь редактирует
            if not self.assembler_widget.editor.document().isModified():
                self.assembler_widget.sync_from_memory()

    # === Help / Справка ===

    def _show_doc(self, filename: str):
        """Show documentation file in a dialog."""
        import os
        from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout
        doc_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(doc_dir, filename)
        if not os.path.exists(path):
            QMessageBox.warning(self, self.tr("menu_help"), f"File not found: {filename}")
            return
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        # Simple markdown to HTML
        html = self._md_to_html(text)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"i8080-5 CI — {filename}")
        dlg.resize(900, 700)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setHtml(html)
        layout.addWidget(browser)
        dlg.exec()

    def _show_about(self):
        """Show About dialog."""
        QMessageBox.about(self, self.tr("help_about"), self.tr("help_about_text")+self.tr("help_author"))

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """Minimal markdown to HTML conversion for documentation display."""
        import re
        html = md_text
        # Headers
        html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        # Code blocks
        html = re.sub(r'```\n(.+?)```', r'<pre>\1</pre>', html, flags=re.DOTALL)
        # Inline code
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        # Horizontal rule
        html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)
        # Tables (basic)
        html = re.sub(r'^\|(.+)\|$', lambda m: '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in m.group(1).split('|')) + '</tr>', html, flags=re.MULTILINE)
        # Wrap in HTML
        html = f'<html><head><meta charset="utf-8"><style>body{{font-family:Segoe UI,Arial,sans-serif;padding:10px;}} pre{{background:#f4f4f4;padding:8px;border-radius:4px;overflow-x:auto;}} code{{background:#f4f4f4;padding:2px 4px;border-radius:2px;}} table{{border-collapse:collapse;width:100%;}} td,th{{border:1px solid #ccc;padding:4px 8px;}} h1{{color:#2c5aa0;}} h2{{color:#3a6db5;}} h3{{color:#4a7dc5;}}</style></head><body>{html}</body></html>'
        return html
