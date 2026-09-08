"""Диагностика: что в видеопамяти и как отображается"""
dev = None
for d in api.system.devices.values():
    if type(d).__name__ == 'I8275':
        dev = d
        break

if dev is None:
    print("❌ 8275 не найден")
    raise SystemExit

print(f"✅ 8275: char_width={getattr(dev, 'char_width', '?')}")
print(f"   display_enabled={dev.display_enabled}")
print(f"   display_buffer: {len(dev.display_buffer)} символов")

# Показываем первые 32 символа из видеопамяти
print("\nПервые 32 символа видеопамяти:")
for i in range(min(32, len(dev.display_buffer))):
    char, attr = dev.display_buffer[i]
    if char == 0x20:
        continue  # Пробел пропускаем
    # Проверяем, есть ли глиф в шрифте
    bitmap = dev.char_gen.get_bitmap(char, 8)
    has_pixels = any(b != 0 for b in bitmap)
    status = "✅" if has_pixels else "❌ пустой"
    print(f"   [{i:2d}] код 0x{char:02X} attr=0x{attr:02X} {status}")

# Проверяем кириллицу КОИ-7 в шрифте
print("\nКириллица КОИ-7 в загруженном шрифте (0x60-0x65):")
for code in range(0x60, 0x66):
    bitmap = dev.char_gen.get_bitmap(code, 8)
    has_pixels = any(b != 0 for b in bitmap)
    if has_pixels:
        print(f"   0x{code:02X}:")
        for row in bitmap:
            line = ''.join('#' if row & (0x01 << b) else '.' for b in range(6))
            print(f"      {line}")
    else:
        print(f"   0x{code:02X}: ❌ пустой глиф")