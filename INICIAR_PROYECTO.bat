@echo off
chcp 65001 > nul
echo ========================================================
echo   HOTEL SUAH - INICIALIZADOR AUTOMÁTICO EN 1 CLIC
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/4] Verificando entorno virtual de Python...
if not exist "venv\Scripts\python.exe" (
    echo Creando entorno virtual nuevo...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual. Verifique que Python 3.10+ esté instalado.
        pause
        exit /b 1
    )
)

echo [2/4] Instalando librerías requeridas (Django, PyOTP, Pillow, QR)...
call venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Advertencia durante la instalación de paquetes. Reintentando...
    call venv\Scripts\pip install django pyotp qrcode pillow python-dotenv
)

echo [3/4] Aplicando migraciones de base de datos...
cd hotelSUAH
..\venv\Scripts\python manage.py migrate --no-input

echo [4/4] Creando usuarios del personal, habitaciones y datos iniciales...
..\venv\Scripts\python poblar_datos.py

echo.
echo ========================================================
echo   ¡SISTEMA LISTO Y CONFIGURADO CON ÉXITO!
echo   Iniciando servidor local en http://127.0.0.1:8000
echo ========================================================
echo.
echo Cuentas listas para usar:
echo   - Recepción:     rep@suah.cl   / 1234
echo   - Aseo:          aseo@suah.cl  / 1234
echo   - Mantenimiento: mant@suah.cl  / 1234
echo   - Admin:         admin@suah.cl / admin123
echo   - Cliente Demo:  cliente@suah.cl / Cliente123!
echo.
echo (Para detener el servidor presione Ctrl + C)
echo.

..\venv\Scripts\python manage.py runserver 0.0.0.0:8000
pause
