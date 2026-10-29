import re
from itertools import cycle

def validar_rut_chileno(rut_str):
    """
    Valida un RUT chileno usando el algoritmo oficial de Módulo 11.
    Soporta formatos con puntos y guion (ej: 12.345.678-5) o solo con guion (12345678-5).
    Retorna (es_valido: bool, mensaje: str, rut_limpio: str)
    """
    if not rut_str:
        return False, "El RUT es obligatorio.", ""

    rut_limpio = rut_str.replace('.', '').replace(' ', '').strip().upper()

    patron = r'^(\d{7,8})-([\dK])$'
    match = re.match(patron, rut_limpio)
    if not match:
        return False, "Formato de RUT inválido. Debe ser ej: 12.345.678-5 o 12345678-K", ""

    cuerpo, dv = match.groups()

    suma = sum(int(digito) * factor for digito, factor in zip(reversed(cuerpo), cycle([2, 3, 4, 5, 6, 7])))
    resto = 11 - (suma % 11)

    if resto == 11:
        dv_esperado = '0'
    elif resto == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(resto)

    if dv != dv_esperado:
        return False, f"El RUT ingresado no es válido", ""

    cuerpo_con_puntos = f"{int(cuerpo):,}".replace(',', '.')
    rut_formateado = f"{cuerpo_con_puntos}-{dv}"
    return True, "RUT válido", rut_formateado


def validar_documento_identidad(tipo_doc, doc_str):
    """
    Valida RUT chileno o Pasaporte extranjero.
    """
    if tipo_doc == 'pasaporte':
        doc_limpio = doc_str.strip().upper()
        if len(doc_limpio) < 6 or len(doc_limpio) > 15:
            return False, "El pasaporte debe tener entre 6 y 15 caracteres alfanuméricos.", ""
        if not re.match(r'^[A-Z0-9]+$', doc_limpio):
            return False, "El pasaporte solo puede contener letras y números sin símbolos.", ""
        return True, "Pasaporte válido", doc_limpio
    else:
        return validar_rut_chileno(doc_str)


DOMINIOS_PERMITIDOS = [
    'gmail.com',
    'outlook.com',
    'hotmail.com',
    'live.com',
    'yahoo.com',
    'yahoo.es',
    'icloud.com',
    'duocuc.cl',
    'inacap.cl',
    'suah.cl',
    'hotel.cl',
    'empresa.cl',
    'correo.cl',
]

def validar_correo_real(email_str):
    """
    Valida formato estricto RFC 5322 y restringe o valida proveedores de correo reconocidos.
    """
    if not email_str:
        return False, "El correo electrónico es obligatorio."

    email = email_str.strip().lower()

    regex_correo = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(regex_correo, email):
        return False, "El formato del correo es inválido (ejemplo: usuario@gmail.com)."

    partes = email.split('@')
    if len(partes) != 2:
        return False, "El correo no tiene una estructura válida."

    usuario, dominio = partes

    if len(usuario) < 2:
        return False, "El nombre de usuario del correo es demasiado corto."

    partes_dominio = dominio.split('.')
    if len(partes_dominio) < 2 or len(partes_dominio[-1]) < 2:
        return False, "El dominio del correo debe terminar en una extensión válida (.com, .cl, etc.)."

    es_reconocido = any(dominio == d or dominio.endswith('.' + d) for d in DOMINIOS_PERMITIDOS)
    if not es_reconocido:
        if not (dominio.endswith('.cl') or dominio.endswith('.com') or dominio.endswith('.edu') or dominio.endswith('.org')):
            return False, f"Dominio '@{dominio}' no admitido. Utilice correos reales como @gmail.com, @outlook.com o dominio institucional."

    return True, "Correo válido"


def validar_telefono_chileno(tel_str):
    """
    Valida formato de número telefónico:
    - Móvil chileno estándar: +56 9 1234 5678, +56912345678, o 912345678 (9 dígitos)
    - Internacional: código de país + número entre 8 y 15 dígitos.
    - Rechaza comillas, caracteres extraños o números absurdos.
    Retorna (es_valido: bool, mensaje: str, tel_formateado: str)
    """
    if not tel_str or not tel_str.strip():
        # Si no ingresó teléfono y no es estrictamente obligatorio, retorna True o pide el campo
        return False, "El teléfono de contacto es obligatorio.", ""

    # Si contiene caracteres sospechosos como comillas, barras o letras
    if re.search(r"['\";<>\\]", tel_str):
        return False, "El teléfono contiene caracteres no válidos (no se permiten comillas ni símbolos especiales).", ""

    # Extraer solo dígitos y el signo + si existe al inicio
    tel_limpio = tel_str.strip()
    tiene_plus = tel_limpio.startswith('+')
    solo_numeros = re.sub(r'\D', '', tel_limpio)

    if len(solo_numeros) < 8 or len(solo_numeros) > 15:
        return False, f"El teléfono debe tener entre 8 y 12 dígitos numéricos (ingresaste {len(solo_numeros)}).", ""

    # Caso Chile: Si ingresó 9 dígitos (ej: 912345678)
    if len(solo_numeros) == 9 and solo_numeros.startswith('9'):
        tel_formateado = f"+56 9 {solo_numeros[1:5]} {solo_numeros[5:]}"
        return True, "Teléfono válido", tel_formateado

    # Caso Chile con 569: (ej: 56912345678 -> 11 dígitos)
    if len(solo_numeros) == 11 and solo_numeros.startswith('569'):
        num = solo_numeros[3:]
        tel_formateado = f"+56 9 {num[:4]} {num[4:]}"
        return True, "Teléfono válido", tel_formateado

    # Caso internacional genérico
    prefijo = "+" if tiene_plus else ""
    return True, "Teléfono válido", f"{prefijo}{solo_numeros}"
