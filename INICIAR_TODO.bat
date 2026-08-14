@echo off
title VENE AUTOS - Lanzador General
color 0A
cls

:: ================================================================
::  AJUSTA ESTAS 3 RUTAS SI TUS CARPETAS SE LLAMAN DIFERENTE
::  (deben apuntar a la carpeta donde esta el app.py / servidor.py
::   de cada sistema)
:: ================================================================
set "BASE=%~dp0"
set "CARPETA_PERITAJE=%BASE%Peritaje"
set "CARPETA_TALLER=%BASE%ControlTaller"
set "CARPETA_NEVERAS=%BASE%Neveras"
:: ================================================================

echo.
echo  ================================================
echo   VENE AUTOS - Iniciando las 3 aplicaciones...
echo  ================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta instalado.
    echo  Ve a: https://python.org/downloads
    echo  y marca "Add Python to PATH" al instalar.
    echo.
    pause
    start https://python.org/downloads
    exit /b
)
echo  [OK] Python encontrado

:: 2. Verificar que las 3 carpetas existan
if not exist "%CARPETA_PERITAJE%\app.py" (
    echo  [ERROR] No encuentro app.py en: %CARPETA_PERITAJE%
    echo  Edita este .bat y corrige CARPETA_PERITAJE.
    pause
    exit /b
)
if not exist "%CARPETA_TALLER%\app.py" (
    echo  [ERROR] No encuentro app.py en: %CARPETA_TALLER%
    echo  Edita este .bat y corrige CARPETA_TALLER.
    pause
    exit /b
)
if not exist "%CARPETA_NEVERAS%\servidor.py" (
    echo  [ERROR] No encuentro servidor.py en: %CARPETA_NEVERAS%
    echo  Edita este .bat y corrige CARPETA_NEVERAS.
    pause
    exit /b
)
echo  [OK] Las 3 carpetas fueron encontradas

:: 3. Crear acceso directo en el Escritorio (solo la primera vez)
set "ACCESO=%USERPROFILE%\Desktop\Vene Autos - Panel.lnk"
if not exist "%ACCESO%" (
    echo  [..] Creando acceso directo en el Escritorio...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ws = New-Object -ComObject WScript.Shell;" ^
        "$sc = $ws.CreateShortcut('%ACCESO%');" ^
        "$sc.TargetPath = '%BASE%INICIAR_TODO.bat';" ^
        "$sc.WorkingDirectory = '%BASE%';" ^
        "$sc.Description = 'Vene Autos - Panel de Aplicaciones';" ^
        "if (Test-Path '%BASE%neveras.ico') { $sc.IconLocation = '%BASE%neveras.ico' };" ^
        "$sc.Save()"
    echo  [OK] Acceso directo creado en el Escritorio
)

:: 4. Liberar puertos 5000, 5001 y 5002 si estan ocupados
for %%P in (5000 5001 5002) do (
    for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":%%P "') do (
        taskkill /PID %%a /F >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

:: 5. Iniciar los 3 servidores OCULTOS (sin ventana, sin icono en la barra de tareas)
echo  [..] Iniciando Peritaje Vehicular (puerto 5001)...
start "" /D "%CARPETA_PERITAJE%" /B cmd /c "set PYTHONIOENCODING=utf-8&& python app.py >> server.log 2>&1"

echo  [..] Iniciando Nomina y Gastos (puerto 5002)...
start "" /D "%CARPETA_TALLER%" /B cmd /c "set PYTHONIOENCODING=utf-8&& python app.py >> server.log 2>&1"

echo  [..] Iniciando Control Neveras (puerto 5000)...
start "" /D "%CARPETA_NEVERAS%" /B cmd /c "set PYTHONIOENCODING=utf-8&& python servidor.py >> server.log 2>&1"

:: 6. Esperar a que los 3 respondan (max 20 seg)
echo  [..] Esperando servidores...
set INTENTOS=0
:ESPERAR
set /a INTENTOS+=1
if %INTENTOS% GTR 20 (
    echo  [!!] Algunos servidores tardaron demasiado.
    echo       Igual se abrira el menu, revisa los puntos de estado.
    goto ABRIR
)
timeout /t 1 /nobreak >nul
python -c "import urllib.request as u; [u.urlopen('http://localhost:%p',timeout=1) for p in (5000,5001,5002)]" >nul 2>&1
if errorlevel 1 goto ESPERAR

:ABRIR
echo  [OK] Servidores listos
echo  [..] Abriendo menu en Chrome...
start chrome "%BASE%menu.html" --new-window

echo.
echo  ================================================
echo   Panel abierto en Chrome.
echo   Los servidores corren ocultos (sin ventana).
echo   Para apagarlos usa DETENER_TODO.bat
echo  ================================================
echo.
timeout /t 3 /nobreak >nul
exit
