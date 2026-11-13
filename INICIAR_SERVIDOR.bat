@echo off
title Levantando Servidor Hotel SUAH
echo ======================================================================
echo           INICIANDO SISTEMA UNIFICADO HOTELERO SUAH
echo ======================================================================
echo.

IF NOT EXIST "venv" (
    echo [!] Creando entorno virtual 'venv'...
    python -m venv venv
    echo [OK] Entorno creado. Instalando dependencias...
    call venv\Scripts\activate
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate
)

cd hotelSUAH
echo.
echo [*] Iniciando servidor Django en http://127.0.0.1:8000/
echo [*] Para detener el servidor presiona Ctrl + C en esta ventana.
echo.
python manage.py runserver 127.0.0.1:8000
pause
