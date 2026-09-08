"""
3D Пинг-понг на кубе 8×8×8.
Итерация 12.7: классический пинг-понг в 3D.

Особенности:
- Шарик летает между двумя ракетками (внизу и вверху по оси Y)
- Ракетки автоматически следуют за шариком и отбивают его
- Шарик отскакивает от боковых стен (по осям X и Z)
- Затухающий след за шариком (рисуется напрямую с градиентом яркости)
- Ракетки и шарик рисуются через порты 8255 (окно 8255 показывает изменения)

Управление:
  api.mw._cube3d_timer.stop()   — остановить пинг-понг
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
    cube_widget.setWindowTitle("3D Куб 8×8×8 — Пинг-понг")
    cube_widget.resize(640, 600)
    api.mw._cube3d_widget = cube_widget

cube_widget.show()
cube_widget.raise_()
cube_widget.activateWindow()

# Настройка
cube_widget.set_persist(False)          # Без автозатухания
cube_widget.set_color(60, 255, 120)     # Зелёный цвет (шарик и ракетки)

# =============================================
# ШАГ 3: НАСТРОЙКА 8255
# =============================================
base = ppi.base_port
ppi.io_write(base + 3, 0x80)  # Все порты на выход
print(f"📡 8255 настроен: все порты на выход")

# =============================================
# ШАГ 4: ПАРАМЕТРЫ ИГРЫ
# =============================================
PONG_SPEED = 60             # мс между кадрами
BALL_SPEED = 0.4            # Скорость шарика (единиц за кадр)
PADDLE_SIZE = 3             # Размер ракетки (3×3 в плоскости)
TRAIL_LENGTH = 8            # Длина следа
PADDLE_FOLLOW = 0.25        # Коэффициент следования ракетки за шариком (0-1)

# =============================================
# ШАГ 5: СОСТОЯНИЕ ИГРЫ
# =============================================
# Шарик: позиция (дробная) и скорость
ball = {
    'x': 3.5, 'y': 3.5, 'z': 3.5,     # Позиция (дробная для плавности)
    'vx': BALL_SPEED * 0.7,             # Скорость по осям
    'vy': BALL_SPEED,                   # Основная ось игры — Y (вертикаль)
    'vz': BALL_SPEED * 0.5,
}

# Ракетки: позиция центра в плоскости X-Z
# Ракетка 1 — внизу (при Y=0), Ракетка 2 — вверху (при Y=7)
paddle1 = {'x': 3.5, 'z': 3.5}  # Нижняя ракетка
paddle2 = {'x': 3.5, 'z': 3.5}  # Верхняя ракетка

# След шарика: список последних позиций (целые координаты)
trail = []

# =============================================
# ШАГ 6: ОБНОВЛЕНИЕ ИГРЫ
# =============================================
def update_game():
    """Обновить состояние игры: движение шарика, отскоки, ракетки"""
    # Двигаем шарик
    ball['x'] += ball['vx']
    ball['y'] += ball['vy']
    ball['z'] += ball['vz']
    
    # Отскок от боковых стен (по осям X и Z)
    if ball['x'] <= 0:
        ball['x'] = 0
        ball['vx'] = abs(ball['vx'])
    elif ball['x'] >= 7:
        ball['x'] = 7
        ball['vx'] = -abs(ball['vx'])
    
    if ball['z'] <= 0:
        ball['z'] = 0
        ball['vz'] = abs(ball['vz'])
    elif ball['z'] >= 7:
        ball['z'] = 7
        ball['vz'] = -abs(ball['vz'])
    
    # Ракетки следуют за шариком (в плоскости X-Z)
    paddle1['x'] += (ball['x'] - paddle1['x']) * PADDLE_FOLLOW
    paddle1['z'] += (ball['z'] - paddle1['z']) * PADDLE_FOLLOW
    paddle2['x'] += (ball['x'] - paddle2['x']) * PADDLE_FOLLOW
    paddle2['z'] += (ball['z'] - paddle2['z']) * PADDLE_FOLLOW
    
    # Ограничиваем ракетки пределами куба
    half = PADDLE_SIZE // 2
    paddle1['x'] = max(half, min(7 - half, paddle1['x']))
    paddle1['z'] = max(half, min(7 - half, paddle1['z']))
    paddle2['x'] = max(half, min(7 - half, paddle2['x']))
    paddle2['z'] = max(half, min(7 - half, paddle2['z']))
    
    # Отскок от ракеток
    # Ракетка 1 (внизу, Y=0): шарик летит вниз (vy < 0)
    if ball['y'] <= 0.5 and ball['vy'] < 0:
        if is_on_paddle(ball['x'], ball['z'], paddle1):
            ball['vy'] = abs(ball['vy'])  # Отскок вверх
            ball['y'] = 0.5
            add_spin(paddle1)  # Добавляем вращение от ракетки
    # Ракетка 2 (вверху, Y=7): шарик летит вверх (vy > 0)
    elif ball['y'] >= 6.5 and ball['vy'] > 0:
        if is_on_paddle(ball['x'], ball['z'], paddle2):
            ball['vy'] = -abs(ball['vy'])  # Отскок вниз
            ball['y'] = 6.5
            add_spin(paddle2)
    
    # Обновляем след
    bx, by, bz = int(round(ball['x'])), int(round(ball['y'])), int(round(ball['z']))
    trail.append((bx, by, bz))
    if len(trail) > TRAIL_LENGTH:
        trail.pop(0)

def is_on_paddle(bx, bz, paddle):
    """Проверить, попадает ли шарик в ракетку (в плоскости X-Z)"""
    half = PADDLE_SIZE / 2
    return (abs(bx - paddle['x']) <= half and
            abs(bz - paddle['z']) <= half)

def add_spin(paddle):
    """Добавить вращение шарика в зависимости от точки удара о ракетку.
    Удар не в центр ракетки меняет горизонтальную скорость.
    """
    offset_x = ball['x'] - paddle['x']
    offset_z = ball['z'] - paddle['z']
    # Небольшое изменение горизонтальной скорости
    ball['vx'] += offset_x * 0.15
    ball['vz'] += offset_z * 0.15
    # Ограничиваем горизонтальную скорость
    max_h = BALL_SPEED * 1.5
    ball['vx'] = max(-max_h, min(max_h, ball['vx']))
    ball['vz'] = max(-max_h, min(max_h, ball['vz']))

# =============================================
# ШАГ 7: ОТРИСОВКА
# =============================================
def render_pong():
    """Отрисовать игру: след (напрямую), шарик и ракетки (через порты)"""
    # Очищаем куб напрямую
    cube_widget.clear()
    
    # === След: рисуем напрямую с градиентом яркости ===
    # Старые позиции тусклее, новые ярче
    for i, (tx, ty, tz) in enumerate(trail[:-1]):  # Последняя позиция — шарик
        brightness = (i + 1) / len(trail) * 0.6  # Градиент яркости
        if 0 <= tx < 8 and 0 <= ty < 8 and 0 <= tz < 8:
            cube_widget.brightness[tz][ty][tx] = brightness
    
    # === Шарик и ракетки: рисуем через порты 8255 ===
    bx, by, bz = int(round(ball['x'])), int(round(ball['y'])), int(round(ball['z']))
    
    # Шарик (яркая точка)
    if 0 <= bx < 8 and 0 <= by < 8 and 0 <= bz < 8:
        ppi.io_write(base + 0, bx)   # X
        ppi.io_write(base + 1, by)   # Y
        ppi.io_write(base + 2, bz)   # Z (строб)
    
    # Ракетка 1 (внизу, при Y=0)
    draw_paddle(paddle1, 0)
    
    # Ракетка 2 (вверху, при Y=7)
    draw_paddle(paddle2, 7)

def draw_paddle(paddle, y_pos):
    """Нарисовать ракетку как плоскость в плоскости X-Z"""
    half = PADDLE_SIZE // 2
    px, pz = int(round(paddle['x'])), int(round(paddle['z']))
    for dx in range(-half, half + 1):
        for dz in range(-half, half + 1):
            rx, rz = px + dx, pz + dz
            if 0 <= rx < 8 and 0 <= rz < 8:
                ppi.io_write(base + 0, rx)     # X
                ppi.io_write(base + 1, y_pos)  # Y (позиция ракетки)
                ppi.io_write(base + 2, rz)     # Z (строб)

# =============================================
# ШАГ 8: АНИМАЦИОННЫЙ ЦИКЛ
# =============================================
def next_frame():
    """Один кадр анимации пинг-понга"""
    update_game()
    render_pong()
    
    timer = QTimer(api.mw)
    timer.setSingleShot(True)
    timer.timeout.connect(next_frame)
    timer.start(PONG_SPEED)
    api.mw._cube3d_timer = timer

# =============================================
# ШАГ 9: ЗАПУСК
# =============================================
if hasattr(api.mw, '_cube3d_timer') and api.mw._cube3d_timer is not None:
    try:
        api.mw._cube3d_timer.stop()
    except Exception:
        pass

print("\n🏓 3D Пинг-понг запущен:")
print("   • Шарик летает между двумя ракетками (внизу и вверху)")
print("   • Ракетки автоматически следуют за шариком")
print("   • Отскок от боковых стен (X и Z)")
print("   • Затухающий след за шариком")
print("   • Вывод через порты 8255")
print("\n📌 Управление:")
print("   • Вращайте куб мышью!")
print("   • Пробел — переворот, стрелки — поворот")
print("\n⏹ Остановка пинг-понга:")
print("   api.mw._cube3d_timer.stop()")

next_frame()
