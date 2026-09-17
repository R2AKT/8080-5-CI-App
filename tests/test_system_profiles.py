"""Тест профилей систем (итерация 9.2)"""
from modules.config.system_profiles import SYSTEM_PROFILES, get_profile, get_profile_names
from modules.config.device_config import DeviceConfig, DeviceFactory

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
# ТЕСТ 1: Список профилей
# =============================================
print("\nТест 1: Список профилей")
print("-" * 50)

profiles = get_profile_names()
check("Доступные профили >= 11", len(profiles) >= 11, True)
check("Профиль radio86rk", "radio86rk" in profiles, True)
check("Профиль micro80", "micro80" in profiles, True)
check("Профиль vector06c", "vector06c" in profiles, True)

# =============================================
# =============================================
# ТЕСТ 2: Загрузка профиля Радио-86РК
# =============================================
print("\nТест 2: Загрузка профиля Радио-86РК")
print("-" * 50)

profile = get_profile("radio86rk")
check("Имя профиля", profile["name"], "radio86rk")

config = DeviceConfig()
config.load_from_dict(profile["config"])

check("Имя системы", config.system_name, "Радио-86РК")
check("Частота", config.clock_mhz, 1.78)
check("Количество регионов памяти", len(config.memory_regions), 3)
check("Количество устройств", len(config.devices), 3)

# Проверка регионов памяти
ram_region = config.memory_regions[0]
check("RAM start", ram_region["start"], 0x0000)
check("RAM end", ram_region["end"], 0x3FFF)

rom_region = config.memory_regions[1]
check("ROM start", rom_region["start"], 0xF800)
check("ROM end", rom_region["end"], 0xFFFF)

# Проверка устройств
ppi_dev = config.devices[0]
check("Тип устройства 1", ppi_dev["type"], "i8255")
check("Порт PPI", ppi_dev["base_port"], 0x00)

kbd_dev = config.devices[1]
check("Тип устройства 2", kbd_dev["type"], "keyboard8x8")

crt_dev = config.devices[2]
check("Тип устройства 3", crt_dev["type"], "i8275")
check("Порт CRT", crt_dev["base_port"], 0x08)

# ТЕСТ 3: Загрузка профиля Микро-80
# =============================================
# =============================================
# ТЕСТ 3: Загрузка профиля Микро-80
# =============================================
print("\nТест 3: Загрузка профиля Микро-80")
print("-" * 50)

profile = get_profile("micro80")
check("Имя профиля", profile["name"], "micro80")

config = DeviceConfig()
config.load_from_dict(profile["config"])

check("Имя системы", config.system_name, "Микро-80")
check("Частота", config.clock_mhz, 1.78)
check("Количество регионов памяти", len(config.memory_regions), 3)
check("Количество устройств", len(config.devices), 3)

# Проверка регионов памяти
ram_region = config.memory_regions[0]
check("RAM start", ram_region["start"], 0x0000)
check("RAM end", ram_region["end"], 0x3FFF)

rom_region = config.memory_regions[1]
check("ROM start", rom_region["start"], 0xF800)
check("ROM end", rom_region["end"], 0xFFFF)

video_region = config.memory_regions[2]
check("Video RAM start", video_region["start"], 0xE000)
check("Video RAM end", video_region["end"], 0xEFFF)

# Проверка устройств
ppi_dev = config.devices[0]
check("Тип устройства 1", ppi_dev["type"], "i8255")
check("Порт PPI", ppi_dev["base_port"], 0x04)

kbd_dev = config.devices[1]
check("Тип устройства 2", kbd_dev["type"], "keyboard8x8")

vid_dev = config.devices[2]
check("Тип устройства 3", vid_dev["type"], "discrete_video")

# ТЕСТ 4: Загрузка профиля Вектор-06Ц
# =============================================
print("\nТест 4: Загрузка профиля Вектор-06Ц")
print("-" * 50)

profile = get_profile("vector06c")
config = DeviceConfig()
config.load_from_dict(profile["config"])

check("Имя системы", config.system_name, "Вектор-06Ц")
check("Частота", config.clock_mhz, 3.0)
check("Количество регионов памяти", len(config.memory_regions), 1)
check("Количество устройств", len(config.devices), 2)

# Проверка всех устройств
device_types = [d["type"] for d in config.devices]
check("i8255 в списке", "i8255" in device_types, True)
check("i8253 в списке", "i8253" in device_types, True)
check("i8253 в списке", "i8253" in device_types, True)
check("i8255 в списке", "i8255" in device_types, True)
check("PIT Timer по имени", any("PIT" in d["name"] for d in config.devices), True)
check("2 устройства всего", len(device_types), 2)

# Проверка портов (не должно быть конфликтов)
errors = config.validate()
check("Конфликтов портов нет", len(errors), 0)

# =============================================
# ТЕСТ 5: Создание устройств из профиля
# =============================================
print("\nТест 5: Создание устройств из профиля")
print("-" * 50)

profile = get_profile("radio86rk")
config = DeviceConfig()
config.load_from_dict(profile["config"])

from modules.memory.memory_bus import MemoryBus
bus = MemoryBus()

created_devices = []
for dev_config in config.devices:
    device = DeviceFactory.create_device(dev_config, memory_bus=bus)
    if device is not None:
        created_devices.append(device)

check("Создано 3 устройства", len(created_devices), 3)
check("Первое устройство: PPI", created_devices[0].name, "PPI")
check("Порт PPI-0", created_devices[0].base_port, 0x00)
check("Второе устройство: Keyboard", created_devices[1].name, "Keyboard")
check("Порт CRT", created_devices[2].base_port, 0x08)

# =============================================
# ТЕСТ 6: Проверка конфликтов портов
# =============================================
print("\nТест 6: Проверка конфликтов портов")
print("-" * 50)

# Создаём профиль с конфликтом
conflict_toml = """
[system]
name = "Conflict Test"

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
config_conflict.load_from_string(conflict_toml)
errors = config_conflict.validate()
check("Конфликт обнаружен", len(errors) > 0, True)

# Профиль без конфликтов
no_conflict_toml = """
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

config_no_conflict = DeviceConfig()
config_no_conflict.load_from_string(no_conflict_toml)
errors = config_no_conflict.validate()
check("Конфликтов нет", len(errors), 0)

# =============================================
# ТЕСТ 7: Создание памяти из профиля
# =============================================
print("\nТест 7: Создание памяти из профиля")
print("-" * 50)

profile = get_profile("radio86rk")
config = DeviceConfig()
config.load_from_dict(profile["config"])

bus2 = MemoryBus()
for mem_config in config.memory_regions:
    region = DeviceFactory.create_memory_region(mem_config)
    if region is not None:
        bus2.register_memory(region)

check("Регионы памяти зарегистрированы", len(bus2.memory_regions), 3)

# Проверяем, что RAM и ROM зарегистрированы
ram_found = any("RAM" in getattr(r, "name", "") for r in bus2.memory_regions)
rom_found = any("ROM" in getattr(r, "name", "") for r in bus2.memory_regions)
check("RAM найден", ram_found, True)
check("ROM найден", rom_found, True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ПРОФИЛЕЙ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 9.2 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
