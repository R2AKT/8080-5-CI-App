"""
Эмулятор процессора Intel 8080
Итерация 1-2: Базовое ядро + команды пересылки данных
"""

from PySide6.QtCore import QObject, Signal
from collections import deque

class _SafeAccessor:
    """Обёртка для безопасной индексации в условиях BP (mem[...], io[...])"""
    def __init__(self, getter):
        self._getter = getter
    def __getitem__(self, key):
        return self._getter(key)

class I8080Emulator(QObject):
    """Эмулятор процессора Intel 8080"""
    
    # Сигналы для UI
    state_changed = Signal()
    breakpoint_hit = Signal(int)
    log_message = Signal(str)
    
    def __init__(self, memory, parent=None):
        super().__init__(parent)
        self.memory = memory
        
        # === IO-порты (виртуальные) ===
        self.io_ports = {}  # {port: value}
        
        # Регистры
        self.a = 0x00
        self.b = 0x00
        self.c = 0x00
        self.d = 0x00
        self.e = 0x00
        self.h = 0x00
        self.l = 0x00
        self.sp = 0xFFFF
        self.pc = 0x0000
        
        # Флаги
        self.flag_s = False
        self.flag_z = False
        self.flag_ac = False
        self.flag_p = False
        self.flag_cy = False
        
        # Состояние
        self.running = False
        self.halted = False
        self.interrupts_enabled = False
        self.breakpoints = set()
        # === Условные breakpoints ===
        self.bp_conditions = {}    # {addr: "условие"}
        self.bp_enabled = {}       # {addr: True/False}
        self.bp_hit_count = {}     # {addr: count}
        self.cycles = 0
        
        # Трассировка
        self.trace_enabled = False
        self.trace_max_records = 10000
        self.trace_buffer = deque(maxlen=self.trace_max_records)
        self.trace_seq = 0
        self.disassembler = None  # Устанавливается из MainWindow
        
        # === ИТЕРАЦИЯ E1: Шина памяти ===
        self.memory_bus = None  # Устанавливается из MainWindow
        
        # Очередь внешних прерываний
        self._pending_interrupts = []
        self._interrupt_vector = None
        
        # === WAIT-сигнал (итерация 10.3) ===
        self.wait_signal = False
        
    def reset(self) -> None:
        """Сброс процессора"""
        self.a = self.b = self.c = self.d = 0x00
        self.e = self.h = self.l = 0x00
        self.sp = 0xFFFF
        self.pc = 0x0000
        self.flag_s = self.flag_z = self.flag_ac = self.flag_p = self.flag_cy = False
        self.running = False
        self.halted = False
        self.interrupts_enabled = False
        self.cycles = 0
        self.io_ports = {}  # ← Добавлено: сброс IO-портов
        self.state_changed.emit()
        # === WAIT-сигнал (итерация 10.3) ===
        self.wait_signal = False
        
    def set_wait(self, active: bool) -> None:
        """Установить сигнал WAIT (от устройства).
        Пока wait_signal=True, CPU не выполняет инструкции."""
        self.wait_signal = active
        
    def set_pc(self, addr: int) -> None:
        """Установить Program Counter"""
        self.pc = addr & 0xFFFF
        self.state_changed.emit()
        
    def get_reg_pair(self, pair: str) -> int:
        """Получить пару регистров"""
        if pair == 'BC': return (self.b << 8) | self.c
        elif pair == 'DE': return (self.d << 8) | self.e
        elif pair == 'HL': return (self.h << 8) | self.l
        elif pair == 'SP': return self.sp
        return 0
        
    def set_reg_pair(self, pair: str, value: int) -> None:
        """Установить пару регистров"""
        value &= 0xFFFF
        high = (value >> 8) & 0xFF
        low = value & 0xFF
        if pair == 'BC': self.b, self.c = high, low
        elif pair == 'DE': self.d, self.e = high, low
        elif pair == 'HL': self.h, self.l = high, low
        elif pair == 'SP': self.sp = value
        
    def get_reg(self, reg: str) -> int:
        # """Получить значение регистра"""
        regs = {
            'A': self.a, 'B': self.b, 'C': self.c,
            'D': self.d, 'E': self.e, 'H': self.h, 'L': self.l,
            'M': self.read_byte(self.get_reg_pair('HL'))
        }
        return regs.get(reg, 0)
        
    def set_reg(self, reg: str, value: int) -> None:
        """Установить значение регистра"""
        value &= 0xFF
        if reg == 'A': self.a = value
        elif reg == 'B': self.b = value
        elif reg == 'C': self.c = value
        elif reg == 'D': self.d = value
        elif reg == 'E': self.e = value
        elif reg == 'H': self.h = value
        elif reg == 'L': self.l = value
        elif reg == 'M':
            addr = self.get_reg_pair('HL')
            self.write_byte(addr, value)
            
    def read_byte(self, addr: int) -> int:
        """Чтение байта из памяти (через шину, если есть)"""
        addr &= 0xFFFF
        if self.memory_bus is not None:
            return self.memory_bus.read(addr)
        return self.memory.get(addr, 0xFF)
        
    def write_byte(self, addr: int, value: int) -> None:
        """Запись байта в память (через шину, если есть)"""
        addr &= 0xFFFF
        if self.memory_bus is not None:
            self.memory_bus.write(addr, value)
        else:
            self.memory[addr] = value & 0xFF
            
    def read_word(self, addr: int) -> int:
        """Чтение слова (little-endian), через шину, если есть"""
        addr &= 0xFFFF
        if self.memory_bus is not None:
            low = self.read_byte(addr)
            high = self.read_byte(addr + 1)
            return (high << 8) | low
        else:
            low = self.memory.get(addr, 0xFF)
            high = self.memory.get(addr + 1, 0xFF)
            return (high << 8) | low
            
    def write_word(self, addr: int, value: int) -> None:
        """Запись слова (little-endian), через шину, если есть"""
        addr &= 0xFFFF
        if self.memory_bus is not None:
            self.write_byte(addr, value & 0xFF)
            self.write_byte(addr + 1, (value >> 8) & 0xFF)
        else:
            self.memory[addr] = value & 0xFF
            self.memory[addr+1] = (value >> 8) & 0xFF
            
    def push(self, value: int) -> None:
        """Поместить слово в стек"""
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, (value >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, value & 0xFF)
        
    def pop(self) -> int:
        """Извлечь слово из стека"""
        low = self.read_byte(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        high = self.read_byte(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        return (high << 8) | low
        
    def set_flags(self, value: int, check_carry: bool = False, carry: int = 0) -> None:
        """Установить флаги по результату операции"""
        value &= 0xFF
        self.flag_z = (value == 0)
        self.flag_s = bool(value & 0x80)
        self.flag_p = bin(value).count('1') % 2 == 0
        if check_carry:
            self.flag_cy = bool(carry)
            
    def check_condition(self, cc: str) -> bool:
        """Проверить условие для условных переходов"""
        if cc == 'NZ': return not self.flag_z
        elif cc == 'Z': return self.flag_z
        elif cc == 'NC': return not self.flag_cy
        elif cc == 'C': return self.flag_cy
        elif cc == 'PO': return not self.flag_p
        elif cc == 'PE': return self.flag_p
        elif cc == 'P': return not self.flag_s
        elif cc == 'M': return self.flag_s
        return False
        
    def _alu_add(self, value, carry_in=0) -> None:
        """Сложение с аккумулятором (для ADD, ADC, ADI, ACI)"""
        old_a = self.a
        result = self.a + value + carry_in
        
        # Флаг Auxiliary Carry (перенос из бита 3 в бит 4)
        self.flag_ac = ((old_a & 0x0F) + (value & 0x0F) + carry_in) > 0x0F
        
        # Флаг Carry (перенос из бита 7)
        self.flag_cy = result > 0xFF
        
        # Результат
        self.a = result & 0xFF
        self.set_flags(self.a)
        
    def _alu_sub(self, value, carry_in=0) -> None:
        """Вычитание из аккумулятора (для SUB, SBB, SUI, SBI, CMP, CPI)"""
        old_a = self.a
        result = self.a - value - carry_in
        
        # Флаг Carry (заём) — инвертирован для вычитания
        self.flag_cy = result < 0
        
        # Флаг Auxiliary Carry (заём из бита 4 в бит 3)
        self.flag_ac = ((old_a & 0x0F) - (value & 0x0F) - carry_in) < 0
        
        # Результат
        self.a = result & 0xFF
        self.set_flags(self.a)
        
    def _alu_and(self, value) -> None:
        """Логическое И (для ANA, ANI)"""
        # AC устанавливается, если бит 3 любого операнда = 1
        self.flag_ac = bool((self.a | value) & 0x08)
        self.a &= value
        self.flag_cy = False
        self.set_flags(self.a)
        
    def _alu_xor(self, value) -> None:
        """Исключающее ИЛИ (для XRA, XRI)"""
        self.a ^= value
        self.flag_cy = False
        self.flag_ac = False
        self.set_flags(self.a)
        
    def _alu_or(self, value) -> None:
        """Логическое ИЛИ (для ORA, ORI)"""
        self.a |= value
        self.flag_cy = False
        self.flag_ac = False
        self.set_flags(self.a)
        
    def _alu_cmp(self, value) -> None:
        """Сравнение (для CMP, CPI) — A не изменяется"""
        old_a = self.a
        result = self.a - value
        
        self.flag_cy = result < 0
        self.flag_ac = ((old_a & 0x0F) - (value & 0x0F)) < 0
        
        result &= 0xFF
        self.set_flags(result)
        # A не изменяется!
		
    def execute_instruction(self, silent: bool = False) -> None:
        """
        Выполнить одну инструкцию.
        Args:
            silent: если True, не эмитить сигналы (для пакетного Run и трассировки)
        """
        # === WAIT-сигнал: пропускаем инструкцию ===
        if self.wait_signal:
            self.cycles += 1  # Wait-state: один такт потрачен
            return True       # Возвращаем True — CPU жив, но ждёт
        
        if self.halted:
            return False
        if self.should_stop_at_bp(self.pc):
            if not silent:
                self.breakpoint_hit.emit(self.pc)
            return False
        opcode = self.read_byte(self.pc)
        pc_start = self.pc
        
        # === ТРАССИРОВКА: определяем байты инструкции ДО выполнения ===
        trace_bytes = None
        if self.trace_enabled:
            if self.disassembler and opcode in self.disassembler.table:
                size = self.disassembler.table[opcode][0]
            else:
                size = 1
            trace_bytes = [self.read_byte(pc_start + i) for i in range(size)]
        
        self.pc = (self.pc + 1) & 0xFFFF
        self._execute_opcode(opcode)
        cycles = self._get_cycles(opcode)
        self.cycles += cycles
        
        # === ТРАССИРОВКА: запись ПОСЛЕ выполнения ===
        if self.trace_enabled and trace_bytes is not None:
            self._add_trace_record(pc_start, opcode, trace_bytes, cycles)
        if not silent:
            self.state_changed.emit()
        return True
        
    def _execute_opcode(self, opcode) -> int:
        """Выполнить опкод"""
        
        # NOP и недокументированные NOP*
        if opcode in [0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xDD, 0xED, 0xFD]:
            return
            
        # HLT
        elif opcode == 0x76:
            self.halted = True
            self.log_message.emit("CPU halted")
            return
            
        # MOV r,r' (0x40-0x7F)
        elif 0x40 <= opcode <= 0x7F:
            dst = (opcode >> 3) & 0x07
            src = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[src])
            self.set_reg(regs[dst], value)
            
        # MVI r,data
        elif opcode in [0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E]:
            reg_idx = (opcode >> 3) & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self.set_reg(regs[reg_idx], data)
            
        # LXI rp,data
        elif opcode in [0x01, 0x11, 0x21, 0x31]:
            rp_idx = (opcode >> 4) & 0x03
            pairs = ['BC', 'DE', 'HL', 'SP']
            data = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            self.set_reg_pair(pairs[rp_idx], data)
            
        # INR r
        elif opcode in [0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C]:
            reg_idx = (opcode >> 3) & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            old_val = self.get_reg(regs[reg_idx])
            new_val = (old_val + 1) & 0xFF
            self.set_reg(regs[reg_idx], new_val)
            self.set_flags(new_val)
            self.flag_ac = (old_val & 0x0F) == 0x0F
            
        # DCR r
        elif opcode in [0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D]:
            reg_idx = (opcode >> 3) & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            old_val = self.get_reg(regs[reg_idx])
            new_val = (old_val - 1) & 0xFF
            self.set_reg(regs[reg_idx], new_val)
            self.set_flags(new_val)
            self.flag_ac = (old_val & 0x0F) == 0x00
            
        # INX rp
        elif opcode in [0x03, 0x13, 0x23, 0x33]:
            rp_idx = (opcode >> 4) & 0x03
            pairs = ['BC', 'DE', 'HL', 'SP']
            value = (self.get_reg_pair(pairs[rp_idx]) + 1) & 0xFFFF
            self.set_reg_pair(pairs[rp_idx], value)
            
        # DCX rp
        elif opcode in [0x0B, 0x1B, 0x2B, 0x3B]:
            rp_idx = (opcode >> 4) & 0x03
            pairs = ['BC', 'DE', 'HL', 'SP']
            value = (self.get_reg_pair(pairs[rp_idx]) - 1) & 0xFFFF
            self.set_reg_pair(pairs[rp_idx], value)
            
        # JMP addr
        elif opcode == 0xC3:
            addr = self.read_word(self.pc)
            self.pc = addr
            
        # JMP cc,addr
        elif opcode in [0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA]:
            cc_idx = (opcode >> 3) & 0x07
            conditions = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            if self.check_condition(conditions[cc_idx]):
                self.pc = addr
        
        # === ИТЕРАЦИЯ 2: Команды пересылки данных ===
        
        # STAX B
        elif opcode == 0x02:
            addr = self.get_reg_pair('BC')
            self.write_byte(addr, self.a)
            
        # STAX D
        elif opcode == 0x12:
            addr = self.get_reg_pair('DE')
            self.write_byte(addr, self.a)
            
        # LDAX B
        elif opcode == 0x0A:
            addr = self.get_reg_pair('BC')
            self.a = self.read_byte(addr)
            
        # LDAX D
        elif opcode == 0x1A:
            addr = self.get_reg_pair('DE')
            self.a = self.read_byte(addr)
            
        # SHLD addr
        elif opcode == 0x22:
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            self.write_byte(addr, self.l)
            self.write_byte(addr + 1, self.h)
            
        # LHLD addr
        elif opcode == 0x2A:
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            self.l = self.read_byte(addr)
            self.h = self.read_byte(addr + 1)
            
        # STA addr
        elif opcode == 0x32:
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            self.write_byte(addr, self.a)
            
        # LDA addr
        elif opcode == 0x3A:
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            self.a = self.read_byte(addr)
            
        # XCHG
        elif opcode == 0xEB:
            self.h, self.d = self.d, self.h
            self.l, self.e = self.e, self.l
            
        # XTHL
        elif opcode == 0xE3:
            low = self.read_byte(self.sp)
            high = self.read_byte(self.sp + 1)
            self.write_byte(self.sp, self.l)
            self.write_byte(self.sp + 1, self.h)
            self.l = low
            self.h = high
            
        # SPHL
        elif opcode == 0xF9:
            self.sp = self.get_reg_pair('HL')
            
        # PCHL
        elif opcode == 0xE9:
            self.pc = self.get_reg_pair('HL')
        
        # =============================================
        # ИТЕРАЦИЯ 3: Арифметика и логика
        # =============================================
        
        # ADD r (0x80-0x87)
        elif 0x80 <= opcode <= 0x87:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_add(value)
            
        # ADC r (0x88-0x8F)
        elif 0x88 <= opcode <= 0x8F:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_add(value, carry_in=1 if self.flag_cy else 0)
            
        # SUB r (0x90-0x97)
        elif 0x90 <= opcode <= 0x97:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_sub(value)
            
        # SBB r (0x98-0x9F)
        elif 0x98 <= opcode <= 0x9F:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_sub(value, carry_in=1 if self.flag_cy else 0)
            
        # ANA r (0xA0-0xA7)
        elif 0xA0 <= opcode <= 0xA7:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_and(value)
            
        # XRA r (0xA8-0xAF)
        elif 0xA8 <= opcode <= 0xAF:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_xor(value)
            
        # ORA r (0xB0-0xB7)
        elif 0xB0 <= opcode <= 0xB7:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_or(value)
            
        # CMP r (0xB8-0xBF)
        elif 0xB8 <= opcode <= 0xBF:
            reg_idx = opcode & 0x07
            regs = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
            value = self.get_reg(regs[reg_idx])
            self._alu_cmp(value)
            
        # ADI data (0xC6)
        elif opcode == 0xC6:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_add(data)
            
        # ACI data (0xCE)
        elif opcode == 0xCE:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_add(data, carry_in=1 if self.flag_cy else 0)
            
        # SUI data (0xD6)
        elif opcode == 0xD6:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_sub(data)
            
        # SBI data (0xDE)
        elif opcode == 0xDE:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_sub(data, carry_in=1 if self.flag_cy else 0)
            
        # ANI data (0xE6)
        elif opcode == 0xE6:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_and(data)
            
        # XRI data (0xEE)
        elif opcode == 0xEE:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_xor(data)
            
        # ORI data (0xF6)
        elif opcode == 0xF6:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_or(data)
            
        # CPI data (0xFE)
        elif opcode == 0xFE:
            data = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            self._alu_cmp(data)
            
        # DAD rp (0x09, 0x19, 0x29, 0x39)
        elif opcode in [0x09, 0x19, 0x29, 0x39]:
            rp_idx = (opcode >> 4) & 0x03
            pairs = ['BC', 'DE', 'HL', 'SP']
            rp_val = self.get_reg_pair(pairs[rp_idx])
            hl_val = self.get_reg_pair('HL')
            result = hl_val + rp_val
            self.flag_cy = result > 0xFFFF
            self.set_reg_pair('HL', result & 0xFFFF)
            
        # RLC (0x07) - Циклический сдвиг влево
        elif opcode == 0x07:
            self.flag_cy = bool(self.a & 0x80)
            self.a = ((self.a << 1) | (1 if self.flag_cy else 0)) & 0xFF
            
        # RRC (0x0F) - Циклический сдвиг вправо
        elif opcode == 0x0F:
            self.flag_cy = bool(self.a & 0x01)
            self.a = ((self.a >> 1) | ((1 if self.flag_cy else 0) << 7)) & 0xFF
            
        # RAL (0x17) - Сдвиг влево через перенос
        elif opcode == 0x17:
            old_cy = self.flag_cy
            self.flag_cy = bool(self.a & 0x80)
            self.a = ((self.a << 1) | (1 if old_cy else 0)) & 0xFF
            
        # RAR (0x1F) - Сдвиг вправо через перенос
        elif opcode == 0x1F:
            old_cy = self.flag_cy
            self.flag_cy = bool(self.a & 0x01)
            self.a = ((self.a >> 1) | ((1 if old_cy else 0) << 7)) & 0xFF
            
        # CMA (0x2F) - Инверсия аккумулятора
        elif opcode == 0x2F:
            self.a = (~self.a) & 0xFF
            
        # CMC (0x3F) - Инверсия флага переноса
        elif opcode == 0x3F:
            self.flag_cy = not self.flag_cy
            
        # STC (0x37) - Установка флага переноса
        elif opcode == 0x37:
            self.flag_cy = True
            
        # DAA (0x27)
        elif opcode == 0x27:
            correction = 0
            if (self.a & 0x0F) > 9 or self.flag_ac:
                correction += 0x06
            # Проверяем старшую тетраду С УЧЁТОМ коррекции младшей
            if ((self.a + correction) >> 4) > 9 or self.flag_cy:
                correction += 0x60
            old_a = self.a
            old_cy = self.flag_cy
            self.a = (self.a + correction) & 0xFF
            self.flag_cy = old_cy or (correction >= 0x60)
            self.flag_ac = ((old_a & 0x0F) + (correction & 0x0F)) > 0x0F
            self.set_flags(self.a)
            
        # =============================================
        # ИТЕРАЦИЯ 4: Стек и подпрограммы
        # =============================================
        
        # PUSH rp (0xC5, 0xD5, 0xE5, 0xF5)
        elif opcode in [0xC5, 0xD5, 0xE5, 0xF5]:
            rp_idx = (opcode >> 4) & 0x03
            # Порядок PUSH: BC, DE, HL, PSW (не SP!)
            if rp_idx == 3:
                # PSW: A и флаги
                flags = (self.flag_s << 7) | (self.flag_z << 6) | (self.flag_ac << 4) | \
                        (self.flag_p << 2) | (1 << 1) | (self.flag_cy)
                value = (self.a << 8) | flags
            else:
                pairs = ['BC', 'DE', 'HL']
                value = self.get_reg_pair(pairs[rp_idx])
            self.push(value)
            
        # POP rp (0xC1, 0xD1, 0xE1, 0xF1)
        elif opcode in [0xC1, 0xD1, 0xE1, 0xF1]:
            rp_idx = (opcode >> 4) & 0x03
            value = self.pop()
            if rp_idx == 3:
                # PSW: A и флаги
                self.a = (value >> 8) & 0xFF
                flags = value & 0xFF
                self.flag_s = bool(flags & 0x80)
                self.flag_z = bool(flags & 0x40)
                self.flag_ac = bool(flags & 0x10)
                self.flag_p = bool(flags & 0x04)
                self.flag_cy = bool(flags & 0x01)
            else:
                pairs = ['BC', 'DE', 'HL']
                self.set_reg_pair(pairs[rp_idx], value)
                
        # CALL addr (0xCD)
        elif opcode == 0xCD:
            addr = self.read_word(self.pc)
            ret_addr = (self.pc + 2) & 0xFFFF
            self.push(ret_addr)
            self.pc = addr
            
        # CALL* (0xCB) — недокументированная
        elif opcode == 0xCB:
            addr = self.read_word(self.pc)
            ret_addr = (self.pc + 2) & 0xFFFF
            self.push(ret_addr)
            self.pc = addr
            
        # RET (0xC9)
        elif opcode == 0xC9:
            self.pc = self.pop()
            
        # RET* (0xD9) — недокументированная
        elif opcode == 0xD9:
            self.pc = self.pop()
            
        # CALL cc, addr (0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC)
        elif opcode in [0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC]:
            cc_idx = (opcode >> 3) & 0x07
            conditions = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']
            addr = self.read_word(self.pc)
            self.pc = (self.pc + 2) & 0xFFFF
            if self.check_condition(conditions[cc_idx]):
                ret_addr = self.pc
                self.push(ret_addr)
                self.pc = addr
                
        # RET cc (0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8)
        elif opcode in [0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8]:
            cc_idx = (opcode >> 3) & 0x07
            conditions = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']
            if self.check_condition(conditions[cc_idx]):
                self.pc = self.pop()
                
        # RST n (0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF)
        elif opcode in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]:
            rst_num = (opcode >> 3) & 0x07
            vector = rst_num * 8  # 00, 08, 10, 18, 20, 28, 30, 38
            self.push(self.pc)
            self.pc = vector
            
        # =============================================
        # ИТЕРАЦИЯ 5: IN/OUT и управление
        # =============================================
        
        # IN port (0xDB)
        elif opcode == 0xDB:
            port = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            # Чтение из виртуального порта
            self.a = self.io_ports.get(port, 0xFF)
            
        # OUT port (0xD3)
        elif opcode == 0xD3:
            port = self.read_byte(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            # Запись в виртуальный порт
            self.io_ports[port] = self.a
            
        # DI (0xF3) - Запрет прерываний
        elif opcode == 0xF3:
            self.interrupts_enabled = False
            
        # EI (0xFB) - Разрешение прерываний
        elif opcode == 0xFB:
            self.interrupts_enabled = True
            
        # Неизвестный опкод
        else:
            self.log_message.emit(f"Unimplemented opcode: 0x{opcode:02X} at 0x{pc_start:04X}")
            self.halted = True
            
    def _get_cycles(self, opcode) -> int:
        """Получить количество тактов для опкода"""
        
        # NOP, HLT
        if opcode in [0x00, 0x76]: return 4
        
        # MOV r,r'
        if 0x40 <= opcode <= 0x7F:
            src = opcode & 0x07
            dst = (opcode >> 3) & 0x07
            if src == 6 or dst == 6: return 7  # M
            return 5
            
        # MVI r,data
        if opcode in [0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x3E]: return 7
        if opcode == 0x36: return 10  # MVI M,data
        
        # LXI rp,data
        if opcode in [0x01, 0x11, 0x21, 0x31]: return 10
        
        # INR r
        if opcode in [0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C]: return 5
        if opcode == 0x34: return 10  # INR M
        
        # DCR r
        if opcode in [0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D]: return 5
        if opcode == 0x35: return 10  # DCR M
        
        # INX / DCX rp
        if opcode in [0x03, 0x13, 0x23, 0x33]: return 5
        if opcode in [0x0B, 0x1B, 0x2B, 0x3B]: return 5
        
        # JMP / JMP cc
        if opcode == 0xC3: return 10
        if opcode in [0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA]: return 10
        
        # STAX / LDAX
        if opcode in [0x02, 0x12, 0x0A, 0x1A]: return 7
        # SHLD / LHLD
        if opcode in [0x22, 0x2A]: return 16
        # STA / LDA
        if opcode in [0x32, 0x3A]: return 13
        # XCHG
        if opcode == 0xEB: return 4
        # XTHL
        if opcode == 0xE3: return 18
        # SPHL / PCHL
        if opcode in [0xF9, 0xE9]: return 5
        
        # === ИТЕРАЦИЯ 3: Арифметика и логика ===
        # ADD, ADC, SUB, SBB, ANA, XRA, ORA, CMP (регистровые)
        if 0x80 <= opcode <= 0xBF:
            reg_idx = opcode & 0x07
            if reg_idx == 6: return 7  # M
            return 4
            
        # Immediate операции
        if opcode in [0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE]: return 7
        
        # DAD rp
        if opcode in [0x09, 0x19, 0x29, 0x39]: return 10
        
        # Сдвиги
        if opcode in [0x07, 0x0F, 0x17, 0x1F]: return 4
        
        # Специальные
        if opcode in [0x27, 0x2F, 0x3F, 0x37]: return 4  # DAA, CMA, CMC, STC
        
        # === ИТЕРАЦИЯ 4: Стек и подпрограммы ===
        # POP rp
        if opcode in [0xC1, 0xD1, 0xE1, 0xF1]: return 10
        # PUSH rp
        if opcode in [0xC5, 0xD5, 0xE5, 0xF5]: return 11
        # CALL / CALL*
        if opcode in [0xCD, 0xCB]: return 17
        # RET / RET*
        if opcode in [0xC9, 0xD9]: return 10
        # CALL cc (условный)
        if opcode in [0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC]:
            cc_idx = (opcode >> 3) & 0x07
            conditions = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']
            return 17 if self.check_condition(conditions[cc_idx]) else 11
        # RET cc (условный)
        if opcode in [0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8]:
            cc_idx = (opcode >> 3) & 0x07
            conditions = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']
            return 11 if self.check_condition(conditions[cc_idx]) else 5
        # RST
        if opcode in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]: return 11
        
        # === ИТЕРАЦИЯ 5: IN/OUT и управление ===
        if opcode == 0xDB: return 10  # IN
        if opcode == 0xD3: return 10  # OUT
        if opcode == 0xF3: return 4   # DI
        if opcode == 0xFB: return 4   # EI
        
        # По умолчанию
        return 4
        
    def step(self) -> None:
        """Выполнить одну инструкцию"""
        if not self.halted:
            return self.execute_instruction()
        return False
        
    def run(self, max_instructions: int = 10000) -> None:
        self.running = True
        instructions_executed = 0
        while self.running and instructions_executed < max_instructions:
            if not self.execute_instruction():
                break
            instructions_executed += 1
        self.running = False
        return instructions_executed
        
    def stop(self) -> None:
        """Остановить выполнение"""
        self.running = False
        
    def add_breakpoint(self, addr: int) -> None:
        """Добавить точку останова"""
        self.breakpoints.add(addr & 0xFFFF)
        
    def remove_breakpoint(self, addr: int) -> None:
        """Удалить точку останова и связанные данные"""
        addr &= 0xFFFF
        self.breakpoints.discard(addr)
        self.bp_conditions.pop(addr, None)
        self.bp_enabled.pop(addr, None)
        self.bp_hit_count.pop(addr, None)
        
    def should_stop_at_bp(self, addr: int) -> bool:
        """Проверяет, нужно ли останавливаться на BP с учётом условия и enabled"""
        if addr not in self.breakpoints:
            return False
        # BP выключена
        if not self.bp_enabled.get(addr, True):
            return False
        # Нет условия — обычная BP
        condition = self.bp_conditions.get(addr, "")
        if not condition.strip():
            return True
        # Проверяем условие через eval
        try:
            context = {
                'A': self.a, 'B': self.b, 'C': self.c,
                'D': self.d, 'E': self.e, 'H': self.h, 'L': self.l,
                'BC': self.get_reg_pair('BC'),
                'DE': self.get_reg_pair('DE'),
                'HL': self.get_reg_pair('HL'),
                'SP': self.sp, 'PC': self.pc,
                'S': int(self.flag_s), 'Z': int(self.flag_z),
                'AC': int(self.flag_ac), 'P': int(self.flag_p),
                'CY': int(self.flag_cy),
                'cycles': self.cycles,
                'mem': _SafeAccessor(lambda a: self.read_byte(a)),
                'io': _SafeAccessor(lambda p: self.io_ports.get(p, 0xFF)),
            }
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception as e:
            self.log_message.emit(f"BP condition error at 0x{addr:04X}: {e}")
            return True  # При ошибке условия считаем BP обычной
            
    def set_bp_condition(self, addr: int, condition: str) -> None:
        """Установить условие для BP"""
        addr &= 0xFFFF
        if condition.strip():
            self.bp_conditions[addr] = condition.strip()
        else:
            self.bp_conditions.pop(addr, None)
            
    def get_bp_condition(self, addr: int) -> str:
        """Получить условие BP"""
        return self.bp_conditions.get(addr & 0xFFFF, "")
        
    def toggle_bp_enabled(self, addr: int) -> None:
        """Включить/выключить BP"""
        addr &= 0xFFFF
        self.bp_enabled[addr] = not self.bp_enabled.get(addr, True)
        
    def register_bp_hit(self, addr: int) -> None:
        """Зарегистрировать срабатывание BP (увеличить счётчик)"""
        addr &= 0xFFFF
        self.bp_hit_count[addr] = self.bp_hit_count.get(addr, 0) + 1
        
    def clear_all_breakpoints(self) -> None:
        """Удалить все BP и условия"""
        self.breakpoints.clear()
        self.bp_conditions.clear()
        self.bp_enabled.clear()
        self.bp_hit_count.clear()
        
    # =============================================
    # Трассировка
    # =============================================
    
    def trace_start(self) -> None:
        """Включить запись трассировки"""
        self.trace_enabled = True
    
    def trace_stop(self) -> None:
        """Выключить запись трассировки"""
        self.trace_enabled = False
    
    def trace_clear(self) -> None:
        """Очистить буфер трассировки"""
        self.trace_buffer.clear()
        self.trace_seq = 0
    
    def trace_set_depth(self, depth: int) -> None:
        """Установить глубину буфера"""
        self.trace_max_records = depth
        # Пересоздаём deque с новым maxlen, сохраняя данные
        old_data = list(self.trace_buffer)
        self.trace_buffer = deque(old_data, maxlen=depth)
    
    def trace_get(self, limit: int | None = None) -> list:
        """Получить записи трассировки (последние limit или все)"""
        if limit is None:
            return list(self.trace_buffer)
        return list(self.trace_buffer)[-limit:]
    
    def trace_count(self) -> int:
        """Количество записей в буфере"""
        return len(self.trace_buffer)
    
    def _get_trace_snapshot(self) -> dict:
        """Компактный снимок состояния для трассировки"""
        return (
            self.a, self.b, self.c, self.d, self.e, self.h, self.l,
            self.sp,
            int(self.flag_s), int(self.flag_z), int(self.flag_ac),
            int(self.flag_p), int(self.flag_cy)
        )
    
    def _add_trace_record(self, pc_start, opcode, instr_bytes, cycles) -> None:
        """Добавить запись в буфер трассировки"""
        a, b, c, d, e, h, l, sp, fs, fz, fac, fp, fcy = self._get_trace_snapshot()
        record = {
            "seq": self.trace_seq,
            "pc": pc_start,
            "opcode": opcode,
            "bytes": instr_bytes,
            "A": a, "B": b, "C": c, "D": d, "E": e, "H": h, "L": l,
            "BC": (b << 8) | c,
            "DE": (d << 8) | e,
            "HL": (h << 8) | l,
            "SP": sp,
            "flags": (fs, fz, fac, fp, fcy),
            "cycles": cycles,
            "cycles_total": self.cycles,
        }
        self.trace_buffer.append(record)
        self.trace_seq += 1
        
    def get_state(self) -> dict:
        """Получить текущее состояние для UI"""
        return {
            'A': self.a, 'B': self.b, 'C': self.c,
            'D': self.d, 'E': self.e, 'H': self.h, 'L': self.l,
            'SP': self.sp, 'PC': self.pc,
            'BC': self.get_reg_pair('BC'),
            'DE': self.get_reg_pair('DE'),
            'HL': self.get_reg_pair('HL'),
            'flags': {
                'S': self.flag_s, 'Z': self.flag_z,
                'AC': self.flag_ac, 'P': self.flag_p, 'CY': self.flag_cy
            },
            'cycles': self.cycles,
            'halted': self.halted,
            'running': self.running,
            'interrupts': self.interrupts_enabled
        }
		
    def is_call_instruction(self, addr: int) -> bool:
        """Проверяет, является ли инструкция по адресу CALL"""
        opcode = self.read_byte(addr)
        # CALL addr (0xCD) и условные CALL cc,addr
        call_opcodes = [0xCD, 0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC, 0xCB]
        return opcode in call_opcodes
    
    def step_into(self) -> bool:
        """Step Into (F11): одна инструкция, игнорируя breakpoint на текущем PC"""
        if self.halted:
            return False
        
        current_pc = self.pc
        had_bp = current_pc in self.breakpoints
        
        # Временно удаляем breakpoint на текущем PC
        if had_bp:
            self.breakpoints.discard(current_pc)
        
        result = self.execute_instruction(silent=True)
        
        # Восстанавливаем breakpoint
        if had_bp:
            self.breakpoints.add(current_pc)
        
        return result
        
    def step_over(self) -> bool:
        """Step Over (F10): выполнить CALL как одну инструкцию, обходя BP на текущем PC"""
        if self.halted:
            return False
        
        current_pc = self.pc
        had_bp = current_pc in self.breakpoints
        
        # Временно удаляем breakpoint на текущем PC для обхода
        if had_bp:
            self.breakpoints.discard(current_pc)
        
        try:
            if self.is_call_instruction(self.pc):
                return_addr = (self.pc + 3) & 0xFFFF
                temp_bp = return_addr
                self.breakpoints.add(temp_bp)
                
                max_steps = 100000
                steps = 0
                while steps < max_steps and not self.halted:
                    if self.pc == temp_bp:
                        break
                    if not self.execute_instruction(silent=True):
                        break
                    steps += 1
                
                self.breakpoints.discard(temp_bp)
                return True
            else:
                # Не CALL — одна инструкция
                return self.execute_instruction(silent=True)
        finally:
            # Восстанавливаем breakpoint в любом случае
            if had_bp:
                self.breakpoints.add(current_pc)
    
    def run_to(self, target_addr: int) -> bool:
        """Выполнять до указанного адреса (Run to Cursor)"""
        self.running = True
        max_steps = 1000000
        steps = 0
        
        while self.running and steps < max_steps:
            if self.pc == target_addr:
                break
            if self.should_stop_at_bp(self.pc):
                self.breakpoint_hit.emit(self.pc)
                break
            # === ТИХИЙ РЕЖИМ ===
            if not self.execute_instruction(silent=True):
                break
            steps += 1
        
        self.running = False
        self.state_changed.emit()  # Одно обновление в конце
        return steps
		
    def set_pc_to_memory_start(self) -> None:
        """Установить PC на минимальный адрес загруженной памяти"""
        # Пробуем шину, потом dict
        if self.memory_bus is not None:
            addrs = []
            for region in self.memory_bus.memory_regions:
                if hasattr(region, 'data') and region.data:
                    addrs.extend(region.data.keys())
            if addrs:
                min_addr = min(addrs)
                self.pc = min_addr & 0xFFFF
                self.state_changed.emit()
                self.log_message.emit(f"PC set to memory start: 0x{self.pc:04X}")
                return self.pc
        elif self.memory:
            min_addr = min(self.memory.keys())
            self.pc = min_addr & 0xFFFF
            self.state_changed.emit()
            self.log_message.emit(f"PC set to memory start: 0x{self.pc:04X}")
            return self.pc
        return None
        
    # =============================================
    # ВНЕШНИЕ ПРЕРЫВАНИЯ (итерация 10.1)
    # =============================================
    def request_interrupt(self, vector: int) -> None:
        """Запросить внешнее прерывание.
        vector — опкод инструкции (0xC7-0xFF для RST, или 0xCD для CALL).
        Вызывается из ComputerSystem."""
        self._pending_interrupts.append(vector)

    def has_pending_interrupt(self) -> bool:
        """Есть ли ожидающие прерывания"""
        return len(self._pending_interrupts) > 0

    def _handle_interrupt(self) -> None:
        """Обработка внешнего прерывания.
        Вызывается после каждой инструкции, если прерывания разрешены."""
        if not self._pending_interrupts:
            return False

        if not self.int_enabled:
            return False  # Прерывания запрещены (DI)

        # Извлекаем вектор
        vector = self._pending_interrupts.pop(0)

        # Запрещаем прерывания на время обработки
        self.int_enabled = False

        # Выполняем вектор как инструкцию
        if vector == 0x76:  # HLT — не обрабатываем
            return False

        # Сохраняем текущий PC в стек (как при CALL)
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, (self.pc >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, self.pc & 0xFF)

        # Определяем адрес перехода по вектору
        if 0xC7 <= vector <= 0xFF and (vector & 0x07) == 0x07:
            # RST 0-7: адрес = (vector - 0xC7) / 8 * 8
            rst_num = (vector - 0xC7) // 8
            self.pc = rst_num * 8
            self.cycles += 12  # RST: 12 тактов
        elif vector == 0xCD:
            # CALL addr: следующий байт — адрес (нужно получить из шины)
            # В упрощённой реализации адрес должен быть передан заранее
            self.cycles += 18
        else:
            # Неизвестный вектор — игнорируем
            self.pc = self.read_word(self.sp)
            self.sp = (self.sp + 2) & 0xFFFF
            return False

        return True
# ============================================================
# АВТОМАТИЧЕСКИЕ ТЕСТЫ (запуск: python i8080_emulator.py)
# ============================================================

def run_tests() -> None:
    """Запуск всех тестов эмулятора"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    print("=" * 70)
    print(" ТЕСТЫ ЭМУЛЯТОРА i8080")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    def check(name: str, actual, expected) -> None:
        nonlocal passed, failed
        if actual == expected:
            print(f"  ✅ {name}: {actual}")
            passed += 1
        else:
            print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
            failed += 1
    
    def make_emu(program: bytes):
        """Создаёт эмулятор и загружает программу"""
        memory = {}
        for i, b in enumerate(program):
            memory[i] = b
        emu = I8080Emulator(memory)
        return emu
    
    # =============================================
    # ТЕСТ 1: MVI + INR + DCR
    # =============================================
    print("\nТест 1: MVI + INR + DCR")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x55,  # MVI A, 55h
        0x3C,        # INR A
        0x3C,        # INR A
        0x3D,        # DCR A
        0x76         # HLT
    ])
    emu.run()
    check("A после MVI 55h + INR + INR + DCR", emu.a, 0x56)
    
    # =============================================
    # ТЕСТ 2: MOV r,r'
    # =============================================
    print("\nТест 2: MOV r,r'")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0xAA,  # MVI A, AAh
        0x47,        # MOV B, A
        0x48,        # MOV C, B
        0x51,        # MOV D, C
        0x76         # HLT
    ])
    emu.run()
    check("B после MOV B,A", emu.b, 0xAA)
    check("C после MOV C,B", emu.c, 0xAA)
    check("D после MOV D,C", emu.d, 0xAA)
    
    # =============================================
    # ТЕСТ 3: LXI + INX + DCX
    # =============================================
    print("\nТест 3: LXI + INX + DCX")
    print("-" * 50)
    emu = make_emu([
        0x01, 0x34, 0x12,  # LXI B, 1234h
        0x03,              # INX B
        0x0B,              # DCX B
        0x0B,              # DCX B
        0x76               # HLT
    ])
    emu.run()
    check("BC после LXI 1234h + INX + DCX + DCX", emu.get_reg_pair('BC'), 0x1233)
    
    # =============================================
    # ТЕСТ 4: JMP
    # =============================================
    print("\nТест 4: JMP")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x00,        # MVI A, 00h
        0xC3, 0x05, 0x00,  # JMP 0005h
        0x3C,              # INR A (не должно выполниться)
        0x3C,              # INR A (не должно выполниться)
        0x3E, 0x42,        # MVI A, 42h (адрес 0005h)
        0x76               # HLT
    ])
    emu.run()
    check("A после JMP (пропуск двух INR)", emu.a, 0x42)
    
    # =============================================
    # ТЕСТ 5: JMP cc (условный переход)
    # =============================================
    print("\nТест 5: JMP Z (условный переход)")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x00,        # MVI A, 00h (устанавливает Z=1)
        0x3D,              # DCR A (A=FF, Z=0)
        0x3C,              # INR A (A=00, Z=1)
        0xCA, 0x07, 0x00,  # JZ 0007h (Z=1, переходим)
        0x3E, 0xFF,        # MVI A, FFh (не должно выполниться)
        0x3E, 0x99,        # MVI A, 99h (адрес 0007h)
        0x76               # HLT
    ])
    emu.run()
    check("A после JZ (переход выполнен)", emu.a, 0x99)
    
    # =============================================
    # ТЕСТ 6: STA / LDA
    # =============================================
    print("\nТест 6: STA / LDA")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x55,        # MVI A, 55h
        0x32, 0x00, 0x01,  # STA 0100h
        0x3E, 0x00,        # MVI A, 00h
        0x3A, 0x00, 0x01,  # LDA 0100h
        0x76               # HLT
    ])
    emu.run()
    check("A после STA/LDA", emu.a, 0x55)
    
    # =============================================
    # ТЕСТ 7: SHLD / LHLD
    # =============================================
    print("\nТест 7: SHLD / LHLD")
    print("-" * 50)
    emu = make_emu([
        0x21, 0x34, 0x12,  # LXI H, 1234h
        0x22, 0x00, 0x02,  # SHLD 0200h
        0x21, 0x00, 0x00,  # LXI H, 0000h
        0x2A, 0x00, 0x02,  # LHLD 0200h
        0x76               # HLT
    ])
    emu.run()
    check("HL после SHLD/LHLD", emu.get_reg_pair('HL'), 0x1234)
    
    # =============================================
    # ТЕСТ 8: STAX / LDAX
    # =============================================
    print("\nТест 8: STAX / LDAX")
    print("-" * 50)
    emu = make_emu([
        0x01, 0x00, 0x03,  # LXI B, 0300h
        0x3E, 0xAA,        # MVI A, AAh
        0x02,              # STAX B
        0x3E, 0x00,        # MVI A, 00h
        0x0A,              # LDAX B
        0x76               # HLT
    ])
    emu.run()
    check("A после STAX/LDAX", emu.a, 0xAA)
    
    # =============================================
    # ТЕСТ 9: XCHG
    # =============================================
    print("\nТест 9: XCHG")
    print("-" * 50)
    emu = make_emu([
        0x21, 0x34, 0x12,  # LXI H, 1234h
        0x11, 0x78, 0x56,  # LXI D, 5678h
        0xEB,              # XCHG
        0x76               # HLT
    ])
    emu.run()
    check("HL после XCHG", emu.get_reg_pair('HL'), 0x5678)
    check("DE после XCHG", emu.get_reg_pair('DE'), 0x1234)
    
    # =============================================
    # ТЕСТ 10: SPHL / PCHL
    # =============================================
    print("\nТест 10: SPHL / PCHL")
    print("-" * 50)
    emu = make_emu([
        0x21, 0x00, 0x04,  # LXI H, 0400h   → адрес 0000-0002
        0xF9,              # SPHL            → адрес 0003 (SP = 0400h)
        0x21, 0x0A, 0x00,  # LXI H, 000Ah   → адрес 0004-0006 (HL = адрес HLT)
        0xE9,              # PCHL            → адрес 0007 (PC = 000Ah)
        0x00,              # NOP             → адрес 0008 (не должно выполниться)
        0x00,              # NOP             → адрес 0009 (не должно выполниться)
        0x76               # HLT             → адрес 000A
    ])
    emu.run()
    check("SP после SPHL", emu.sp, 0x0400)
    check("CPU halted", emu.halted, True)
	
	# =============================================
    # ТЕСТ 11: ADD / ADC
    # =============================================
    print("\nТест 11: ADD / ADC")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x10,  # MVI A, 10h
        0x06, 0x20,  # MVI B, 20h
        0x80,        # ADD B (A = 30h)
        0x37,        # STC (CY = 1)
        0x88,        # ADC B (A = 30h + 20h + 1 = 51h)
        0x76         # HLT
    ])
    emu.run()
    
    emu2 = make_emu([
        0x3E, 0x10,  # MVI A, 10h
        0x06, 0x20,  # MVI B, 20h
        0x80,        # ADD B (A = 30h)
        0x76         # HLT
    ])
    emu2.run()
    check("A после ADD B", emu2.a, 0x30)
    check("A после ADC B", emu.a, 0x51)
    
    # =============================================
    # ТЕСТ 12: SUB / SBB
    # =============================================
    print("\nТест 12: SUB / SBB")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x50,  # MVI A, 50h
        0x06, 0x20,  # MVI B, 20h
        0x90,        # SUB B (A = 30h)
        0x37,        # STC (CY = 1)
        0x98,        # SBB B (A = 30h - 20h - 1 = 0Fh)
        0x76         # HLT
    ])
    emu.run()
    check("A после SUB/SBB", emu.a, 0x0F)
    
    # =============================================
    # ТЕСТ 13: Флаг Carry при переполнении
    # =============================================
    print("\nТест 13: Флаг Carry при переполнении")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0xFF,  # MVI A, FFh
        0xC6, 0x01,  # ADI 01h (A = 00h, CY = 1)
        0x76         # HLT
    ])
    emu.run()
    check("A после FFh + 01h", emu.a, 0x00)
    check("CY после переполнения", emu.flag_cy, True)
    check("Z после переполнения", emu.flag_z, True)
    
    # =============================================
    # ТЕСТ 14: Флаг Zero
    # =============================================
    print("\nТест 14: Флаг Zero")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x50,  # MVI A, 50h
        0xD6, 0x50,  # SUI 50h (A = 00h, Z = 1)
        0x76         # HLT
    ])
    emu.run()
    check("A после 50h - 50h", emu.a, 0x00)
    check("Z", emu.flag_z, True)
    check("CY (не было займа)", emu.flag_cy, False)
    
    # =============================================
    # ТЕСТ 15: Логические операции
    # =============================================
    print("\nТест 15: ANA / XRA / ORA")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0xFF,  # MVI A, FFh
        0x06, 0x0F,  # MVI B, 0Fh
        0xA0,        # ANA B (A = 0Fh)
        0x3E, 0xFF,  # MVI A, FFh
        0xA8,        # XRA B (A = F0h)
        0x3E, 0x00,  # MVI A, 00h
        0xB0,        # ORA B (A = 0Fh)
        0x76         # HLT
    ])
    emu.run()
    check("A после ANA/XRA/ORA", emu.a, 0x0F)
    
    # =============================================
    # ТЕСТ 16: CMP (сравнение)
    # =============================================
    print("\nТест 16: CMP")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x50,  # MVI A, 50h
        0xFE, 0x50,  # CPI 50h (A == 50h, Z = 1)
        0x76         # HLT
    ])
    emu.run()
    check("A не изменился после CMP", emu.a, 0x50)
    check("Z после равных значений", emu.flag_z, True)
    
    # =============================================
    # ТЕСТ 17: DAD
    # =============================================
    print("\nТест 17: DAD")
    print("-" * 50)
    emu = make_emu([
        0x21, 0x00, 0x10,  # LXI H, 1000h
        0x01, 0x00, 0x20,  # LXI B, 2000h
        0x09,              # DAD B (HL = 3000h)
        0x76               # HLT
    ])
    emu.run()
    check("HL после DAD B", emu.get_reg_pair('HL'), 0x3000)
    check("CY без переполнения", emu.flag_cy, False)
    
    # =============================================
    # ТЕСТ 18: RLC / RRC
    # =============================================
    print("\nТест 18: RLC / RRC")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x80,  # MVI A, 80h (10000000b)
        0x07,        # RLC (A = 00000001b, CY = 1)
        0x07,        # RLC (A = 00000010b, CY = 0)
        0x0F,        # RRC (A = 00000001b, CY = 0)
        0x76         # HLT
    ])
    emu.run()
    check("A после RLC/RLC/RRC", emu.a, 0x01)
    
    # =============================================
    # ТЕСТ 19: CMA / CMC / STC
    # =============================================
    print("\nТест 19: CMA / CMC / STC")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x0F,  # MVI A, 0Fh
        0x2F,        # CMA (A = F0h)
        0x37,        # STC (CY = 1)
        0x3F,        # CMC (CY = 0)
        0x76         # HLT
    ])
    emu.run()
    check("A после CMA", emu.a, 0xF0)
    check("CY после STC/CMC", emu.flag_cy, False)
    
    # =============================================
    # ТЕСТ 20: DAA (BCD коррекция)
    # =============================================
    print("\nТест 20: DAA")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x15,  # MVI A, 15h (BCD: 15)
        0xC6, 0x27,  # ADI 27h (A = 3Ch, не BCD)
        0x27,        # DAA (A = 42h, BCD: 42)
        0x76         # HLT
    ])
    emu.run()
    check("A после DAA (15+27=42)", emu.a, 0x42)
    
    # =============================================
    # ТЕСТ 21: PUSH / POP (регистровые пары)
    # =============================================
    print("\nТест 21: PUSH / POP (регистровые пары)")
    print("-" * 50)
    emu = make_emu([
        0x01, 0x34, 0x12,  # LXI B, 1234h
        0x11, 0x78, 0x56,  # LXI D, 5678h
        0xC5,              # PUSH B
        0xD5,              # PUSH D
        0x01, 0x00, 0x00,  # LXI B, 0000h
        0x11, 0x00, 0x00,  # LXI D, 0000h
        0xD1,              # POP D (D = 5678h)
        0xC1,              # POP B (B = 1234h)
        0x76               # HLT
    ])
    emu.run()
    check("BC после PUSH/POP", emu.get_reg_pair('BC'), 0x1234)
    check("DE после PUSH/POP", emu.get_reg_pair('DE'), 0x5678)
    
    # =============================================
    # ТЕСТ 22: PUSH / POP PSW
    # =============================================
    print("\nТест 22: PUSH / POP PSW (A и флаги)")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x55,        # MVI A, 55h
        0x37,              # STC (CY = 1)
        0xF5,              # PUSH PSW
        0x3E, 0x00,        # MVI A, 00h (сбросить A)
        0x3F,              # CMC (CY = 0)
        0xF1,              # POP PSW (A = 55h, CY = 1)
        0x76               # HLT
    ])
    emu.run()
    check("A после PUSH/POP PSW", emu.a, 0x55)
    check("CY после PUSH/POP PSW", emu.flag_cy, True)
    
    # =============================================
    # ТЕСТ 23: CALL / RET (простой вызов)
    # =============================================
    print("\nТест 23: CALL / RET")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x00,        # MVI A, 00h         [0000]
        0xCD, 0x08, 0x00,  # CALL 0008h         [0002]
        0x3C,              # INR A (после возврата) [0005]
        0x3C,              # INR A               [0006]
        0x76,              # HLT                 [0007]
        0x00,              # NOP (пропускается)  [0008]
        0x3C,              # INR A (внутри подпрограммы) [0009]
        0xC9,              # RET                 [000A]
    ])
    emu.run()
    # После выполнения: MVI A,0 -> CALL -> INR A -> RET -> INR A -> INR A -> HLT
    # A должен быть 3
    check("A после CALL/RET", emu.a, 0x03)
    
    # =============================================
    # ТЕСТ 24: CALL cc / RET cc (условные вызовы)
    # =============================================
    print("\nТест 24: CALL cc / RET cc")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x01,        # MVI A, 01h         [0000]
        0x3D,              # DCR A (A=0, Z=1)   [0002]
        0xCC, 0x08, 0x00,  # CZ 0008h           [0003]
        0x76,              # HLT                 [0006]
        0x00,              # NOP                  [0007]
        0x3C,              # INR A (A=1, Z=0)   [0008]
        0xC0,              # RNZ                  [0009]
        0x3C,              # INR A (не должно)  [000A]
    ])
    emu.run()
    check("A после условного CALL/RET", emu.a, 0x01)
    check("CPU halted", emu.halted, True)
    
    # =============================================
    # ТЕСТ 25: RST (перезапуск по векторам)
    # =============================================
    print("\nТест 25: RST (перезапуск)")
    print("-" * 50)
    # Программа: RST 3 → вектор 0018h → INR A → RET → HLT
    program = [0x00] * 0x1B  # 27 байт памяти
    program[0x00] = 0xDF  # RST 3 (вектор 0x18)
    program[0x18] = 0x3C  # INR A (по адресу 0018h)
    program[0x19] = 0xC9  # RET
    program[0x01] = 0x76  # HLT (после возврата)
    
    emu = make_emu(program)
    emu.run()
    check("A после RST 3", emu.a, 0x01)
    check("CPU halted", emu.halted, True)
    
    # =============================================
    # ТЕСТ 26: Вложенные вызовы
    # =============================================
    print("\nТест 26: Вложенные вызовы")
    print("-" * 50)
    emu = make_emu([
        # Главная программа
        0x3E, 0x00,        # MVI A, 00h         [0000]
        0xCD, 0x07, 0x00,  # CALL sub1          [0002]
        0x76,              # HLT                 [0005]
        0x00,              # NOP                  [0006]
        # sub1
        0x3C,              # INR A (A=1)        [0007]
        0xCD, 0x0D, 0x00,  # CALL sub2          [0008]
        0xC9,              # RET                 [000B]
        0x00,              # NOP                  [000C]
        # sub2
        0x3C,              # INR A (A=2)        [000D]
        0xC9,              # RET                 [000E]
    ])
    emu.run()
    check("A после вложенных вызовов", emu.a, 0x02)
    
    # =============================================
    # ТЕСТ 27: Рекурсия (сумма 1+2+3+4+5 = 15)
    # =============================================
    print("\nТест 27: Рекурсия (суммирование)")
    print("-" * 50)
    emu = make_emu([
        # Главная программа
        0x3E, 0x05,        # MVI A, 5           [0000]
        0xCD, 0x06, 0x00,  # CALL sum           [0002]
        0x76,              # HLT (A=15=0Fh)     [0005]
        # sum(n): вход A=n, выход A=1+2+...+n
        0xFE, 0x00,        # CPI 0              [0006]
        0xC8,              # RZ (вернуть 0)     [0008]
        0x47,              # MOV B, A (n)       [0009]
        0x3D,              # DCR A (n-1)        [000A]
        0xC5,              # PUSH B (сохранить n) [000B]
        0xCD, 0x06, 0x00,  # CALL sum           [000C]
        0xC1,              # POP B (n)          [000F]
        0x80,              # ADD B (A+=n)       [0010]
        0xC9,              # RET                 [0011]
    ])
    emu.run()
    check("Сумма 1+2+3+4+5 = 15", emu.a, 0x0F)
	
	# =============================================
    # ТЕСТ 28: OUT / IN
    # =============================================
    print("\nТест 28: OUT / IN")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0x55,        # MVI A, 55h        [0000]
        0xD3, 0x01,        # OUT 01h           [0002]
        0x3E, 0x00,        # MVI A, 00h        [0004]
        0xDB, 0x01,        # IN 01h            [0006]
        0x76               # HLT               [0008]
    ])
    emu.run()
    check("A после OUT/IN", emu.a, 0x55)
    check("Порт 01h содержит 55h", emu.io_ports.get(0x01), 0x55)
    
    # =============================================
    # ТЕСТ 29: DI / EI
    # =============================================
    print("\nТест 29: DI / EI")
    print("-" * 50)
    emu = make_emu([
        0xFB,              # EI (прерывания разрешены)  [0000]
        0x00,              # NOP                         [0001]
        0xF3,              # DI (прерывания запрещены)  [0002]
        0x00,              # NOP                         [0003]
        0xFB,              # EI (прерывания разрешены)  [0004]
        0x76               # HLT                         [0005]
    ])
    emu.run()
    check("Прерывания разрешены после EI", emu.interrupts_enabled, True)
    
    # =============================================
    # ТЕСТ 30: Несколько портов IO
    # =============================================
    print("\nТест 30: Несколько портов IO")
    print("-" * 50)
    emu = make_emu([
        0x3E, 0xAA,        # MVI A, AAh        [0000]
        0xD3, 0x10,        # OUT 10h           [0002]
        0x3E, 0xBB,        # MVI A, BBh        [0004]
        0xD3, 0x20,        # OUT 20h           [0006]
        0x3E, 0x00,        # MVI A, 00h        [0008]
        0xDB, 0x10,        # IN 10h (A=AAh)    [000A]
        0xD3, 0x30,        # OUT 30h (30h=AAh) [000C]
        0xDB, 0x20,        # IN 20h (A=BBh)    [000E]
        0x76               # HLT               [0010]
    ])
    emu.run()
    check("Порт 10h = AAh", emu.io_ports.get(0x10), 0xAA)
    check("Порт 20h = BBh", emu.io_ports.get(0x20), 0xBB)
    check("Порт 30h = AAh (из IN 10h)", emu.io_ports.get(0x30), 0xAA)  # ← Исправлено
    check("A = BBh (из порта 20h)", emu.a, 0xBB)
	
	# =============================================
    # ИТОГИ
    # =============================================
    print("\n" + "=" * 70)
    print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
    print("=" * 70)
    
    if failed == 0:
        print(" ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(" ❌ Есть проваленные тесты.")


if __name__ == "__main__":
    run_tests()