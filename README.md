# Hotel SUAH - Sistema Unificado de Administración Hotelera

Proyecto Integrado de Gestión Hotelera desarrollado en **Python 3.12**, **Django 6** y **Bootstrap 5**, cumpliendo con los estándares de seguridad informática y normativa chilena (Ley N° 21.719, Ley N° 21.459 e ISO/IEC 27001).

---

## 🚀 Requisitos Previos

- **Python 3.12+** instalado con opción *"Add Python to PATH"*.
- **Git** instalado.

---

## 🛠️ Instalación y Puesta en Marcha (Para el equipo)

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd "Proyecto integrado"
   ```

2. **Crear y activar el entorno virtual:**
   - En Windows (PowerShell):
     ```powershell
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   - Crear archivo `.env` dentro de la carpeta `hotelSUAH/` (o copiar desde `.env.example` si existe):
     ```env
     SECRET_KEY=django-insecure-suah-hotel-secret-key-2026
     DEBUG=True
     ALLOWED_HOSTS=*
     DB_ENGINE=sqlite
     ```

5. **Aplicar migraciones y poblar datos iniciales:**
   ```bash
   cd hotelSUAH
   python manage.py migrate
   python manage.py poblar_sistema_integral
   ```

6. **Iniciar el servidor local:**
   ```bash
   python manage.py runserver
   ```
   - Portal Huéspedes: `http://127.0.0.1:8000/`
   - Intranet Colaboradores: `http://127.0.0.1:8000/login-admin/`

---

## 👥 Credenciales de Prueba (Equipo / Intranet)

Todos los correos de colaboradores pertenecen al dominio `@suah.cl`:
- **Administrador:** `admin@suah.cl` | Clave: `admin123`
- **Recepción:** `rep@suah.cl` | Clave: `admin123`
- **Housekeeping / Aseo:** `aseo@suah.cl` | Clave: `admin123`
- **Mantenimiento:** `mant@suah.cl` | Clave: `admin123`
