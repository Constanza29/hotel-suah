@echo off
chcp 65001 > nul
title Servidor Hotel SUAH
echo ======================================================================
echo           INICIANDO SISTEMA UNIFICADO HOTELERO SUAH
echo ======================================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [!] Creando entorno virtual 'venv'...
    python -m venv venv
    echo [OK] Instalando dependencias...
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

REM Verificar que Pillow y librerías binarias coincidan con la versión de Python de este PC
venv\Scripts\python.exe -c "from PIL import _imaging; import qrcode, pyotp" >nul 2>&1
if errorlevel 1 (
    echo [*] Adaptando librerías a la versión de Python de este computador...
    python -m venv venv
    venv\Scripts\python.exe -m pip install --upgrade --force-reinstall -r requirements.txt
)

echo [*] Verificando base de datos y datos iniciales...
venv\Scripts\python.exe manage.py migrate --no-input
venv\Scripts\python.exe poblar_datos.py

echo.
echo ======================================================================
echo   ¡SERVIDOR ACTIVO EN: http://127.0.0.1:8000/
echo   IMPORTANTE: Mantén esta ventana abierta mientras uses el sistema.
echo   (Puedes minimizarla. Para apagar el servidor, ciérrala o usa Ctrl+C)
echo ======================================================================
echo.
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
