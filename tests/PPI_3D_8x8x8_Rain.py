"""
Эмуляция дождя из облака на 3D-кубе 8×8×8.
Итерация 12.6: демонстрационный эффект.

Особенности:
- Облако в верхней части (плоскость X-Z при Y=6,7)
- Капли падают ВНИЗ по оси Y (от облака ко дну)
- Всплески на дне (плоскость X-Z при Y=0)
- Редкие молнии (вспышка облака)
- Вывод через порты 8255 (окно 8255 показывает изменения)

Управление:
  api.mw._cube3d_timer.stop()   — остановить дождь
"""
import random
from PySide6.QtCore import QTimer

# =============================================
# ШАГ 1: ПОИСК УСТРОЙСТВ
# =============================================
ppi = None
cube_dev = None

for d in api.system.devices.values():
    cls = type(d).__name__
    if cls == 'I8255' and ppi is None:
        ppi = d
    elif cls == 'Cube3D' and cube_dev is None:
        cube_dev = d

if ppi is None:
    print("❌ 8255 не найден! Добавьте 8255 в профиль.")
    raise SystemExit

print(f"✅ 8255 @ 0x{ppi.base_port:02X}")
if cube_dev is not None:
    print(f"✅ Cube3D: {cube_dev.name}")

# =============================================
# ШАГ 2: ОТКРЫТИЕ ВИДЖЕТА КУБА
# =============================================
from ui.cube3d_widget import Cube3DWidget

if hasattr(api.mw, '_cube3d_widget') and api.mw._cube3d_widget is not None:
    cube_widget = api.mw._cube3d_widget
else:
    target = cube_dev if cube_dev is not None else ppi
    cube_widget = Cube3DWidget(target)
    cube_widget.setWindowTitle("3D Куб 8×8×8 — Дождь")
    cube_widget.resize(640, 600)
    api.mw._cube3d_widget = cube_widget

cube_widget.show()
cube_widget.raise_()
cube_widget.activateWindow()

# Настройка для дождя
cube_widget.set_persist(False)          # Без автозатухания
cube_widget.set_color(80, 160, 255)     # Голубой цвет дождя

# =============================================
# ШАГ 3: НАСТРОЙКА 8255
# =============================================
base = ppi.base_port
ppi.io_write(base + 3, 0x80)  # Все порты на выход
print(f"📡 8255 настроен: все порты на выход")

# =============================================
# ШАГ 4: ПАРАМЕТРЫ ДОЖДЯ
# =============================================
RAIN_SPEED = 80             # мс между кадрами
DROP_SPAWN_CHANCE = 0.4     # Вероятность появления капли за кадр
LIGHTNING_INTERVAL = 60     # Средний интервал между молниями (кадров)
SPLASH_MAX_AGE = 2          # Время жизни всплеска (кадров)

# Паттерн облака (плоскость X-Z, вид сверху)
# 1 = облако есть, 0 = нет
CLOUD_PATTERN = [
    [0,0,1,1,1,1,0,0],  # z=0
    [0,1,1,1,1,1,1,0],  # z=1
    [1,1,1,1,1,1,1,1],  # z=2
    [1,1,1,1,1,1,1,1],  # z=3
    [0,1,1,1,1,1,1,0],  # z=4
    [0,0,1,1,1,1,0,0],  # z=5
    [0,0,0,1,1,0,0,0],  # z=6
    [0,0,0,0,0,0,0,0],  # z=7
]

# =============================================
# ШАГ 5: СОСТОЯНИЕ ДОЖДЯ
# =============================================
drops = []        # Капли: [x, z, y] — текущая позиция
splashes = []     # Всплески: [x, z, age] — возраст в кадрах
lightning = [0]   # Таймер молнии: >0 = молния активна

# =============================================
# ШАГ 6: ПОЯВЛЕНИЕ КАПЕЛЬ
# =============================================
def spawn_drops():
    """Породить новые капли из облака"""
    if random.random() < DROP_SPAWN_CHANCE:
        # Пробуем найти позицию в облаке
        for _ in range(3):
            x = random.randint(1, 6)
            z = random.randint(1, 5)
            if CLOUD_PATTERN[z][x]:
                # Капля начинает падать чуть ниже облака
                drops.append([x, z, 5])
                break

# =============================================
# ШАГ 7: ПАДЕНИЕ КАПЕЛЬ
# =============================================
def update_drops():
    """Двигать капли вниз, создавать всплески на дне"""
    to_remove = []
    for i, drop in enumerate(drops):
        drop[2] -= 1  # y уменьшается (падение вниз)
        if drop[2] <= 0:
            # Достигла дна — создаём всплеск
            splashes.append([drop[0], drop[1], 0])
            to_remove.append(i)
    # Удаляем капли, достигшие дна
    for i in reversed(to_remove):
        drops.pop(i)

# =============================================
# ШАГ 8: ВСПЛЕСКИ
# =============================================
def update_splashes():
    """Старить всплески, удалять старые"""
    to_remove = []
    for i, splash in enumerate(splashes):
        splash[2] += 1
        if splash[2] > SPLASH_MAX_AGE:
            to_remove.append(i)
    for i in reversed(to_remove):
        splashes.pop(i)

# =============================================
# ШАГ 9: МОЛНИИ
# =============================================
def update_lightning():
    """Обновить состояние молнии"""
    if lightning[0] > 0:
        lightning[0] -= 1  # Молния гаснет
    elif random.random() < 1.0 / LIGHTNING_INTERVAL:
        # Случайная вспышка
        lightning[0] = random.randint(2, 4)

# =============================================
# ШАГ 10: ОТРИСОВКА ЧЕРЕЗ ПОРТЫ 8255
# =============================================
def render_rain():
    """Нарисовать дождь через порты 8255"""
    cube_widget.clear()  # Очистка куба
    
    is_lightning = lightning[0] > 0
    
    # === Облако (слои Y=6 и Y=7 для объёма) ===
    cloud_layers = [(7, 0.8), (6, 0.5)]  # (слой, вероятность горения)
    for layer_y, prob in cloud_layers:
        for x in range(8):
            for z in range(8):
                if CLOUD_PATTERN[z][x]:
                    # При молнии облако горит полностью, иначе мерцает
                    if is_lightning or random.random() < prob:
                        ppi.io_write(base + 0, x)        # X
                        ppi.io_write(base + 1, layer_y)  # Y (слой облака)
                        ppi.io_write(base + 2, z)        # Z (строб)
    
    # === Капли (падают вниз) ===
    for drop in drops:
        x, z, y = drop
        if 0 <= y < 8:
            ppi.io_write(base + 0, x)   # X
            ppi.io_write(base + 1, y)   # Y (высота капли)
            ppi.io_write(base + 2, z)   # Z (строб)
    
    # === Всплески (на дне) ===
    for splash in splashes:
        x, z, age = splash
        # Центральная точка всплеска
        points = [(x, z)]
        if age == 0:
            # В первый кадр добавляем крестик (расширение)
            points.extend([(x+1, z), (x-1, z), (x, z+1), (x, z-1)])
        for px, pz in points:
            if 0 <= px < 8 and 0 <= pz < 8:
                ppi.io_write(base + 0, px)  # X
                ppi.io_write(base + 1, 0)   # Y=0 (дно)
                ppi.io_write(base + 2, pz)  # Z (строб)

# =============================================
# ШАГ 11: АНИМАЦИОННЫЙ ЦИКЛ
# =============================================
def next_frame():
    """Один кадр анимации дождя"""
    spawn_drops()
    update_drops()
    update_splashes()
    update_lightning()
    render_rain()
    
    timer = QTimer(api.mw)
    timer.setSingleShot(True)
    timer.timeout.connect(next_frame)
    timer.start(RAIN_SPEED)
    api.mw._cube3d_timer = timer

# =============================================
# ШАГ 12: ЗАПУСК
# =============================================
if hasattr(api.mw, '_cube3d_timer') and api.mw._cube3d_timer is not None:
    try:
        api.mw._cube3d_timer.stop()
    except Exception:
        pass

print("\n🌧 Дождь из облака запущен:")
print("   • Облако сверху (мерцает, при молнии вспыхивает)")
print("   • Капли падают вниз по оси Y")
print("   • Всплески на дне (крестик в первый кадр)")
print("   • Вывод через порты 8255")
print("\n📌 Управление:")
print("   • Вращайте куб мышью!")
print("   • Пробел — переворот, стрелки — поворот")
print("\n⏹ Остановка дождя:")
print("   api.mw._cube3d_timer.stop()")

next_frame()
