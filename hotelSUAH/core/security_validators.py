import re
from django.core.exceptions import ValidationError

def validar_politica_contrasena_chile(password, password_confirm=None):
    """
    Política de contraseñas robustas alineada con la Ley N° 21.459 (Delitos Informáticos),
    Ley N° 21.719 (Protección de Datos Personales en Chile), ISO/IEC 27001 y OWASP:
    - Longitud mínima de 8 caracteres (recomendado 10+)
    - Coincidencia exacta con la confirmación de contraseña
    - Al menos una letra mayúscula (A-Z)
    - Al menos una letra minúscula (a-z)
    - Al menos un número (0-9)
    - Al menos un carácter especial (@, $, !, %, *, ?, &, #, _, -, .)
    """
    errores = []

    if password_confirm is not None and password != password_confirm:
        errores.append("Las contraseñas no coinciden. Por favor verifícalas.")

    if len(password) < 8:
        errores.append("La contraseña debe tener un mínimo de 8 caracteres.")

    if not re.search(r'[A-Z]', password):
        errores.append("Debe contener al menos una letra mayúscula (A-Z).")

    if not re.search(r'[a-z]', password):
        errores.append("Debe contener al menos una letra minúscula (a-z).")

    if not re.search(r'[0-9]', password):
        errores.append("Debe contener al menos un número (0-9).")

    if not re.search(r'[@$!%*?&#_\-\.]', password):
        errores.append("Debe contener al menos un carácter especial (@, $, !, %, *, ?, &, #, _, -, .).")

    return errores
