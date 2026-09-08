"""
Тест терминала для 8251/16550.
Отправляет тестовое сообщение через порт данных.
"""
import time

def find_serial_device(api):
    for dev in api.system.devices.values():
        cls_name = type(dev).__name__
        if cls_name in ('I8251', 'I16550'):
            return dev
    return None

dev = find_serial_device(api)
if dev is None:
    print("Последовательное устройство не найдено!")
    print("Добавьте 8251 или 16550 в профиль.")
else:
    cls_name = type(dev).__name__
    base_port = getattr(dev, 'base_port', 0)
    print(f"Найдено устройство: {cls_name} @ 0x{base_port:02X}")
    
    # === Инициализация 16550 (если нужно) ===
    if cls_name == 'I16550':
        dev.reset()
        # LCR: DLAB=1 для установки делителя
        dev.io_write(base_port + 3, 0x80)
        # Делитель: 9600 бод при 1.8432 МГц = 12
        dev.io_write(base_port + 0, 12)   # DLL
        dev.io_write(base_port + 1, 0)    # DLM
        # LCR: 8N1, DLAB=0
        dev.io_write(base_port + 3, 0x03)
        # IER: включаем прерывания по приёму
        dev.io_write(base_port + 1, 0x01)
        print("16550 инициализирован: 9600 бод, 8N1")
    
    # === Инициализация 8251 (если нужно) ===
    elif cls_name == 'I8251':
        dev.reset()
        # Mode Register: асинхронный, 16x, 8 бит, без паритета, 1 стоп
        dev.io_write(base_port, 0x4E)
        # Command Register: включение приёма/передачи
        dev.io_write(base_port, 0x37)
        print("8251 инициализирован: асинхронный режим")
    
    # === Отправка тестовых данных через порт данных ===
    test_message = "Hello from i8080!\r\n"
    print(f"Отправляем: {test_message!r}")
    for char in test_message:
        dev.io_write(base_port, ord(char))
    
    print("Данные отправлены через порт данных")
    print("Откройте окно терминала для просмотра вывода")