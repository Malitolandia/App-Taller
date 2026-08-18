@echo off
title VENE AUTOS - Detener Servidores
color 0C
cls

echo.
echo  ================================================
echo   VENE AUTOS - Deteniendo servidores...
echo  ================================================
echo.

for %%P in (5000 5001 5002) do (
    set "ENCONTRADO=0"
    for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":%%P "') do (
        echo  [..] Apagando servidor en puerto %%P (PID %%a)...
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo.
echo  [OK] Servidores detenidos.
echo.
timeout /t 2 /nobreak >nul
exit
