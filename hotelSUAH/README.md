# Proyecto Integrado: SUAH (Sistema Unificado de Administración Hotelera) en Django

Sistema hotelero web full-stack desarrollado con **Python** y **Django**, integrando seguridad, control de acceso basado en roles (RBAC), base de datos relacional y frontend responsivo en **Tailwind CSS**.

---

## 🚀 Requisitos e Instalación

### 1. Activar el Entorno Virtual
En la raíz del proyecto (`Proyecto integrado`):
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Ejecutar el Servidor de Desarrollo
```powershell
cd hotelSUAH
python manage.py runserver
```
El servidor quedará disponible en: `http://127.0.0.1:8000/`

---

## 👥 Cuentas de Acceso y Roles (RBAC)

El sistema cuenta con usuarios demo precargados para evaluar cada módulo según los casos de uso:

| Rol | Correo / Usuario | Contraseña | Vistas y Permisos |
| :--- | :--- | :--- | :--- |
| **Recepción** | `rep@hotel.cl` | `1234` | Matriz de habitaciones, Check-In, Folios, Abonos (RF-02) y Liquidación (RF-05) |
| **Housekeeping** | `aseo@hotel.cl` | `1234` | Checklist móvil y cambio de estado de habitaciones (Sucia ➔ En Limpieza ➔ Disponible) |
| **Mantenimiento** | `mant@hotel.cl` | `1234` | Gestión de tickets técnicos, bloqueo preventivo y liberación de habitaciones (RF-04) |
| **Administrador** | `admin` | `admin123` | Control total del sistema y acceso a `/admin/` de Django |

---

## 📂 Arquitectura del Proyecto (`hotelSUAH`)

* **`core/`**: Vistas principales, autenticación, control de sesiones y APIs AJAX.
* **`habitaciones/`**: Modelos de `TipoHabitacion` y `Habitación` con control de estados (*Disponible, Ocupada, Sucia, EnLimpieza, Mantenimiento*).
* **`reservas/`**: Modelos de `Cliente`, `Reserva`, `Folio`, `Cargo` y `Abono`.
* **`operaciones/`**: Modelos de `TareaLimpieza` (Checklist de insumos) y `OrdenMantenimiento` (Tickets de falla).
* **`templates/`**:
  * `base.html`: Layout principal con Tailwind CSS y alertas Toast interactivas.
  * `publico/index.html`: Portal web público idéntico al prototipo con buscador en tiempo real y catálogo.
  * `admin/login.html`: Portal de autenticación con seguridad Django y protección CSRF.
  * `admin/panel.html`: Panel operativo unificado con cambio dinámico de pestañas según rol.
