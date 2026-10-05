@echo off
REM ============================================================
REM  dev_mode.bat — режим разработки (F5 / Extension Development Host)
REM  Запускает VS Code с плагином в режиме разработки.
REM ============================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo  i8080_ci-vscode — режим разработки
echo ============================================================

where node >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Node.js не найден. Установите Node.js 18+
    exit /b 1
)

echo [1/2] npm install...
call npm install
if errorlevel 1 (
    echo [ОШИБКА] npm install завершился с ошибкой.
    exit /b 1
)

echo [2/2] Компиляция...
call npm run compile
if errorlevel 1 (
    echo [ОШИБКА] Компиляция завершилась с ошибкой.
    exit /b 1
)

echo.
echo Запуск Extension Development Host...
echo  (В открывшемся окне: F5 для отладки, или просто работайте с .asm-файлами)
where code >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] 'code' не найден в PATH.
    exit /b 1
)
call code --extensionDevelopmentPath="%cd%"
endlocal
