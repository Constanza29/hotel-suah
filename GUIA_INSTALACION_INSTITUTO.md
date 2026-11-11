# 🚀 Guía de Instalación y Ejecución Rápida en Cualquier Computador (Instituto / Presentación)

Esta guía explica **por qué ocurrió el problema en el computador del instituto** y cómo ejecutarlo ahora **en 1 solo clic** sin errores.

---

## 🔍 ¿Por qué falló ayer en el instituto?

1. **La Base de Datos `db.sqlite3` no viaja en GitHub por seguridad:**
   - En todos los proyectos profesionales de software, el archivo de base de datos (`db.sqlite3`) está en el `.gitignore` para no subir datos sensibles al repositorio público.
   - Al clonar el proyecto en el instituto, **la base de datos llegó vacía y sin tablas**, por lo que no existían ni los usuarios (`rep@suah.cl`, etc.) ni las habitaciones.
2. **El script antiguo de datos creaba `@hotel.cl` en vez de `@suah.cl`:**
   - En el archivo `poblar_datos.py` original los usuarios se llamaban `rep@hotel.cl`, pero la pantalla de login pedía `rep@suah.cl`.
3. **Librerías de MFA no instaladas en la máquina nueva:**
   - `PyOTP`, `qrcode` y `pillow` (necesarios para el código QR y el segundo factor) no vienen por defecto con Python y requerían `pip install -r requirements.txt`.
4. **Desfase horario de Windows en el laboratorio del instituto:**
   - Si el reloj del PC del instituto tiene unos minutos de diferencia con la hora de internet, el algoritmo matemático de Google Authenticator (TOTP) rechaza los códigos. Ya dejamos la ventana de tolerancia extendida a $\pm 2$ minutos para evitar esto.

---

## ⚡ Solución en 1 Clic (Creada y Subida a GitHub)

Creé un archivo ejecutable en la raíz del proyecto llamado:
### 👉 **`INICIAR_PROYECTO.bat`**

Cuando llegues al instituto (o en cualquier computador nuevo), solo debes hacer **DOBLE CLIC** sobre ese archivo. El script hace automáticamente en segundos:
1. Crea el entorno virtual `venv` si no existe.
2. Instala automáticamente todas las librerías (`Django`, `PyOTP`, `Pillow`, `qrcode`, etc.).
3. Ejecuta las migraciones de base de datos (`migrate`).
4. **Crea automáticamente todo el personal, habitaciones y reservas iniciales** ejecutando `poblar_datos.py` con los correos oficiales `@suah.cl`.
5. Enciende el servidor en `http://127.0.0.1:8000`.

---

## 🔑 Credenciales Listas para Usar:
* **Recepción:** `rep@suah.cl` / Clave: `1234`
* **Housekeeping / Aseo:** `aseo@suah.cl` / Clave: `1234`
* **Mantenimiento:** `mant@suah.cl` / Clave: `1234`
* **Administrador:** `admin@suah.cl` / Clave: `admin123`
* **Huésped Demo (con MFA):** `cliente@suah.cl` / Clave: `Cliente123!` (o puedes registrar uno nuevo en la web).
