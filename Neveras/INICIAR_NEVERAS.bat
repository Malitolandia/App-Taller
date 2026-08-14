@echo off
title Dashboard Neveras

set "CARPETA=%~dp0"
set "ACCESO=%USERPROFILE%\Desktop\Dashboard Neveras.lnk"

echo.
echo  ==========================================
echo   Dashboard Neveras - Iniciando...
echo  ==========================================
echo.

:: ── 1. Verificar Python ───────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python no esta instalado.
    echo.
    echo  Ve a: https://python.org/downloads
    echo  y marca "Add Python to PATH" al instalar.
    echo.
    pause
    start https://python.org/downloads
    exit /b
)
echo  [OK] Python encontrado

:: ── 2. Instalar dependencias ──────────────
echo  [..] Verificando dependencias...
pip install flask flask-cors pandas openpyxl --quiet --exists-action i >nul 2>&1
echo  [OK] Dependencias listas

:: ── 3. Crear icono ────────────────────────
if not exist "%CARPETA%neveras.ico" (
    echo  [..] Creando icono...
    python "%CARPETA%crear_icono.py" >nul 2>&1
    echo  [OK] Icono creado
)

:: ── 4. Crear acceso directo con PowerShell ──
if not exist "%ACCESO%" (
    echo  [..] Creando acceso directo en el Escritorio...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%ACCESO%'); $sc.TargetPath = '%CARPETA%INICIAR_NEVERAS.bat'; $sc.WorkingDirectory = '%CARPETA%'; $sc.Description = 'Dashboard Neveras'; $ico = '%CARPETA%neveras.ico'; if (Test-Path $ico) { $sc.IconLocation = $ico }; $sc.Save()"
    echo  [OK] Acceso directo creado en el Escritorio
)

:: ── 5. Liberar puerto 5000 si esta ocupado ──
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ── 6. Iniciar servidor en ventana minimizada ──
echo  [..] Iniciando servidor...
start "Servidor Neveras" /min cmd /k "cd /d %CARPETA% && python servidor.py"

:: ── 7. Esperar a que el servidor responda (max 15 seg) ──
echo  [..] Esperando servidor...
set INTENTOS=0
:ESPERAR
set /a INTENTOS+=1
if %INTENTOS% GTR 15 (
    echo.
    echo  [!!] El servidor tardo demasiado.
    echo       Revisa que servidor.py este en la carpeta.
    pause
    exit /b
)
timeout /t 1 /nobreak >nul
python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000', timeout=1)" >nul 2>&1
if errorlevel 1 goto ESPERAR

:: ── 8. Abrir navegador Chrome (no incógnito) ──
echo  [OK] Servidor listo
echo  [..] Abriendo Chrome...
start chrome "http://localhost:5000" --new-window

echo.
echo  ==========================================
echo   Dashboard abierto en Chrome
echo   Para cerrar el servidor: cierra la
echo   ventana negra minimizada en la barra.
echo  ==========================================
echo.
timeout /t 3 /nobreak >nul
exit