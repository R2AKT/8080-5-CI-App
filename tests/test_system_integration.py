"""Тест интеграции системы (итерация 10.4)"""
from modules.system import ComputerSystem
from modules.config.system_profiles import get_profile_names

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
# ТЕСТ 1: Загрузка всех профилей
# =============================================
print("\nТест 1: Загрузка всех профилей")
print("-" * 50)

for profile_name in get_profile_names():
    system = ComputerSystem()
    system.load_profile(profile_name)
    check(f"Профиль {profile_name} загружен",
          system.profile_name, profile_name)
    check(f"Профиль {profile_name}: устройства созданы",
          len(system.devices) > 0, True)

# =============================================
# ТЕСТ 2: Уникальность адресов устройств
# =============================================
print("\nТест 2: Уникальность адресов устройств")
print("-" * 50)

for profile_name in get_profile_names():
    system = ComputerSystem()
    system.load_profile(profile_name)

    ports = [d.base_port for d in system.devices.values()]
    check(f"Профиль {profile_name}: все адреса уникальны",
          len(ports) == len(set(ports)), True)

# =============================================
# ТЕСТ 3: Доступ к устройствам по имени
# =============================================
print("\nТест 3: Доступ к устройствам по имени")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")

ppi = system.get_device("PPI-0")
check("PPI-0 найден", ppi is not None, True)
check("PPI-0 адрес 0x00", ppi.base_port, 0x00)

pit = system.get_device("PIT-0")
check("PIT-0 найден", pit is not None, True)
check("PIT-0 адрес 0x04", pit.base_port, 0x04)

# =============================================
# ТЕСТ 4: Переключение профилей
# =============================================
print("\nТест 4: Переключение профилей")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")
check("Начальный профиль", system.profile_name, "radio86rk")
check("Устройств в радио86рк", len(system.devices), 2)

system.load_profile("vector06c")
check("Профиль переключён", system.profile_name, "vector06c")
check("Устройств в вектор06ц", len(system.devices), 6)

system.load_profile("radio86rk")
check("Профиль переключён обратно", system.profile_name, "radio86rk")
check("Устройств снова 2", len(system.devices), 2)

# =============================================
# ТЕСТ 5: Вектор-06Ц — все устройства на месте
# =============================================
print("\nТест 5: Вектор-06Ц — состав устройств")
print("-" * 50)

system = ComputerSystem()
system.load_profile("vector06c")

expected_devices = ["PPI-0", "PIT-0", "DMA-0", "FDC-0", "CRT-0", "LCD-0"]
for dev_name in expected_devices:
    device = system.get_device(dev_name)
    check(f"{dev_name} найден", device is not None, True)

# Проверка адресов (не должно быть конфликтов)
errors = system.config.validate()
check("Конфликтов нет", len(errors), 0)

# =============================================
# ТЕСТ 6: Работа через шину памяти
# =============================================
print("\nТест 6: Работа через шину памяти")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")

# Запись в RAM
system.bus.write(0x0100, 0xAB)
check("Запись в RAM", system.bus.read(0x0100), 0xAB)

# IO запись в PPI (порт 0x00)
system.bus.io_write(0x00, 0x55)
check("IO запись без исключения", True, True)

# =============================================
# ТЕСТ 7: Callback для прерываний (подготовка к 10.1)
# =============================================
print("\nТест 7: Callback для прерываний")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")

irq_events = []
result = system.set_callback("PIT-0", "on_irq",
                            lambda ch, active: irq_events.append((ch, active)))
check("Callback PIT-0 установлен", result, True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ИНТЕГРАЦИИ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 10.4 ЗАВЕРШЕНА!")
    print("    Теперь можно подключать прерывания (10.1),")
    print("    ПДП (10.2) и WAIT-сигналы (10.3)")
    print("    к реальным адресам устройств.")
else:
    print(" ❌ Есть проваленные тесты.")
