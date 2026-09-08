"""
8259/8259A — Programmable Interrupt Controller.
Итерация E3: базовые IO-устройства.

Различия:
  - 8259  (КР580ВН59):  ICW1, ICW2, ICW3. НЕТ ICW4. Только режим 8080.
  - 8259A (КР1810ВН59): ICW1, ICW2, ICW3, ICW4. Режимы 8080/8086,
                        Auto-EOI, Fully Nested Mode.

8 линий IRQ0-IRQ7, фиксированный приоритет с ротацией,
маскирование (IMR), EOI (специфический/неспецифический).
"""

from .iodevice import IODevice


class I8259(IODevice):
    """8259 (КР580ВН59) — контроллер прерываний БЕЗ ICW4.
    
    Только режим MCS-80 (8080). Нет Auto-EOI и Fully Nested Mode.
    Последовательность: ICW1 → ICW2 → ICW3 → READY.
    """

    # Состояния конечного автомата инициализации
    STATE_READY = 0      # Инициализирован, режим OCW
    STATE_ICW2 = 1       # Ожидание ICW2
    STATE_ICW3 = 2       # Ожидание ICW3

    def __init__(self, base_port, name="I8259"):
        super().__init__(base_port, 2, name)
        self.reset()
        # Callback при готовности прерывания: on_int(vector, irq_num)
        self.on_int = None

    def reset(self):
        """Сброс контроллера"""
        # Основные регистры
        self.imr = 0x00
        self.irr = 0x00
        self.isr = 0x00
        # Слова инициализации
        self.icw1 = 0x00
        self.icw2 = 0x00
        self.icw3 = 0x00
        self.icw4 = 0x00
        # Конечный автомат
        self.state = self.STATE_READY
        # Режимы (у 8259 фиксированные, без ICW4)
        self.is_8086 = False
        self.auto_eoi = False
        self.fully_nested = False
        # Приоритет: от наивысшего к низшему
        self.priority = list(range(8))
        # Выбор чтения IRR/ISR (OCW3)
        self._read_isr = False
        # Режим опроса
        self.poll_mode = False
        # Ротация приоритета при EOI (OCW2)
        self.rotate_on_eoi = False

    # =============================================
    # ЗАПРОСЫ ПРЕРЫВАНИЙ (от устройств)
    # =============================================
    def request_irq(self, irq_num):
        """Запрос прерывания по линии IRQ (фронт)"""
        if 0 <= irq_num < 8:
            self.irr |= (1 << irq_num)

    def release_irq(self, irq_num):
        """Освобождение линии IRQ (level-triggered)"""
        if 0 <= irq_num < 8:
            self.irr &= ~(1 << irq_num)

    # =============================================
    # РАЗРЕШЕНИЕ ПРЕРЫВАНИЙ
    # =============================================
    def has_interrupt(self):
        """Есть ли ожидающее прерывание, готовое к обслуживанию"""
        return self._resolve() is not None

    def _resolve(self):
        """Разрешить прерывание с наивысшим приоритетом"""
        pending = self.irr & ~self.imr
        if not pending:
            return None

        # В normal mode новое прерывание не обслуживается, если уже есть
        # in-service с более высоким приоритетом
        if self.isr and not self.special_mask_mode():
            in_service = self._highest_priority(self.isr)
            if in_service is not None:
                pending_best = self._highest_priority(pending)
                if not self._is_higher_priority(pending_best, in_service):
                    return None

        return self._highest_priority(pending)

    def special_mask_mode(self):
        """У 8259 нет special mask mode (всегда False)"""
        return False

    def _highest_priority(self, mask):
        """Вернуть IRQ с наивысшим приоритетом из маски"""
        for irq in self.priority:
            if mask & (1 << irq):
                return irq
        return None

    def _is_higher_priority(self, irq_a, irq_b):
        """irq_a имеет более высокий приоритет, чем irq_b?"""
        if irq_a is None:
            return False
        if irq_b is None:
            return True
        return self.priority.index(irq_a) < self.priority.index(irq_b)

    def get_vector(self, auto_acknowledge=True):
        """Получить вектор прерывания и подтвердить его.
        Вектор = (ICW2 & 0xF8) | irq_number.
        """
        irq = self._resolve()
        if irq is None:
            return None

        if auto_acknowledge:
            self.acknowledge(irq)

        vector = (self.icw2 & 0xF8) | irq

        if self.on_int:
            self.on_int(vector, irq)

        return vector

    def acknowledge(self, irq):
        """Подтвердить прерывание: IRR → ISR"""
        self.irr &= ~(1 << irq)
        self.isr |= (1 << irq)
        if self.auto_eoi:
            # Auto-EOI: сразу снимаем ISR (только у 8259A)
            self.isr &= ~(1 << irq)

    # =============================================
    # EOI (END OF INTERRUPT)
    # =============================================
    def end_of_interrupt(self, irq=None):
        """EOI: конец обработки прерывания"""
        if irq is None:
            irq = self._highest_priority(self.isr)
        if irq is not None:
            self.isr &= ~(1 << irq)
            if self.rotate_on_eoi:
                self._rotate_priority(irq)

    def _rotate_priority(self, irq):
        """Ротация приоритета: irq становится низшим"""
        if irq in self.priority:
            idx = self.priority.index(irq)
            self.priority = self.priority[idx + 1:] + self.priority[:idx + 1]

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = (port - self.base_port) & 0x01
        if offset == 0:
            # Порт 0: IRR или ISR
            if self.poll_mode:
                return self._poll_read()
            return self.isr if self._read_isr else self.irr
        else:
            # Порт 1: IMR
            return self.imr

    def io_write(self, port, value):
        """Запись в порт"""
        value &= 0xFF
        offset = (port - self.base_port) & 0x01
        if offset == 0:
            self._write_port0(value)
        else:
            self._write_port1(value)

    def _write_port0(self, value):
        """Порт 0: ICW1 или OCW2/OCW3"""
        if value & 0x10:
            # ICW1: бит 4 = 1
            self._write_icw1(value)
        elif value & 0x08:
            # OCW3: бит 3 = 1
            self._write_ocw3(value)
        else:
            # OCW2
            self._write_ocw2(value)

    def _write_port1(self, value):
        """Порт 1: ICW2/ICW3 или OCW1 (IMR).
        У 8259 НЕТ ICW4 — после ICW3 сразу READY.
        """
        if self.state == self.STATE_ICW2:
            self.icw2 = value
            if self.icw1 & 0x02:
                # SNGL=1: одиночный режим, без ICW3
                self.state = self.STATE_READY
            else:
                self.state = self.STATE_ICW3
        elif self.state == self.STATE_ICW3:
            self.icw3 = value
            # 8259: после ICW3 сразу READY (нет ICW4)
            self.state = self.STATE_READY
        else:
            # OCW1: IMR
            self.imr = value

    # =============================================
    # INITIALIZATION COMMAND WORDS
    # =============================================
    def _write_icw1(self, value):
        """ICW1: старт инициализации"""
        self.icw1 = value
        # Сброс состояния
        self.imr = 0x00
        self.irr = 0x00
        self.isr = 0x00
        self.priority = list(range(8))
        self._read_isr = False
        self.poll_mode = False
        self.state = self.STATE_ICW2

    # =============================================
    # OPERATION COMMAND WORDS
    # =============================================
    def _write_ocw2(self, value):
        """OCW2: EOI и ротация приоритета"""
        r = bool(value & 0x80)
        sl = bool(value & 0x40)
        eoi = bool(value & 0x20)
        level = value & 0x07

        if eoi and not sl and not r:
            # Неспецифический EOI (001xxxxx)
            self.end_of_interrupt()
        elif eoi and sl and not r:
            # Специфический EOI (011xxxxx)
            self.end_of_interrupt(level)
        elif eoi and not sl and r:
            # Rotate on non-specific EOI (101xxxxx)
            irq = self._highest_priority(self.isr)
            if irq is not None:
                self.isr &= ~(1 << irq)
                self._rotate_priority(irq)
        elif eoi and sl and r:
            # Rotate on specific EOI (111xxxxx)
            self.end_of_interrupt(level)
            self._rotate_priority(level)
        elif not eoi and sl and r:
            # Set priority (110xxxxx)
            self._rotate_priority(level)

    def _write_ocw3(self, value):
        """OCW3: чтение IRR/ISR, poll mode"""
        # Биты 1-0: выбор регистра чтения
        if value & 0x02:
            self._read_isr = bool(value & 0x01)
        # Бит 2: poll mode
        if value & 0x04:
            self.poll_mode = True

    def _poll_read(self):
        """Чтение в poll mode"""
        irq = self._resolve()
        if irq is not None:
            self.acknowledge(irq)
            return 0x80 | irq
        return 0x00

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "imr": f"0x{self.imr:02X}",
            "irr": f"0x{self.irr:02X}",
            "isr": f"0x{self.isr:02X}",
            "icw1": f"0x{self.icw1:02X}",
            "icw2": f"0x{self.icw2:02X}",
            "icw3": f"0x{self.icw3:02X}",
            "state": self.state,
            "priority": self.priority,
            "has_interrupt": self.has_interrupt(),
            "vector_base": f"0x{(self.icw2 & 0xF8):02X}",
        }


class I8259A(I8259):
    """8259A (КР1810ВН59) — контроллер прерываний С ICW4.
    
    Добавляет:
    - ICW4 (режим 8080/8086, Auto-EOI, Fully Nested Mode)
    - Special Mask Mode (через OCW3)
    Последовательность: ICW1 → ICW2 → ICW3 → ICW4 (если IC4=1) → READY.
    """

    # Дополнительное состояние для ICW4
    STATE_ICW4 = 3

    def __init__(self, base_port, name="I8259A"):
        super().__init__(base_port, name)
        # Дополнительные режимы (управляются через ICW4)
        self.special_mask = False

    def reset(self):
        """Сброс с дополнительными режимами 8259A"""
        super().reset()
        self.special_mask = False

    def special_mask_mode(self):
        """У 8259A есть special mask mode"""
        return self.special_mask

    def _write_port1(self, value):
        """Порт 1: ICW2/ICW3/ICW4 или OCW1 (IMR).
        У 8259A ЕСТЬ ICW4.
        """
        if self.state == self.STATE_ICW2:
            self.icw2 = value
            if self.icw1 & 0x02:
                # SNGL=1: одиночный режим, без ICW3
                self._after_icw3()
            else:
                self.state = self.STATE_ICW3
        elif self.state == self.STATE_ICW3:
            self.icw3 = value
            self._after_icw3()
        elif self.state == self.STATE_ICW4:
            self.icw4 = value
            self._apply_icw4()
            self.state = self.STATE_READY
        else:
            # OCW1: IMR
            self.imr = value

    def _after_icw3(self):
        """После ICW3: ICW4 если нужен, иначе READY"""
        if self.icw1 & 0x01:
            # IC4=1: нужен ICW4
            self.state = self.STATE_ICW4
        else:
            self.state = self.STATE_READY

    def _apply_icw4(self):
        """Применить настройки ICW4"""
        self.is_8086 = bool(self.icw4 & 0x01)       # Бит 0: 8086/8080
        self.auto_eoi = bool(self.icw4 & 0x02)      # Бит 1: Auto-EOI
        # Бит 2: M/S (buffered), Бит 3: BUF
        self.fully_nested = bool(self.icw4 & 0x10)  # Бит 4: Fully Nested

    def _write_ocw3(self, value):
        """OCW3: чтение IRR/ISR, poll, special mask (расширено для 8259A)"""
        super()._write_ocw3(value)
        # Биты 6-5: special mask mode (только у 8259A)
        if value & 0x40:
            self.special_mask = bool(value & 0x20)

    def get_state(self):
        """Состояние с дополнительными полями 8259A"""
        state = super().get_state()
        state.update({
            "icw4": f"0x{self.icw4:02X}",
            "is_8086": self.is_8086,
            "auto_eoi": self.auto_eoi,
            "fully_nested": self.fully_nested,
            "special_mask": self.special_mask,
        })
        return state
