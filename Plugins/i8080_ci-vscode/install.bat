@echo off
REM ============================================================
REM  install.bat — установка .vsix плагина i8080_ci-vscode
REM  в VS Code через 'code --install-extension'
REM ============================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo  i8080_ci-vscode — установка в VS Code
echo ============================================================

REM Ищем .vsix в папке
set VSIX=
for %%f in (*.vsix) do set VSIX=%%f
if not defined VSIX (
    echo [ОШИБКА] .vsix-файл не найден. Сначала выполните build_vsix.bat
    exit /b 1
)
echo Найден: %VSIX%

REM Ищем 'code' в PATH
where code >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] 'code' не найден в PATH.
    echo  В VS Code: Ctrl+Shift+P -^> "Shell Command: Install 'code' command in PATH"
    exit /b 1
)

echo.
echo Установка %VSIX% ...
call code --install-extension "%VSIX%" --force
if errorlevel 1 (
    echo [ОШИБКА] Установка завершилась с ошибкой.
    exit /b 1
)

echo.
echo ============================================================
echo  УСТАНОВЛЕНО! Перезагрузите VS Code (Ctrl+Shift+P -^>
echo  "Developer: Reload Window"), чтобы плагин активировался.
echo ============================================================
endlocal
