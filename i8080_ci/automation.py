"""Automation API for external control."""
import time

from PySide6.QtWidgets import QApplication
from .intelhex import IntelHex
from .slip import (CMD_HOLD, CMD_UNHOLD,
                   CMD_MEM_READ_BYTE, CMD_MEM_READ_BLOCK,
                   CMD_MEM_WRITE_BYTE, CMD_MEM_WRITE_BLOCK,
                   CMD_IO_READ_BYTE, CMD_IO_WRITE_BYTE,
                   CMD_EEPROM_WRITE_BYTE, CMD_EEPROM_WRITE_BLOCK,
                   ACK_MEM_READ_BYTE, ACK_MEM_READ_BLOCK,
                   ACK_MEM_WRITE_BYTE, ACK_MEM_WRITE_BLOCK,
                   ACK_IO_READ_BYTE, ACK_IO_WRITE_BYTE,
                   ACK_EEPROM_WRITE_BYTE, ACK_EEPROM_WRITE_BLOCK)

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
        self._last_asm_result = None
        
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
		
    # =============================================
    # АССЕМБЛЕР
    # =============================================
    def _check_assembler(self):
        """Проверяет, что виджет ассемблера создан"""
        if not hasattr(self.mw, 'assembler_widget') or self.mw.assembler_widget is None:
            raise RuntimeError("Виджет ассемблера не создан")
        return self.mw.assembler_widget

    def asm_get_source(self):
        """Вернуть исходный код из редактора ассемблера."""
        return self._check_assembler().editor.toPlainText()

    def asm_set_source(self, source):
        """Установить исходный код в редактор ассемблера."""
        self._check_assembler().editor.setPlainText(source)

    def asm_load_file(self, path):
        """Загрузить .asm файл в редактор ассемблера. Возвращает текст."""
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.asm_set_source(source)
        return source

    def asm_assemble(self, source=None, load_to_memory=False):
        """Ассемблировать код (из редактора или из параметра source).

        Возвращает AsmResult (binary, origin, symbols, errors, warnings).
        При load_to_memory=True результат загружается в память эмулятора.
        """
        widget = self._check_assembler()
        if source is not None:
            widget.editor.setPlainText(source)
        else:
            source = widget.editor.toPlainText()
        result = widget.assembler.assemble(source, getattr(widget, '_current_file', None) or '')
        self._last_asm_result = result
        if result.errors:
            return result
        # Сохранение map-файла рядом с исходным
        cur_file = getattr(widget, '_current_file', None)
        if result.map_text and cur_file:
            import os as _os
            map_path = _os.path.splitext(cur_file)[0] + '.map'
            try:
                from assemble8080.mapfile import save_map_file
                save_map_file(map_path, result.map_text)
            except Exception:
                pass
        if load_to_memory and result.binary:
            widget._load_to_memory(result.binary, result.origin)
        return result

    def asm_get_binary(self):
        """Вернуть бинарный результат последней сборки (bytes)."""
        if not hasattr(self, '_last_asm_result') or self._last_asm_result is None:
            raise RuntimeError("Сначала вызовите asm_assemble()")
        return bytes(self._last_asm_result.binary)

    def asm_get_symbols(self):
        """Вернуть словарь меток последней сборки {имя: адрес}."""
        if not hasattr(self, '_last_asm_result') or self._last_asm_result is None:
            raise RuntimeError("Сначала вызовите asm_assemble()")
        return dict(self._last_asm_result.symbols)

    def asm_get_map(self):
        """Вернуть текст map-файла последней сборки (str)."""
        if not hasattr(self, '_last_asm_result') or self._last_asm_result is None:
            raise RuntimeError("Сначала вызовите asm_assemble()")
        return self._last_asm_result.map_text

    def asm_save_map(self, path, source=None):
        """Ассемблировать (если нужно) и сохранить map-файл.

        Args:
            path: путь к .map файлу
            source: опциональный исходный код (иначе из редактора)
        """
        from assemble8080.mapfile import save_map_file
        result = self.asm_assemble(source=source)
        if result.errors:
            raise RuntimeError("Assembly errors: " + "; ".join(e.message for e in result.errors))
        save_map_file(path, result.map_text)
        return result.map_text

    def asm_assemble_obj(self, path, source=None):
        """Ассемблировать код и сохранить объектный файл (.obj).

        Args:
            path: путь к .obj файлу
            source: опциональный исходный код (иначе из редактора)

        Возвращает ObjectFile.
        """
        from assemble8080.objfile import obj_from_asm_result, save_obj
        result = self.asm_assemble(source=source)
        if result.errors:
            raise RuntimeError("Assembly errors: " + "; ".join(e.message for e in result.errors))
        widget = self._check_assembler()
        obj = obj_from_asm_result(result, getattr(widget, '_current_file', None) or '')
        save_obj(path, obj)
        return obj

    def asm_link(self, script_path=None, obj_paths=None, origin=0, size=0x10000, fill=0xFF):
        """Слинковать объектные файлы.

        Args:
            script_path: путь к .lnk скрипту линковщика (приоритет)
            obj_paths: список путей к .obj файлам (если нет script_path)
            origin, size, fill: параметры линковки (для obj_paths)

        Возвращает LinkResult (binary, origin, size, symbols, errors, warnings, map_text).
        """
        from assemble8080.linker import link, link_from_script
        from assemble8080.objfile import load_obj
        if script_path:
            return link_from_script(script_path)
        if not obj_paths:
            raise RuntimeError("Нужен script_path или obj_paths")
        objects = [load_obj(p) for p in obj_paths]
        return link(objects, origin=origin, size=size, fill=fill)

    def asm_load_map(self, path):
        """Загрузить map-файл в дизассемблер для резолва символов.

        Args:
            path: путь к .map файлу

        Возвращает MapFile.
        """
        from assemble8080.mapfile import load_map_file
        map_file = load_map_file(path)
        self.mw.disassembler.set_map(map_file)
        return map_file


# ==================== РАБОЧИЙ ПОТОК ====================

