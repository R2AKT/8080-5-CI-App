"""Тест ComputerSystem — полная интеграция (итерация 9.3)"""
from modules.system import ComputerSystem
from modules.config.system_profiles import get_profile_names
from modules.io.i8255 import I8255
from modules.io.i8253 import I8253
from modules.io.lcd1602 import LCD1602

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
# ТЕСТ 1: Создание пустой системы
# =============================================
print("\nТест 1: Создание пустой системы")
print("-" * 50)

system = ComputerSystem()
check("Шина памяти создана", system.bus is not None, True)
check("Нет устройств", len(system.devices), 0)
check("Нет регионов памяти", len(system.memory_regions), 0)

# =============================================
# ТЕСТ 2: Загрузка профиля Радио-86РК
# =============================================
print("\nТест 2: Загрузка профиля Радио-86РК")
print("-" * 50)

system2 = ComputerSystem()
system2.load_profile("radio86rk")

check("Профиль загружен", system2.profile_name, "radio86rk")
check("Имя системы", system2.config.system_name, "Радио-86РК")
check("CPU: i8080", system2.config.cpu, "i8080")
check("Частота: 1.78 МГц", system2.config.clock_mhz, 1.78)
check("Регионов памяти: 2", len(system2.memory_regions), 2)
check("Устройств: 2", len(system2.devices), 2)

# Проверяем типы устройств
device_types = [d.__class__.__name__ for d in system2.devices.values()]
check("I8255 создан", "I8255" in device_types, True)
check("I8253 создан", "I8253" in device_types, True)

# =============================================
# ТЕСТ 3: Загрузка профиля Вектор-06Ц
# =============================================
print("\nТест 3: Загрузка профиля Вектор-06Ц")
print("-" * 50)

system3 = ComputerSystem()
system3.load_profile("vector06c")

check("Профиль загружен", system3.profile_name, "vector06c")
check("Устройств: 6", len(system3.devices), 6)
check("Регионов памяти: 2", len(system3.memory_regions), 2)

device_types = [d.__class__.__name__ for d in system3.devices.values()]
check("I8255 создан", "I8255" in device_types, True)
check("I8272 создан", "I8272" in device_types, True)
check("I8276 создан", "I8276" in device_types, True)
check("LCD1602 создан", "LCD1602" in device_types, True)

# =============================================
# ТЕСТ 4: Доступ к устройствам по имени
# =============================================
print("\nТест 4: Доступ к устройствам по имени")
print("-" * 50)

ppi = system2.get_device("PPI")
check("PPI найден", ppi is not None, True)
check("PPI — правильный тип", isinstance(ppi, I8255), True)
check("PPI порт 0x00", ppi.base_port, 0x00)

pit = system2.get_device("PIT-0")
check("PIT-0 найден", pit is not None, True)
check("PIT-0 — правильный тип", isinstance(pit, I8253), True)

unknown = system2.get_device("UNKNOWN")
check("Неизвестное устройство: None", unknown, None)

# =============================================
# ТЕСТ 5: Поиск устройств по типу
# =============================================
print("\nТест 5: Поиск устройств по типу")
print("-" * 50)

ppis = system2.get_devices_by_type("I8255")
check("Найден 1 PPI", len(ppis), 1)

lcds = system3.get_devices_by_type("LCD1602")
check("Найден 1 LCD", len(lcds), 1)
check("LCD — правильный тип", isinstance(lcds[0], LCD1602), True)

# =============================================
# ТЕСТ 6: Работа с шиной памяти
# =============================================
print("\nТест 6: Работа с шиной памяти")
print("-" * 50)

# Запись в RAM (0x0000-0xBFFF для Радио-86РК)
system2.bus.write(0x1000, 0xAB)
check("Запись в RAM", system2.bus.read(0x1000), 0xAB)

# Запись в ROM (0xC000-0xFFFF) — должна быть запрещена
try:
    system2.bus.write(0xC100, 0xCD)
    # Если не исключение — читаем, должно остаться 0x00 или оригинал
    val = system2.bus.read(0xC100)
    check("ROM защищена от записи", val != 0xCD, True)
except Exception:
    check("ROM защищена от записи (исключение)", True, True)

# =============================================
# ТЕСТ 7: IO через шину
# =============================================
print("\nТест 7: IO через шину")
print("-" * 50)

# Сначала устанавливаем режим (сброс портов)
system2.bus.io_write(0x03, 0x80)  # Mode 0, все порты на выход
# Потом записываем данные
system2.bus.io_write(0x00, 0x55)
# Потом читаем
val = system2.bus.io_read(0x00)
check("IO чтение PPI", val, 0x55)

# =============================================
# ТЕСТ 8: Список устройств
# =============================================
print("\nТест 8: Список устройств")
print("-" * 50)

device_list = system2.list_devices()
check("Список содержит 2 устройства", len(device_list), 2)
check("Первое устройство имеет имя", "name" in device_list[0], True)
check("Первое устройство имеет тип", "type" in device_list[0], True)

# =============================================
# ТЕСТ 9: Callbacks для устройств
# =============================================
print("\nТест 9: Callbacks для устройств")
print("-" * 50)

irq_events = []
result = system2.set_callback("PIT-0", "on_irq",
                             lambda ch, active: irq_events.append((ch, active)))
check("Callback установлен", result, True)

# Неизвестный callback
result2 = system2.set_callback("PIT-0", "unknown_callback", lambda: None)
check("Неизвестный callback: False", result2, False)

# Неизвестное устройство
result3 = system2.set_callback("UNKNOWN", "on_irq", lambda: None)
check("Неизвестное устройство: False", result3, False)

# =============================================
# ТЕСТ 10: Полное состояние системы
# =============================================
print("\nТест 10: Полное состояние системы")
print("-" * 50)

state = system2.get_state()
check("Профиль в состоянии", state["profile_name"], "radio86rk")
check("Имя системы", state["system_name"], "Радио-86РК")
check("CPU в состоянии", state["cpu"], "i8080")
check("Устройств в состоянии", state["devices_count"], 2)
check("Состояния устройств — словарь", isinstance(state["devices"], dict), True)

# =============================================
# ТЕСТ 11: Перезагрузка профиля (смена системы)
# =============================================
print("\nТест 11: Перезагрузка профиля")
print("-" * 50)

system4 = ComputerSystem()
system4.load_profile("radio86rk")
check("Радио-86РК: 2 устройства", len(system4.devices), 2)

# Переключаемся на Вектор-06Ц
system4.load_profile("vector06c")
check("Вектор-06Ц: 6 устройств", len(system4.devices), 6)
check("Старые устройства очищены", system4.profile_name, "vector06c")

# =============================================
# ТЕСТ 12: Загрузка из TOML-строки
# =============================================
print("\nТест 12: Загрузка из TOML-строки")
print("-" * 50)

custom_toml = """
[system]
name = "Custom System"
cpu = "i8080"
clock_mhz = 2.5

[[memory]]
type = "ram"
start = 0x0000
end = 0xFFFF
name = "Full RAM"

[[devices]]
type = "i8255"
name = "MY-PPI"
base_port = 0x40

[[devices]]
type = "lcd2004"
name = "MY-LCD"
base_port = 0x50
"""

system5 = ComputerSystem()
system5.load_from_toml_string(custom_toml, name="custom_test")

check("Профиль custom", system5.profile_name, "custom_test")
check("Имя: Custom System", system5.config.system_name, "Custom System")
check("Частота: 2.5 МГц", system5.config.clock_mhz, 2.5)
check("Устройств: 2", len(system5.devices), 2)
check("MY-PPI создан", system5.get_device("MY-PPI") is not None, True)
check("MY-LCD создан", system5.get_device("MY-LCD") is not None, True)

# =============================================
# ТЕСТ 13: Валидация конфликтов при загрузке
# =============================================
print("\nТест 13: Валидация конфликтов")
print("-" * 50)

conflict_toml = """
[system]
name = "Conflict"

[[devices]]
type = "i8255"
name = "PPI"
base_port = 0x00

[[devices]]
type = "i8253"
name = "PIT"
base_port = 0x02
"""

system6 = ComputerSystem()
try:
    system6.load_from_toml_string(conflict_toml)
    check("Конфликт вызвал исключение", False, True)
except ValueError as e:
    check("Конфликт вызвал ValueError", "Конфликт" in str(e) or "пересекается" in str(e), True)

# =============================================
# ТЕСТ 14: Неизвестный профиль
# =============================================
print("\nТест 14: Неизвестный профиль")
print("-" * 50)

system7 = ComputerSystem()
try:
    system7.load_profile("unknown_profile")
    check("Неизвестный профиль вызвал исключение", False, True)
except ValueError:
    check("Неизвестный профиль вызвал ValueError", True, True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ СИСТЕМЫ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 9.3 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
