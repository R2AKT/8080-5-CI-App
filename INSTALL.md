# i8080-5 CI — установка / Installation

## Windows 10/11 x64

Распакуйте `i8080-5_CI_v<версия>_win64.zip` в любую папку и запустите
`i8080_CI.exe` двойным щелчком.

Unpack the archive to any folder and double-click `i8080_CI.exe`.

## GNU/Linux x86_64

### Вариант 1: готовый бинарник / Prebuilt binary

Файл `i8080-5_CI_v<версия>_linux_x86_64.tar.gz` (собирается GitHub Actions
или скриптом `build_linux.sh`):

```bash
tar xzf i8080-5_CI_v*_linux_x86_64.tar.gz -C ~/i8080-5-ci
cd ~/i8080-5-ci
./i8080_CI
```

Системные зависимости для запуска (обычно уже установлены):
- Debian/Ubuntu: `libgl1 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0`
- Fedora: `mesa-libGL libxkbcommon dbus-libs fontconfig glib2`

### Вариант 2: из исходников / From source

```bash
tar xzf i8080-5_CI_v*_source.tar.gz
cd i8080-5_CI-v*
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python i8080_CI.py
```

Или собрать портативный бинарник: `./build_linux.sh`
(нужен Python 3.10+ с venv и pip).

## Внешние файлы / External files

Каталоги `profiles/` и `roms/` **не вшиты** в исполняемый файл —
они лежат рядом с ним и могут свободно меняться и дополняться:

- `profiles/*.toml` — профили систем (шаблоны в `profiles/template/`);
- `roms/` — ROM-образы и шрифты, на которые ссылаются профили
  (пути в профиле — относительно каталога приложения,
  например `file = "roms/micro80_monitor.bin"`).

The `profiles/` and `roms/` folders are **not embedded** in the binary —
they sit next to it and can be freely modified or extended.
New files are picked up after restarting the application.

## Проверка загрузки профилей / Profile loading check

Запустите приложение с переменной окружения `I8080_DEBUG_PROFILES=1` —
в консоли появится строка `[profiles] dir=... loaded=N`.

Run the app with the `I8080_DEBUG_PROFILES=1` environment variable —
the console will show `[profiles] dir=... loaded=N`.
