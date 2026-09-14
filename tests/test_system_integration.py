"""Тест интеграции системы (итерация 10.4)"""
from modules.system import ComputerSystem
from modules.config.system_profiles import get_profile_names

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274c {name}: ожидалось {expected}, получено {actual}")
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
    # "empty" профиль — без устройств
    if profile_name == "empty":
        check(f"Профиль empty: нет устройств", len(system.devices), 0)
    else:
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

    # Только устройства с реальными IO-портами
    ports = [d.base_port for d in system.devices.values()
             if getattr(d, 'base_port', -1) >= 0]
    check(f"Профиль {profile_name}: все адреса уникальны",
          len(ports) == len(set(ports)), True)

# =============================================
# ТЕСТ 3: Доступ к устройствам по имени (radio86rk)
# =============================================
print("\nТест 3: Доступ к устройствам по имени")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")

ppi = system.get_device("PPI")
check("PPI найден", ppi is not None, True)
if ppi:
    check("PPI адрес 0x00", ppi.base_port, 0x00)

crt = system.get_device("CRT")
check("CRT найден", crt is not None, True)
if crt:
    check("CRT адрес 0x08", crt.base_port, 0x08)

# Неведомое устройство
check("Неизвестное устройство: None", system.get_device("XYZ-123"), None)

# =============================================
# ТЕСТ 4: Вектор-06Ц — состав устройств
# =============================================
print("\nТест 4: Вектор-06Ц — состав устройств")
print("-" * 50)

system = ComputerSystem()
system.load_profile("vector06c")

check("Вектор-06Ц: устройств >= 2", len(system.devices) >= 2, True)

# Реальные имена из профиля
ppi_v = system.get_device("PPI System/Keyboard")
check("PPI System/Keyboard найден", ppi_v is not None, True)
if ppi_v:
    check("PPI адрес 0x00", ppi_v.base_port, 0x00)

pit = system.get_device("PIT Timer")
check("PIT Timer найден", pit is not None, True)
if pit:
    check("PIT адрес 0x04", pit.base_port, 0x04)

# Проверка адресов (не должно быть конфликтов)
errors = system.config.validate()
check("Конфликтов портов нет", len(errors), 0)

# =============================================
# ТЕСТ 5: Работа через шину памяти
# =============================================
print("\nТест 5: Работа через шину памяти")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")

# Запись в RAM
system.bus.write(0x0100, 0xAB)
check("Запись в RAM", system.bus.read(0x0100), 0xAB)

# IO запись в PPI (порт 0x00)
# Сначала устанавливаем Port A в режим вывода: 1000 0000
system.bus.io_write(0x03, 0x80)
system.bus.io_write(0x00, 0x55)
check("IO запись без исключения", True, True)

# Чтение из PPI (Port A теперь в режиме вывода)
val = system.bus.io_read(0x00)
check("IO чтение PPI Port A (output mode)", val, 0x55)

# =============================================
# ТЕСТ 6: Callback для прерываний
# =============================================
print("\nТест 6: Callback для прерываний")
print("-" * 50)

system = ComputerSystem()
system.load_profile("vector06c")

irq_events = []
result = system.set_callback("PIT Timer", "on_irq",
                            lambda ch, active: irq_events.append((ch, active)))
check("Callback PIT Timer установлен", result, True)

# Пустое устройство
result2 = system.set_callback("NO_SUCH", "on_irq", lambda *a: None)
check("Callback на несуществующее: False", result2, False)

# =============================================
# ТЕСТ 7: Переключение профилей
# =============================================
print("\nТест 7: Переключение профилей")
print("-" * 50)

system = ComputerSystem()
system.load_profile("radio86rk")
n1 = len(system.devices)
check("radio86rk: устройств > 0", n1 > 0, True)

system.load_profile("vector06c")
n2 = len(system.devices)
check("vector06c: устройств > 0", n2 > 0, True)
check("Профиль переключён", system.profile_name, "vector06c")

system.load_profile("radio86rk")
n3 = len(system.devices)
check("Возврат: устройств = тот же", n3, n1)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" \u2705 ВСЕ ТЕСТЫ ИНТЕГРАЦИИ ПРОЙДЕНЫ!")
else:
    print(" \u274c Есть проваленные тесты.")
