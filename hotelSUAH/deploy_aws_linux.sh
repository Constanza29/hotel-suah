#!/bin/bash
# ========================================================
# SCRIPT DE DESPLIEGUE EN AWS EC2 (UBUNTU / DEBIAN LINUX)
# Sistema Unificado de Administración Hotelera (SUAH)
# ========================================================

set -e

echo "=== Actualizando paquetes del sistema ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Instalando Python, Nginx, Git y dependencias de base de datos ==="
sudo apt-get install -y python3-pip python3-venv python3-dev libpq-dev libmysqlclient-dev nginx git curl

# Crear directorio de la app si no existe
APP_DIR="/var/www/suah_hotel"
echo "=== Preparando directorio de la aplicación en $APP_DIR ==="
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# Copiar archivos o clonar repositorio
# cd $APP_DIR
# git pull origin main

echo "=== Creando y activando entorno virtual en Linux ==="
python3 -m venv $APP_DIR/venv
source $APP_DIR/venv/bin/activate

echo "=== Instalando requerimientos de Python y Gunicorn ==="
pip install --upgrade pip
pip install -r $APP_DIR/hotelSUAH/requirements.txt
pip install gunicorn

echo "=== Aplicando migraciones y recolectando archivos estáticos ==="
cd $APP_DIR/hotelSUAH
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "=== Configuración lista para Systemd y Nginx ==="
