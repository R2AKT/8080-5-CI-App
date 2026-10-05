@echo off
REM ============================================================
REM  build_vsix.bat — сборка .vsix плагина i8080_ci-vscode
REM  Требования: Node.js 18+, npm, VS Code (для vsce)
REM ============================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo  i8080_ci-vscode — сборка .vsix
echo ============================================================

REM 1) Проверяем Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Node.js не найден. Установите Node.js 18+ с https://nodejs.org
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODEVER=%%v
echo Node.js: %NODEVER%

REM 2) Устанавливаем зависимости (typescript, @types)
echo.
echo [1/3] npm install...
call npm install
if errorlevel 1 (
    echo [ОШИБКА] npm install завершился с ошибкой.
    exit /b 1
)

REM 3) Компилируем TypeScript
echo.
echo [2/3] Компиляция TypeScript...
call npm run compile
if errorlevel 1 (
    echo [ОШИБКА] Компиляция TypeScript завершилась с ошибкой.
    exit /b 1
)

REM 4) Собираем .vsix через vsce
echo.
echo [3/3] Сборка .vsix (vsce package)...
REM vsce — глобально или через npx
where vsce >nul 2>nul
if errorlevel 1 (
    echo vsce не найден глобально, используем npx...
    call npx --yes @vscode/vsce package --allow-missing-repository --no-dependencies
) else (
    call vsce package --allow-missing-repository --no-dependencies
)
if errorlevel 1 (
    echo [ОШИБКА] Сборка .vsix завершилась с ошибкой.
    exit /b 1
)

echo.
echo ============================================================
echo  ГОТОВО! Файл .vsix создан в папке плагина.
echo  Установка:  install.bat
echo  или:        code --install-extension i8080_ci-vscode-*.vsix
echo ============================================================
endlocal
