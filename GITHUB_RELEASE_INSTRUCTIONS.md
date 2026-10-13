# Релиз v2.1.14 на GitHub — пошаговая инструкция (GitHub Desktop)

Дата: 2026-10-13
Коммит релиза: `f45c57b` (ветка `master`)
Файл для вложения: `Release\i8080-5_CI_v2.1.14_win64.zip` (~76.5 МБ)

---

## Шаг 0. Подготовка (уже выполнено)

- [x] Все изменения закоммичены (в GitHub Desktop панель «Изменения» должна быть пустой).
- [x] Пакет релиза собран в каталоге `Release/`:
  - `i8080_CI.exe` — портативное приложение (PyInstaller one-file)
  - `profiles/` — внешние профили систем + шаблоны
  - `roms/` — внешние ROM-образы и шрифты
  - документация: README, USER_GUIDE, ASSEMBLER_GUIDE, OPCODE_REFERENCE, MCP_GUIDE, SCRIPTS_GUIDE, CHANGES, LICENSE, INSTALL
- [x] Windows: zip-архив пакета `Release\i8080-5_CI_v2.1.14_win64.zip` (~76.5 МБ)
- [x] GNU/Linux: исходный архив `Release\i8080-5_CI_v2.1.14_source.tar.gz` (~2.2 МБ);
      готовый Linux-бинарник собирается GitHub Actions
      (см. раздел «Linux-бинарник через GitHub Actions»)

## Шаг 1. Открыть репозиторий в GitHub Desktop

1. Запустите **GitHub Desktop**.
2. `File → Open…` (Файл → Открыть) → выберите папку
   `c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis` → **Open**.
3. Убедитесь, что вверху выбрана ветка **master** и нет незакоммиченных
   изменений (панель «Изменения» слева пуста).

## Шаг 2. Связать репозиторий с GitHub (если ещё не связано)

> Если в панели «Текущая ветка» уже виден `origin` — переходите к Шагу 3.

1. На сайте: войдите на **github.com** → правый верхний угол `+` →
   **New repository**.
2. Имя репозитория: `i8080-5_CI` (или любое удобное),
   Public/Private — по желанию.
   **Не ставьте** галочки «Add a README / .gitignore / license»
   (репозиторий создаём пустым).
3. Нажмите **Create repository**.
4. В GitHub Desktop в панели «Текущая ветка» нажмите
   **Create new repository** (Создать новый репозиторий) —
   приложение само подставит только что созданный репозиторий;
   подтвердите выбор.
   *Альтернатива:* стрелка рядом с именем ветки → **Add remote…** →
   тип `Origin` → вставьте URL вида
   `https://github.com/<ваш-логин>/i8080-5_CI.git` → **Add**.

## Шаг 3. Отправить код на GitHub

1. В панели «Текущая ветка» нажмите **Publish Branch**
   (при первой отправке) или **Push origin** (при последующих).
2. Дождитесь сообщения «You're all synced up!» (ветка и тэги отправлены).

## Шаг 4. Создать тег v2.1.14

1. Нажмите на **стрелку (⌄) рядом с именем ветки** вверху слева.
2. В выпадающем меню выберите **Create tag…** (Создать тег).
3. В диалоге:
   - **Tag name:** `v2.1.14`
   - **Description:** `v2.1.14 — label+addend, безопасная замена $, эталон опкодов, чистка тестов`
4. Нажмите **Create tag**. Тег создаётся на текущем коммите (`f45c57b`).

## Шаг 5. Отправить тег на GitHub

1. Снова нажмите **Push origin** — тег уйдёт вместе с веткой.
2. После отправки в панели «Текущая ветка» появится ссылка
   **Create release** (Создать релиз) — нажмите её.
   *Если ссылки нет:* откройте в браузере
   `https://github.com/<ваш-логин>/i8080-5_CI/releases/new?tag=v2.1.14`

## Шаг 6. Заполнить страницу релиза (браузер, github.com)

1. **Choose a tag:** `v2.1.14` (подставится автоматически).
2. **Release title:** `v2.1.14`
3. В поле **Describe this release** вставьте текст из раздела
   «Текст release notes» ниже.
4. Перетащите файлы в блок **Attach binaries**:
   - `Release\i8080-5_CI_v2.1.14_win64.zip` (Windows)
   - `Release\i8080-5_CI_v2.1.14_source.tar.gz` (GNU/Linux, исходники)
   - при наличии: `i8080-5_CI_v2.1.14_linux_x86_64.tar.gz` (готовый Linux-бинарник,
     скачанный из артефактов GitHub Actions — см. раздел ниже)
5. Нажмите **Publish release**.

Готово: релиз доступен по адресу
`https://github.com/<ваш-логин>/i8080-5_CI/releases/tag/v2.1.14`

---

## Текст release notes (скопировать в шаг 6)

```
## i8080-5 CI v2.1.14 (build 20261013)

### Что нового / What's new

- **Ассемблер v2 (Notepad++ style):** вкладки файлов, workspace-файлы (.ws),
  Ctrl+Click — переход к метке, жирная подсветка глобальных меток (::),
  автозагрузка map-файла и отображение символов в дизассемблере.
- **Поддержка 8085:** DSUB, ARHL, SHLX, LHLX, RIM, SIM;
  корректные пересекающиеся опкоды 8080/8085 (cpu_type).
- **label+addend** (метка+N) и безопасная замена `$` в ассемблере.
- **OPCODE_REFERENCE.md** — эталонный справочник опкодов 8080/8085.
- Чистка и стабилизация тестов: 921 + 203 + 57 + 7 + 6 + 44 тестов проходят.

### Состав пакета / Package contents

- **Windows:** `i8080-5_CI_v2.1.14_win64.zip` — портативное приложение
  (Windows 10/11 x64, PyInstaller) + profiles/ + roms/ + документация
- **GNU/Linux:** `i8080-5_CI_v2.1.14_linux_x86_64.tar.gz` — портативный
  бинарник (PyInstaller) + profiles/ + roms/ + документация;
  либо исходники `i8080-5_CI_v2.1.14_source.tar.gz`
  (сборка: `./build_linux.sh` или `pip install -r requirements.txt`)
- `profiles/` — внешние профили систем (TOML) + шаблоны
- `roms/` — внешние ROM-образы и шрифты
- документация: README, USER_GUIDE, ASSEMBLER_GUIDE, OPCODE_REFERENCE,
  MCP_GUIDE, SCRIPTS_GUIDE, CHANGES, LICENSE, INSTALL

### Установка / Installation

- **Windows:** распакуйте zip в любую папку и запустите `i8080_CI.exe`.
- **GNU/Linux:** распакуйте tar.gz и выполните `./i8080_CI`
  (или из исходников: `pip install -r requirements.txt && python i8080_CI.py`).

Каталоги `profiles/` и `roms/` лежат рядом с приложением и могут
свободно меняться и дополняться (см. INSTALL.md).

Unpack the archive and run the app. The `profiles/` and `roms/` folders
sit next to the binary and can be freely modified or extended (see INSTALL.md).
```

---

## Linux-бинарник через GitHub Actions (готовый файл для вложения)

PyInstaller не умеет кросс-сборку: Linux-бинарник собирается только в Linux.
В репозитории уже есть workflow `.github/workflows/build-linux.yml`:

1. После первого **Push origin** (Шаг 3) откройте на GitHub:
   `https://github.com/<ваш-логин>/i8080-5_CI/actions` → workflow **build-linux**
   → **Run workflow** (или дождитесь автоматического запуска —
   он срабатывает при отправке тега `v*`).
2. Когда запуск станет зелёным (~3–5 мин): страница run → вкладка
   **Artifacts** → скачайте `i8080-5_CI_linux_x86_64`
   (это `i8080-5_CI_v2.1.14_linux_x86_64.tar.gz`: бинарник + profiles/ + roms/ + docs).
3. Прикрепите скачанный файл к релизу в Шаге 6.

Альтернатива без GitHub: на любой Linux-машине распакуйте исходный архив
и выполните `./build_linux.sh` (нужен Python 3.10+ с venv и pip).

## Примечания

- **Размер вложения:** ~76.5 МБ — в пределах лимита GitHub (2 ГБ).
- **Внешние файлы:** профили, ROM и шрифты НЕ вшиты в exe —
  это осознанное решение, чтобы пользователь мог их менять.
- **Проверка загрузки профилей:** запустите exe с переменной окружения
  `I8080_DEBUG_PROFILES=1` — в консоли появится строка
  `[profiles] dir=... loaded=12`.
- Если нужно обновить релиз: замените файлы в `Release/`, пересоберите zip
  (те же команды, что использовались при сборке) и на странице релиза
  GitHub нажмите «Edit” → обновите вложение.
