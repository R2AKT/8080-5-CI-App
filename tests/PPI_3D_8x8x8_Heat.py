"""
Многокадровая анимация 3D сердца в кубе 8×8×8.
Итерация 12.3: демонстрационная визуализация.

Особенности:
- Тонкое сердце в покое (2 слоя), объёмное при сокращении (6 слоёв)
- Управление через порты 8255 (окно 8255 показывает изменения)
- Реалистичный сердечный цикл: тук-тук → длинная пауза
- Поддержка устройства Cube3D из профиля или виджета через скрипт
"""
from PySide6.QtCore import QTimer

# =============================================
# ШАГ 1: ПОИСК УСТРОЙСТВ
# =============================================
ppi = None       # 8255 (для управления через порты)
cube = None      # Cube3D (устройство из профиля)

for d in api.system.devices.values():
    cls_name = type(d).__name__
    if cls_name == 'I8255' and ppi is None:
        ppi = d
    elif cls_name == 'Cube3D' and cube is None:
        cube = d

if ppi is None and cube is None:
    print("❌ Не найдены ни 8255, ни Cube3D!")
    print("   Добавьте устройства в профиль или проверьте конфигурацию.")
    raise SystemExit

print(f"🔍 Найдено: 8255={'✅' if ppi else '❌'}, Cube3D={'✅' if cube else '❌'}")

# =============================================
# ШАГ 2: ПОЛУЧЕНИЕ ОКНА КУБА (через диспетчер устройств)
# =============================================
from ui.cube3d_widget import Cube3DWidget

# Ищем существующее окно куба в диспетчере устройств
cube_window = None
if hasattr(api.mw, 'device_manager') and api.mw.device_manager is not None:
    dm = api.mw.device_manager
    cube_dev_name = cube.name if cube is not None else None
    if cube_dev_name and cube_dev_name in dm.device_windows:
        cube_window = dm.device_windows[cube_dev_name]

if cube_window is None:
    # Окна нет — создаём чистое окно с виджетом (как из диспетчера)
    target = cube if cube is not None else ppi
    cube_window = Cube3DWidget(target)
    if cube is not None:
        cube_window.setWindowTitle(f"3D Куб 8×8×8 — {cube.name}")
    else:
        cube_window.setWindowTitle("3D Куб 8×8×8 — Бьющееся сердце")
    cube_window.resize(640, 600)
    # Регистрируем в диспетчере, чтобы не плодить дубликаты
    if hasattr(api.mw, 'device_manager') and api.mw.device_manager is not None:
        key = cube.name if cube is not None else '_cube3d_script'
        api.mw.device_manager.device_windows[key] = cube_window

cube_window.show()
cube_window.raise_()

# Сохраняем для остановки
api.mw._cube3d_widget = cube_window

# Определяем, куда рисовать: устройство Cube3D или виджет
draw_target = cube if cube is not None else cube_window

# =============================================
# ШАГ 3: НАСТРОЙКА 8255 (если есть)
# =============================================
use_ports = False
if ppi is not None:
    base = ppi.base_port
    # Управляющее слово: режим 0, все порты — выход
    # Бит 7=1 (режим), биты 4,3,1,0 = 0 (выходы)
    ppi.io_write(base + 3, 0x80)
    use_ports = True
    print(f"📡 8255 @ 0x{base:02X} — рисуем через порты (окно 8255 обновляется)")
else:
    print("⚠ 8255 не найден — рисуем напрямую в куб")

# =============================================
# ШАГ 4: ПАТТЕРНЫ СЕРДЦА
# =============================================
# Бит 0 = левый пиксель, строки идут снизу вверх (y=0 внизу)
# Сердце правильно ориентировано: "ушки" вверху (y=7)

# Самое маленькое сердце (диастола, полный покой)
HEART_TINY = [
    0b00000000,  # y=0 — низ
    0b00000000,
    0b00000000,
    0b00000000,
    0b01100110,  # .XX..XX.
    0b00111100,  # ..XXXX..
    0b00011000,  # ...XX...
    0b00000000,  # y=7 — верх
]

# Маленькое сердце
HEART_SMALL = [
    0b00000000,
    0b00000000,
    0b01100110,  # .XX..XX.
    0b01111110,  # .XXXXXX.
    0b00111100,  # ..XXXX..
    0b00011000,  # ...XX...
    0b00000000,
    0b00000000,
]

# Среднее сердце
HEART_MEDIUM = [
    0b00000000,
    0b01100110,  # .XX..XX.
    0b11111111,  # XXXXXXXX
    0b11111111,  # XXXXXXXX
    0b01111110,  # .XXXXXX.
    0b00111100,  # ..XXXX..
    0b00011000,  # ...XX...
    0b00000000,
]

# Большое сердце (пик систолы)
HEART_LARGE = [
    0b01100110,  # .XX..XX.  ← "ушки" вверху
    0b11111111,  # XXXXXXXX
    0b11111111,  # XXXXXXXX
    0b11111111,  # XXXXXXXX
    0b11111111,  # XXXXXXXX
    0b01111110,  # .XXXXXX.
    0b00111100,  # ..XXXX..
    0b00011000,  # ...XX...
]

# =============================================
# ШАГ 5: ПОСТРОЕНИЕ ОБЪЁМНОГО СЕРДЦА
# =============================================
def build_heart_layers(pattern, depth):
    """Построить 8 слоёв с заданной глубиной.
    
    Args:
        pattern: 2D паттерн сердца (8 байт)
        depth: количество активных слоёв (1-8), центрированных
        
    Returns:
        список из 8 слоёв (каждый — 8 байт)
        
    Примеры:
        depth=2 → слои 3,4 (тонкое сердце в покое)
        depth=4 → слои 2,3,4,5 (среднее)
        depth=6 → слои 1,2,3,4,5,6 (объёмное)
    """
    layers = [[0]*8 for _ in range(8)]
    if depth <= 0:
        return layers
    
    # Центрируем активные слои
    start = (8 - depth) // 2
    end = start + depth
    
    for z in range(start, min(end, 8)):
        # Расстояние от центра куба (3.5)
        dist_from_center = abs(z - 3.5)
        
        if dist_from_center < 2.0:
            # Центральные слои — полный паттерн
            layers[z] = pattern
        elif depth > 4:
            # Внешние слои объёмного сердца — уменьшенный паттерн
            layers[z] = HEART_TINY
        else:
            # Внешние слои тонкого сердца — пустые
            layers[z] = [0]*8
    
    return layers

# =============================================
# ШАГ 6: СЕРДЕЧНЫЙ ЦИКЛ
# =============================================
# Формат: (глубина, паттерн, длительность мс)
# Диастола: тонкое сердце (2 слоя)
# Систола: объёмное сердце (6 слоёв)
# Реалистичный цикл: тук-тук → длинная пауза

BEAT = [
    # --- Диастола (расслабление) — тонкое сердце ---
    (2, HEART_TINY,   500),   # Кадр 0: полный покой
    (2, HEART_TINY,   300),   # Кадр 1: пауза
    
    # --- Начало систолы (первое сокращение) ---
    (3, HEART_SMALL,  150),   # Кадр 2: лёгкое расширение
    (4, HEART_MEDIUM, 150),   # Кадр 3: рост
    
    # --- Пик систолы ---
    (6, HEART_LARGE,  200),   # Кадр 4: максимальное расширение
    
    # --- Быстрый спад ---
    (4, HEART_MEDIUM, 120),   # Кадр 5: сжатие
    (3, HEART_SMALL,  120),   # Кадр 6: почти покой
    
    # --- Возврат к диастолу ---
    (2, HEART_TINY,   400),   # Кадр 7: полный покой
]

# =============================================
# ШАГ 7: ОТРИСОВКА КАДРА
# =============================================
def draw_frame(layers):
    """Рисует кадр в кубе.
    
    Если 8255 доступен — рисуем через порты (окно 8255 обновляется).
    Иначе — рисуем напрямую в куб.
    """
    if use_ports:
        # === ЧЕСТНОЕ управление через порты 8255 ===
        # Сначала очищаем куб напрямую (нет команды очистки через порты)
        draw_target.clear()
        
        # Затем рисуем каждый включённый светодиод через порты
        for z in range(8):
            for y in range(8):
                pattern = layers[z]
                if pattern[y] == 0:
                    continue  # Пустая строка — пропускаем
                for x in range(8):
                    if pattern[y] & (1 << x):
                        # Записываем координаты в порты 8255
                        ppi.io_write(base + 0, x & 0x07)  # Порт A = X
                        ppi.io_write(base + 1, y & 0x07)  # Порт B = Y
                        ppi.io_write(base + 2, z & 0x07)  # Порт C = Z
                        # Куб получает координаты через on_port_change
                        # и зажигает светодиод
    else:
        # === Прямое управление (без 8255) ===
        draw_target.clear()
        for z in range(8):
            draw_target.set_layer(z, layers[z])

# =============================================
# ШАГ 8: АНИМАЦИОННЫЙ ЦИКЛ
# =============================================
frame_idx = [0]

def next_frame():
    """Показать следующий кадр анимации"""
    depth, pattern, duration = BEAT[frame_idx[0]]
    layers = build_heart_layers(pattern, depth)
    draw_frame(layers)
    
    # Переход к следующему кадру
    frame_idx[0] = (frame_idx[0] + 1) % len(BEAT)
    
    # Планируем следующий кадр
    timer = QTimer(api.mw)
    timer.setSingleShot(True)
    timer.timeout.connect(next_frame)
    timer.start(duration)
    api.mw._cube3d_timer = timer

# =============================================
# ШАГ 9: ЗАПУСК
# =============================================
# Останавливаем предыдущую анимацию (безопасная проверка)
if hasattr(api.mw, '_cube3d_timer') and api.mw._cube3d_timer is not None:
    try:
        api.mw._cube3d_timer.stop()
    except Exception:
        pass

print("\n🫀 Анимация сердца запущена:")
print("   • Диастола: тонкое сердце (2 слоя)")
print("   • Систола: объёмное сердце (6 слоёв)")
print("   • Вращайте куб мышью!")
print("\n📌 Управление:")
print("   • ЛКМ — вращение")
print("   • Колесо — зум")
print("   • Пробел — переворот на 180°")
print("   • Двойной клик / R — сброс вида")
print("\n⏹ Остановка анимации:")
print("   api.mw._cube3d_timer.stop()")
print("   api.mw._cube3d_widget.close()")

# Запускаем анимацию
frame_idx[0] = 0
next_frame()