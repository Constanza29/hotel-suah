import re

def validar_politica_contrasena_chile(password, password_confirm=None):
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
