"""Тест режимов 8255"""
dev = None
for d in api.system.devices.values():
    if type(d).__name__ == 'I8255':
        dev = d
        break

if dev is None:
    print("8255 не найден!")
else:
    base = dev.base_port
    
    # === Режим 0: все порты на выход ===
    print("=== Режим 0: все порты на ВЫХОД ===")
    dev.io_write(base + 3, 0x80)  # Все порты — выход
    modes = dev.get_port_modes()
    print(f"  A: режим {modes['a_mode']}, {modes['a_direction']}")
    print(f"  B: режим {modes['b_mode']}, {modes['b_direction']}")
    print(f"  CL: {modes['c_low_direction']}, CH: {modes['c_high_direction']}")
    
    # === Режим 0: все порты на вход ===
    print("\n=== Режим 0: все порты на ВХОД ===")
    dev.io_write(base + 3, 0x9B)  # Все порты — вход
    modes = dev.get_port_modes()
    print(f"  A: режим {modes['a_mode']}, {modes['a_direction']}")
    print(f"  B: режим {modes['b_mode']}, {modes['b_direction']}")
    
    # === Режим 2: порт A двунаправленный ===
    print("\n=== Режим 2: порт A ДВУНАПРАВЛЕННЫЙ ===")
    dev.io_write(base + 3, 0xC0)  # Биты 6-5 = 11 → режим 2
    modes = dev.get_port_modes()
    print(f"  A: режим {modes['a_mode']}, {modes['a_direction']}")
    print(f"  Ожидание: режим 2, bidir")
    
    # Проверка двунаправленного режима
    print("\n=== Проверка двунаправленного режима ===")
    dev.io_write(base + 0, 0xAA)  # Запись в выходной регистр
    dev.set_external_input(0, 0x55)  # Внешние входные данные
    val_read = dev.io_read(base + 0)
    print(f"  port_a (выход) = 0x{dev.port_a:02X}  (ожидаем 0xAA)")
    print(f"  external_input[0] = 0x{dev.external_input[0]:02X}  (ожидаем 0x55)")
    print(f"  io_read(порт A) = 0x{val_read:02X}  (ожидаем 0x55 — входные данные)")
    
    print("\n✅ Все тесты выполнены")