"""
AM9511 — Арифметический сопроцессор (APU).
Итерация E7: Сопроцессоры и спец-устройства.

Возможности:
- 16-битный целочисленный стековый сопроцессор
- Стек из 4 регистров (TOS, NOS, B, C)
- Арифметические, логические операции и сдвиги
- 3 режима синхронизации с CPU:
  1. Wait State (READY/WAIT) — CPU ждёт завершения
  2. IRQ — прерывание по завершении
  3. DMA+IRQ — запрос DMA для передачи данных

Регистры (2 порта):
  offset 0: Data Port (чтение/запись TOS, 16-bit little-endian)
  offset 1: Command/Status Port (запись команд, чтение статуса)

Команды:
  0x00: NOP
  0x01: POP  — удалить TOS
  0x02: PTOS — дублировать TOS (Push TOS)
  0x60: ADD  — TOS = NOS + TOS
  0x61: SUB  — TOS = NOS - TOS
  0x62: MUL  — [NOS:TOS] = NOS * TOS (32-bit результат)
  0x63: DIV  — NOS = NOS / TOS, TOS = NOS % TOS
  0x70: AND  — TOS = NOS & TOS
  0x71: OR   — TOS = NOS | TOS
  0x72: XOR  — TOS = NOS ^ TOS
  0x74: SL   — TOS = TOS << 1
  0x75: SR   — TOS = TOS >> 1 (логический)
  0x76: SRA  — TOS = TOS >> 1 (арифметический)

Статус (Status Register):
  Bit 7: BUSY     (1 = операция выполняется)
  Bit 6: END      (1 = операция завершена, сбрасывается при чтении)
  Bit 5: CARRY    (перенос/заём)
  Bit 4: ZERO     (результат = 0)
  Bit 3: SIGN     (бит 15 результата = 1)
  Bit 2: OVERFLOW (знаковое переполнение)
  Bit 1-0: DIVIDE ERROR / SHIFT ERROR
"""
from .iodevice import IODevice


class AM9511(IODevice):
    """AM9511 — арифметический стековый сопроцессор"""

    # Команды
    CMD_NOP  = 0x00
    CMD_POP  = 0x01
    CMD_PTOS = 0x02
    CMD_ADD  = 0x60
    CMD_SUB  = 0x61
    CMD_MUL  = 0x62
    CMD_DIV  = 0x63
    CMD_AND  = 0x70
    CMD_OR   = 0x71
    CMD_XOR  = 0x72
    CMD_SL   = 0x74
    CMD_SR   = 0x75
    CMD_SRA  = 0x76

    # Биты статуса
    STATUS_BUSY     = 0x80
    STATUS_END      = 0x40
    STATUS_CARRY    = 0x20
    STATUS_ZERO     = 0x10
    STATUS_SIGN     = 0x08
    STATUS_OVERFLOW = 0x04
    STATUS_DIV_ERR  = 0x02

    # Режимы синхронизации
    MODE_WAIT = 0  # Wait State (CPU ждёт)
    MODE_IRQ  = 1  # Прерывание по завершении
    MODE_DMA  = 2  # DMA + IRQ

    def __init__(self, base_port, name="AM9511"):
        super().__init__(base_port, 2, name)
        self.reset()
        # Callbacks
        self.on_irq = None   # callback(active)
        self.on_drq = None   # callback(active)
        self.on_wait = None  # callback(active) — для сигнала WAIT процессору

    def reset(self):
        """Сброс сопроцессора"""
        # Стек (4 элемента по 16 бит, индекс 0 = TOS)
        self.stack = [0, 0, 0, 0]
        # Статус и флаги
        self.status = 0
        self.busy = False
        self.end_flag = False
        self.flag_carry = False
        self.flag_zero = False
        self.flag_sign = False
        self.flag_overflow = False
        self.flag_div_err = False
        # Такты выполнения текущей операции
        self.exec_cycles = 0
        # Режим синхронизации
        self.sync_mode = self.MODE_WAIT
        # Состояние чтения/записи 16-битного порта (little-endian)
        self.read_state = 0   # 0=LSB, 1=MSB
        self.write_state = 0  # 0=LSB, 1=MSB
        self.data_latch = 0   # Младший байт при записи

    # =============================================
    # СТЕК
    # =============================================
    def _tos(self):
        """Верхний элемент стека (Top of Stack)"""
        return self.stack[0]

    def _nos(self):
        """Следующий элемент стека (Next on Stack)"""
        return self.stack[1]

    def _push(self, value):
        """Затолкнуть 16-битное значение в стек"""
        value &= 0xFFFF
        self.stack[3] = self.stack[2]
        self.stack[2] = self.stack[1]
        self.stack[1] = self.stack[0]
        self.stack[0] = value

    def _pop(self):
        """Вытолкнуть TOS из стека"""
        self.stack[0] = self.stack[1]
        self.stack[1] = self.stack[2]
        self.stack[2] = self.stack[3]
        self.stack[3] = 0

    def _pop2(self):
        """Вытолкнуть TOS и NOS (после бинарной операции)"""
        self.stack[0] = self.stack[2]
        self.stack[1] = self.stack[3]
        self.stack[2] = 0
        self.stack[3] = 0

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Data Port: чтение TOS (little-endian)
            return self._read_data()
        elif offset == 1:
            # Status Port
            return self._read_status()
        return 0xFF

    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        value &= 0xFF
        if offset == 0:
            # Data Port: запись в стек (little-endian)
            self._write_data(value)
        elif offset == 1:
            # Command Port
            self._write_command(value)

    def _read_data(self):
        """Чтение 16-битного TOS побайтно"""
        if self.read_state == 0:
            # Младший байт
            self.read_state = 1
            return self._tos() & 0xFF
        else:
            # Старший байт + POP
            self.read_state = 0
            val = (self._tos() >> 8) & 0xFF
            self._pop()
            return val

    def _write_data(self, value):
        """Запись 16-битного значения в стек побайтно"""
        if self.write_state == 0:
            self.data_latch = value
            self.write_state = 1
        else:
            val = (value << 8) | self.data_latch
            self._push(val)
            self.write_state = 0

    def _read_status(self):
        """Чтение регистра статуса"""
        status = 0
        if self.busy:
            status |= self.STATUS_BUSY
        if self.end_flag:
            status |= self.STATUS_END
            self.end_flag = False  # Сброс при чтении
        if self.flag_carry:
            status |= self.STATUS_CARRY
        if self.flag_zero:
            status |= self.STATUS_ZERO
        if self.flag_sign:
            status |= self.STATUS_SIGN
        if self.flag_overflow:
            status |= self.STATUS_OVERFLOW
        if self.flag_div_err:
            status |= self.STATUS_DIV_ERR
        return status

    def _write_command(self, cmd):
        """Запись команды"""
        if self.busy:
            return  # Игнорируем команды во время выполнения

        # Сброс флагов перед новой операцией
        self.flag_carry = False
        self.flag_zero = False
        self.flag_sign = False
        self.flag_overflow = False
        self.flag_div_err = False
        self.end_flag = False

        if cmd == self.CMD_NOP:
            return
        elif cmd == self.CMD_POP:
            self._pop()
            return
        elif cmd == self.CMD_PTOS:
            self._push(self._tos())
            return

        # Операции, требующие времени выполнения
        self.busy = True
        self._current_cmd = cmd

        # Устанавливаем время выполнения (в тактах CPU)
        if cmd in (self.CMD_MUL, self.CMD_DIV):
            self.exec_cycles = 30
        elif cmd in (self.CMD_ADD, self.CMD_SUB):
            self.exec_cycles = 10
        else:
            self.exec_cycles = 5

        # Wait State: уведомляем CPU о занятости
        if self.sync_mode == self.MODE_WAIT and self.on_wait:
            self.on_wait(True)

    # =============================================
    # TICK — выполнение операций
    # =============================================
    def tick(self, cycles=1):
        """Вызывается каждый такт CPU. Уменьшает счётчик выполнения."""
        if not self.busy:
            return

        self.exec_cycles -= cycles
        if self.exec_cycles <= 0:
            self._execute_command()
            self.busy = False
            self.end_flag = True

            # Снятие Wait State
            if self.sync_mode == self.MODE_WAIT and self.on_wait:
                self.on_wait(False)

            # IRQ по завершении
            if self.sync_mode == self.MODE_IRQ and self.on_irq:
                self.on_irq(True)

            # DMA + IRQ
            elif self.sync_mode == self.MODE_DMA:
                if self.on_drq:
                    self.on_drq(True)
                if self.on_irq:
                    self.on_irq(True)

    def _execute_command(self):
        """Выполнение сохранённой команды"""
        cmd = getattr(self, '_current_cmd', self.CMD_NOP)
        tos = self._tos()
        nos = self._nos()

        if cmd == self.CMD_ADD:
            result = tos + nos
            self.flag_carry = result > 0xFFFF
            self._pop2()
            self._push(result & 0xFFFF)
            self._update_flags(result & 0xFFFF)

        elif cmd == self.CMD_SUB:
            result = nos - tos
            self.flag_carry = nos < tos  # Заём
            self._pop2()
            self._push(result & 0xFFFF)
            self._update_flags(result & 0xFFFF)
            # Знаковое переполнение для SUB
            self.flag_overflow = self._check_sub_overflow(nos, tos, result & 0xFFFF)

        elif cmd == self.CMD_MUL:
            # 16x16 = 32 бит. TOS = low, NOS = high
            result = tos * nos
            low = result & 0xFFFF
            high = (result >> 16) & 0xFFFF
            self._pop2()
            self._push(high)  # ← Сначала high (становится NOS)
            self._push(low)   # ← Затем low (становится TOS)
            self.flag_carry = high != 0
            self._update_flags(low)

        elif cmd == self.CMD_DIV:
            if tos == 0:
                self.flag_div_err = True
                self._pop2()
                self._push(0xFFFF)
                self._push(0xFFFF)
            else:
                quotient = nos // tos
                remainder = nos % tos
                self._pop2()
                self._push(quotient)   # ← Сначала quotient (становится NOS)
                self._push(remainder)  # ← Затем remainder (становится TOS)
                self._update_flags(quotient)

        elif cmd == self.CMD_AND:
            result = tos & nos
            self._pop2()
            self._push(result)
            self._update_flags(result)

        elif cmd == self.CMD_OR:
            result = tos | nos
            self._pop2()
            self._push(result)
            self._update_flags(result)

        elif cmd == self.CMD_XOR:
            result = tos ^ nos
            self._pop2()
            self._push(result)
            self._update_flags(result)

        elif cmd == self.CMD_SL:
            self.flag_carry = bool(tos & 0x8000)
            result = (tos << 1) & 0xFFFF
            self.stack[0] = result
            self._update_flags(result)

        elif cmd == self.CMD_SR:
            self.flag_carry = bool(tos & 0x0001)
            result = (tos >> 1) & 0xFFFF
            self.stack[0] = result
            self._update_flags(result)

        elif cmd == self.CMD_SRA:
            self.flag_carry = bool(tos & 0x0001)
            sign_bit = tos & 0x8000
            result = ((tos >> 1) | sign_bit) & 0xFFFF
            self.stack[0] = result
            self._update_flags(result)

    def _update_flags(self, result):
        """Обновление флагов Zero и Sign"""
        result &= 0xFFFF
        self.flag_zero = (result == 0)
        self.flag_sign = bool(result & 0x8000)

    def _check_sub_overflow(self, a, b, result):
        """Проверка знакового переполнения при вычитании"""
        # Переполнение если: (a положительно, b отрицательно, результат отрицательный)
        # или (a отрицательно, b положительно, результат положительный)
        a_sign = bool(a & 0x8000)
        b_sign = bool(b & 0x8000)
        r_sign = bool(result & 0x8000)
        return (not a_sign and b_sign and r_sign) or (a_sign and not b_sign and not r_sign)

    # =============================================
    # УТИЛИТЫ
    # =============================================
    def is_busy(self):
        """Проверка занятости (для Wait State)"""
        return self.busy

    def set_sync_mode(self, mode):
        """Установить режим синхронизации"""
        self.sync_mode = mode

    def get_stack(self):
        """Получить содержимое стека (для отладки)"""
        return list(self.stack)

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "stack": [f"0x{v:04X}" for v in self.stack],
            "busy": self.busy,
            "end_flag": self.end_flag,
            "sync_mode": ["WAIT", "IRQ", "DMA"][self.sync_mode],
            "flags": {
                "C": self.flag_carry,
                "Z": self.flag_zero,
                "S": self.flag_sign,
                "O": self.flag_overflow,
            },
            "status": f"0x{self._read_status():02X}",
        }
