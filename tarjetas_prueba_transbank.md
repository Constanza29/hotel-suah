# 💳 Tarjetas Oficiales de Transbank Developers para Pruebas (Webpay Plus)

El sistema está conectado a la pasarela oficial de **Transbank Developers** (`webpay3gint.transbank.cl`).

---

### 1. Tarjeta APROBADA (Pago Exitoso) ✅
* **Número de Tarjeta:** `4051 8856 0044 6623`
* **Fecha de Expiración:** Cualquier fecha futura (ej: `12/28` o `10/30`)
* **CVV:** `123`
* **Comportamiento:** Transbank aprueba el pago, genera el código de autorización, abona el dinero al Folio de la habitación en SUAH y muestra el comprobante verde.

---

### 2. Tarjeta RECHAZADA (Prueba de Fallo) ❌
* **Número de Tarjeta:** `5186 0595 5959 0568`
* **Fecha de Expiración:** Cualquier fecha futura
* **CVV:** `123`
* **Comportamiento:** Transbank rechaza la transacción y el sistema muestra el comprobante rojo sin descontar dinero.
