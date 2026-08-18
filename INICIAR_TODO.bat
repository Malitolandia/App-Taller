@echo off
chcp 65001 >nul
title Cotizador de Repuestos - Servidor Local
cd /d "%~dp0"

echo ============================================
echo   Cotizador de Repuestos - entorno local
echo ============================================
echo.

REM ---------------------------------------------------------
REM 1. Verificar Node.js
REM ---------------------------------------------------------
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Node.js instalado.
    echo Descargalo desde https://nodejs.org/ y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node -v') do echo [OK] Node.js: %%v

REM ---------------------------------------------------------
REM 2. Verificar/crear .env.local
REM ---------------------------------------------------------
if not exist ".env.local" (
    if exist ".env.example" (
        copy /y ".env.example" ".env.local" >nul
        echo.
        echo [AVISO] No existia .env.local, se creo a partir de .env.example.
        echo Se va a abrir en el Bloc de notas para que pongas tus credenciales:
        echo   GOOGLE_SHEETS_CLIENT_EMAIL
        echo   GOOGLE_SHEETS_PRIVATE_KEY
        echo   SPREADSHEET_ID
        echo   ADMIN_PASSWORD
        echo.
        notepad ".env.local"
        echo Cuando termines de editar y guardar el archivo, vuelve aqui.
        pause
    ) else (
        echo [ERROR] No se encontro .env.example ni .env.local. No puedo continuar.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env.local encontrado
)

REM ---------------------------------------------------------
REM 3. Instalar dependencias si falta node_modules
REM ---------------------------------------------------------
if not exist "node_modules" (
    echo.
    echo [...] Instalando dependencias ^(npm install^), puede tardar un poco...
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
) else (
    echo [OK] Dependencias ya instaladas
)

REM ---------------------------------------------------------
REM 4. Verificar Vercel CLI
REM ---------------------------------------------------------
where vercel >nul 2>nul
if errorlevel 1 (
    echo [AVISO] Vercel CLI no esta instalado globalmente.
    echo Instalandolo ahora ^(npm install -g vercel^)...
    call npm install -g vercel
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo instalar Vercel CLI automaticamente.
        echo Instalalo manualmente con: npm install -g vercel
        pause
        exit /b 1
    )
)
for /f "delims=" %%v in ('vercel --version') do echo [OK] Vercel CLI: %%v

REM ---------------------------------------------------------
REM 5. Levantar todo con vercel dev
REM ---------------------------------------------------------
echo.
echo ============================================
echo  Iniciando servidor local...
echo  Panel admin: http://localhost:3000/admin.html
echo  ^(la primera vez, Vercel pedira iniciar sesion
echo   y enlazar el proyecto - solo se hace una vez^)
echo.
echo  Para detener el servidor: cierra esta ventana
echo  o presiona Ctrl+C.
echo ============================================
echo.

call vercel dev

echo.
echo El servidor se detuvo.
pause
