"""
512ВИ1 (КР512ВИ1) — часы реального времени с энергонезависимой памятью.
Аналог Dallas DS1287 / Motorola MC146818.
Итерация E6: Хранение.

Возможности:
- Часы реального времени (секунды, минуты, часы, день, месяц, год)
- Календарь с автоматической корректировкой високосных годов
- Энергонезависимая RAM (50 байт, адреса 0x0E-0x3F)
- Регистры A, B, C, D для управления
- Прерывания (обновление времени, будильник)
- Инициализация времени по системным часам при старте
- Опциональная загрузка/сохранение NVM во внешний файл (путь из TOML)

Регистры (2 порта):
  offset 0: Address Register (запись номера регистра 0x00-0x3F)
  offset 1: Data Register (чтение/запись данных)

Карта регистров:
  0x00: Секунды (0-59)
  0x01: Будильник секунды
  0x02: Минуты (0-59)
  0x03: Будильник минуты
  0x04: Часы (0-23 или 1-12 AM/PM)
  0x05: Будильник часы
  0x06: День недели (1-7)
  0x07: День месяца (1-31)
  0x08: Месяц (1-12)
  0x09: Год (0-99)
  0x0A: Регистр A (UIP, DV, RS)
  0x0B: Регистр B (SET, PIE, AIE, UIE, SQWE, DM, 24/12, DSE)
  0x0C: Регистр C (IRQF, PF, AF, UF) — только чтение
  0x0D: Регистр D (VRT) — только чтение
  0x0E-0x3F: Энергонезависимая RAM (50 байт)
"""
from .iodevice import IODevice
import time
import os


class I512VI1(IODevice):
    """512ВИ1 — часы реального времени с энергонезависимой памятью"""

    # Размер энергонезависимой памяти (байт)
    NVM_SIZE = 50
    NVM_START = 0x0E

    # Адреса регистров
    REG_SECONDS   = 0x00
    REG_ALARM_SEC = 0x01
    REG_MINUTES   = 0x02
    REG_ALARM_MIN = 0x03
    REG_HOURS     = 0x04
    REG_ALARM_HRS = 0x05
    REG_DOW       = 0x06  # Day of Week
    REG_DOM       = 0x07  # Day of Month
    REG_MONTH     = 0x08
    REG_YEAR      = 0x09
    REG_A         = 0x0A
    REG_B         = 0x0B
    REG_C         = 0x0C
    REG_D         = 0x0D

    # Биты регистра B
    B_SET  = 0x80  # Остановка обновления
    B_PIE  = 0x40  # Periodic Interrupt Enable
    B_AIE  = 0x20  # Alarm Interrupt Enable
    B_UIE  = 0x10  # Update-ended Interrupt Enable
    B_SQWE = 0x08  # Square Wave Enable
    B_DM   = 0x04  # Data Mode (1=binary, 0=BCD)
    B_24H  = 0x02  # 24/12 часов
    B_DSE  = 0x01  # Daylight Saving Enable

    # Биты регистра C
    C_IRQF = 0x80  # Interrupt Request Flag
    C_PF   = 0x40  # Periodic Flag
    C_AF   = 0x20  # Alarm Flag
    C_UF   = 0x10  # Update-ended Flag

    # Биты регистра D
    D_VRT  = 0x80  # Valid RAM and Time

    # Значение "don't care" для будильника
    ALARM_DONT_CARE = 0xC0

    def __init__(self, base_port, name="I512VI1"):
        super().__init__(base_port, 2, name)
        self.nvm_file = None       # Путь к файлу NVM (из TOML)
        self.on_irq = None         # Callback прерывания
        self._last_tick = time.time()
        self.reset()

    def reset(self):
        """Сброс модуля"""
        self.current_reg = self.REG_D
        # Регистры управления
        self.reg_a = 0x26          # DV=010, RS=0110
        self.reg_b = self.B_24H    # 24 часа, BCD
        self.reg_c = 0x00
        self.reg_d = self.D_VRT
        # Время
        self.seconds = 0
        self.minutes = 0
        self.hours = 0
        self.day_of_week = 1
        self.day_of_month = 1
        self.month = 1
        self.year = 0
        # Будильник
        self.alarm_sec = self.ALARM_DONT_CARE
        self.alarm_min = self.ALARM_DONT_CARE
        self.alarm_hrs = self.ALARM_DONT_CARE
        # NVM
        self.nvm = [0x00] * self.NVM_SIZE
        self._last_tick = time.time()

    # =============================================
    # ИНИЦИАЛИЗАЦИЯ ВРЕМЕНИ
    # =============================================
    def init_from_system_time(self):
        """Инициализация времени по системным часам"""
        now = time.localtime()
        self.seconds = now.tm_sec
        self.minutes = now.tm_min
        self.hours = now.tm_hour
        self.day_of_week = now.tm_wday + 1  # 1-7
        self.day_of_month = now.tm_mday
        self.month = now.tm_mon
        self.year = now.tm_year % 100
        self._last_tick = time.time()

    # =============================================
    # ОБНОВЛЕНИЕ ВРЕМЕНИ (tick)
    # =============================================
    def tick(self, cycles=1):
        """Обновление времени по реальному системному времени"""
        if self.reg_b & self.B_SET:
            return  # Время остановлено (SET=1)

        now = time.time()
        elapsed = now - self._last_tick

        if elapsed >= 1.0:
            seconds_elapsed = int(elapsed)
            self._last_tick = now
            for _ in range(seconds_elapsed):
                self._update_time()

    def _update_time(self):
        """Обновление времени на 1 секунду"""
        # Проверка SET режима — время остановлено
        if self.reg_b & self.B_SET:
            return
        self.seconds += 1
        if self.seconds >= 60:
            self.seconds = 0
            self.minutes += 1
            if self.minutes >= 60:
                self.minutes = 0
                self.hours += 1
                if self.hours >= 24:
                    self.hours = 0
                    self._increment_day()
        # Проверка будильника
        self._check_alarm()
        # Флаг UF (Update-ended)
        self.reg_c |= self.C_UF
        if self.reg_b & self.B_UIE:
            self.reg_c |= self.C_IRQF
            if self.on_irq:
                self.on_irq(True)

    def _increment_day(self):
        """Инкремент дня с учётом месяцев и високосных годов"""
        self.day_of_week += 1
        if self.day_of_week > 7:
            self.day_of_week = 1
        self.day_of_month += 1
        if self.day_of_month > self._days_in_month(self.month, self.year):
            self.day_of_month = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year = (self.year + 1) % 100

    def _days_in_month(self, month, year):
        """Количество дней в месяце с учётом високосного года"""
        if month in (1, 3, 5, 7, 8, 10, 12):
            return 31
        elif month in (4, 6, 9, 11):
            return 30
        elif month == 2:
            full_year = 2000 + year
            if full_year % 4 == 0 and (full_year % 100 != 0 or full_year % 400 == 0):
                return 29
            return 28
        return 30

    def _check_alarm(self):
        """Проверка будильника"""
        if not (self.reg_b & self.B_AIE):
            return

        match = True
        if self.alarm_sec != self.ALARM_DONT_CARE and self.alarm_sec != self.seconds:
            match = False
        if self.alarm_min != self.ALARM_DONT_CARE and self.alarm_min != self.minutes:
            match = False
        if self.alarm_hrs != self.ALARM_DONT_CARE and self.alarm_hrs != self.hours:
            match = False

        if match:
            self.reg_c |= self.C_AF | self.C_IRQF
            if self.on_irq:
                self.on_irq(True)

    # =============================================
    # BCD / BINARY ПРЕОБРАЗОВАНИЯ
    # =============================================
    def _is_binary(self):
        """Проверка режима данных (DM бит регистра B)"""
        return bool(self.reg_b & self.B_DM)

    def _encode(self, value):
        """Кодирование значения в зависимости от режима DM"""
        if self._is_binary():
            return value & 0xFF
        return ((value // 10) << 4) | (value % 10)

    def _decode(self, value):
        """Декодирование значения в зависимости от режима DM"""
        if self._is_binary():
            return value & 0xFF
        return ((value >> 4) * 10) + (value & 0x0F)

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            return self.current_reg
        elif offset == 1:
            return self._read_reg(self.current_reg)
        return 0xFF

    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        if offset == 0:
            self.current_reg = value & 0x3F
        elif offset == 1:
            self._write_reg(self.current_reg, value)

    def _read_reg(self, reg):
        """Чтение регистра"""
        if reg == self.REG_SECONDS:
            return self._encode(self.seconds)
        elif reg == self.REG_MINUTES:
            return self._encode(self.minutes)
        elif reg == self.REG_HOURS:
            return self._encode(self.hours)
        elif reg == self.REG_DOW:
            return self._encode(self.day_of_week)
        elif reg == self.REG_DOM:
            return self._encode(self.day_of_month)
        elif reg == self.REG_MONTH:
            return self._encode(self.month)
        elif reg == self.REG_YEAR:
            return self._encode(self.year)
        elif reg == self.REG_ALARM_SEC:
            return self.alarm_sec
        elif reg == self.REG_ALARM_MIN:
            return self.alarm_min
        elif reg == self.REG_ALARM_HRS:
            return self.alarm_hrs
        elif reg == self.REG_A:
            return self.reg_a
        elif reg == self.REG_B:
            return self.reg_b
        elif reg == self.REG_C:
            result = self.reg_c
            self.reg_c = 0x00  # Чтение C сбрасывает флаги
            if self.on_irq:
                self.on_irq(False)
            return result
        elif reg == self.REG_D:
            return self.reg_d
        elif self.NVM_START <= reg <= 0x3F:
            return self.nvm[reg - self.NVM_START]
        return 0xFF

    def _write_reg(self, reg, value):
        """Запись регистра"""
        if reg == self.REG_SECONDS:
            self.seconds = self._decode(value)
        elif reg == self.REG_MINUTES:
            self.minutes = self._decode(value)
        elif reg == self.REG_HOURS:
            self.hours = self._decode(value)
        elif reg == self.REG_DOW:
            self.day_of_week = self._decode(value)
        elif reg == self.REG_DOM:
            self.day_of_month = self._decode(value)
        elif reg == self.REG_MONTH:
            self.month = self._decode(value)
        elif reg == self.REG_YEAR:
            self.year = self._decode(value)
        elif reg == self.REG_ALARM_SEC:
            self.alarm_sec = value
        elif reg == self.REG_ALARM_MIN:
            self.alarm_min = value
        elif reg == self.REG_ALARM_HRS:
            self.alarm_hrs = value
        elif reg == self.REG_A:
            # Бит UIP только чтение
            self.reg_a = (value & 0x7F) | (self.reg_a & 0x80)
        elif reg == self.REG_B:
            self.reg_b = value
        elif reg in (self.REG_C, self.REG_D):
            pass  # Только чтение
        elif self.NVM_START <= reg <= 0x3F:
            self.nvm[reg - self.NVM_START] = value

    # =============================================
    # ЭНЕРГОНЕЗАВИСИМАЯ ПАМЯТЬ (NVM)
    # =============================================
    def set_nvm_file(self, path):
        """Установить путь к файлу NVM (из TOML-конфигурации)"""
        self.nvm_file = path

    def load_nvm(self):
        """Загрузить NVM из файла. Возвращает True при успехе."""
        if not self.nvm_file or not os.path.exists(self.nvm_file):
            return False
        try:
            with open(self.nvm_file, 'rb') as f:
                data = f.read(self.NVM_SIZE)
            for i in range(min(len(data), self.NVM_SIZE)):
                self.nvm[i] = data[i]
            return True
        except OSError:
            return False

    def save_nvm(self):
        """Сохранить NVM в файл. Возвращает True при успехе."""
        if not self.nvm_file:
            return False
        try:
            with open(self.nvm_file, 'wb') as f:
                f.write(bytes(self.nvm))
            return True
        except OSError:
            return False

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "time": f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}",
            "date": f"{self.day_of_month:02d}.{self.month:02d}.{self.year:02d}",
            "day_of_week": self.day_of_week,
            "reg_a": f"0x{self.reg_a:02X}",
            "reg_b": f"0x{self.reg_b:02X}",
            "reg_c": f"0x{self.reg_c:02X}",
            "reg_d": f"0x{self.reg_d:02X}",
            "set_mode": bool(self.reg_b & self.B_SET),
            "binary_mode": self._is_binary(),
            "nvm_file": self.nvm_file,
        }
