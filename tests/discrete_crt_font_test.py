"""Финальный тест: полный русский текст в окне Video Микро-80"""
from modules.io.discrete_video import DiscreteVideo

dev = None
bus = api.system.bus
for d in api.system.devices.values():
    if type(d).__name__ == 'DiscreteVideo':
        dev = d
        break

if dev is None:
    print("❌ DiscreteVideo не найден!")
else:
    test_text = "ПРИВЕТ МИКРО-80!"
    codes = DiscreteVideo.unicode_to_koi7(test_text)

    # Записываем текст в видеопамять символов
    for i, code in enumerate(codes):
        bus.write(dev.video_addr + i, code)

    # Заполняем остаток экрана пробелами
    total = dev.chars_per_line * dev.lines_per_screen
    for i in range(len(codes), total):
        bus.write(dev.video_addr + i, 0x20)

    # Обновляем буфер из памяти
    dev.refresh_from_memory()

    print(f"✅ Записано: '{test_text}'")
    print(f"   Коды: {' '.join(f'{c:02X}' for c in codes)}")
    print("   📺 Откройте окно Video из Диспетчера устройств")