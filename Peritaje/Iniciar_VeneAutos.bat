@echo off
title VENE AUTOS - Sistema de Peritaje
color 0C
cls

echo.
echo  ================================================
echo   VENE AUTOS ^| Sistema de Peritaje Vehicular
echo  ================================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta instalado.
    echo  Descargalo desde: https://www.python.org/downloads/
    echo  Marca "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b
)

:: Instalar dependencias una por una con feedback
echo  Instalando flask...
pip install flask --quiet --disable-pip-version-check 2>nul

echo  Instalando openpyxl...
pip install openpyxl --quiet --disable-pip-version-check 2>nul

echo  Instalando reportlab...
pip install reportlab --quiet --disable-pip-version-check 2>nul

echo  Instalando pillow...
pip install pillow --quiet --disable-pip-version-check 2>nul

echo  Dependencias listas.
echo.

:: Abrir en Chrome despues de 3 segundos
start "" cmd /c "timeout /t 3 >nul && start chrome http://localhost:5001"

echo  Servidor corriendo en: http://localhost:5001
echo  Para detener: cierra esta ventana o presiona Ctrl+C
echo  ================================================
echo.

cd /d "%~dp0"
python app.py

echo.
echo  El servidor se detuvo.
pause
