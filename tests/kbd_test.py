"""Тест клавиатуры 8×8"""
dev = None
ppi = None
for d in api.system.devices.values():
    cls = type(d).__name__
    if cls == 'Keyboard8x8':
        dev = d
    elif cls == 'I8255':
        ppi = d

if dev is None:
    print("❌ Keyboard8x8 не найдена!")
else:
    print(f"✅ Keyboard8x8: {dev.name}")
    print(f"   Подключена к: {dev._ppi.name if dev._ppi else 'не подключена'}")
    
    # Имитируем сканирование клавиатуры программой на 8080
    print("\n=== Имитация сканирования ===")
    # Нажимаем клавишу (2, 0) = 'J' (Й)
    dev.press_key(2, 0)
    
    # Программа выбирает строку 2 через порт A
    if ppi:
        ppi.io_write(ppi.base_port + 0, 2)
        # Программа читает столбцы из порта B
        cols = ppi.io_read(ppi.base_port + 1)
        print(f"   Строка 2, столбцы: 0x{cols:02X}")
        print(f"   Ожидание: 0xFE (бит 0 = 0, клавиша нажата)")
        if cols == 0xFE:
            print("   ✅ ТЕСТ ПРОЙДЕН")
        else:
            print("   ❌ ТЕСТ ПРОВАЛЕН")
    
    # Отпускаем
    dev.release_key(2, 0)
    print("\n   Клавиша отпущена")