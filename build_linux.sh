#!/usr/bin/env bash
# i8080-5 CI — сборка портативного Linux-бинарника (PyInstaller one-file)
#
# Требования:
#   - Linux x86_64, Python 3.10+ (python3-venv, python3-pip)
#   - Системные библиотеки Qt для ЗАПУСКА (обычно уже есть на десктоп-дистрибутивах):
#       Debian/Ubuntu: libgl1 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0
#       Fedora:        mesa-libGL libxkbcommon dbus-libs fontconfig glib2
#
# Результат: i8080-5_CI_v<версия>_linux_x86_64.tar.gz
#   (бинарник + внешние каталоги profiles/ и roms/ + документация)
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}

echo "==> Виртуальное окружение .venv-build"
$PYTHON -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo "==> PyInstaller (one-file)"
pyinstaller --onefile --optimize 2 i8080_CI.py

echo "==> Сборка пакета release-linux/"
rm -rf release-linux
mkdir -p release-linux
cp dist/i8080_CI release-linux/i8080_CI
chmod +x release-linux/i8080_CI
cp -r profiles roms release-linux/
for f in README.md LICENSE CHANGES.md INSTALL.md USER_GUIDE.md \
         ASSEMBLER_GUIDE.md OPCODE_REFERENCE.md MCP_GUIDE.md \
         SCRIPTS_GUIDE.md logo.png; do
  [ -f "$f" ] && cp "$f" release-linux/
done

VERSION=$($PYTHON -c "import version; print(version.__version__)")
tar czf "i8080-5_CI_v${VERSION}_linux_x86_64.tar.gz" -C release-linux .
echo "==> Готово: i8080-5_CI_v${VERSION}_linux_x86_64.tar.gz"
echo "    Запуск: распаковать архив и выполнить ./i8080_CI"
