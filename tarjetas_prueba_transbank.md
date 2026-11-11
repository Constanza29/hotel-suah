# 💳 Tarjetas Oficiales de Transbank Developers para Demostración

Para tu defensa con el profesor, puedes demostrar los tres escenarios reales de pago:

---

### 1. 🟢 Tarjeta de CRÉDITO Aprobada (VISA)
* **Número:** `4051 8856 0044 6623`
* **Vencimiento:** `12/28` (o cualquier fecha futura)
* **CVV:** `123`
* **Pantalla de Autorización Bancaria Transbank:**
  - **RUT:** `11.111.111-1` (con puntos y guion)
  - **Clave:** `123`
* **Resultado:** Pago aprobado inmediatamente. Genera código de autorización y voucher verde, abonando al Folio.

---

### 2. 🔵 Tarjeta de DÉBITO Aprobada (Redcompra)
* **Número:** `4051 8842 3993 7763`
* **Vencimiento:** `12/28`
* **CVV:** `123`
* **Pantalla de Autorización Bancaria:**
  - **RUT:** `11.111.111-1`
  - **Clave:** `123`
* **Resultado:** Simula el débito bancario Redcompra y confirma el abono en el folio.

---

### 3. 🔴 Tarjeta de Pago RECHAZADO (Prueba de Error)
* **Número:** `5186 0595 5959 0568`
* **Vencimiento:** `12/28`
* **CVV:** `123`
* **Resultado:** Transbank rechaza la transacción y el sistema muestra el comprobante rojo de *"Transacción Rechazada"* sin descontar dinero.
