import sys
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QPushButton, QComboBox, QLabel, 
                               QLineEdit, QTextEdit, QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QTableView, QHeaderView, QFileDialog,
                               QProgressBar, QSpinBox, QCheckBox, QScrollArea, QInputDialog,
                               QToolTip, QStyle, QStatusBar, QDialog, QListWidget, QListWidgetItem, QMenu, QSplitter,
							   QFormLayout, QStackedWidget)
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, QAbstractTableModel, QModelIndex, QEvent, QLocale, QSettings, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QShortcut, QKeySequence, QAction

from i8080_emulator import I8080Emulator
from ui.device_manager import DeviceManagerDialog

# === MCP Server (опционально) ===
try:
    from mcp_server import MCPServerManager
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"MCP Server недоступен: {e}")
	
# === Опкоды переходов для подсветки в трассировке ===
JUMP_OPCODES = {
    0xC3, 0xCA, 0xC2, 0xDA, 0xD2, 0xF2, 0xFA, 0xEA, 0xE2,  # JMP, JZ, JNZ, JC, JNC, JP, JM, JPE, JPO
    0xCD, 0xCC, 0xC4, 0xDC, 0xD4, 0xF4, 0xFC, 0xEC, 0xE4,  # CALL, CZ, CNZ, CC, CNC, CP, CM, CPE, CPO
    0xC9, 0xC8, 0xC0, 0xD8, 0xD0, 0xF0, 0xF8, 0xE8, 0xE0,  # RET, RZ, RNZ, RC, RNC, RP, RM, RPE, RPO
    0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF         # RST 0-7
}

# ==================== ЛОКАЛИЗАЦИЯ И ТЕМЫ ====================
LANGS = {
    "en": {
        "app_title": "i8080-5 CI",
        "port": "Port:", "baud": "Baud:", "connect": "Connect", "disconnect": "Disconnect",
        "refresh": "Refresh", "tab_control": "Control", "tab_data": "Data", "tab_hex": "Hex Editor",
        "tab_disasm": "Disassembler", "tab_test": "Memory Test", "tab_io_seq": "IO Sequencer",
        "log": "Log:", "bus_control": "Bus Control", "hold": "Hold Bus (HOLD)", "unhold": "Release Bus (UnHOLD)",
        "files": "Files (Intel HEX / BIN)", "save_dump": "Save Dump (.hex)", "load_fw": "Load Firmware (.hex/.bin)",
        "memory": "Memory (RAM/ROM) — read/write values", "io_port": "IO Port — read/write values",
        "addr_hex": "Address (HEX):", "port_hex": "Port (HEX):", "bits": "Bit width:",
        "value_hex": "Value (HEX):", "endian": "Byte order:", "read": "Read", "write": "Write",
        "range": "Range:", "read_block": "Read Block...", "start": "Start:", "len": "Len:",
        "disasm": "Disassemble", "auto_disasm": "Auto on read/load",
        "pattern": "Pattern:", "start_test": "Start Memory Test",
        "single_io": "Single IO Operations", "read_in": "Read (IN)", "write_out": "Write (OUT)",
        "io_seq": "IO Sequencer (command sequence)", "load_file": "Load File...", "run_seq": "Run Sequence",
        "connected": "Connected", "disconnected": "Disconnected", "test_conn": "Connection test (NOP)...",
        "err_port": "Select a COM port!", "err_connect": "Connection Error", "err_open": "Failed to open port",
        "err_addr": "Invalid address!", "err_addr_val": "Invalid address or value!",
        "err_port_addr": "Invalid port address!", "err_empty": "Empty", "err_no_data": "No data to save.",
        "save_as": "Save Dump As", "load_fw_title": "Load Firmware", "base_addr": "Base Address",
        "base_addr_hint": "Enter base address for BIN (HEX):", "err_hex": "Invalid HEX address!",
        "flash_q": "Flash", "flash_msg": "Write this data to device memory?", "loaded": "Loaded",
        "bytes_from_file": "bytes from file.", "thread_done": "Thread finished.",
        "err_not_open": "Port not open!", "err_send": "Send error:", "err_read_port": "Port read error:",
        "err_write_port": "Port write error:", "err_seq_fmt": "Invalid line format:",
        "io_seq_start": "Starting IO sequencer...", "io_seq_done": "IO sequencer finished.",
        "delay": "DELAY", "ok": "OK", "error": "ERROR", "write_io": "IO Write", "read_io": "IO Read",
        "conn_est": "Connection established (NOP).", "err_ack": "AckError from device.",
        "theme": "Theme:", "language": "Language:", "light": "Light", "dark": "Dark",
        "mem_test": "Memory test", "errors": "errors", "write_block": "Writing block to",
        "read_block_msg": "Reading block:", "read_ok": "Successfully read", "bytes": "bytes.",
        "read_err": "Block read error!", "write_done": "Write complete", "write_err": "Write error at address",
        "io_read_block": "Reading IO block:", "io_read_ok": "Successfully read", "io_bytes": "IO bytes.",
        "io_read_err": "IO block read error!", "io_write_block": "Writing IO block to",
        "io_write_done": "IO write complete", "io_write_err": "IO write error at address",
        "test_mem": "Memory test", "pattern": "pattern", "test_done": "Test complete.",
        "write_fail": "Write failure at", "read_fail": "Read failure at",
        "expected": "Expected", "got": "Got", "export": "Export", "search": "Search",
        "goto_addr": "Goto Address", "fill_range": "Fill Range", "copy_addr": "Copy Address",
        "copy_val": "Copy Value", "invert_byte": "Invert Byte", "disasm_from": "Disassemble from",
        "text_column": "Text", "addr_column": "Addr", "tab_compare": "Compare",
        "load_compare": "Load File to Compare", "btn_compare": "Compare", "export_report": "Export Report",
        "compare_addr": "Address", "compare_current": "Current", "compare_file": "File", "compare_status": "Status",
        "status_changed": "Changed", "status_added": "Added in File", "status_removed": "Removed in File",
        "no_compare_file": "No file loaded for comparison", "compare_loaded": "Loaded", 
        "run_compare_first": "Run compare first!", "compare_found": "differences found",
        "compare_complete": "Compare complete", "compare_exported": "Compare report exported to",
        "load_compare_title": "Load File to Compare", "export_compare_title": "Export Compare Report",
		"tab_scripts": "Scripts", "run_script": "▶ Run Script", "load_script": "Load Script",
		"save_script": "Save Script", "clear_output": "Clear Output", "script_output": "Output:",
        "tab_emulator": "Emulator", "emulator_registers": "Registers", "emulator_flags": "Flags",
        "emulator_stats": "Statistics", "emulator_control": "Control", "emulator_current_instr": "Current Instruction",
        "emulator_breakpoints": "Breakpoints", "emulator_reset": "⚡ Reset (Ctrl+F2)", "emulator_set_pc": "📌 Set PC...",
        "emulator_step_into": "↴ Step Into (F11)", "emulator_step_over": "➟ Step Over (F10)",
        "emulator_run": "🚀 Run (F5)", "emulator_stop": "⛔ Stop (F8)", "emulator_add_bp": "Add",
        "emulator_clear_bp": "🗑 Clear All", "end": "End:", "emulator_stack": "Stack",
        "tab_trace": "Trace", "emulator_trace": "Trace",  "trace_filter_clear":  "Reset filter ",
        "emulator_trace_on": "Trace on", "emulator_trace_off": "Trace off", 
        "menu_profile":  "System Profile ",
        "trace_on":  "🔥 Enable Recording ",  "trace_off":  "⏹ Disable Recording ",
        "trace_clear":  "🗑 Clear ",  "trace_export":  "💾 Export ",
        "trace_depth":  "Depth: ",  "trace_records":  "Records: ",
        "trace_search":  "Search: ",
        "trace_search_hint":  "Address (HEX) or register OP value (A==55, HL>1000, SP<=F000) ",
        "trace_detail_title":  "Selected Record Details ",
        "trace_detail_hint":  "Select a record to view ",
        "trace_col_seq":  "# ",  "trace_col_pc":  "PC ",  "trace_col_bytes":  "Bytes ",
        "trace_col_mnem":  "Mnemonic ",  "trace_col_flags":  "Flags ",
        "emu_code":  "Code: ",  "emu_watch":  "Watch ",  "emu_bp":  "Breakpoints ",
        "status_addr":  "Address: ",  "status_data":  "Data: ",
        "status_mnem":  "Mnemonic: ",  "status_size":  "Size: ",
        "search_title":  "Search Memory ",  "search_pattern":  "Pattern: ",
        "search_mode":  "Mode: ",
        "search_mode_hex":  "HEX Bytes ",  "search_mode_ascii":  "ASCII String ",
        "search_mode_mask":  "HEX with Mask (??) ",
        "search_find_next":  "Find Next ",  "search_find_all":  "Find All ",
        "search_close":  "Close ",  "search_results":  "Results: ",
        "ctx_run_to":  "Run to Cursor ",  "ctx_run_from":  "Run from Here ",
        "ctx_jump":  "Jump to Cursor ",  "ctx_toggle_bp":  "Toggle Breakpoint ",
        "ctx_cond_bp":  "Set Conditional BP... ",
        "ctx_copy_addr":  "Copy Address ",  "ctx_copy_val":  "Copy Value ",
        "ctx_invert":  "Invert Byte ",  "ctx_fill":  "Fill Range... ",
        "ctx_disasm":  "Disassemble from ",  "ctx_goto":  "Goto Address... ",
        "fill_title":  "Fill Range ",  "fill_value":  "Value (HEX): ",
        "goto_title":  "Goto Address ",
        "watch_add_title":  "Add to Watch ",  "watch_name":  "Name: ",
        "watch_type":  "Type: ",  "watch_type_byte":  "Memory (byte) ",
        "watch_type_word":  "Memory (word) ",  "watch_type_reg":  "Register ",
        "watch_target":  "Address/Register: ",  "watch_format":  "Format: ",
        "watch_addr_hint":  "HEX address, e.g. 0100 ",
        "bp_cond_title":  "Breakpoint Condition ",
        "bp_cond_clear":  "Clear Condition ",  "bp_cond_ok":  "OK ",  "bp_cond_cancel":  "Cancel ",
        "bp_cond_hint":  "Available variables:\n"
                         "  Registers: A, B, C, D, E, H, L, BC, DE, HL, SP, PC\n"
                         "  Flags: S, Z, AC, P, CY\n"
                         "  Memory: mem[0x0100]   Ports: io[0x01]\n"
                         "  Cycles: cycles\n"
                         "  Operators: ==, !=, <, >, <=, >=, and, or, not ",
        "err_addr_mem":  "Enter memory address! ",  "err_syntax":  "Invalid syntax! ",
        "dlg_cancel": "Cancel ", "dlg_ok": "OK ",
        # Статистика эмулятора
        "emu_cycles": "Cycles: ",
        "emu_state": "State: ",
        "emu_state_halted": "Halted (HLT)",
        "emu_state_running": "Running",
        "emu_state_ready": "Ready",
        # Трассировка: детали и контекстное меню
        "trace_regs_after": "Registers AFTER: ",
        "trace_flags": "Flags: ",
        "trace_cycles": "Cycles: ",
        "trace_cycles_total": "(total: ",
        "trace_ctx_view": "👁 View state ",
        "trace_ctx_restore": "↩ Restore state",
        "trace_ctx_goto": "➤ Goto address 0x",
        "trace_ctx_goto_suffix": " in disassembler",
        "trace_export_title": "Export Trace",
        "trace_no_data": "No data to export",
        "trace_exported": "Trace exported: ",
        "trace_export_err": "Failed to export trace:\n",
        # Watch: статусы и пресеты
        "watch_select_del": "Select an item to delete",
        "watch_confirm": "Confirmation",
        "watch_confirm_del": "Delete all Watch items?",
        "watch_save_preset": "Save Watch Preset",
        "watch_load_preset": "Load Watch Preset",
        "watch_preset_saved": "Preset saved: ",
        "watch_preset_loaded": "Preset loaded: ",
        "watch_preset_save_err": "Failed to save preset",
        "watch_preset_load_err": "Failed to load preset. Check file format.",
        "watch_auto_prefix": "Auto: ",
        "watch_err_addr": "Enter memory address!",
        "watch_err_fmt_title": "Format Error",
        "watch_err_add": "Failed to add Watch:\n",
        # BP: статусы и пресеты
        "bp_select": "Select a breakpoint",
        "bp_add_title": "Add Breakpoint",
        "bp_addr": "Address (HEX): ",
        "bp_err_addr": "Invalid address!",
        "bp_save_preset": "Save BP Preset",
        "bp_load_preset": "Load BP Preset",
        "bp_preset_saved": "BP preset saved: ",
        "bp_preset_loaded": "BP preset loaded: ",
        "bp_preset_save_err": "Failed to save BP preset:\n",
        "bp_preset_load_err": "Failed to load BP preset:\n",
        "bp_cond_err": "Invalid condition syntax!",
        "bp_cond_example": "Example: A == 0x55",
        # Диалоги
        "set_pc_title": "Set PC",
        "export_disasm_title": "Export Disassembly",
        "export_disasm_log": "Disassembly exported to: ",
        "export_disasm_status": "Exported to ",
        "search_invalid_hex": "Invalid HEX pattern!",
        "search_invalid_len": "Invalid pattern length!",
        "search_invalid_byte": "Invalid byte: ",
        "search_found": "Found ",
        "search_matches": " matches",
        "fill_size": "Size (Dec): ",
        "fill_start_addr": "Start Address (HEX): ",
        # Статусбар
        "status_cursor": "Cursor: 0x",
        "status_cursor_hint": " (Ctrl+F10 — run to cursor)",
        "status_not_connected": "Not connected!",
        "status_bus_active": "Bus already active!",
        "status_bus_not_active": "Bus not active!",
        "status_reached_cursor": "Reached cursor 0x",
        "status_emu_stopped": "Emulator stopped",
        "status_bp_hit": "Breakpoint at 0x",
        "status_running": "Running...",
        "status_cpu_halted": "CPU halted. Press Reset (Ctrl+F2).",
        "status_cpu_halted_short": "CPU halted. Press Reset.",
        "status_cursor_not_set": "Cursor not set. Click a disassembler line.",
        "status_cursor_eq_pc": "Cursor equals PC.",
        "status_running_to": "Running to 0x",
        "status_running_from": "Running from 0x",
        "status_pc_set": "PC set to 0x",
        "status_state_restored": "State restored: PC=0x",
        "status_trace_search_err": "Invalid query format: ",
        "status_trace_found": "Found: ",
        "status_trace_of": " of ",
        "status_refreshed": "Refreshed",
        "status_undo_depth": "Undo depth: ",
        "status_nothing_undo": "Nothing to undo",
        "status_undo": "Undo: ",
        "status_undo_bytes": " bytes",
        "status_nothing_redo": "Nothing to redo",
        "status_redo": "Redo: ",
        "status_redo_bytes": " bytes",
        "status_profile_loaded": "Profile loaded: ",
        "status_profile_err": "Profile Error",
        # Скрипты
        "script_no_code": "No code to run.",
        "script_running": "Running script...",
        "script_done": "✓ Script completed successfully.",
        "script_completed": "Script completed",
        "script_err": "✗ ERROR: ",
        "script_error": "Script error!",
        "script_load_title": "Load Script",
        "script_loaded": "Script loaded: ",
        "script_save_title": "Save Script",
        "script_saved": "Script saved: ",
        # Скрипты: метка вывода
        "script_output_label": "Output: ",
        # IO секвенсор: placeholder
        "seq_placeholder": "Format:\nW 01 FF ; Write value FFh to port 01h\nR 02    ; Read from port 02h\nD 10    ; Delay 10 ms",
        # Разное
        "bus_not_active_msg": "Bus not active! Hold the bus first.",
        "mcp_err_title": "MCP",
        "mcp_err_msg": "MCP Server unavailable. Install dependencies:\npip install mcp uvicorn starlette",
        "info_title": "Info",
        "hold_bus_first": "Hold the bus (HOLD) before flashing.",
        "dev_not_connected": "Device not connected. Firmware loaded to editor only.",
        "bus_not_active_log": "Bus not active. Hold the bus before flashing.",
        "trace_buf_cleared": "Trace buffer cleared",
        "trace_search_log": "Trace search: '",
        "trace_search_found": "' — found ",
        "trace_filter_clear":  "Reset filter ",
        "tip_watch_add":  "Add watch item ",  "tip_watch_del":  "Delete selected item ",
        "tip_watch_clear":  "Clear all ",  "tip_watch_save":  "Save preset ",
        "tip_watch_load":  "Load preset ",  "tip_bp_add":  "Add breakpoint ",
        "tip_bp_cond":  "Edit condition ",  "tip_bp_toggle":  "Enable/disable ",
        "tip_bp_del":  "Delete selected ",  "tip_bp_clear":  "Clear all ",
        "tip_bp_save":  "Save BP preset ",  "tip_bp_load":  "Load BP preset ",
        "tip_trace_enable":  "Enable trace recording ",
        "trace_filter_clear":  "Reset filter ",
        "watch_col_name":   "Name  ",   "watch_col_target":   "Addr/Reg  ",
        "watch_col_value":   "Value  ",   "watch_col_format":   "Format  ",
        "bp_col_addr":   "Address  ",   "bp_col_cond":   "Condition  ",
        "bp_col_enabled":   "On  ",   "bp_col_hits":   "Hits  ",
        # Устройства
        "menu_devices": "Devices", "device_manager": "Device Manager",
    },
    "ru": {
        "app_title": "i8080-5 CI",
        "port": "Порт:", "baud": "Скорость:", "connect": "Подключиться", "disconnect": "Отключиться",
        "refresh": "Обновить", "tab_control": "Управление", "tab_data": "Данные", "tab_hex": "Hex Редактор",
        "tab_disasm": "Дизассемблер", "tab_test": "Тест Памяти", "tab_io_seq": "IO Секвенсор",
        "log": "Журнал:", "bus_control": "Управление шиной", "hold": "Захватить шину (HOLD)", "unhold": "Освободить шину (UnHOLD)",
        "files": "Файлы (Intel HEX / BIN)", "save_dump": "Сохранить дамп (.hex)", "load_fw": "Загрузить прошивку (.hex/.bin)",
        "memory": "Память (RAM/ROM) — чтение/запись значений", "io_port": "Порт ввода-вывода (IO) — чтение/запись значений",
        "addr_hex": "Адрес (HEX):", "port_hex": "Порт (HEX):", "bits": "Разрядность (бит):",
        "value_hex": "Значение (HEX):", "endian": "Порядок байтов:", "read": "Прочитать", "write": "Записать",
        "range": "Диапазон:", "read_block": "Читать блок...", "start": "Старт:", "len": "длина:",
        "disasm": "Дизассемблировать", "auto_disasm": "Авто при чтении/загрузке",
        "pattern": "Паттерн:", "start_test": "Запустить тест памяти",
        "single_io": "Одиночные операции IO", "read_in": "Читать (IN)", "write_out": "Записать (OUT)",
        "io_seq": "IO Секвенсор (последовательность команд)", "load_file": "Загрузить файл...", "run_seq": "Выполнить последовательность",
        "connected": "Подключено", "disconnected": "Отключено", "test_conn": "Тест соединения (NOP)...",
        "err_port": "Выберите COM-порт!", "err_connect": "Ошибка подключения", "err_open": "Не удалось открыть порт",
        "err_addr": "Неверный адрес!", "err_addr_val": "Неверный адрес или значение!",
        "err_port_addr": "Неверный адрес порта!", "err_empty": "Пусто", "err_no_data": "Нет данных для сохранения.",
        "save_as": "Сохранить дамп", "load_fw_title": "Загрузить прошивку", "base_addr": "Базовый адрес",
        "base_addr_hint": "Укажите базовый адрес для BIN (HEX):", "err_hex": "Неверный HEX адрес!",
        "flash_q": "Прошивка", "flash_msg": "Записать эти данные в память устройства?", "loaded": "Загружено",
        "bytes_from_file": "байт из файла.", "thread_done": "Поток завершен.",
        "err_not_open": "Порт не открыт!", "err_send": "Ошибка отправки:", "err_read_port": "Ошибка чтения порта:",
        "err_write_port": "Ошибка записи в порт:", "err_seq_fmt": "Неверный формат строки:",
        "io_seq_start": "Запуск IO секвенсора...", "io_seq_done": "IO секвенсор завершен.",
        "delay": "ЗАДЕРЖКА", "ok": "OK", "error": "ОШИБКА", "write_io": "Запись IO", "read_io": "Чтение IO",
        "conn_est": "Соединение установлено (NOP).", "err_ack": "AckError от устройства.",
        "theme": "Тема:", "language": "Язык:", "light": "Светлая", "dark": "Тёмная",
        "mem_test": "Тест памяти", "errors": "ошибок", "write_block": "Запись блока в",
        "read_block_msg": "Чтение блока:", "read_ok": "Успешно прочитано", "bytes": "байт.",
        "read_err": "Ошибка чтения блока!", "write_done": "Запись завершена", "write_err": "Ошибка записи на адресе",
        "io_read_block": "Чтение IO блока:", "io_read_ok": "Успешно прочитано", "io_bytes": "IO байт.",
        "io_read_err": "Ошибка чтения IO блока!", "io_write_block": "Запись IO блока в",
        "io_write_done": "Запись IO завершена", "io_write_err": "Ошибка записи IO на адресе",
        "test_mem": "Тест памяти", "pattern": "паттерном", "test_done": "Тест завершен.",
        "write_fail": "Сбой записи на", "read_fail": "Сбой чтения на",
        "expected": "Ожидалось", "got": "Получено", "export": "Экспорт", "search": "Поиск",
        "goto_addr": "Перейти к адресу", "fill_range": "Заполнить диапазон", "copy_addr": "Копировать адрес",
        "copy_val": "Копировать значение", "invert_byte": "Инвертировать байт", "disasm_from": "Дизассемблировать от",
        "text_column": "Текст", "addr_column": "Адрес", "tab_compare": "Сравнение",
        "load_compare": "Загрузить файл для сравнения", "btn_compare": "Сравнить", "export_report": "Экспорт отчёта",
        "compare_addr": "Адрес", "compare_current": "Текущий", "compare_file": "Файл", "compare_status": "Статус",
        "status_changed": "Изменено", "status_added": "Добавлено в файле", "status_removed": "Удалено в файле",
        "no_compare_file": "Файл для сравнения не загружен", "compare_loaded": "Загружено", 
        "run_compare_first": "Сначала выполните сравнение!", "compare_found": "различий найдено",
        "compare_complete": "Сравнение завершено", "compare_exported": "Отчёт о сравнении экспортирован в",
        "load_compare_title": "Загрузить файл для сравнения", "export_compare_title": "Экспорт отчёта о сравнении",
		"tab_scripts": "Скрипты", "run_script": "▶ Выполнить скрипт", "load_script": "Загрузить скрипт",
		"save_script": "Сохранить скрипт", "clear_output": "Очистить вывод", "script_output": "Вывод:",
        "tab_emulator": "Эмулятор", "emulator_registers": "Регистры", "emulator_flags": "Флаги", "emulator_stats": "Статистика",
        "emulator_control": "Управление", "emulator_current_instr": "Текущая инструкция", "emulator_breakpoints": "Точки останова",
        "emulator_reset": "⚡ Сброс (Ctrl+F2)", "emulator_set_pc": "📌 Установить PC...", "emulator_step_into": "↴ Шаг с заходом (F11)",
        "emulator_step_over": "➟ Шаг без захода (F10)", "emulator_run": "🚀 Запуск (F5)", "emulator_stop": "⛔ Стоп (F8)",
        "emulator_add_bp": "Добавить", "emulator_clear_bp": "🗑 Очистить все", "end": "Конец:", "emulator_stack": "Стек",
        "tab_trace": "Трассировка", "emulator_trace": "Трассировка",
        "emulator_trace_on": "Трассировка включена", "emulator_trace_off": "Трассировка выключена", 
        "menu_profile":  "Профиль системы ",
        "trace_on":  "🔥 Включить запись ",  "trace_off":  "⏹ Выключить запись ",
        "trace_clear":  "🗑 Очистить ",  "trace_export":  "💾 Экспорт ",
        "trace_depth":  "Глубина: ",  "trace_records":  "Записей: ", "trace_filter_clear":  "Сбросить фильтр",
        "trace_search":  "Поиск: ",
        "trace_search_hint":  "Адрес (HEX) или регистр ОП значение (A==55, HL>1000, SP<=F000) ",
        "trace_detail_title":  "Детали выбранной записи ",
        "trace_detail_hint":  "Выберите запись для просмотра ",
        "trace_col_seq":  "# ",  "trace_col_pc":  "PC ",  "trace_col_bytes":  "Байты ",
        "trace_col_mnem":  "Мнемо ",  "trace_col_flags":  "Флаги ",
        "emu_code":  "Код: ",  "emu_watch":  "Watch ",  "emu_bp":  "Точки останова ",
        "status_addr":  "Адрес: ",  "status_data":  "Данные: ",
        "status_mnem":  "Мнемоника: ",  "status_size":  "Размер: ",
        "search_title":  "Поиск в памяти ",  "search_pattern":  "Паттерн: ",
        "search_mode":  "Режим: ",
        "search_mode_hex":  "HEX байты ",  "search_mode_ascii":  "ASCII строка ",
        "search_mode_mask":  "HEX с маской (??) ",
        "search_find_next":  "Найти далее ",  "search_find_all":  "Найти все ",
        "search_close":  "Закрыть ",  "search_results":  "Результаты: ",
        "ctx_run_to":  "Выполнить до курсора ",  "ctx_run_from":  "Выполнить отсюда ",
        "ctx_jump":  "Перейти к курсору ",  "ctx_toggle_bp":  "Точка останова ",
        "ctx_cond_bp":  "Условная точка останова... ",
        "ctx_copy_addr":  "Копировать адрес ",  "ctx_copy_val":  "Копировать значение ",
        "ctx_invert":  "Инвертировать байт ",  "ctx_fill":  "Заполнить диапазон... ",
        "ctx_disasm":  "Дизассемблировать от ",  "ctx_goto":  "Перейти к адресу... ",
        "fill_title":  "Заполнить диапазон ",  "fill_value":  "Значение (HEX): ",
        "goto_title":  "Перейти к адресу ",
        "watch_add_title":  "Добавить в Watch ",  "watch_name":  "Имя: ",
        "watch_type":  "Тип: ",  "watch_type_byte":  "Память (байт) ",
        "watch_type_word":  "Память (слово) ",  "watch_type_reg":  "Регистр ",
        "watch_target":  "Адрес/Регистр: ",  "watch_format":  "Формат: ",
        "watch_addr_hint":  "Адрес HEX, например: 0100 ",
        "bp_cond_title":  "Условие точки останова ",
        "bp_cond_clear":  "Очистить условие ",  "bp_cond_ok":  "OK ",  "bp_cond_cancel":  "Отмена ",
        "bp_cond_hint":  "Доступные переменные:\n"
                         "  Регистры: A, B, C, D, E, H, L, BC, DE, HL, SP, PC\n"
                         "  Флаги: S, Z, AC, P, CY\n"
                         "  Память: mem[0x0100]   Порты: io[0x01]\n"
                         "  Такты: cycles\n"
                         "  Операторы: ==, !=, <, >, <=, >=, and, or, not ",
        "err_addr_mem":  "Введите адрес памяти! ",  "err_syntax":  "Неверный синтаксис! ",
        "dlg_cancel": "Отмена ", "dlg_ok": "OK ",
        # Статистика эмулятора
        "emu_cycles": "Такты: ",
        "emu_state": "Состояние: ",
        "emu_state_halted": "Остановлен (HLT)",
        "emu_state_running": "Выполняется",
        "emu_state_ready": "Готов",
        # Трассировка: детали и контекстное меню
        "trace_regs_after": "Регистры ПОСЛЕ: ",
        "trace_flags": "Флаги: ",
        "trace_cycles": "Такты: ",
        "trace_cycles_total": "(всего: ",
        "trace_ctx_view": "👁 Просмотр состояния ",
        "trace_ctx_restore": "↩ Восстановить состояние",
        "trace_ctx_goto": "➤ Перейти к адресу 0x",
        "trace_ctx_goto_suffix": " в дизассемблере",
        "trace_export_title": "Экспорт трассировки",
        "trace_no_data": "Нет данных для экспорта",
        "trace_exported": "Трассировка экспортирована: ",
        "trace_export_err": "Не удалось экспортировать трассировку:\n",
        # Watch: статусы и пресеты
        "watch_select_del": "Выберите элемент для удаления",
        "watch_confirm": "Подтверждение",
        "watch_confirm_del": "Удалить все элементы Watch?",
        "watch_save_preset": "Сохранить пресет Watch",
        "watch_load_preset": "Загрузить пресет Watch",
        "watch_preset_saved": "Пресет сохранён: ",
        "watch_preset_loaded": "Пресет загружен: ",
        "watch_preset_save_err": "Не удалось сохранить пресет",
        "watch_preset_load_err": "Не удалось загрузить пресет. Проверьте формат файла.",
        "watch_auto_prefix": "Авто: ",
        "watch_err_addr": "Введите адрес памяти!",
        "watch_err_fmt_title": "Ошибка формата",
        "watch_err_add": "Не удалось добавить Watch:\n",
        # BP: статусы и пресеты
        "bp_select": "Выберите точку останова",
        "bp_add_title": "Добавить точку останова",
        "bp_addr": "Адрес (HEX): ",
        "bp_err_addr": "Неверный адрес!",
        "bp_save_preset": "Сохранить пресет BP",
        "bp_load_preset": "Загрузить пресет BP",
        "bp_preset_saved": "Пресет BP сохранён: ",
        "bp_preset_loaded": "Пресет BP загружен: ",
        "bp_preset_save_err": "Не удалось сохранить пресет BP:\n",
        "bp_preset_load_err": "Не удалось загрузить пресет BP:\n",
        "bp_cond_err": "Неверный синтаксис условия!",
        "bp_cond_example": "Например: A == 0x55",
        # Диалоги
        "set_pc_title": "Установить PC",
        "export_disasm_title": "Экспорт дизассемблера",
        "export_disasm_log": "Дизассемблер экспортирован в: ",
        "export_disasm_status": "Экспортировано в ",
        "search_invalid_hex": "Неверный HEX-паттерн!",
        "search_invalid_len": "Неверная длина паттерна!",
        "search_invalid_byte": "Неверный байт: ",
        "search_found": "Найдено ",
        "search_matches": " совпадений",
        "fill_size": "Размер (дек): ",
        "fill_start_addr": "Начальный адрес (HEX): ",
        # Статусбар
        "status_cursor": "Курсор: 0x",
        "status_cursor_hint": " (Ctrl+F10 — выполнить до курсора)",
        "status_not_connected": "Не подключено!",
        "status_bus_active": "Шина уже активна!",
        "status_bus_not_active": "Шина не активна!",
        "status_reached_cursor": "Достигнут курсор 0x",
        "status_emu_stopped": "Эмулятор остановлен",
        "status_bp_hit": "Точка останова на 0x",
        "status_running": "Выполнение...",
        "status_cpu_halted": "CPU остановлен. Нажмите Сброс (Ctrl+F2).",
        "status_cpu_halted_short": "CPU остановлен. Нажмите Сброс.",
        "status_cursor_not_set": "Курсор не установлен. Кликните по строке дизассемблера.",
        "status_cursor_eq_pc": "Курсор совпадает с PC.",
        "status_running_to": "Выполнение до 0x",
        "status_running_from": "Выполнение от 0x",
        "status_pc_set": "PC установлен на 0x",
        "status_state_restored": "Состояние восстановлено: PC=0x",
        "status_trace_search_err": "Неверный формат запроса: ",
        "status_trace_found": "Найдено: ",
        "status_trace_of": " из ",
        "status_refreshed": "Обновлено",
        "status_undo_depth": "Глубина отмены: ",
        "status_nothing_undo": "Нечего отменять",
        "status_undo": "Отмена: ",
        "status_undo_bytes": " байт",
        "status_nothing_redo": "Нечего повторять",
        "status_redo": "Повтор: ",
        "status_redo_bytes": " байт",
        "status_profile_loaded": "Профиль загружен: ",
        "status_profile_err": "Ошибка профиля",
        # Скрипты
        "script_no_code": "Нет кода для выполнения.",
        "script_running": "Выполнение скрипта...",
        "script_done": "✓ Скрипт выполнен успешно.",
        "script_completed": "Скрипт выполнен",
        "script_err": "✗ ОШИБКА: ",
        "script_error": "Ошибка скрипта!",
        "script_load_title": "Загрузить скрипт",
        "script_loaded": "Скрипт загружен: ",
        "script_save_title": "Сохранить скрипт",
        "script_saved": "Скрипт сохранён: ",
        # Скрипты: метка вывода
        "script_output_label": "Вывод: ",
        # IO секвенсор: placeholder
        "seq_placeholder": "Формат:\nW 01 FF ; Запись в порт 01h значения FFh\nR 02    ; Чтение из порта 02h\nD 10    ; Задержка 10 мс",
        # Разное
        "bus_not_active_msg": "Шина не активна! Сначала захватите шину.",
        "mcp_err_title": "MCP",
        "mcp_err_msg": "MCP Server недоступен. Установите зависимости:\npip install mcp uvicorn starlette",
        "info_title": "Информация",
        "hold_bus_first": "Сначала захватите шину (HOLD) перед прошивкой.",
        "dev_not_connected": "Устройство не подключено. Прошивка загружена только в редактор.",
        "bus_not_active_log": "Шина не активна. Захватите шину перед прошивкой.",
        "trace_buf_cleared": "Буфер трассировки очищен",
        "trace_search_log": "Поиск в трассировке: '",
        "trace_search_found": "' — найдено ",
        "trace_filter_clear":  "Сбросить фильтр ",
        "tip_watch_add":  "Добавить элемент наблюдения ",  "tip_watch_del":  "Удалить выбранный элемент ",
        "tip_watch_clear":  "Очистить все ",  "tip_watch_save":  "Сохранить пресет ",
        "tip_watch_load":  "Загрузить пресет ",  "tip_bp_add":  "Добавить точку останова ",
        "tip_bp_cond":  "Редактировать условие ",  "tip_bp_toggle":  "Включить/выключить ",
        "tip_bp_del":  "Удалить выбранную ",  "tip_bp_clear":  "Очистить все ",
        "tip_bp_save":  "Сохранить пресет BP ",  "tip_bp_load":  "Загрузить пресет BP ",
        "tip_trace_enable":  "Включить запись трассировки выполнения ",
        "trace_filter_clear":  "Сбросить фильтр ",
        "watch_col_name":   "Имя  ",   "watch_col_target":   "Адрес/Рег  ",
        "watch_col_value":   "Значение  ",   "watch_col_format":   "Формат  ",
        "bp_col_addr":   "Адрес  ",   "bp_col_cond":   "Условие  ",
        "bp_col_enabled":   "Вкл  ",   "bp_col_hits":   "Сраб.  ",
        # Устройства
        "menu_devices": "Устройства", "device_manager": "Диспетчер устройств",
    }
}

THEMES = {
    "Light": "",
    "Dark": """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #d4d4d4; }
        QTabWidget::pane { border: 1px solid #555; }
        QTabBar::tab { background: #3c3c3c; padding: 5px 10px; }
        QTabBar::tab:selected { background: #0078d4; color: white; }
        QPushButton { background-color: #3c3c3c; border: 1px solid #555; padding: 5px; border-radius: 3px; }
        QPushButton:hover { background-color: #505050; }
        QLineEdit, QComboBox, QSpinBox { background-color: #3c3c3c; border: 1px solid #555; padding: 3px; border-radius: 3px; }
        QTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #555; }
        QTableView { background-color: #1e1e1e; color: #d4d4d4; gridline-color: #555; border: 1px solid #555; }
        QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 10px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; }
        QProgressBar::chunk { background-color: #0078d4; }
    """
}

def get_system_language():
    """Определяет системный язык. Возвращает 'ru', 'en' или 'en' по умолчанию."""
    try:
        lang = QLocale.system().name()  # Например: 'ru_RU', 'en_US', 'de_DE'
        if lang.startswith('ru'):
            return "ru"
        elif lang.startswith('en'):
            return "en"
        # Можно добавить другие языки здесь
    except Exception:
        pass
    return "en"  # По умолчанию английский

# --- Константы SLIP и Команд ---
_FEND = 0xC0; _FESC = 0xDB; _TFEND = 0xDC; _TFESC = 0xDD
CMD_NOP = 0x00
CMD_HOLD = 0x01; CMD_UNHOLD = 0x02
CMD_MEM_READ_BYTE = 0x10; CMD_MEM_READ_BLOCK = 0x11
CMD_MEM_WRITE_BYTE = 0x12; CMD_MEM_WRITE_BLOCK = 0x13
CMD_IO_READ_BYTE = 0x20; CMD_IO_READ_BLOCK = 0x21
CMD_IO_WRITE_BYTE = 0x22; CMD_IO_WRITE_BLOCK = 0x23
CMD_EEPROM_WRITE_BYTE = 0x32
CMD_EEPROM_WRITE_BLOCK = 0x33
ACK_NOP = 0x00
ACK_HOLD_WAIT_LOW = 0x00          # ожидание HLDA low
ACK_HOLD_WAIT_HIGH = 0x01         # ожидание HLDA high
ACK_HOLD_ACTIVE = 0x03
ACK_WAIT_UNHOLD = 0xF1            # ожидание освобождения
ACK_UNHOLD = 0xF2 
ACK_MEM_READ_BYTE = 0x10; ACK_MEM_READ_BLOCK = 0x11
ACK_MEM_WRITE_BYTE = 0x12; ACK_MEM_WRITE_BLOCK = 0x13
ACK_IO_READ_BYTE = 0x20; ACK_IO_READ_BLOCK = 0x21
ACK_IO_WRITE_BYTE = 0x22; ACK_IO_WRITE_BLOCK = 0x23
ACK_EEPROM_READ_BYTE = 0x30
ACK_EEPROM_READ_BLOCK = 0x31
ACK_EEPROM_WRITE_BYTE = 0x32
ACK_EEPROM_WRITE_BLOCK = 0x33
ACK_ERROR = 0xFF
CMD_GET_SIZE_SETUP = 0x40
ACK_GET_SIZE_SETUP = 0x40
# ==================== ПРОТОКОЛ SLIP ====================
class SlipProtocol:
    @staticmethod
    def encode(data: bytes) -> bytes:
        encoded = bytearray([_FEND])
        for b in data:
            if b == _FEND: encoded.extend([_FESC, _TFEND])
            elif b == _FESC: encoded.extend([_FESC, _TFESC])
            else: encoded.append(b)
        encoded.append(_FEND)
        return bytes(encoded)

    @staticmethod
    def decode(data: bytes) -> bytes:
        decoded = bytearray()
        i = 0
        while i < len(data):
            if data[i] == _FESC:
                if i + 1 < len(data):
                    if data[i+1] == _TFEND: decoded.append(_FEND)
                    elif data[i+1] == _TFESC: decoded.append(_FESC)
                    i += 2
                else: break
            else:
                decoded.append(data[i])
                i += 1
        return bytes(decoded)

# ==================== INTEL HEX PARSER ====================
class IntelHex:
    @staticmethod
    def parse(text):
        mem = {}
        base_addr = 0
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line.startswith(':') or len(line) < 11: continue
            try:
                length = int(line[1:3], 16)
                addr = int(line[3:7], 16)
                rec_type = int(line[7:9], 16)
                data = bytes.fromhex(line[9:-2])
                if rec_type == 0x00:
                    for i in range(length):
                        mem[base_addr + addr + i] = data[i]
                elif rec_type == 0x02:
                    base_addr = int.from_bytes(data, 'big') << 4
                elif rec_type == 0x04:
                    base_addr = int.from_bytes(data, 'big') << 16
                elif rec_type == 0x01: break
            except ValueError: continue
        return mem

    @staticmethod
    def generate(mem_dict):
        lines = []
        sorted_addrs = sorted(mem_dict.keys())
        i = 0
        while i < len(sorted_addrs):
            addr = sorted_addrs[i]
            chunk_len = min(16, len(sorted_addrs) - i)
            actual_len = 0
            for j in range(chunk_len):
                if i + j < len(sorted_addrs) and sorted_addrs[i+j] == addr + j:
                    actual_len += 1
                else: break
            
            data = [mem_dict[addr + k] for k in range(actual_len)]
            hex_data = "".join(f"{b:02X}" for b in data)
            checksum = (actual_len + (addr >> 8) + (addr & 0xFF) + 0x00 + sum(data)) & 0xFF
            checksum = (~checksum + 1) & 0xFF
            lines.append(f":{actual_len:02X}{addr:04X}00{hex_data}{checksum:02X}")
            i += actual_len
        lines.append(":00000001FF")
        return "\n".join(lines)

# ==================== I8080 DISASSEMBLER ====================
class I8080Disassembler:
    REGS = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
    ALUS = ['ADD', 'ADC', 'SUB', 'SBB', 'ANA', 'XRA', 'ORA', 'CMP']
    RP = ['B', 'D', 'H', 'SP']
    RP_PUSH = ['B', 'D', 'H', 'PSW']
    CC = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']

    def __init__(self):
        self.table = self._generate_table()
        
    def _generate_table(self):
        t = {}
        for op in [0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xDD, 0xED, 0xFD]:
            t[op] = (1, "NOP*")
        t[0xD9] = (1, "RET*")
        t[0xCB] = (1, "CALL*")
        
        t[0x00] = (1, "NOP"); t[0x76] = (1, "HLT")
        
        # LXI: 0x01, 0x11, 0x21, 0x31
        for i in range(4): t[0x01 + i*16] = (3, f"LXI {self.RP[i]},{{1:02X}}{{0:02X}}h")
        
        # DAD: 0x09, 0x19, 0x29, 0x39 ← ДОБАВЛЕНО
        for i in range(4): t[0x09 + i*16] = (1, f"DAD {self.RP[i]}")
        
        # INX: 0x03, 0x13, 0x23, 0x33
        for i in range(4): t[0x03 + i*16] = (1, f"INX {self.RP[i]}")
        
        # DCX: 0x0B, 0x1B, 0x2B, 0x3B
        for i in range(4): t[0x0B + i*16] = (1, f"DCX {self.RP[i]}")
        
        # INR: 0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C
        for i in range(8): t[0x04 + i*8] = (1, f"INR {self.REGS[i]}")
        
        # DCR: 0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D
        for i in range(8): t[0x05 + i*8] = (1, f"DCR {self.REGS[i]}")
        
        # MVI: 0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E
        for i in range(8): t[0x06 + i*8] = (2, f"MVI {self.REGS[i]},{{0:02X}}h")
        
        t[0x02] = (1, "STAX B"); t[0x12] = (1, "STAX D")
        t[0x0A] = (1, "LDAX B"); t[0x1A] = (1, "LDAX D")
        t[0x22] = (3, "SHLD {1:02X}{0:02X}h"); t[0x2A] = (3, "LHLD {1:02X}{0:02X}h")
        t[0x32] = (3, "STA {1:02X}{0:02X}h"); t[0x3A] = (3, "LDA {1:02X}{0:02X}h")
        t[0x07] = (1, "RLC"); t[0x0F] = (1, "RRC"); t[0x17] = (1, "RAL"); t[0x1F] = (1, "RAR")
        t[0x27] = (1, "DAA"); t[0x2F] = (1, "CMA"); t[0x37] = (1, "STC"); t[0x3F] = (1, "CMC")
        t[0xE3] = (1, "XTHL"); t[0xE9] = (1, "PCHL"); t[0xF9] = (1, "SPHL")
        t[0xEB] = (1, "XCHG"); t[0xF3] = (1, "DI"); t[0xFB] = (1, "EI")
        t[0xDB] = (2, "IN {0:02X}h"); t[0xD3] = (2, "OUT {0:02X}h")
        
        for i in range(0x40, 0x80):
            if i not in t:
                dst = (i >> 3) & 7; src = i & 7
                t[i] = (1, f"MOV {self.REGS[dst]},{self.REGS[src]}")
                
        for i in range(0x80, 0xC0):
            alu = (i >> 3) & 7; src = i & 7
            t[i] = (1, f"{self.ALUS[alu]} {self.REGS[src]}")
            
        for i in range(8):
            t[0xC0 + i*8] = (1, f"R{self.CC[i]}")
            t[0xC2 + i*8] = (3, f"J{self.CC[i]} {{1:02X}}{{0:02X}}h")
            t[0xC4 + i*8] = (3, f"C{self.CC[i]} {{1:02X}}{{0:02X}}h")
            
        t[0xC3] = (3, "JMP {1:02X}{0:02X}h")
        t[0xCD] = (3, "CALL {1:02X}{0:02X}h")
        t[0xC9] = (1, "RET")
        
        for i in range(4):
            t[0xC1 + i*16] = (1, f"POP {self.RP_PUSH[i]}")
            t[0xC5 + i*16] = (1, f"PUSH {self.RP_PUSH[i]}")
            
        for i in range(8):
            t[0xC6 + i*8] = (2, f"{self.ALUS[i]} {{0:02X}}h")
            
        t[0xC7] = (1, "RST 0"); t[0xCF] = (1, "RST 1"); t[0xD7] = (1, "RST 2")
        t[0xDF] = (1, "RST 3"); t[0xE7] = (1, "RST 4"); t[0xEF] = (1, "RST 5")
        t[0xF7] = (1, "RST 6"); t[0xFF] = (1, "RST 7")
        return t

    def get_target(self, op, args):
        if op in [0xC3, 0xCD] or \
           op in [0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA] or \
           op in [0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC]:
            if len(args) >= 2:
                return (args[1] << 8) | args[0]
        elif op in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]:
            return ((op - 0xC7) // 8) * 8
        return None

    def get_mnemonic(self, byte_val):
        """Возвращает мнемонику для одного байта (для подсказок)"""
        if byte_val in self.table:
            size, fmt = self.table[byte_val]
            # Извлекаем мнемонику из формата (первое слово)
            parts = fmt.split()
            if parts:
                mnemonic = parts[0]
                # Для команд с аргументами показываем только мнемонику
                if "{" in fmt:
                    return f"{mnemonic} ..."
                return mnemonic
        return f"DB {byte_val:02X}h"

    def disassemble(self, mem_dict, start_addr, length):
        lines = []
        i = 0
        while i < length:
            addr = start_addr + i
            if addr not in mem_dict:
                i += 1; continue
            op = mem_dict[addr]
            if op not in self.table:
                lines.append((addr, 1, f"DB {op:02X}h", "*", None))
                i += 1; continue
            
            size, fmt = self.table[op]
            args = [mem_dict.get(addr+1+k, 0) for k in range(size-1)]
            try:
                asm = fmt.format(*args) if args else fmt
            except (ValueError, IndexError, KeyError):
                asm = fmt
                
            undoc = "*" if "NOP*" in asm or "RET*" in asm or "CALL*" in asm else ""
            target = self.get_target(op, args)
            
            lines.append((addr, size, asm, undoc, target))
            i += size
        return lines

# ==================== КАСТОМНЫЙ ВИДЖЕТ ДИЗАССЕМБЛЕРА СО СТРЕЛКАМИ ====================
class DisasmView(QWidget):
    toggleBreakpoint = Signal(int)  # Сигнал для установки/удаления breakpoint
    cursorChanged = Signal(int)             # Одинарный клик по строке
    runToCursorRequested = Signal(int)      # Контекстное меню: Run to Cursor
    runFromHereRequested = Signal(int)      # Контекстное меню: Run from Here
    jumpToCursorRequested = Signal(int)     # Контекстное меню: Jump to Cursor
    setConditionalBreakpointRequested = Signal(int)  # ИТЕРАЦИЯ C
    
    def __init__(self, mem_data, parent=None):
        super().__init__(parent)
        self.lines = []
        self.mem_data = mem_data
        self.line_height = 22
        self.addr_to_index = {}
        self.font_size = 10
        self.setFont(QFont("Consolas", self.font_size))
        self.setMinimumWidth(700)
        self.arrow_margin = 30
        self.is_dark_theme = False
        self.setup_colors()
        self.highlight_addr = None  # Адрес для подсветки (PC эмулятора)
        
        # === ИТЕРАЦИЯ B: Интерактивный режим (курсор + контекстное меню) ===
        self.interactive = False       # По умолчанию выключено
        self.cursor_addr = None        # Адрес курсора Run to Cursor
        
        self.breakpoints = set()  # Точки останова для отрисовки
        self.bp_conditions = {}  # ← ИТЕРАЦИЯ C: условия для отрисовки
        
        self.lang = "en"
        
    def set_bp_conditions(self, conditions):
        """Установить условия BP для отрисовки"""
        self.bp_conditions = conditions
        self.update()
        
    def set_highlight(self, addr):
        """Установить подсветку строки (PC эмулятора)"""
        self.highlight_addr = addr
        self.update()
        
    def setup_colors(self):
        """Настраивает цвета в зависимости от темы"""
        if self.is_dark_theme:
            # Тёмная тема
            self.colors = {
                "bg": QColor("#1e1e1e"),
                "addr": QColor("#858585"),
                "bytes": QColor("#6a6a6a"),
                "jump": QColor("#569cd6"),      # Синий
                "memory": QColor("#6bcf7f"),    # Зелёный
                "io": QColor("#c586c0"),        # Фиолетовый
                "control": QColor("#858585"),   # Серый
                "register": QColor("#ce9178"),  # Оранжевый
                "alu": QColor("#dcdcaa"),       # Жёлтый
                "stack": QColor("#4ec9b0"),     # Бирюзовый
                "undoc": QColor("#ff6b6b"),     # Красный
                "comment": QColor("#569cd6"),   # Голубой
                "text": QColor("#d4d4d4"),      # Основной текст
            }
        else:
            # Светлая тема (яркие, контрастные цвета на белом фоне)
            self.colors = {
                "bg": QColor("#ffffff"),        # Белый фон
                "addr": QColor("#808080"),      # Серый
                "bytes": QColor("#666666"),     # Тёмно-серый
                "jump": QColor("#0055cc"),      # Тёмно-синий
                "memory": QColor("#007700"),    # Тёмно-зелёный
                "io": QColor("#8800aa"),        # Фиолетовый
                "control": QColor("#666666"),   # Серый
                "register": QColor("#cc5500"),  # Тёмно-оранжевый
                "alu": QColor("#886600"),       # Тёмно-жёлтый
                "stack": QColor("#008888"),     # Тёмно-бирюзовый
                "undoc": QColor("#cc0000"),     # Красный
                "comment": QColor("#0055cc"),   # Голубой
                "text": QColor("#000000"),      # Чёрный текст
            }
        
    def set_theme(self, is_dark):
        """Устанавливает тему"""
        self.is_dark_theme = is_dark
        self.setup_colors()
        self.update()
        
    def set_lines(self, lines):
        self.lines = lines
        self.addr_to_index = {line[0]: i for i, line in enumerate(lines)}
        self.setFixedHeight(len(lines) * self.line_height + 10)
        self.repaint()
        if self.parent():
            self.parent().update()
            
    def get_instruction_color(self, asm):
        """Возвращает цвет для команды в зависимости от её типа"""
        parts = asm.split()
        if not parts:
            return self.colors["text"]
            
        mnemonic = parts[0].upper()
        
        # Недокументированные команды
        if asm.endswith("*"):
            return self.colors["undoc"]
        
        # Переходы: JMP, CALL, Jcc, Ccc, RST
        if mnemonic in ["JMP", "CALL", "RST"]:
            return self.colors["jump"]
        if len(mnemonic) > 1:
            suffix = mnemonic[1:]
            if mnemonic[0] == 'J' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
            if mnemonic[0] == 'C' and suffix in ["NZ", "Z", "NC", "C", "PO", "PE", "P", "M"]:
                return self.colors["jump"]
        
        # Память
        if mnemonic in ["LDA", "STA", "LHLD", "SHLD", "LDAX", "STAX", "XCHG", "XTHL"]:
            return self.colors["memory"]
        if mnemonic == "MOV" and len(parts) > 1 and "M" in parts[1]:
            return self.colors["memory"]
        
        # Ввод-вывод
        if mnemonic in ["IN", "OUT"]:
            return self.colors["io"]
        
        # Управление
        if mnemonic in ["NOP", "HLT", "DI", "EI", "RET", "PCHL", "SPHL"]:
            return self.colors["control"]
        
        # Регистры и данные
        if mnemonic in ["MVI", "LXI", "INR", "DCR", "MOV", "INX", "DCX"]:
            return self.colors["register"]
        
        # Арифметика и логика (включая DAD)
        if mnemonic in ["ADD", "ADC", "SUB", "SBB", "ANA", "XRA", "ORA", "CMP",
                        "RLC", "RRC", "RAL", "RAR", "DAA", "CMA", "STC", "CMC",
                        "ADI", "ACI", "SUI", "SBI", "ANI", "XRI", "ORI", "CPI",
                        "DAD"]:
            return self.colors["alu"]
        
        # Стек
        if mnemonic in ["PUSH", "POP"]:
            return self.colors["stack"]
        
        return self.colors["text"]
        
    def wheelEvent(self, event):
        """Ctrl + колесо мыши для изменения размера шрифта"""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(self.font_size + 1, 36)
            else:
                self.font_size = max(self.font_size - 1, 8)
                
            self.setFont(QFont("Consolas", self.font_size))
            self.line_height = self.font_size + 12
            self.setFixedHeight(len(self.lines) * self.line_height + 10)
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font())
        
        # Фон (белый для светлой темы)
        painter.fillRect(self.rect(), self.colors["bg"])
        
        # Получаем ширину символа для выравнивания
        font_metrics = painter.fontMetrics()
        char_width = font_metrics.averageCharWidth()
        
        # Фиксированные позиции колонок
        addr_x = self.arrow_margin + 10
        bytes_x = addr_x + 6 * char_width
        asm_x = bytes_x + 14 * char_width
        
        # Рисуем строки
        for i, (addr, size, asm, undoc, target) in enumerate(self.lines):
            y = i * self.line_height + self.line_height // 2 + 5
            
            # === ИТЕРАЦИЯ B: Отрисовка курсора (зелёная стрелка ▷) ===
            if self.interactive and self.cursor_addr is not None and addr == self.cursor_addr:
                # Зелёная стрелка слева от адреса
                painter.setPen(QColor("#4CAF50"))  # Зелёный
                cursor_font = QFont("Consolas", 10, QFont.Bold)
                painter.setFont(cursor_font)
                painter.drawText(5, y, "▷")
                
                # Лёгкая зелёная подсветка строки (если нет PC-подсветки)
                if self.highlight_addr != addr:
                    cursor_rect = QRect(
                        self.arrow_margin + 5,
                        i * self.line_height + 2,
                        self.width() - self.arrow_margin - 10,
                        self.line_height - 4
                    )
                    painter.fillRect(cursor_rect, QColor("#E8F5E9"))  # Бледно-зелёный
                   
            # === Подсветка текущей инструкции (PC эмулятора) ===
            if self.highlight_addr is not None and addr == self.highlight_addr:
                # Жёлтый фон для текущей инструкции
                highlight_rect = QRect(
                    self.arrow_margin + 5,
                    i * self.line_height + 2,
                    self.width() - self.arrow_margin - 10,
                    self.line_height - 4
                )
                painter.fillRect(highlight_rect, QColor("#fff3cd"))  # Светло-жёлтый
                
                # Стрелка слева
                painter.setPen(QColor("#ff9800"))
                painter.drawText(5, y, "►")
                
            # === Точки останова (красные/оранжевые кружки) ===
            if addr in self.breakpoints:
                bp_x = self.arrow_margin + 2
                bp_y = i * self.line_height + self.line_height // 2
                # Проверяем, условная ли это BP
                is_conditional = (
                    hasattr(self, 'bp_conditions') and 
                    addr in self.bp_conditions and 
                    self.bp_conditions[addr]
                )
                if is_conditional:
                    painter.setBrush(QColor("#ff9800"))  # Оранжевый для условных
                else:
                    painter.setBrush(QColor("#f44336"))  # Красный для обычных
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(bp_x - 4, bp_y - 4, 8, 8)
				
            # Адрес
            painter.setPen(self.colors["addr"])
            painter.drawText(addr_x, y, f"{addr:04X}")
            
            # Байты
            bytes_str = " ".join(f"{self.mem_data.get(addr+k, 0):02X}" for k in range(size))
            painter.setPen(self.colors["bytes"])
            painter.drawText(bytes_x, y, bytes_str)
            
            # Команда
            asm_text = f"{asm} {undoc}".strip()
            color = self.get_instruction_color(asm_text)
            painter.setPen(color)
            painter.drawText(asm_x, y, asm_text)
            
            # Комментарий перехода
            if target is not None:
                comment = f"; -> {target:04X}h"
                comment_x = asm_x + len(asm_text) * char_width + 3 * char_width
                painter.setPen(self.colors["comment"])
                painter.drawText(comment_x, y, comment)
                
        # Рисуем стрелки переходов
        self.draw_arrows(painter)
        
    def draw_arrows(self, painter):
        arrow_x_start = 5
        arrow_colors = [QColor("#ff6b6b"), QColor("#4ecdc4"), QColor("#ffe66d"), 
                        QColor("#a8e6cf"), QColor("#ffd93d"), QColor("#6bcf7f")]
        color_idx = 0
        
        for i, (addr, size, asm, undoc, target) in enumerate(self.lines):
            if target is not None and target in self.addr_to_index:
                target_idx = self.addr_to_index[target]
                y1 = i * self.line_height + self.line_height // 2 + 5
                y2 = target_idx * self.line_height + self.line_height // 2 + 5
                
                color = arrow_colors[color_idx % len(arrow_colors)]
                color_idx += 1
                
                pen = QPen(color, 2)
                painter.setPen(pen)
                
                x_offset = arrow_x_start + (color_idx % 5) * 4
                
                painter.drawLine(x_offset, y1, x_offset, y2)
                painter.drawLine(x_offset, y2, self.arrow_margin + 5, y2)
                
                if y2 > y1:
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 - 4)
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 + 4)
                else:
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 - 4)
                    painter.drawLine(self.arrow_margin + 5, y2, self.arrow_margin, y2 + 4)
                    
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x_offset - 2, y1 - 2, 4, 4)
                painter.setPen(pen)
				
    def mouseDoubleClickEvent(self, event):
        """Двойной ЛЕВЫЙ клик — установить/удалить точку останова"""
        # === Обрабатываем только левую кнопку ===
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        
        y = event.position().y()
        line_idx = int((y - 5) / self.line_height)
        
        if 0 <= line_idx < len(self.lines):
            addr = self.lines[line_idx][0]
            self.toggleBreakpoint.emit(addr)
        
        super().mouseDoubleClickEvent(event)
        
    def set_breakpoints(self, breakpoints):
        """Установить точки останова для отрисовки"""
        self.breakpoints = breakpoints
        self.update()
        
    def set_interactive(self, enabled):
        """Включает/выключает интерактивный режим (курсор + меню)"""
        self.interactive = enabled
        
    def set_cursor(self, addr):
        """Установить курсор Run to Cursor"""
        self.cursor_addr = addr
        self.update()
        
    def get_line_addr_at(self, y):
        """Возвращает адрес строки по Y-координате мыши"""
        if not hasattr(self, 'lines') or not self.lines:
            return None
        line_idx = int((y - 5) / self.line_height)
        if 0 <= line_idx < len(self.lines):
            return self.lines[line_idx][0]
        return None
        
    def mousePressEvent(self, event):
        """Одинарный ЛЕВЫЙ клик — установка курсора"""
        if self.interactive and event.button() == Qt.LeftButton:
            addr = self.get_line_addr_at(event.position().y())
            if addr is not None:
                self.cursor_addr = addr
                self.cursorChanged.emit(addr)
                self.update()
            # НЕ вызываем super() для левого клика в интерактивном режиме,
            # чтобы избежать конфликта с mouseDoubleClickEvent
            event.accept()
            return
        super().mousePressEvent(event)
        
    def contextMenuEvent(self, event):
        """Контекстное меню (только в интерактивном режиме)"""
        if not self.interactive:
            super().contextMenuEvent(event)
            return
        addr = self.get_line_addr_at(event.pos().y())
        if addr is None:
            super().contextMenuEvent(event)
            return
        self.cursor_addr = addr
        self.update()
        L = LANGS.get(self.lang, LANGS["en"])
        menu = QMenu(self)
        act_run_to = menu.addAction(f"⥗ {L.get('ctx_run_to', 'Run to Cursor')} (0x{addr:04X})  [Ctrl+F10]")
        act_run_from = menu.addAction(f"⥟ {L.get('ctx_run_from', 'Run from Here')} (0x{addr:04X})")
        act_jump = menu.addAction(f"⤼ {L.get('ctx_jump', 'Jump to Cursor')} (0x{addr:04X})")
        menu.addSeparator()
        act_toggle_bp = menu.addAction(f"● {L.get('ctx_toggle_bp', 'Toggle Breakpoint')} (0x{addr:04X})")
        act_cond_bp = menu.addAction(f"◉ {L.get('ctx_cond_bp', 'Set Conditional BP...')} (0x{addr:04X})")
        selected = menu.exec(event.globalPos())
        if selected == act_run_to:
            self.runToCursorRequested.emit(addr)
        elif selected == act_run_from:
            self.runFromHereRequested.emit(addr)
        elif selected == act_jump:
            self.jumpToCursorRequested.emit(addr)
        elif selected == act_toggle_bp:
            self.toggleBreakpoint.emit(addr)
        elif selected == act_cond_bp:
            self.setConditionalBreakpointRequested.emit(addr)

# ==================== МОДЕЛЬ ДАННЫХ HEX-РЕДАКТОРА ====================
class HexModel(QAbstractTableModel):
    dataEdited = Signal()
    
    def __init__(self, mem_dict=None):
        super().__init__()
        self.mem = mem_dict if mem_dict is not None else {}
        self.min_addr = 0
        self.max_addr = 0
        self.lang = "en"  # ← Добавлено для локализации заголовков
        self.update_range()

    def update_data(self, new_mem):
        self.mem.update(new_mem)
        self.update_range()
        self.layoutChanged.emit()

    def update_range(self):
        if self.mem:
            self.min_addr = min(self.mem.keys())
            self.max_addr = max(self.mem.keys())
            self.min_addr &= ~0x0F
        else:
            self.min_addr = 0; self.max_addr = 0

    def rowCount(self, parent=QModelIndex()):
        if not self.mem: return 0
        return ((self.max_addr - self.min_addr) >> 4) + 1

    def columnCount(self, parent=QModelIndex()):
        return 18

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Заголовки колонок"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return LANGS.get(self.lang, LANGS['en']).get('addr_column', 'Addr')
            elif 1 <= section <= 16:
                return f"{section - 1:X}"  # 0, 1, 2, ... F
            elif section == 17:
                return LANGS.get(self.lang, LANGS['en']).get('text_column', 'Text')
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = index.row(); col = index.column()
        addr = self.min_addr + (row * 16)
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0: return f"{addr:04X}"
            elif 1 <= col <= 16:
                byte_addr = addr + col - 1
                if byte_addr in self.mem: return f"{self.mem[byte_addr]:02X}"
            elif col == 17:
                ascii_str = ""
                for c in range(16):
                    b = self.mem.get(addr + c, -1)
                    if 32 <= b <= 126: ascii_str += chr(b)
                    else: ascii_str += "."
                return ascii_str
        elif role == Qt.FontRole:
            return QFont("Consolas", 10)
        return None

    def flags(self, index):
        flags = super().flags(index)
        if 1 <= index.column() <= 16:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and 1 <= index.column() <= 16:
            try:
                val = int(value, 16)
                if 0 <= val <= 255:
                    addr = self.min_addr + (index.row() * 16) + index.column() - 1
                    old_val = self.mem.get(addr, 0)
                    if old_val != val:  # Только если значение изменилось
                        self.mem[addr] = val
                        self.last_edit = (addr, old_val, val)  # ← Сохраняем для undo
                        self.dataChanged.emit(index, index, [Qt.DisplayRole])
                        self.dataEdited.emit()
                    return True
            except ValueError: pass
        return False

# ==================== КАСТОМНАЯ ТАБЛИЦА HEX-РЕДАКТОРА С ПОДСКАЗКАМИ ====================
class HexTableView(QTableView):
    editOperation = Signal(list)  # ← Добавлено: [(addr, old_val, new_val), ...]
    statusUpdate = Signal(str, str, str)
    gotoAddress = Signal(int)
    
    def __init__(self, disassembler, mem_data, parent=None):
        super().__init__(parent)
        self.disassembler = disassembler
        self.mem_data = mem_data
        self.setMouseTracking(True)
    
    def tr(self, key):
        if self.parent() and hasattr(self.parent(), 'tr'):
            return self.parent().tr(key)
        return key
    
    def event(self, event):
        if event.type() == QEvent.ToolTip:
            viewport_pos = self.viewport().mapFrom(self, event.pos())
            index = self.indexAt(viewport_pos)
            if index.isValid() and 1 <= index.column() <= 16:
                row = index.row()
                col = index.column()
                model = self.model()
                if model and hasattr(model, 'min_addr'):
                    addr = model.min_addr + (row * 16) + col - 1
                    if addr in self.mem_data:
                        byte_val = self.mem_data[addr]
                        mnemonic = self.disassembler.get_mnemonic(byte_val)
                        QToolTip.showText(event.globalPos(), f"0x{byte_val:02X}: {mnemonic}", self)
                        return True
                        
        elif event.type() == QEvent.HoverMove:
            viewport_pos = self.viewport().mapFrom(self, event.pos())
            index = self.indexAt(viewport_pos)
            if index.isValid() and 1 <= index.column() <= 16:
                row = index.row()
                col = index.column()
                model = self.model()
                if model and hasattr(model, 'min_addr'):
                    addr = model.min_addr + (row * 16) + col - 1
                    if addr in self.mem_data:
                        byte_val = self.mem_data[addr]
                        mnemonic = self.disassembler.get_mnemonic(byte_val)
                        self.statusUpdate.emit(f"0x{addr:04X}", f"0x{byte_val:02X}", mnemonic)
                        
        return super().event(event)
        
    def contextMenuEvent(self, event):
        """Контекстное меню при правом клике"""
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
            
        menu = QMenu(self)
        
        # Определяем адрес ячейки
        addr = None
        if 1 <= index.column() <= 16:
            model = self.model()
            if model and hasattr(model, 'min_addr'):
                row = index.row()
                col = index.column()
                addr = model.min_addr + (row * 16) + col - 1
        
        if addr is not None and addr in self.mem_data:
            byte_val = self.mem_data[addr]
            
            # Копировать адрес
            act_copy_addr = menu.addAction(f"{self.tr('ctx_copy_addr')} (0x{addr:04X})")
            act_copy_addr.triggered.connect(lambda: self.copy_to_clipboard(f"{addr:04X}"))
            
            # Копировать значение
            act_copy_val = menu.addAction(f"{self.tr('ctx_copy_val')} (0x{byte_val:02X})")
            act_copy_val.triggered.connect(lambda: self.copy_to_clipboard(f"{byte_val:02X}"))
            
            menu.addSeparator()
            
            # Инвертировать байт
            act_invert = menu.addAction(f"{self.tr('ctx_invert')} (0x{~byte_val & 0xFF:02X})")
            act_invert.triggered.connect(lambda: self.invert_byte(addr))
            
            # Заполнить диапазон
            act_fill = menu.addAction(self.tr("ctx_fill"))
            act_fill.triggered.connect(lambda: self.fill_range(addr))
            
            menu.addSeparator()
            
            # Дизассемблировать отсюда
            act_disasm = menu.addAction(f"{self.tr('ctx_disasm')}0x{addr:04X}")
            act_disasm.triggered.connect(lambda: self.disasm_from(addr))
            
            # Перейти к адресу
            act_goto = menu.addAction(self.tr("ctx_goto"))
            act_goto.triggered.connect(lambda: self.goto_dialog())
            
        menu.exec(event.globalPos())
        
    def copy_to_clipboard(self, text):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        
    def invert_byte(self, addr):
        """Инвертирует байт по адресу"""
        if addr in self.mem_data:
            old_val = self.mem_data[addr]
            new_val = ~old_val & 0xFF
            self.mem_data[addr] = new_val
            self.editOperation.emit([(addr, old_val, new_val)])  # ← Для undo
            model = self.model()
            if model:
                model.update_data({addr: new_val})
                
    def fill_range(self, start_addr):
        """Заполняет диапазон значением"""
        text, ok = QInputDialog.getText(self, self.tr("fill_title"), self.tr("fill_value"))
        if not ok: return
        try:
            val = int(text, 16)
        except ValueError:
            return
            
        size, ok2 = QInputDialog.getInt(self, self.tr("fill_title"), self.tr("fill_size"), 16, 1, 4096)
        if not ok2: return
        
        changes = []
        for i in range(size):
            addr = start_addr + i
            old_val = self.mem_data.get(addr, 0)
            self.mem_data[addr] = val
            changes.append((addr, old_val, val))
            
        self.editOperation.emit(changes)  # ← Для undo
        model = self.model()
        if model:
            model.update_data({start_addr + i: val for i in range(size)})
            
    def disasm_from(self, addr):
        """Дизассемблировать от указанного адреса"""
        self.parent().parent().parent().parent().disasm_from_address(addr)
        
    def goto_dialog(self):
        """Диалог перехода к адресу"""
        text, ok = QInputDialog.getText(self, self.tr("goto_title"), self.tr("bp_addr"))
        if not ok: return
        try:
            addr = int(text, 16)
            self.gotoAddress.emit(addr)
        except ValueError:
            pass

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

class AutomationAPI:
    """API для автоматизации работы с программой из скриптов
    
    Разделение методов:
    - read_mem, write_mem, ... — работа с ЛОКАЛЬНЫМ образом
    - dev_read_mem, dev_write_mem, ... — работа с УСТРОЙСТВОМ
    - download, upload — синхронизация между устройством и локальным образом
    """
    
    def __init__(self, main_window):
        self.mw = main_window
        self.system = main_window.system
        
    # =============================================
    # ПРОВЕРКИ СОСТОЯНИЯ
    # =============================================
    def _check_connected(self):
        """Проверяет подключение к устройству"""
        if not self.mw.is_connected:
            raise RuntimeError("Device not connected!")
            
    def _check_bus(self):
        """Проверяет подключение и захват шины"""
        self._check_connected()
        if not self.mw.bus_active:
            raise RuntimeError("Bus not active! Call hold_bus() and wait_bus() first.")
        return True
        
    # =============================================
    # УПРАВЛЕНИЕ ШИНОЙ
    # =============================================
    def hold_bus(self):
        """Захватить шину. Возвращает True, если команда отправлена."""
        self._check_connected()
        if self.mw.bus_active:
            return True
        self.mw.send_command(bytes([CMD_HOLD]))
        return True
        
    def unhold_bus(self):
        """Освободить шину. Возвращает True, если команда отправлена."""
        self._check_connected()
        if not self.mw.bus_active:
            return True
        self.mw.send_command(bytes([CMD_UNHOLD]))
        return True
        
    def wait_bus(self, timeout=5.0):
        """Ждёт захвата шины. Возвращает True, если шина захвачена."""
        start = time.time()
        while time.time() - start < timeout:
            if self.mw.bus_active:
                return True
            time.sleep(0.05)
            QApplication.processEvents()
        return False
        
    def wait_unhold(self, timeout=5.0):
        """Ждёт освобождения шины. Возвращает True, если шина освобождена."""
        start = time.time()
        while time.time() - start < timeout:
            if not self.mw.bus_active:
                return True
            time.sleep(0.05)
            QApplication.processEvents()
        return False
        
    # =============================================
    # ЛОКАЛЬНАЯ ПАМЯТЬ (не требует подключения)
    # =============================================
    def read_mem(self, addr):
        """Прочитать байт из локального образа"""
        return self.mw.mem_data.get(addr, None)
        
    def write_mem(self, addr, val):
        """Записать байт в локальный образ"""
        self.mw.mem_data[addr] = val & 0xFF
        self.mw.hex_model.update_data({addr: val & 0xFF})
        # Обновляем окно эмулятора ===
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        
    def read_block(self, addr, size):
        """Прочитать блок из локального образа"""
        return [self.mw.mem_data.get(addr + i, None) for i in range(size)]
        
    def write_block(self, addr, data):
        """Записать блок в локальный образ"""
        changes = {addr + i: data[i] & 0xFF for i in range(len(data))}
        self.mw.mem_data.update(changes)
        self.mw.hex_model.update_data(changes)
        # Обновляем окно эмулятора ===
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        
    def fill_mem(self, addr, size, val):
        """Заполнить диапазон в локальном образе"""
        changes = {addr + i: val & 0xFF for i in range(size)}
        self.mw.mem_data.update(changes)
        self.mw.hex_model.update_data(changes)
        # Обновляем окно эмулятора ===
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        
    # =============================================
    # ПАМЯТЬ УСТРОЙСТВА (требует шину)
    # =============================================
    def dev_read_mem(self, addr):
        """Прочитать байт из памяти УСТРОЙСТВА"""
        self._check_bus()
        payload = bytes([CMD_MEM_READ_BYTE, (addr >> 8) & 0xFF, addr & 0xFF])
        resp = self.mw.sync_send_and_recv(payload)
        if resp and resp[0] == ACK_MEM_READ_BYTE and len(resp) >= 4:
            return resp[3]
        return None
        
    def dev_write_mem(self, addr, val):
        """Записать байт в память УСТРОЙСТВА"""
        self._check_bus()
        payload = bytes([CMD_MEM_WRITE_BYTE, (addr >> 8) & 0xFF, addr & 0xFF, val & 0xFF])
        resp = self.mw.sync_send_and_recv(payload)
        return resp is not None and resp[0] == ACK_MEM_WRITE_BYTE
        
    def dev_read_io(self, port):
        """Прочитать из IO-порта УСТРОЙСТВА"""
        self._check_bus()
        payload = bytes([CMD_IO_READ_BYTE, (port >> 8) & 0xFF, port & 0xFF])
        resp = self.mw.sync_send_and_recv(payload)
        if resp and resp[0] == ACK_IO_READ_BYTE and len(resp) >= 4:
            return resp[3]
        return None
        
    def dev_write_io(self, port, val):
        """Записать в IO-порт УСТРОЙСТВА"""
        self._check_bus()
        payload = bytes([CMD_IO_WRITE_BYTE, (port >> 8) & 0xFF, port & 0xFF, val & 0xFF])
        resp = self.mw.sync_send_and_recv(payload)
        return resp is not None and resp[0] == ACK_IO_WRITE_BYTE
        
    def dev_write_eeprom_byte(self, addr, val):
        """Записать байт в EEPROM устройства"""
        self._check_bus()
        payload = bytes([CMD_EEPROM_WRITE_BYTE, (addr >> 8) & 0xFF, addr & 0xFF, val & 0xFF])
        resp = self.mw.sync_send_and_recv(payload)
        return resp is not None and resp[0] == ACK_EEPROM_WRITE_BYTE

    def dev_write_eeprom_block(self, addr, data):
        """Записать блок в EEPROM устройства"""
        self._check_bus()
        if len(data) > self.mw.max_block_size:
            raise ValueError(f"Block size {len(data)} exceeds max {self.mw.max_block_size}")
        cmd = bytearray([CMD_EEPROM_WRITE_BLOCK, len(data) & 0xFF,
                         (addr >> 8) & 0xFF, addr & 0xFF])
        cmd.extend(data)
        resp = self.mw.sync_send_and_recv(bytes(cmd))
        return resp is not None and resp[0] == ACK_EEPROM_WRITE_BLOCK
        
    # =============================================
    # СИНХРОНИЗАЦИЯ (устройство ↔ локальный образ)
    # =============================================
    def download(self, addr, size):
        """Считать блок из УСТРОЙСТВА в локальный образ
        
        Возвращает список прочитанных байтов или None при ошибке.
        """
        self._check_bus()
        
        result = []
        remaining = size
        current_addr = addr
        
        while remaining > 0:
            chunk_size = min(remaining, self.mw.max_block_size)
            payload = bytes([CMD_MEM_READ_BLOCK, chunk_size & 0xFF, 
                           (current_addr >> 8) & 0xFF, current_addr & 0xFF])
            resp = self.mw.sync_send_and_recv(payload)
            
            if resp and resp[0] == ACK_MEM_READ_BLOCK:
                for i in range(resp[1]):
                    if 3 + i < len(resp):
                        val = resp[3 + i]
                        result.append(val)
                        self.mw.mem_data[current_addr + i] = val
            else:
                self.mw.log(f"Download error at 0x{current_addr:04X}")
                return None
                
            current_addr += chunk_size
            remaining -= chunk_size
            
        # Обновляем hex-редактор
        self.mw.hex_model.update_data(self.mw.mem_data)
        self.mw.update_range_label()
        if self.mw.auto_disasm_check.isChecked():
            self.mw.auto_disasm()
            
        return result
        
    def upload(self, addr, size):
        """Записать блок из локального образа в УСТРОЙСТВО
        
        Возвращает True при успехе.
        """
        self._check_bus()
        
        remaining = size
        current_addr = addr
        
        while remaining > 0:
            chunk_size = min(remaining, self.mw.max_block_size)
            chunk_data = [self.mw.mem_data.get(current_addr + i, 0xFF) for i in range(chunk_size)]
            
            cmd = bytearray([CMD_MEM_WRITE_BLOCK, chunk_size & 0xFF,
                           (current_addr >> 8) & 0xFF, current_addr & 0xFF])
            cmd.extend(chunk_data)
            
            resp = self.mw.sync_send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_MEM_WRITE_BLOCK:
                self.mw.log(f"Upload error at 0x{current_addr:04X}")
                return False
                
            current_addr += chunk_size
            remaining -= chunk_size
            
        return True
        
    def download_all(self, start=0x0000, end=0xFFFF):
        """Считать всю память устройства в локальный образ"""
        return self.download(start, end - start + 1)
        
    def upload_all(self):
        """Записать весь локальный образ в память устройства"""
        if not self.mw.mem_data:
            return False
        mn = min(self.mw.mem_data.keys())
        mx = max(self.mw.mem_data.keys())
        return self.upload(mn, mx - mn + 1)
        
    # =============================================
    # ФАЙЛЫ
    # =============================================
    def load_file(self, path, base_addr=0):
        """Загрузить файл прошивки в локальный образ"""
        loaded_mem = {}
        if path.endswith(".hex"):
            with open(path, "r") as f:
                loaded_mem = IntelHex.parse(f.read())
        else:
            with open(path, "rb") as f:
                data = f.read()
                for i, b in enumerate(data):
                    loaded_mem[base_addr + i] = b
                    
        self.mw.mem_data.update(loaded_mem)
        self.mw.hex_model.update_data(loaded_mem)
        self.mw.update_range_label()
        
        # === Устанавливаем PC на начало образа ===
        if hasattr(self.mw, 'emulator') and self.mw.emulator:
            self.mw.emulator.set_pc_to_memory_start()
            self.update_disasm_highlight()
		    
        return len(loaded_mem)
        
    def save_file(self, path):
        """Сохранить локальный образ в файл"""
        if not self.mw.mem_data:
            return False
        if path.endswith(".hex"):
            with open(path, "w") as f:
                f.write(IntelHex.generate(self.mw.mem_data))
        else:
            mn, mx = min(self.mw.mem_data.keys()), max(self.mw.mem_data.keys())
            with open(path, "wb") as f:
                for i in range(mn, mx + 1):
                    f.write(bytes([self.mw.mem_data.get(i, 0xFF)]))
        return True
        
    # =============================================
    # ДИЗАССЕМБЛЕР И ПОИСК (локально)
    # =============================================
    def disassemble(self, addr=None, length=None, show=False):
        """Дизассемблировать локальный образ.
        
        Args:
            addr: начальный адрес (по умолчанию — минимальный адрес в памяти)
            length: длина (по умолчанию — вся память)
            show: если True, обновляет окно дизассемблера в GUI
        
        Returns:
            Список строк дизассемблированного кода.
        """
        if not self.mw.mem_data:
            return []
            
        if addr is None:
            addr = min(self.mw.mem_data.keys())
        if length is None:
            length = max(self.mw.mem_data.keys()) - addr + 1
            
        # Дизассемблируем
        lines = self.mw.disassembler.disassemble(self.mw.mem_data, addr, length)
        result = []
        for line_addr, size, asm, undoc, target in lines:
            bytes_str = " ".join(f"{self.mw.mem_data.get(line_addr+k, 0):02X}" for k in range(size))
            result.append(f"{line_addr:04X}  {bytes_str:<12} {asm} {undoc}".strip())
        
        # Обновляем GUI, если запрошено
        if show:
            self.mw.disasm_start.setText(f"{addr:04X}")
            self.mw.disasm_len.setText(f"{length:X}")
            self.mw.disasm_view.set_lines(lines)
            self.mw.tabs.setCurrentWidget(self.mw.tab_disasm)
        
        return result
        
    def search(self, pattern, mode="hex"):
        """Поиск в локальном образе"""
        results = []
        if mode == "hex":
            try:
                pattern_bytes = bytes.fromhex(pattern.replace(" ", ""))
            except ValueError:
                return []
            for addr in sorted(self.mw.mem_data.keys()):
                match = True
                for i, b in enumerate(pattern_bytes):
                    if addr + i not in self.mw.mem_data or self.mw.mem_data[addr + i] != b:
                        match = False
                        break
                if match:
                    results.append(addr)
        elif mode == "ascii":
            pattern_bytes = pattern.encode('ascii')
            for addr in sorted(self.mw.mem_data.keys()):
                match = True
                for i, b in enumerate(pattern_bytes):
                    if addr + i not in self.mw.mem_data or self.mw.mem_data[addr + i] != b:
                        match = False
                        break
                if match:
                    results.append(addr)
        return results
        
    def refresh(self):
        """Принудительно обновить hex-редактор и дизассемблер в GUI"""
        self.mw.hex_model.layoutChanged.emit()
        self.mw.update_range_label()
        # Обновляем дизассемблер, если включено автодизассемблирование
        if self.mw.auto_disasm_check.isChecked() and self.mw.mem_data:
            self.mw.auto_disasm()
		
    # =============================================
    # УТИЛИТЫ
    # =============================================
    def log(self, msg):
        """Вывод в журнал программы"""
        self.mw.log(str(msg))
        
    def status(self):
        """Текущее состояние программы"""
        return {
            "connected": self.mw.is_connected,
            "bus_active": self.mw.bus_active,
            "mem_size": len(self.mw.mem_data),
            "max_block_size": self.mw.max_block_size,
        }
        
    def goto(self, addr):
        """Переход к адресу в hex-редакторе"""
        self.mw.goto_address(addr)
        
    # =============================================
    # ДОСТУП К ЭМУЛЯТОРУ ИЗ СКРИПТОВ
    # =============================================
    
    def emu_get_reg(self, reg):
        """Прочитать регистр эмулятора. reg: A,B,C,D,E,H,L,BC,DE,HL,SP,PC"""
        reg = reg.upper()
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        if reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
            return emu.get_reg(reg)
        elif reg in ['BC', 'DE', 'HL', 'SP', 'PC']:
            if reg == 'PC':
                return emu.pc
            elif reg == 'SP':
                return emu.sp
            return emu.get_reg_pair(reg)
        else:
            raise ValueError(f"Неизвестный регистр: {reg}")
    
    def emu_set_reg(self, reg, val):
        """Установить регистр эмулятора. reg: A,B,C,D,E,H,L,BC,DE,HL,SP,PC"""
        reg = reg.upper()
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        if reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
            emu.set_reg(reg, val & 0xFF)
        elif reg == 'BC': emu.set_reg_pair('BC', val)
        elif reg == 'DE': emu.set_reg_pair('DE', val)
        elif reg == 'HL': emu.set_reg_pair('HL', val)
        elif reg == 'SP': emu.sp = val & 0xFFFF
        elif reg == 'PC': emu.set_pc(val)
        else:
            raise ValueError(f"Неизвестный регистр: {reg}")
        # Обновляем UI
        if hasattr(self.mw, 'update_emulator_ui'):
            self.mw.update_emulator_ui()
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        return f"{reg} = 0x{val:X}"
    
    def emu_get_psw(self):
        """Прочитать слово состояния процессора (PSW: A + флаги)"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        flags = (int(emu.flag_s) << 7) | (int(emu.flag_z) << 6) | \
                (int(emu.flag_ac) << 4) | (int(emu.flag_p) << 2) | \
                (1 << 1) | int(emu.flag_cy)
        return (emu.a << 8) | flags
    
    def emu_set_psw(self, val):
        """Установить слово состояния процессора (PSW: A + флаги)"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        val &= 0xFFFF
        emu.a = (val >> 8) & 0xFF
        flags = val & 0xFF
        emu.flag_s = bool(flags & 0x80)
        emu.flag_z = bool(flags & 0x40)
        emu.flag_ac = bool(flags & 0x10)
        emu.flag_p = bool(flags & 0x04)
        emu.flag_cy = bool(flags & 0x01)
        if hasattr(self.mw, 'update_emulator_ui'):
            self.mw.update_emulator_ui()
        return f"PSW = 0x{val:04X}"
    
    def emu_get_flags(self):
        """Прочитать флаги процессора как словарь"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        return {
            'S': emu.flag_s, 'Z': emu.flag_z,
            'AC': emu.flag_ac, 'P': emu.flag_p, 'CY': emu.flag_cy
        }
    
    def emu_set_flag(self, flag, val):
        """Установить флаг процессора. flag: S,Z,AC,P,CY; val: True/False"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        emu = self.mw.emulator
        flag = flag.upper()
        val = bool(val)
        if flag == 'S': emu.flag_s = val
        elif flag == 'Z': emu.flag_z = val
        elif flag == 'AC': emu.flag_ac = val
        elif flag == 'P': emu.flag_p = val
        elif flag == 'CY': emu.flag_cy = val
        else:
            raise ValueError(f"Неизвестный флаг: {flag}")
        if hasattr(self.mw, 'update_emulator_ui'):
            self.mw.update_emulator_ui()
        return f"Флаг {flag} = {val}"
    
    def emu_reset(self):
        """Сброс эмулятора"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        self.mw.emulator.reset()
        if hasattr(self.mw, 'update_emulator_ui'):
            self.mw.update_emulator_ui()
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        return "Эмулятор сброшен"
    
    def emu_step(self):
        """Выполнить одну инструкцию эмулятора"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        self.mw.emulator.step()
        if hasattr(self.mw, 'update_emulator_ui'):
            self.mw.update_emulator_ui()
        if hasattr(self.mw, 'update_emu_disasm_view'):
            self.mw.update_emu_disasm_view()
        return f"PC = 0x{self.mw.emulator.pc:04X}"
    
    def emu_get_state(self):
        """Получить полное состояние эмулятора"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        return self.mw.emulator.get_state()
        
    # =============================================
    # ТРАССИРОВКА (ИТЕРАЦИЯ D)
    # =============================================
    def emu_trace_start(self):
        """Включить запись трассировки"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        self.mw.emulator.trace_start()
        return "Трассировка включена"
    
    def emu_trace_stop(self):
        """Выключить запись трассировки"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        self.mw.emulator.trace_stop()
        return "Трассировка выключена"
    
    def emu_trace_clear(self):
        """Очистить буфер трассировки"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        self.mw.emulator.trace_clear()
        return "Буфер трассировки очищен"
    
    def emu_trace_get(self, limit=None):
        """Получить записи трассировки"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        records = self.mw.emulator.trace_get(limit)
        result = []
        for rec in records:
            mnemonic = self.mw._get_trace_mnemonic(rec) if hasattr(self.mw, '_get_trace_mnemonic') else f"DB {rec['opcode']:02X}h"
            bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
            flags = rec["flags"]
            result.append({
                "seq": rec['seq'],
                "pc": f"{rec['pc']:04X}",
                "bytes": bytes_str,
                "mnemonic": mnemonic,
                "A": f"{rec['A']:02X}",
                "BC": f"{rec['BC']:04X}",
                "DE": f"{rec['DE']:04X}",
                "HL": f"{rec['HL']:04X}",
                "SP": f"{rec['SP']:04X}",
                "flags": {"S": flags[0], "Z": flags[1], "AC": flags[2], "P": flags[3], "CY": flags[4]},
                "cycles": rec['cycles'],
                "cycles_total": rec['cycles_total']
            })
        return result
    
    def emu_trace_export(self, path, format="txt"):
        """Экспорт трассировки в файл"""
        if not hasattr(self.mw, 'emulator'):
            raise RuntimeError("Эмулятор не инициализирован")
        records = self.mw.emulator.trace_get()
        if not records:
            return "Нет данных для экспорта"
        try:
            if format == "csv":
                self.mw._export_trace_csv(path, records)
            elif format == "json":
                self.mw._export_trace_json(path, records)
            else:
                self.mw._export_trace_txt(path, records)
            return f"Трассировка экспортирована в {path} ({len(records)} записей)"
        except Exception as e:
            raise RuntimeError(f"Ошибка экспорта: {e}")
		
# ==================== РАБОЧИЙ ПОТОК ====================
class BusWorker(QObject):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(object)
    
    def __init__(self, serial_port, task, params, lang="en", max_block_size=128):
        super().__init__()
        self.ser = serial_port
        self.task = task
        self.params = params
        self.is_running = True
        self.lang = lang
        self.max_block_size = max_block_size

    def stop(self):
        self.is_running = False

    def tr(self, key):
        return LANGS.get(self.lang, LANGS["en"]).get(key, key)

    def run(self):
        if self.task == "read_block":
            self.do_read_block()
        elif self.task == "test_mem":
            self.do_test_mem()
        elif self.task == "write_block":
            self.do_write_block()
        elif self.task == "run_io_sequence":
            self.do_run_io_sequence()
        elif self.task == "read_io_block":
            self.do_read_io_block()
        elif self.task == "write_io_block":
            self.do_write_io_block()

    def send_and_recv(self, payload, timeout=2.0):
        try:
            self.ser.write(SlipProtocol.encode(payload))
            self.ser.flush()
        except serial.SerialException as e:
            self.log.emit(f"{self.tr('err_write_port')} {e}")
            return None
            
        buffer = bytearray()
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running: return None
            try:
                if self.ser.in_waiting:
                    buffer.extend(self.ser.read(self.ser.in_waiting))
                    if _FEND in buffer:
                        # Пропускаем начальные FEND (маркеры начала пакета)
                        start_idx = 0
                        while start_idx < len(buffer) and buffer[start_idx] == _FEND:
                            start_idx += 1
                        if start_idx < len(buffer):
                            # Ищем конечный FEND после данных
                            try:
                                end_idx = buffer.index(_FEND, start_idx)
                                raw = buffer[start_idx:end_idx]
                                if raw:
                                    self.ser.reset_input_buffer()
                                    return SlipProtocol.decode(raw)
                            except ValueError:
                                pass  # Конечный FEND ещё не пришёл, ждём
            except serial.SerialException as e:
                self.log.emit(f"{self.tr('err_read_port')} {e}")
                return None
            time.sleep(0.01)
        return None

    def do_read_block(self):
        addr, size = self.params
        self.log.emit(f"{self.tr('read_block_msg')} 0x{addr:04X} ({size})")
        cmd = bytes([CMD_MEM_READ_BLOCK, size & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
        resp = self.send_and_recv(cmd)
        mem = {}
        if resp and resp[0] == ACK_MEM_READ_BLOCK:
            for i in range(resp[1]):
                if 3 + i < len(resp):
                    mem[addr + i] = resp[3 + i]
            self.log.emit(f"{self.tr('read_ok')} {len(mem)} {self.tr('bytes')}")
        else:
            self.log.emit(self.tr('read_err'))
        self.finished.emit(mem)

    def do_write_block(self):
        mem_dict, start_addr = self.params
        self.log.emit(f"{self.tr('write_block')} 0x{start_addr:04X}...")
        addrs = sorted(mem_dict.keys())
        written = 0
        for i in range(0, len(addrs), self.max_block_size):
            if not self.is_running: break
            chunk_addrs = addrs[i:i+self.max_block_size]
            chunk_data = [mem_dict[a] for a in chunk_addrs]
            c_addr = chunk_addrs[0]
            c_size = len(chunk_data)
            
            cmd = bytearray([CMD_MEM_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(chunk_data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_MEM_WRITE_BLOCK:
                self.log.emit(f"{self.tr('write_err')} 0x{c_addr:04X}")
                break
            written += c_size
            self.progress.emit(int((i + c_size) * 100 / len(addrs)))
        self.log.emit(f"{self.tr('write_done')} ({written} {self.tr('bytes')}).")
        self.finished.emit({})

    def do_read_io_block(self):
        addr, size = self.params
        self.log.emit(f"{self.tr('io_read_block')} 0x{addr:04X} ({size})")
        cmd = bytes([CMD_IO_READ_BLOCK, size & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
        resp = self.send_and_recv(cmd)
        mem = {}
        if resp and resp[0] == ACK_IO_READ_BLOCK:
            for i in range(resp[1]):
                if 3 + i < len(resp):
                    mem[addr + i] = resp[3 + i]
            self.log.emit(f"{self.tr('io_read_ok')} {len(mem)} {self.tr('io_bytes')}")
        else:
            self.log.emit(self.tr('io_read_err'))
        self.finished.emit(mem)

    def do_write_io_block(self):
        mem_dict, start_addr = self.params
        self.log.emit(f"{self.tr('io_write_block')} 0x{start_addr:04X}...")
        addrs = sorted(mem_dict.keys())
        written = 0
        for i in range(0, len(addrs), self.max_block_size):
            if not self.is_running: break
            chunk_addrs = addrs[i:i+self.max_block_size]
            chunk_data = [mem_dict[a] for a in chunk_addrs]
            c_addr = chunk_addrs[0]
            c_size = len(chunk_data)
            
            cmd = bytearray([CMD_IO_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(chunk_data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_IO_WRITE_BLOCK:
                self.log.emit(f"{self.tr('io_write_err')} 0x{c_addr:04X}")
                break
            written += c_size
            self.progress.emit(int((i + c_size) * 100 / len(addrs)))
        self.log.emit(f"{self.tr('io_write_done')} ({written} {self.tr('bytes')}).")
        self.finished.emit({})

    def do_test_mem(self):
        start, end, pattern_name = self.params
        size = end - start + 1
        self.log.emit(f"{self.tr('test_mem')} 0x{start:04X}-0x{end:04X} {self.tr('pattern')} '{pattern_name}'")
        
        errors = 0
        chunk_size = self.max_block_size
        
        def get_pattern(offset, length):
            if pattern_name == "Zero": return [0x00] * length
            elif pattern_name == "One": return [0xFF] * length
            elif pattern_name == "Checker": return [0x55 if (offset + i) % 2 == 0 else 0xAA for i in range(length)]
            elif pattern_name == "Addr": return [(start + offset + i) & 0xFF for i in range(length)]
            return [0x00] * length

        for i in range(0, size, chunk_size):
            if not self.is_running: break
            c_size = min(chunk_size, size - i)
            c_addr = start + i
            data = get_pattern(i, c_size)
            
            cmd = bytearray([CMD_MEM_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_MEM_WRITE_BLOCK:
                self.log.emit(f"{self.tr('write_fail')} 0x{c_addr:04X}")
                break
                
            cmd_r = bytes([CMD_MEM_READ_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            resp_r = self.send_and_recv(cmd_r)
            if resp_r and resp_r[0] == ACK_MEM_READ_BLOCK:
                for j in range(c_size):
                    if 3 + j < len(resp_r) and resp_r[3+j] != data[j]:
                        errors += 1
                        self.log.emit(f"{self.tr('error')}: Addr 0x{c_addr+j:04X} {self.tr('expected')} 0x{data[j]:02X}, {self.tr('got')} 0x{resp_r[3+j]:02X}")
            else:
                self.log.emit(f"{self.tr('read_fail')} 0x{c_addr:04X}")
                break
                
            self.progress.emit(int((i + c_size) * 100 / size))
            
        self.log.emit(f"{self.tr('test_done')} {self.tr('errors')}: {errors}")
        self.finished.emit({"errors": errors})

    def do_run_io_sequence(self):
        sequence = self.params['sequence']
        self.log.emit(self.tr('io_seq_start'))
        for line in sequence:
            if not self.is_running: break
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
                
            parts = line.split()
            cmd = parts[0].upper()
            
            try:
                if cmd == 'W' and len(parts) == 3:
                    port = int(parts[1], 16)
                    data = int(parts[2], 16)
                    payload = bytes([CMD_IO_WRITE_BYTE, (port >> 8) & 0xFF, port & 0xFF, data])
                    resp = self.send_and_recv(payload, timeout=1.0)
                    if not resp or resp[0] != ACK_IO_WRITE_BYTE:
                        self.log.emit(f"  [{self.tr('error')}] {self.tr('write_io')} 0x{port:02X}")
                    else:
                        self.log.emit(f"  [{self.tr('ok')}] W IO 0x{port:02X} = 0x{data:02X}")
                        
                elif cmd == 'R' and len(parts) == 2:
                    port = int(parts[1], 16)
                    payload = bytes([CMD_IO_READ_BYTE, (port >> 8) & 0xFF, port & 0xFF])
                    resp = self.send_and_recv(payload, timeout=1.0)
                    if resp and resp[0] == ACK_IO_READ_BYTE:
                        val = resp[3]
                        self.log.emit(f"  [{self.tr('ok')}] R IO 0x{port:02X} = 0x{val:02X}")
                    else:
                        self.log.emit(f"  [{self.tr('error')}] {self.tr('read_io')} 0x{port:02X}")
                        
                elif cmd == 'D' and len(parts) == 2:
                    ms = int(parts[1])
                    time.sleep(ms / 1000.0)
                    self.log.emit(f"  [{self.tr('delay')}] {ms} ms")
            except ValueError:
                self.log.emit(f"  [{self.tr('error')}] {self.tr('err_seq_fmt')} {line}")
                
        self.log.emit(self.tr('io_seq_done'))
        self.finished.emit({})

# ==================== WATCH ОКНО ====================
class WatchModel(QAbstractTableModel):
    """Модель для Watch-окна (наблюдение за памятью и регистрами)"""
    
    # Форматы отображения
    FORMATS = ["hex", "dec", "signed", "bin", "ascii"]
    
    # Типы наблюдения
    TYPE_MEM_BYTE = "mem_byte"
    TYPE_MEM_WORD = "mem_word"
    TYPE_REG = "reg"
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.lang = "en"
        self.items = []  # Список элементов наблюдения
        self.prev_values = {}  # Предыдущие значения для подсветки
        
    # =============================================
    # УПРАВЛЕНИЕ ЭЛЕМЕНТАМИ
    # =============================================
    
    def add_watch(self, name, watch_type, target, fmt="hex"):
        """Добавить элемент наблюдения"""
        item = {
            "name": name,
            "type": watch_type,
            "target": target,
            "format": fmt
        }
        self.beginInsertRows(QModelIndex(), len(self.items), len(self.items))
        self.items.append(item)
        self.endInsertRows()
        
    def remove_watch(self, row):
        """Удалить элемент наблюдения"""
        if 0 <= row < len(self.items):
            self.beginRemoveRows(QModelIndex(), row, row)
            self.items.pop(row)
            self.endRemoveRows()
            
    def clear(self):
        """Очистить все элементы"""
        self.beginResetModel()
        self.items.clear()
        self.prev_values.clear()
        self.endResetModel()
        
    # =============================================
    # ПОЛУЧЕНИЕ И ФОРМАТИРОВАНИЕ ЗНАЧЕНИЙ
    # =============================================
    
    def get_value(self, item):
        """Получить текущее значение элемента"""
        try:
            if item["type"] == self.TYPE_MEM_BYTE:
                return self.emulator.read_byte(item["target"])
            elif item["type"] == self.TYPE_MEM_WORD:
                return self.emulator.read_word(item["target"])
            elif item["type"] == self.TYPE_REG:
                reg = item["target"].upper()
                if reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L']:
                    return self.emulator.get_reg(reg)
                elif reg == 'BC': return self.emulator.get_reg_pair('BC')
                elif reg == 'DE': return self.emulator.get_reg_pair('DE')
                elif reg == 'HL': return self.emulator.get_reg_pair('HL')
                elif reg == 'SP': return self.emulator.sp
                elif reg == 'PC': return self.emulator.pc
                elif reg == 'FLAGS':
                    return (int(self.emulator.flag_s) << 7) | \
                           (int(self.emulator.flag_z) << 6) | \
                           (int(self.emulator.flag_ac) << 4) | \
                           (int(self.emulator.flag_p) << 2) | \
                           int(self.emulator.flag_cy)
        except Exception:
            return 0
        return 0
        
    def format_value(self, value, fmt, is_word=False):
        """Форматировать значение"""
        try:
            if fmt == "hex":
                return f"{value:04X}" if is_word else f"{value:02X}"
            elif fmt == "dec":
                return str(value)
            elif fmt == "signed":
                if is_word:
                    if value >= 0x8000:
                        return str(value - 0x10000)
                else:
                    if value >= 0x80:
                        return str(value - 0x100)
                return str(value)
            elif fmt == "bin":
                return f"{value:016b}" if is_word else f"{value:08b}"
            elif fmt == "ascii":
                if is_word:
                    chars = []
                    for i in range(2):
                        b = (value >> (i * 8)) & 0xFF
                        chars.append(chr(b) if 32 <= b < 127 else '.')
                    return ''.join(chars)
                else:
                    return chr(value) if 32 <= value < 127 else '.'
        except Exception:
            return "?"
        return str(value)
        
    def get_display_value(self, item):
        """Получить отформатированное значение"""
        value = self.get_value(item)
        is_word = item["type"] == self.TYPE_MEM_WORD or \
                  (item["type"] == self.TYPE_REG and item["target"].upper() in ['BC', 'DE', 'HL', 'SP', 'PC'])
        return self.format_value(value, item["format"], is_word)
        
    # =============================================
    # СОХРАНЕНИЕ/ЗАГРУЗКА ПРЕСЕТА
    # =============================================
    
    def save_preset(self, filepath):
        """Сохранить пресет в JSON файл"""
        data = {
            "version": 1,
            "watches": [
                {
                    "name": item["name"],
                    "type": item["type"],
                    "target": item["target"],
                    "format": item["format"]
                }
                for item in self.items
            ]
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
            
    def load_preset(self, filepath):
        """Загрузить пресет из JSON файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.beginResetModel()
            self.items.clear()
            self.prev_values.clear()
            
            for watch in data.get("watches", []):
                self.items.append({
                    "name": watch.get("name", "watch"),
                    "type": watch.get("type", self.TYPE_MEM_BYTE),
                    "target": watch.get("target", 0),
                    "format": watch.get("format", "hex")
                })
            
            self.endResetModel()
            return True
        except Exception:
            return False
            
    # =============================================
    # ОБНОВЛЕНИЕ
    # =============================================
    
    def save_prev_values(self):
        """Сохранить текущие значения для подсветки изменений"""
        self.prev_values = {}
        for i, item in enumerate(self.items):
            key = f"{item['type']}_{item['target']}"
            self.prev_values[key] = self.get_value(item)
            
    def refresh(self):
        """Обновить данные модели"""
        if self.items:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self.items) - 1, 3)
            )
    
    # =============================================
    # QAbstractTableModel INTERFACE
    # =============================================
    
    def rowCount(self, parent=None):
        return len(self.items)
        
    def columnCount(self, parent=None):
        return 4  # Имя | Адрес/Регистр | Значение | Формат
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("watch_col_name", "Name"),
                L.get("watch_col_target", "Addr/Reg"),
                L.get("watch_col_value", "Value"),
                L.get("watch_col_format", "Format"),
            ]
            return headers[section]
        return None
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self.items):
            return None
            
        item = self.items[row]
        
        if role == Qt.DisplayRole:
            if col == 0:
                return item["name"]
            elif col == 1:
                if item["type"] == self.TYPE_REG:
                    return item["target"].upper()
                return f"0x{item['target']:04X}"
            elif col == 2:
                return self.get_display_value(item)
            elif col == 3:
                return item["format"]
                
        elif role == Qt.BackgroundRole:
            # Подсветка изменённых значений
            if col == 2:
                current = self.get_value(item)
                key = f"{item['type']}_{item['target']}"
                if key in self.prev_values and self.prev_values[key] != current:
                    return QColor("#ffcccc")  # Красный фон
                    
        elif role == Qt.TextAlignmentRole:
            if col in [1, 2]:
                return Qt.AlignCenter
                
        return None

class BreakpointModel(QAbstractTableModel):
    """Модель для панели точек останова"""
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.lang = "en"
    
    def get_bp_list(self):
        """Отсортированный список адресов BP"""
        return sorted(self.emulator.breakpoints)
    
    def refresh(self):
        """Полный сброс модели для пересчёта строк"""
        self.beginResetModel()
        self.endResetModel()
    
    # QAbstractTableModel interface
    def rowCount(self, parent=None):
        return len(self.emulator.breakpoints)
    
    def columnCount(self, parent=None):
        return 4  # Адрес | Условие | Вкл | Срабатываний
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("bp_col_addr", "Address"),
                L.get("bp_col_cond", "Condition"),
                L.get("bp_col_enabled", "On"),
                L.get("bp_col_hits", "Hits"),
            ]
            return headers[section]
        return None
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        bps = self.get_bp_list()
        row, col = index.row(), index.column()
        if row >= len(bps):
            return None
        addr = bps[row]
        
        if role == Qt.DisplayRole:
            if col == 0:
                return f"0x{addr:04X}"
            elif col == 1:
                return self.emulator.get_bp_condition(addr) or "—"
            elif col == 2:
                return "✓" if self.emulator.bp_enabled.get(addr, True) else "✗"
            elif col == 3:
                return str(self.emulator.bp_hit_count.get(addr, 0))
        elif role == Qt.ForegroundRole:
            if not self.emulator.bp_enabled.get(addr, True):
                return QColor("#999999")
            if col == 1 and self.emulator.get_bp_condition(addr):
                return QColor("#0066cc")
        elif role == Qt.TextAlignmentRole:
            if col in [0, 2, 3]:
                return Qt.AlignCenter
        return None

class TraceModel(QAbstractTableModel):
    """Виртуальная модель трассировки с поддержкой фильтра"""
    
    def __init__(self, emulator, parent=None):
        super().__init__(parent)
        self.emulator = emulator
        self.disassembler = None
        self._filter = None
        self._filtered_indices = None  # Индексы отфильтрованных записей
        self.lang = "en"
    
    def set_filter(self, filter_dict):
        """Установить фильтр и обновить модель"""
        self._filter = filter_dict
        self.refresh()
    
    def refresh(self):
        """Уведомить Qt об изменении данных"""
        self._apply_filter()
        self.beginResetModel()
        self.endResetModel()
    
    def _apply_filter(self):
        """Применить фильтр и сохранить индексы подходящих записей"""
        if self._filter is None:
            self._filtered_indices = None
            return
        buf = self.emulator.trace_buffer
        self._filtered_indices = []
        f = self._filter
        if f["type"] == "addr":
            for i, rec in enumerate(buf):
                if rec["pc"] == f["value"]:
                    self._filtered_indices.append(i)
        elif f["type"] == "reg":
            reg = f["reg"]
            op = f.get("op", "==")  # ← По умолчанию равенство
            value = f["value"]
            flag_map = {'S': 0, 'Z': 1, 'AC': 2, 'P': 3, 'CY': 4}
            for i, rec in enumerate(buf):
                # Получаем значение регистра
                if reg == 'A': val = rec["A"]
                elif reg == 'B': val = rec["B"]
                elif reg == 'C': val = rec["C"]
                elif reg == 'D': val = rec["D"]
                elif reg == 'E': val = rec["E"]
                elif reg == 'H': val = rec["H"]
                elif reg == 'L': val = rec["L"]
                elif reg == 'BC': val = rec["BC"]
                elif reg == 'DE': val = rec["DE"]
                elif reg == 'HL': val = rec["HL"]
                elif reg == 'SP': val = rec["SP"]
                elif reg == 'PC': val = rec["pc"]
                elif reg in flag_map:
                    val = rec["flags"][flag_map[reg]]
                else:
                    continue
                
                # Сравниваем с учётом оператора
                if op == '==' and val == value:
                    self._filtered_indices.append(i)
                elif op == '!=' and val != value:
                    self._filtered_indices.append(i)
                elif op == '>' and val > value:
                    self._filtered_indices.append(i)
                elif op == '<' and val < value:
                    self._filtered_indices.append(i)
                elif op == '>=' and val >= value:
                    self._filtered_indices.append(i)
                elif op == '<=' and val <= value:
                    self._filtered_indices.append(i)
        elif f["type"] == "mnemonic":
            for i, rec in enumerate(buf):
                mnemonic = self._get_mnemonic(rec)
                if f["value"] in mnemonic.upper():
                    self._filtered_indices.append(i)
    
    def _get_record(self, row):
        """Получить запись по строке (с учётом фильтра)"""
        buf = self.emulator.trace_buffer
        if self._filtered_indices is not None:
            if row >= len(self._filtered_indices):
                return None
            idx = self._filtered_indices[row]
            if idx >= len(buf):
                return None
            return buf[idx]
        else:
            if row >= len(buf):
                return None
            return buf[row]
    
    def rowCount(self, parent=None):
        if self._filtered_indices is not None:
            return len(self._filtered_indices)
        return self.emulator.trace_count()
    
    def columnCount(self, parent=None):
        return 10
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            L = LANGS.get(self.lang, LANGS["en"])
            headers = [
                L.get("trace_col_seq", "#"),
                L.get("trace_col_pc", "PC"),
                L.get("trace_col_bytes", "Bytes"),
                L.get("trace_col_mnem", "Mnemonic"),
                "A", "BC", "DE", "HL", "SP",
                L.get("trace_col_flags", "Flags")
            ]
            return headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._get_record(index.row())
        if rec is None:
            return None
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == 0:
                return str(rec["seq"])
            elif col == 1:
                return f"{rec['pc']:04X}"
            elif col == 2:
                return " ".join(f"{b:02X}" for b in rec["bytes"])
            elif col == 3:
                return self._get_mnemonic(rec)
            elif col == 4:
                return f"{rec['A']:02X}"
            elif col == 5:
                return f"{rec['BC']:04X}"
            elif col == 6:
                return f"{rec['DE']:04X}"
            elif col == 7:
                return f"{rec['HL']:04X}"
            elif col == 8:
                return f"{rec['SP']:04X}"
            elif col == 9:
                f = rec["flags"]
                return (f"{'S' if f[0] else '-'}{'Z' if f[1] else '-'}"
                        f"{'A' if f[2] else '-'}{'P' if f[3] else '-'}"
                        f"{'C' if f[4] else '-'}")
        elif role == Qt.TextAlignmentRole:
            if col in [0, 1, 4, 5, 6, 7, 8]:
                return Qt.AlignCenter
        elif role == Qt.BackgroundRole:
            # === Подсветка переходов (JMP/CALL/RET/RST) ===
            if rec["opcode"] in JUMP_OPCODES:
                return QColor("#FFE0B2")  # Оранжевый фон для переходов
            # === Подсветка изменённых регистров ===
            prev_rec = self._get_record(index.row() - 1)
            if prev_rec is not None:
                if col == 4 and rec["A"] != prev_rec["A"]:
                    return QColor("#FFCDD2")  # Красный фон
                elif col == 5 and rec["BC"] != prev_rec["BC"]:
                    return QColor("#FFCDD2")
                elif col == 6 and rec["DE"] != prev_rec["DE"]:
                    return QColor("#FFCDD2")
                elif col == 7 and rec["HL"] != prev_rec["HL"]:
                    return QColor("#FFCDD2")
                elif col == 8 and rec["SP"] != prev_rec["SP"]:
                    return QColor("#FFCDD2")
                elif col == 9 and rec["flags"] != prev_rec["flags"]:
                    return QColor("#FFCDD2")
        return None
    
    def _get_mnemonic(self, rec):
        """Определить мнемонику для записи"""
        if not self.disassembler:
            return f"DB {rec['opcode']:02X}h"
        temp_mem = {rec["pc"] + i: b for i, b in enumerate(rec["bytes"])}
        lines = self.disassembler.disassemble(temp_mem, rec["pc"], len(rec["bytes"]))
        if lines:
            return lines[0][2]
        return f"DB {rec['opcode']:02X}h"

# ==================== ГЛАВНОЕ ОКНО ====================
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
        else:
            self.current_lang = get_system_language()
            
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
        devices_menu = self.menuBar().addMenu("Устройства")
        act_manager = devices_menu.addAction("Диспетчер устройств")
        act_manager.triggered.connect(self.show_device_manager)

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
        self.status_label_addr = QLabel("Адрес: -")
        self.status_label_data = QLabel("Данные: -")
        self.status_label_mnem = QLabel("Мнемоника: -")
        self.status_label_size = QLabel("Размер: 0 байт")
        self.status_label_conn = QLabel("Отключено")
        
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
        self.theme_combo.addItems(["Light", "Dark"])
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
        
        self.create_tab_control()
        self.create_tab_data()
        self.create_tab_hex()
        self.create_tab_disasm()
        self.create_tab_test()
        self.create_tab_io_seq()
        self.create_tab_compare()
        self.create_tab_scripts()
        
        self.lbl_log = QLabel()
        main_layout.addWidget(self.lbl_log)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: Consolas, Courier New, monospace;")
        main_layout.addWidget(self.log_text)
        
        # Подключаем сигнал изменения данных в hex-редакторе
        self.hex_model.dataEdited.connect(self.on_hex_data_changed)
        
        # Эмулятор
        self.create_tab_emulator()
        
        # Трассировка
        self.create_tab_trace()
        
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
		
        self.btn_mcp = QPushButton("MCP Server: OFF")
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
        self.mem_data_endian.addItems(["Little", "Big"])
        self.mem_data_endian.setCurrentText("Little")
        
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
        self.io_data_endian.addItems(["Little", "Big"])
        self.io_data_endian.setCurrentText("Little")
        
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
        self.test_pattern.addItems(["Checker", "Zero", "One", "Addr"])
        
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
        self.settings.setValue("language", self.current_lang)  # Сохраняем настройку
        self.retranslate_ui()
        
    def on_theme_changed(self, index):
        self.current_theme = "Light" if index == 0 else "Dark"
        self.settings.setValue("theme", self.current_theme)  # Сохраняем настройку
        QApplication.instance().setStyleSheet(THEMES[self.current_theme])

        # Обновляем тему дизассемблера
        is_dark = (self.current_theme == "Dark")
        self.disasm_view.set_theme(is_dark)
        
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
        self.tabs.setTabText(0, self.tr("tab_control"))    # Управление
        self.tabs.setTabText(1, self.tr("tab_data"))       # Данные
        self.tabs.setTabText(2, self.tr("tab_hex"))        # Hex Редактор
        self.tabs.setTabText(3, self.tr("tab_disasm"))     # Дизассемблер
        self.tabs.setTabText(4, self.tr("tab_test"))       # Тест Памяти
        self.tabs.setTabText(5, self.tr("tab_io_seq"))     # IO Секвенсор
        self.tabs.setTabText(6, self.tr("tab_compare"))    # Сравнение
        self.tabs.setTabText(7, self.tr("tab_scripts"))    # Скрипты
        self.tabs.setTabText(8, self.tr("tab_emulator"))   # Эмулятор
        self.tabs.setTabText(9, self.tr("tab_trace"))      # Трассировка
        
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
                self.log(f"  [WAIT] HLDA low...")
            elif ack == ACK_HOLD_WAIT_HIGH:
                self.log(f"  [WAIT] HLDA high...")
        elif cmd == CMD_UNHOLD and len(data) >= 2:
            ack = data[1]
            if ack == ACK_UNHOLD:
                self.bus_active = False
                self.update_ui_state()
                self.log(f"  [{self.tr('ok')}] Bus UNHOLD. CPU running.")
            elif ack == ACK_WAIT_UNHOLD:
                self.log(f"  [WAIT] HLDA high...")
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
            endian = self.mem_data_endian.currentText()
            self.pending_read = {"addr": addr, "bits": bits, "endian": endian, "is_io": False}
            self.start_worker("read_block", (addr, size))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_addr"))

    def write_memory_data(self):
        try:
            addr = int(self.mem_data_addr.text(), 16)
            bits = int(self.mem_data_bits.currentText())
            endian = self.mem_data_endian.currentText()
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
            endian = self.io_data_endian.currentText()
            self.pending_read = {"addr": port, "bits": bits, "endian": endian, "is_io": True}
            self.start_worker("read_io_block", (port, size))
        except ValueError:
            QMessageBox.warning(self, self.tr("error"), self.tr("err_port_addr"))

    def write_io_data(self):
        try:
            port = int(self.io_data_addr.text(), 16)
            bits = int(self.io_data_bits.currentText())
            endian = self.io_data_endian.currentText()
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

    def on_hex_data_changed(self):
        """Вызывается при изменении данных в hex-редакторе"""
        # Добавляем операцию в undo stack
        if hasattr(self.hex_model, 'last_edit') and self.hex_model.last_edit:
            addr, old_val, new_val = self.hex_model.last_edit
            self.push_undo([(addr, old_val, new_val)])
            self.hex_model.last_edit = None
        
        if self.auto_disasm_check.isChecked() and self.mem_data:
            self.auto_disasm()

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
            pat = self.test_pattern.currentText()
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
            self.status_label_conn.setText(f"{self.tr('connected')} | BUS ACTIVE")
        else:
            self.status_label_conn.setText(f"{self.tr('connected')} | BUS FREE")
			
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
        elf.statusBar.showMessage(f"{self.tr('status_undo_depth')}{len(self.undo_stack)}", 2000)
        
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
        }
        
        try:
            # Перенаправляем stdout
            import io
            import sys
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
            import traceback
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
            self.btn_mcp.setText("MCP Server: OFF")
        else:
            self.mcp_server.start()
            self.btn_mcp.setText("MCP Server: ON")
			
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
        
        self.cycles_label = QLabel("Такты: 0")
        self.state_label = QLabel("Состояние: Остановлен")
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
            import json
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
            import json
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
        self.lbl_trace_status = QLabel("Записей: 0 / 10000")
        self.lbl_trace_status.setStyleSheet("color: #666;")
        ctrl_layout.addWidget(self.lbl_trace_status)
        
        ctrl_layout.addStretch()
        
        # Поиск
        self.lbl_trace_search = QLabel("Поиск:")
        ctrl_layout.addWidget(self.lbl_trace_search)
        self.txt_trace_search = QLineEdit()
        self.txt_trace_search.setPlaceholderText("Адрес (HEX) или регистр OP значение (A==55, HL>1000, SP<=F000)")
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
            f.write(f"# i8080 Trace Export\n")
            f.write(f"# Records: {len(records)}\n")
            f.write(f"{'#':>6}  {'PC':>4}  {'Bytes':<12}  {'Mnemonic':<20}  {'A':>2}  {'BC':>4}  {'DE':>4}  {'HL':>4}  {'SP':>4}  {'Flags':<5}  {'Cyc':>5}\n")
            f.write("-" * 110 + "\n")
            for rec in records:
                mnemonic = self._get_trace_mnemonic(rec)
                bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
                flags = rec["flags"]
                flags_str = f"{'S' if flags[0] else '-'}{'Z' if flags[1] else '-'}{'A' if flags[2] else '-'}{'P' if flags[3] else '-'}{'C' if flags[4] else '-'}"
                f.write(f"{rec['seq']:>6}  {rec['pc']:04X}  {bytes_str:<12}  {mnemonic:<20}  "
                        f"{rec['A']:>2}  {rec['BC']:04X}  {rec['DE']:04X}  {rec['HL']:04X}  "
                        f"{rec['SP']:04X}  {flags_str:<5}  {rec['cycles']:>5}\n")

    def _export_trace_csv(self, path, records):
        """Экспорт в CSV"""
        import csv
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['seq', 'pc', 'bytes', 'mnemonic', 'A', 'BC', 'DE', 'HL', 'SP', 'flags', 'cycles', 'cycles_total'])
            for rec in records:
                mnemonic = self._get_trace_mnemonic(rec)
                bytes_str = " ".join(f"{b:02X}" for b in rec["bytes"])
                flags = rec["flags"]
                flags_str = f"{'S' if flags[0] else '-'}{'Z' if flags[1] else '-'}{'A' if flags[2] else '-'}{'P' if flags[3] else '-'}{'C' if flags[4] else '-'}"
                writer.writerow([
                    rec['seq'], f"{rec['pc']:04X}", bytes_str, mnemonic,
                    f"{rec['A']:02X}", f"{rec['BC']:04X}", f"{rec['DE']:04X}",
                    f"{rec['HL']:04X}", f"{rec['SP']:04X}", flags_str,
                    rec['cycles'], rec['cycles_total']
                ])

    def _export_trace_json(self, path, records):
        """Экспорт в JSON"""
        import json
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
                raise ValueError(f"Ошибки загрузки профиля:\n" + "\n".join(errors))

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
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
