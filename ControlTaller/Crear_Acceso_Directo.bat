@echo off
title VENE AUTOS - Crear Acceso Directo
color 0C
cls

echo.
echo  ================================================
echo   Creando acceso directo en el Escritorio...
echo  ================================================
echo.

set "HERE=%~dp0"
set "TARGET=%HERE%Iniciar_ControlTaller.bat"
set "ICON=%HERE%static\icon.ico"
set "SHORTCUT=%USERPROFILE%\Desktop\Vene Autos - Nomina y Gastos.lnk"
set "PS1=%TEMP%\vene_autos_shortcut.ps1"

if not exist "%TARGET%" (
    echo  [ERROR] No se encuentra Iniciar_ControlTaller.bat junto a este archivo.
    echo  Asegurate de ejecutar esto dentro de la carpeta del proyecto.
    echo.
    pause
    exit /b
)

:: Generar script de PowerShell en un archivo temporal (mas confiable que -Command)
> "%PS1%" echo $WshShell = New-Object -ComObject WScript.Shell
>>"%PS1%" echo $Shortcut = $WshShell.CreateShortcut("%SHORTCUT%")
>>"%PS1%" echo $Shortcut.TargetPath = "%TARGET%"
>>"%PS1%" echo $Shortcut.WorkingDirectory = "%HERE%"
>>"%PS1%" echo $Shortcut.IconLocation = "%ICON%"
>>"%PS1%" echo $Shortcut.Description = "Vene Autos - Control de Nomina y Gastos"
>>"%PS1%" echo $Shortcut.Save()

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

del "%PS1%" >nul 2>&1

if exist "%SHORTCUT%" (
    echo.
    echo  Listo. Revisa tu Escritorio: "Vene Autos - Nomina y Gastos"
) else (
    echo.
    echo  [ERROR] No se pudo crear el acceso directo.
    echo  Intenta hacer clic derecho en este archivo y elegir
    echo  "Ejecutar como administrador".
)

echo.
pause
