"""Тест WAIT-сигналов для CF IDE (итерация 10.3)"""
import os
import tempfile
from modules.memory.memory_bus import MemoryBus
from modules.io.cf_ide import CFIDE

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
# ТЕСТ 1: Инициализация
# =============================================
print("\nТест 1: Инициализация")
print("-" * 50)

bus = MemoryBus()
cf = CFIDE(base_port=0x10, name="CF-0")
cf.register_to_bus(bus)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    cf.set_disk_image(disk_path, size_mb=4)
    check("Образ подключён", cf.disk_file is not None, True)
    check("Не занят", cf.is_busy(), False)
    check("emulate_delay выключен", cf.emulate_delay, False)

    # =============================================
    # ТЕСТ 2: Мгновенное выполнение (без задержки)
    # =============================================
    print("\nТест 2: Мгновенное выполнение")
    print("-" * 50)

    irq_events = []
    cf.on_irq = lambda active: irq_events.append(active)

    # IDENTIFY
    cf.io_write(cf.base_port + 7, CFIDE.CMD_IDENTIFY_DEVICE)
    check("Не занят после IDENTIFY", cf.is_busy(), False)
    check("IRQ сгенерирован", len(irq_events) > 0, True)

    # Чтение данных
    data = [cf.io_read(cf.base_port + 0) for _ in range(10)]
    check("Данные доступны", len(data), 10)

    # =============================================
    # ТЕСТ 3: Включение эмуляции задержки
    # =============================================
    print("\nТест 3: Эмуляция задержки")
    print("-" * 50)

    cf.set_emulate_delay(True)
    check("emulate_delay включён", cf.emulate_delay, True)

    wait_events = []
    cf.on_wait = lambda active: wait_events.append(active)

    # IDENTIFY с задержкой
    cf.io_write(cf.base_port + 7, CFIDE.CMD_IDENTIFY_DEVICE)
    check("Занят после IDENTIFY", cf.is_busy(), True)
    check("on_wait(True) вызван", len(wait_events) > 0 and wait_events[-1], True)

    # Статус показывает BSY
    status = cf.io_read(cf.base_port + 7)
    check("BSY в статусе", bool(status & CFIDE.STATUS_BSY), True)

    # Данные недоступны во время занятости
    data = cf.io_read(cf.base_port + 0)
    check("Данные = 0 во время занятости", data, 0x00)

    # =============================================
    # ТЕСТ 4: Операция завершается через tick
    # =============================================
    print("\nТест 4: Операция завершается через tick")
    print("-" * 50)

    for i in range(35):
        cf.tick(cycles=1)
        if not cf.is_busy():
            break

    check("Операция завершена", cf.is_busy(), False)
    check("on_wait(False) вызван", len(wait_events) >= 2 and wait_events[-1], False)
    check("BSY сброшен", bool(cf.io_read(cf.base_port + 7) & CFIDE.STATUS_BSY), False)

    # Данные доступны
    data = cf.io_read(cf.base_port + 0)
    check("Данные доступны после завершения", data, 0x84)  # Word 0: 0x848A

    # =============================================
    # ТЕСТ 5: Чтение секторов с задержкой
    # =============================================
    print("\nТест 5: Чтение секторов с задержкой")
    print("-" * 50)

    # Устанавливаем LBA mode
    cf.io_write(cf.base_port + 6, 0xE0)  # Device/Head: LBA mode
    cf.io_write(cf.base_port + 3, 0x01)  # LBA Low = 1
    cf.io_write(cf.base_port + 4, 0x00)  # LBA Mid = 0
    cf.io_write(cf.base_port + 5, 0x00)  # LBA High = 0
    cf.io_write(cf.base_port + 2, 0x01)  # Sector Count = 1

    # READ SECTORS
    cf.io_write(cf.base_port + 7, CFIDE.CMD_READ_SECTORS)
    check("Занят после READ", cf.is_busy(), True)

    for i in range(55):
        cf.tick(cycles=1)
        if not cf.is_busy():
            break

    check("READ завершён", cf.is_busy(), False)
    check("DRQ установлен", bool(cf.io_read(cf.base_port + 7) & CFIDE.STATUS_DRQ), True)

    # =============================================
    # ТЕСТ 6: Интеграция с CPU через on_wait
    # =============================================
    print("\nТест 6: Интеграция с CPU")
    print("-" * 50)

    class MockCPU:
        def __init__(self):
            self.wait_signal = False
        def set_wait(self, active):
            self.wait_signal = active

    cpu = MockCPU()
    cf.on_wait = lambda active: cpu.set_wait(active)

    # Запускаем операцию
    cf.io_write(cf.base_port + 6, 0xE0)
    cf.io_write(cf.base_port + 3, 0x02)
    cf.io_write(cf.base_port + 4, 0x00)
    cf.io_write(cf.base_port + 5, 0x00)
    cf.io_write(cf.base_port + 2, 0x01)
    cf.io_write(cf.base_port + 7, CFIDE.CMD_READ_SECTORS)

    check("CPU.wait_signal = True", cpu.wait_signal, True)

    # Завершаем операцию
    for i in range(55):
        cf.tick(cycles=1)
        if not cf.is_busy():
            break

    check("CPU.wait_signal = False", cpu.wait_signal, False)

finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ WAIT CF IDE ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10.3 ЗАВЕРШЕНА!")
    print("    WAIT реализован для: AM9511, CF IDE, CH376S")
else:
    print(" ❌ Есть проваленные тесты.")
