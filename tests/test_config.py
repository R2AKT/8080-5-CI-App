"""Тест конфигурации устройств и профилей систем (итерации 9.1 + 9.2)"""
import sys
from modules.config.device_config import DeviceConfig, DeviceFactory
from modules.config.system_profiles import SYSTEM_PROFILES, get_profile, get_profile_names
from modules.memory.memory_bus import MemoryBus

# Проверка доступности TOML-парсера
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

passed = 0
failed = 0
skipped = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

def skip(name, reason):
    global skipped
    print(f"  ⏭ {name}: пропущено ({reason})")
    skipped += 1

if tomllib is None:
    print("⚠ tomllib/tomli не установлен. Установите: pip install tomli")
    print("Тесты конфигурации пропущены.")
    sys.exit(0)

# =============================================
# ТЕСТ 1: Парсинг TOML-строки
# =============================================
print("\nТест 1: Парсинг TOML-строки")
print("-" * 50)

toml_str = """
[system]
name = "Test System"
cpu = "i8080"
clock_mhz = 2.0

[[memory]]
type = "ram"
start = 0x0000
end = 0x7FFF
name = "RAM"

[[devices]]
type = "i8255"
name = "PPI-0"
base_port = 0x00

[[devices]]
type = "i8253"
name = "PIT-0"
base_port = 0x10
"""

config = DeviceConfig()
config.load_from_string(toml_str)

check("Имя системы", config.system_name, "Test System")
check("CPU", config.cpu, "i8080")
check("Частота", config.clock_mhz, 2.0)
check("Регионов памяти", len(config.memory_regions), 1)
check("Устройств", len(config.devices), 2)
check("Тип устройства 1", config.devices[0]["type"], "i8255")
check("Порт устройства 1", config.devices[0]["base_port"], 0x00)
check("Порт устройства 2", config.devices[1]["base_port"], 0x10)

# =============================================
# ТЕСТ 2: Проверка конфликтов портов
# =============================================
print("\nТест 2: Проверка конфликтов портов")
print("-" * 50)

# Конфликт: i8255 (4 порта: 00-03) пересекается с i8253 (4 порта: 02-05)
toml_conflict = """
[system]
name = "Conflict"

[[devices]]
type = "i8255"
name = "PPI-0"
base_port = 0x00

[[devices]]
type = "i8253"
name = "PIT-0"
base_port = 0x02
"""

config_conflict = DeviceConfig()
config_conflict.load_from_string(toml_conflict)
errors = config_conflict.validate()
check("Конфликт обнаружен", len(errors) > 0, True)

# Без конфликта
toml_ok = """
[system]
name = "No Conflict"

[[devices]]
type = "i8255"
name = "PPI-0"
base_port = 0x00

[[devices]]
type = "i8253"
name = "PIT-0"
base_port = 0x10
"""

config_ok = DeviceConfig()
config_ok.load_from_string(toml_ok)
errors_ok = config_ok.validate()
check("Конфликтов нет", len(errors_ok), 0)

# =============================================
# ТЕСТ 3: Фабрика устройств
# =============================================
print("\nТест 3: Фабрика устройств")
print("-" * 50)

bus = MemoryBus()
created = []
for dev_config in config_ok.devices:
    device = DeviceFactory.create_device(dev_config, memory_bus=bus)
    if device is not None:
        created.append(device)

check("Создано 2 устройства", len(created), 2)
check("Имя устройства 1", created[0].name, "PPI-0")
check("Порт устройства 1", created[0].base_port, 0x00)
check("Имя устройства 2", created[1].name, "PIT-0")
check("Порт устройства 2", created[1].base_port, 0x10)

# Неизвестный тип устройства
unknown = DeviceFactory.create_device({"type": "unknown", "name": "X", "base_port": 0x50})
check("Неизвестный тип → None", unknown, None)

# =============================================
# ТЕСТ 4: Список профилей
# =============================================
print("\nТест 4: Список профилей")
print("-" * 50)

profiles = get_profile_names()
check("Количество профилей ≥ 3", len(profiles) >= 3, True)
check("radio86rk доступен", "radio86rk" in profiles, True)
check("micro80 доступен", "micro80" in profiles, True)
check("vector06c доступен", "vector06c" in profiles, True)

# =============================================
# ТЕСТ 5: Профиль Радио-86РК
# =============================================
print("\nТест 5: Профиль Радио-86РК")
print("-" * 50)

profile = get_profile("radio86rk")
check("Имя профиля", profile["name"], "Радио-86РК")

config5 = DeviceConfig()
config5.load_from_string(profile["toml"])

check("Имя системы", config5.system_name, "Радио-86РК")
check("Частота 1.78 МГц", config5.clock_mhz, 1.78)
check("Регионов памяти: 2", len(config5.memory_regions), 2)
check("Устройств: 2", len(config5.devices), 2)
check("RAM: 0x0000-0xBFFF", (config5.memory_regions[0]["start"], config5.memory_regions[0]["end"]), (0x0000, 0xBFFF))
check("ROM: 0xC000-0xFFFF", (config5.memory_regions[1]["start"], config5.memory_regions[1]["end"]), (0xC000, 0xFFFF))
check("Устройство 1: i8255", config5.devices[0]["type"], "i8255")
check("Устройство 2: i8253", config5.devices[1]["type"], "i8253")
check("Конфликтов нет", len(config5.validate()), 0)

# =============================================
# ТЕСТ 6: Профиль Микро-80
# =============================================
print("\nТест 6: Профиль Микро-80")
print("-" * 50)

profile6 = get_profile("micro80")
config6 = DeviceConfig()
config6.load_from_string(profile6["toml"])

check("Имя системы", config6.system_name, "Микро-80")
check("Частота 1.0 МГц", config6.clock_mhz, 1.0)
check("Регионов памяти: 2", len(config6.memory_regions), 2)
check("Устройств: 1", len(config6.devices), 1)
check("RAM: 0x0000-0x7FFF", (config6.memory_regions[0]["start"], config6.memory_regions[0]["end"]), (0x0000, 0x7FFF))
check("ROM: 0x8000-0xFFFF", (config6.memory_regions[1]["start"], config6.memory_regions[1]["end"]), (0x8000, 0xFFFF))
check("Конфликтов нет", len(config6.validate()), 0)

# =============================================
# ТЕСТ 7: Профиль Вектор-06Ц
# =============================================
print("\nТест 7: Профиль Вектор-06Ц")
print("-" * 50)

profile7 = get_profile("vector06c")
config7 = DeviceConfig()
config7.load_from_string(profile7["toml"])

check("Имя системы", config7.system_name, "Вектор-06Ц")
check("Частота 3.0 МГц", config7.clock_mhz, 3.0)
check("Устройств: 6", len(config7.devices), 6)

device_types = [d["type"] for d in config7.devices]
check("i8255 в списке", "i8255" in device_types, True)
check("i8253 в списке", "i8253" in device_types, True)
check("i8257 в списке", "i8257" in device_types, True)
check("i8272 в списке", "i8272" in device_types, True)
check("i8276 в списке", "i8276" in device_types, True)
check("lcd1602 в списке", "lcd1602" in device_types, True)
check("Конфликтов нет", len(config7.validate()), 0)

# =============================================
# ТЕСТ 8: Создание памяти из конфигурации
# =============================================
print("\nТест 8: Создание памяти из конфигурации")
print("-" * 50)

bus8 = MemoryBus()
for mem_config in config5.memory_regions:
    region = DeviceFactory.create_memory_region(mem_config)
    if region is not None:
        bus8.register_memory(region)

check("Регионы зарегистрированы", len(bus8.memory_regions), 2)

# Проверка чтения/записи через шину
bus8.write(0x0100, 0xAB)
check("Запись в RAM через шину", bus8.read(0x0100), 0xAB)

# =============================================
# ТЕСТ 9: Интеграционный тест (полный цикл)
# =============================================
print("\nТест 9: Интеграционный тест (Вектор-06Ц)")
print("-" * 50)

bus9 = MemoryBus()

# Создаём память
for mem_config in config7.memory_regions:
    region = DeviceFactory.create_memory_region(mem_config)
    if region is not None:
        bus9.register_memory(region)

# Создаём устройства
created9 = []
for dev_config in config7.devices:
    device = DeviceFactory.create_device(dev_config, memory_bus=bus9)
    if device is not None:
        created9.append(device)

check("Все устройства созданы", len(created9), 6)

# Проверка, что устройства на разных портах
ports = [d.base_port for d in created9]
check("Все порты уникальны", len(ports) == len(set(ports)), True)

# Проверка IO через шину
# PPI на порту 0x00: запись в порт A
bus9.io_write(0x00, 0x55)
check("IO запись через шину", True, True)  # Не должно быть исключения

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено, {skipped} пропущено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ КОНФИГУРАЦИИ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИИ 9.1 + 9.2 ЗАВЕРШЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
