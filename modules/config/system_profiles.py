"""
Профили систем для i8080-5 CI.
Итерация 10.4 + вынос профилей во внешние TOML-файлы.

Приоритет загрузки:
1. Внешний файл профилей в рабочем каталоге (профили/*.toml)
2. Встроенные профили (встроенные как fallback)
"""

import os
import os.path
import glob

# Базовый каталог проекта (каталог скрипта)
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROFILES_DIR = os.path.join(_PROJECT_DIR, "profiles")

# ============================================================
# ВСТРОЕННЫЕ ПРОФИЛИ (минимальный набор, если нет внешних)
# ============================================================
SYSTEM_PROFILES = {
    "empty": {
        "name": "empty",
        "description": "Пустая система (без устройств)",
        "toml": """
[system]
name = "Empty System"
cpu = "i8080"
clock_mhz = 2

[[memory.regions]]
type = "ram"
start = 0
end = 65535
name = "RAM"
"""
    },
}

# ============================================================
# ЗАГРУЗКА ИЗ ВНЕШНИХ TOML-ФАЙЛОВ
# ============================================================
_external_profiles = {}

def _load_external_profiles():
    """Загружает профили из каталога профили/*.toml"""
    global _external_profiles
    _external_profiles = {}

    if not os.path.isdir(_PROFILES_DIR):
        return

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return

    for filepath in sorted(glob.glob(os.path.join(_PROFILES_DIR, "*.toml"))):
        try:
            with open(filepath, 'rb') as f:
                data = tomllib.load(f)

            profile_name = os.path.splitext(os.path.basename(filepath))[0]

            for pname, pdata in data.get("profiles", {}).items():
                full_name = (
                    f"{profile_name}.{pname}"
                    if len(data.get("profiles", {})) > 1
                    else profile_name
                )

                # Храним как dict вместо TOML-строки (без tomli_w)
                _external_profiles[full_name] = {
                    "name": full_name,
                    "description": pdata.get("description", ""),
                    "config": pdata,          # ← dict вместо TOML-строки
                    "filepath": filepath,
                }
        except Exception as e:
            print(f"Ошибка загрузки профиля {filepath}: {e}")

# Загружаем при импорте модуля
_load_external_profiles()


def reload_profiles():
    """Перезагрузить профили из внешних файлов"""
    _load_external_profiles()


def get_profile(profile_name):
    """Получить профиль по имени.
    
    Приоритет: внешние профили → встроенные профили.
    """
    if profile_name in _external_profiles:
        return _external_profiles[profile_name]
    return SYSTEM_PROFILES.get(profile_name, None)


def get_profile_names():
    """Список доступных профилей (внешние + встроенные)"""
    names = list(_external_profiles.keys())
    for name in SYSTEM_PROFILES:
        if name not in names:
            names.append(name)
    return names


def get_profiles_dir():
    """Вернуть путь к каталогу профилей"""
    return _PROFILES_DIR
