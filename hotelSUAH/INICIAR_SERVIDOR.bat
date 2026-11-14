@echo off
title Servidor Hotel SUAH
echo ======================================================================
echo           INICIANDO SISTEMA UNIFICADO HOTELERO SUAH
echo ======================================================================
echo.
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual venv...
    python -m venv venv
    echo [2/3] Instalando librerias requeridas...
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
)

"venv\Scripts\python.exe" -c "from PIL import _imaging; import qrcode, pyotp" >nul 2>&1
if errorlevel 1 (
    echo [*] Instalando librerias compatibles con este PC...
    python -m venv venv
    "venv\Scripts\python.exe" -m pip install --upgrade --force-reinstall -r requirements.txt
)

echo [3/3] Preparando base de datos y cuentas del sistema...
"venv\Scripts\python.exe" manage.py migrate --no-input
"venv\Scripts\python.exe" poblar_datos.py

echo.
echo ======================================================================
echo   SERVIDOR ACTIVO EN: http://127.0.0.1:8000/
echo   IMPORTANTE: Manten esta ventana abierta mientras uses el sistema.
echo ======================================================================
echo.
"venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
pause
