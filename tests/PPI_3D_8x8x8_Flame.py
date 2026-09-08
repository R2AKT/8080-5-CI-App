"""
Эмуляция пламени на 3D-кубе 8×8×8.
Итерация 12.5: пламя на нижней плоскости, вывод через 8255.

Особенности:
- Основание пламени на НИЖНЕЙ плоскости (плоскость X-Z при Y=0)
- Пламя растёт ВВЕРХ по оси Y
- Вывод через порты 8255 (окно 8255 показывает изменения)
- Порт A = X, Порт B = Y, Порт C = Z (строб)
"""
import random
import math
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
    cube_widget.setWindowTitle("3D Куб 8×8×8 — Пламя")
    cube_widget.resize(640, 600)
    api.mw._cube3d_widget = cube_widget

cube_widget.show()
cube_widget.raise_()
cube_widget.activateWindow()

# Настройка для пламени
cube_widget.set_persist(False)          # Без автозатухания
cube_widget.set_color(255, 100, 20)     # Оранжевый цвет пламени

# =============================================
# ШАГ 3: НАСТРОЙКА 8255
# =============================================
base = ppi.base_port
# Все порты на выход (режим 0)
ppi.io_write(base + 3, 0x80)
print(f"📡 8255 настроен: все порты на выход")

# =============================================
# ШАГ 4: КАРТА ВЫСОТ ПЛАМЕНИ
# =============================================
# Основание пламени в плоскости X-Z (горизонталь)
# Пламя растёт ВВЕРХ по оси Y
# flame_height[x][z] — высота пламени для позиции (x, z)
flame_height = [[0.0]*8 for _ in range(8)]
spark_timers = {}   # Искры: (x, y, z) -> время жизни
flare_state = [0]   # Состояние вспышки

# Параметры
FLAME_SPEED = 70        # мс между кадрами
SMOOTHING = 0.35        # Плавность
SPARK_CHANCE = 0.15     # Вероятность искры
FLARE_INTERVAL = 40     # Кадров между вспышками

def distance_from_center_xz(x, z):
    """Расстояние от центра в плоскости X-Z (нормализованное 0..1)"""
    dx = (x - 3.5) / 3.5
    dz = (z - 3.5) / 3.5
    return math.sqrt(dx*dx + dz*dz)

# =============================================
# ШАГ 5: ОБНОВЛЕНИЕ КАРТЫ ПЛАМЕНИ
# =============================================
def update_flame():
    """Обновить высоты языков пламени"""
    for x in range(8):
        for z in range(8):
            dist = distance_from_center_xz(x, z)
            
            # Целевая высота: выше в центре, ниже к краям
            if dist < 0.4:
                target = random.uniform(5.5, 7.5)   # Ядро
            elif dist < 0.8:
                target = random.uniform(3.5, 5.5)   # Средняя зона
            elif dist < 1.2:
                target = random.uniform(1.5, 3.5)   # Периферия
            else:
                target = random.uniform(0.5, 2.0)   # Углы
            
            # Плавная интерполяция + шум
            current = flame_height[x][z]
            noise = random.uniform(-0.8, 0.8)
            flame_height[x][z] = current + (target - current) * SMOOTHING + noise
            flame_height[x][z] = max(0.3, min(7.8, flame_height[x][z]))

# =============================================
# ШАГ 6: ИСКРЫ
# =============================================
def update_sparks():
    """Обновить искры"""
    # Гасим старые
    expired = []
    for key in spark_timers:
        spark_timers[key] -= 1
        if spark_timers[key] <= 0:
            expired.append(key)
    for key in expired:
        del spark_timers[key]
    
    # Создаём новые (высоко по оси Y)
    if random.random() < SPARK_CHANCE:
        x = random.randint(1, 6)
        z = random.randint(1, 6)
        y = random.randint(5, 7)  # Искры высоко
        spark_timers[(x, y, z)] = random.randint(2, 5)

# =============================================
# ШАГ 7: ОТРИСОВКА ЧЕРЕЗ ПОРТЫ 8255
# =============================================
def render_flame_via_ports():
    """Отрисовать пламя через порты 8255.
    Окно 8255 показывает изменения портов.
    """
    # Очищаем куб напрямую (нет команды очистки через порты)
    cube_widget.clear()
    
    # Проверяем вспышку
    flare_state[0] += 1
    is_flare = flare_state[0] >= FLARE_INTERVAL
    if is_flare:
        flare_state[0] = 0
    
    # Рисуем столбцы пламени через порты
    for x in range(8):
        for z in range(8):
            height = int(flame_height[x][z])
            
            # Имитация затухания: чем выше, тем меньше пикселей горит
            # Нижние уровни горят всегда, верхние — с вероятностью
            for y in range(min(height, 8)):
                # Вероятность горения: ниже = 100%, выше = меньше
                if y <= 2:
                    burn_prob = 1.0
                elif y <= 4:
                    burn_prob = 0.85
                else:
                    burn_prob = 0.6
                
                # Вспышка увеличивает вероятность
                if is_flare:
                    burn_prob = min(1.0, burn_prob + 0.2)
                
                if random.random() < burn_prob:
                    # Записываем координаты в порты 8255
                    ppi.io_write(base + 0, x & 0x07)  # Порт A = X
                    ppi.io_write(base + 1, y & 0x07)  # Порт B = Y
                    ppi.io_write(base + 2, z & 0x07)  # Порт C = Z (строб)
    
    # Рисуем искры через порты
    for (sx, sy, sz) in spark_timers:
        ppi.io_write(base + 0, sx & 0x07)  # X
        ppi.io_write(base + 1, sy & 0x07)  # Y
        ppi.io_write(base + 2, sz & 0x07)  # Z (строб)

# =============================================
# ШАГ 8: АНИМАЦИОННЫЙ ЦИКЛ
# =============================================
def next_frame():
    """Один кадр анимации пламени"""
    update_flame()
    update_sparks()
    render_flame_via_ports()
    
    # Планируем следующий кадр
    timer = QTimer(api.mw)
    timer.setSingleShot(True)
    timer.timeout.connect(next_frame)
    timer.start(FLAME_SPEED)
    api.mw._cube3d_timer = timer

# =============================================
# ШАГ 9: ЗАПУСК
# =============================================
# Останавливаем предыдущую анимацию
if hasattr(api.mw, '_cube3d_timer') and api.mw._cube3d_timer is not None:
    try:
        api.mw._cube3d_timer.stop()
    except Exception:
        pass

print("\n🔥 Эмуляция пламени запущена:")
print("   • Основание на НИЖНЕЙ плоскости (X-Z при Y=0)")
print("   • Пламя растёт ВВЕРХ по оси Y")
print("   • Вывод через порты 8255")
print("   • Окно 8255 показывает изменения портов")
print("\n📌 Управление:")
print("   • Вращайте куб мышью!")
print("   • Пробел — переворот, стрелки — поворот")
print("\n⏹ Остановка пламени:")
print("   api.mw._cube3d_timer.stop()")

# Инициализация карты
for x in range(8):
    for z in range(8):
        flame_height[x][z] = random.uniform(1.0, 4.0)

next_frame()
