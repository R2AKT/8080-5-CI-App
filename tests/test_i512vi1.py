"""Тест I512VI1 RTC (итерация E6)"""
import os
import tempfile
from modules.memory.memory_bus import MemoryBus
from modules.io.i512vi1 import I512VI1

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: Инициализация и сброс
# =============================================
print("\nТест 1: Инициализация и сброс")
print("-" * 50)

bus = MemoryBus()
rtc = I512VI1(base_port=0x70)
rtc.register_to_bus(bus)

check("Регистр D: VRT=1", rtc.reg_d & 0x80, 0x80)
check("Режим 24 часа", bool(rtc.reg_b & I512VI1.B_24H), True)
check("Режим BCD", bool(rtc.reg_b & I512VI1.B_DM), False)

# =============================================
# ТЕСТ 2: Инициализация по системным часам
# =============================================
print("\nТест 2: Инициализация по системным часам")
print("-" * 50)

rtc.init_from_system_time()
import time as _time
now = _time.localtime()

check("Секунды из системы", rtc.seconds, now.tm_sec)
check("Минуты из системы", rtc.minutes, now.tm_min)
check("Часы из системы", rtc.hours, now.tm_hour)
check("День из системы", rtc.day_of_month, now.tm_mday)
check("Месяц из системы", rtc.month, now.tm_mon)

# =============================================
# ТЕСТ 3: Чтение времени через порты (BCD)
# =============================================
print("\nТест 3: Чтение времени через порты (BCD)")
print("-" * 50)

rtc.seconds = 30
rtc.minutes = 45
rtc.hours = 12

bus.io_write(0x70, I512VI1.REG_SECONDS)
check("Секунды BCD (30)", bus.io_read(0x71), 0x30)

bus.io_write(0x70, I512VI1.REG_MINUTES)
check("Минуты BCD (45)", bus.io_read(0x71), 0x45)

bus.io_write(0x70, I512VI1.REG_HOURS)
check("Часы BCD (12)", bus.io_read(0x71), 0x12)

# =============================================
# ТЕСТ 4: Запись времени через порты (BCD)
# =============================================
print("\nТест 4: Запись времени через порты (BCD)")
print("-" * 50)

bus.io_write(0x70, I512VI1.REG_SECONDS)
bus.io_write(0x71, 0x59)  # 59 BCD
check("Секунды записаны", rtc.seconds, 59)

bus.io_write(0x70, I512VI1.REG_HOURS)
bus.io_write(0x71, 0x23)  # 23 BCD
check("Часы записаны", rtc.hours, 23)

# =============================================
# ТЕСТ 5: Binary режим (DM=1)
# =============================================
print("\nТест 5: Binary режим (DM=1)")
print("-" * 50)

rtc.reg_b |= I512VI1.B_DM  # Binary mode
rtc.seconds = 59

bus.io_write(0x70, I512VI1.REG_SECONDS)
check("Секунды binary (59)", bus.io_read(0x71), 59)

bus.io_write(0x70, I512VI1.REG_SECONDS)
bus.io_write(0x71, 42)  # Binary
check("Секунды binary записаны", rtc.seconds, 42)

rtc.reg_b &= ~I512VI1.B_DM  # Вернуть BCD

# =============================================
# ТЕСТ 6: NVM — чтение/запись
# =============================================
print("\nТест 6: NVM — чтение/запись")
print("-" * 50)

# Запись в NVM (адрес 0x0E)
bus.io_write(0x70, 0x0E)
bus.io_write(0x71, 0xAA)
check("NVM[0] записано", rtc.nvm[0], 0xAA)

# Чтение из NVM
bus.io_write(0x70, 0x0E)
check("NVM[0] прочитано", bus.io_read(0x71), 0xAA)

# Запись в последний байт NVM (адрес 0x3F)
bus.io_write(0x70, 0x3F)
bus.io_write(0x71, 0xBB)
check("NVM[49] записано", rtc.nvm[49], 0xBB)

# =============================================
# ТЕСТ 7: NVM — сохранение и загрузка из файла
# =============================================
print("\nТест 7: NVM — сохранение и загрузка из файла")
print("-" * 50)

# Создаём временный файл
with tempfile.NamedTemporaryFile(delete=False, suffix='.nvm') as f:
    nvm_path = f.name

try:
    # Заполняем NVM данными
    for i in range(I512VI1.NVM_SIZE):
        rtc.nvm[i] = i & 0xFF

    # Сохраняем
    rtc.set_nvm_file(nvm_path)
    save_ok = rtc.save_nvm()
    check("NVM сохранён", save_ok, True)

    # Очищаем NVM
    rtc.nvm = [0x00] * I512VI1.NVM_SIZE

    # Загружаем
    load_ok = rtc.load_nvm()
    check("NVM загружен", load_ok, True)
    check("NVM[0] после загрузки", rtc.nvm[0], 0x00)
    check("NVM[10] после загрузки", rtc.nvm[10], 0x0A)
    check("NVM[49] после загрузки", rtc.nvm[49], 0x31)
finally:
    if os.path.exists(nvm_path):
        os.remove(nvm_path)

# =============================================
# ТЕСТ 8: Регистр C — чтение сбрасывает флаги
# =============================================
print("\nТест 8: Регистр C — чтение сбрасывает флаги")
print("-" * 50)

rtc.reg_c = I512VI1.C_UF | I512VI1.C_AF
bus.io_write(0x70, I512VI1.REG_C)
val = bus.io_read(0x71)
check("Регистр C прочитан", val & 0x30, 0x30)

bus.io_write(0x70, I512VI1.REG_C)
val2 = bus.io_read(0x71)
check("Регистр C сброшен после чтения", val2, 0x00)

# =============================================
# ТЕСТ 9: SET режим (остановка времени)
# =============================================
print("\nТест 9: SET режим (остановка времени)")
print("-" * 50)

rtc.reg_b |= I512VI1.B_SET
rtc.seconds = 30
old_sec = rtc.seconds
rtc._update_time()  # Не должно обновиться
check("Время остановлено (SET=1)", rtc.seconds, old_sec)

rtc.reg_b &= ~I512VI1.B_SET
rtc._update_time()
check("Время обновляется (SET=0)", rtc.seconds, old_sec + 1)

# =============================================
# ТЕСТ 10: Високосный год
# =============================================
print("\nТест 10: Високосный год")
print("-" * 50)

check("Февраль 2024 (29 дней)", rtc._days_in_month(2, 24), 29)
check("Февраль 2023 (28 дней)", rtc._days_in_month(2, 23), 28)
check("Февраль 2000 (29 дней)", rtc._days_in_month(2, 0), 29)

# =============================================
# ТЕСТ 11: Будильник
# =============================================
print("\nТест 11: Будильник")
print("-" * 50)

irq_events = []
rtc.on_irq = lambda active: irq_events.append(active)

rtc.reg_b |= I512VI1.B_AIE  # Разрешить прерывание будильника
rtc.alarm_sec = 30
rtc.alarm_min = I512VI1.ALARM_DONT_CARE
rtc.alarm_hrs = I512VI1.ALARM_DONT_CARE

rtc.seconds = 30
rtc.minutes = 15
rtc.hours = 10

rtc._check_alarm()
check("Будильник сработал", bool(rtc.reg_c & I512VI1.C_AF), True)
check("IRQ сгенерирован", len(irq_events) > 0 and irq_events[-1], True)

# =============================================
# ТЕСТ 12: Переход через полночь
# =============================================
print("\nТест 12: Переход через полночь")
print("-" * 50)

rtc.reg_b &= ~I512VI1.B_SET
rtc.seconds = 59
rtc.minutes = 59
rtc.hours = 23
rtc.day_of_month = 31
rtc.month = 12
rtc.year = 25
rtc.day_of_week = 3

rtc._update_time()
check("Секунды = 0", rtc.seconds, 0)
check("Минуты = 0", rtc.minutes, 0)
check("Часы = 0", rtc.hours, 0)
check("День = 1", rtc.day_of_month, 1)
check("Месяц = 1", rtc.month, 1)
check("Год = 26", rtc.year, 26)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I512VI1 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
