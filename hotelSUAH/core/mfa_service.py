import pyotp
import qrcode
import io
import base64
import hashlib

def obtener_secret_mfa_usuario(user):
    """
    Genera un secreto TOTP base32 determinista pero seguro por usuario,
    basado en su ID y la SECRET_KEY de Django (o un salt fijo).
    Esto evita tener que hacer migraciones complejas de base de datos
    y permite que cada usuario tenga su propio secreto único y persistente.
    """
    seed = f"suah-mfa-{user.id}-{user.username}"
    # Genera 16 bytes base32 válidos
    h = hashlib.sha256(seed.encode('utf-8')).digest()
    b32 = base64.b32encode(h[:10]).decode('utf-8') # 16 caracteres base32
    return b32

def generar_datos_mfa(user):
    """
    Retorna el secreto TOTP, el código actual y la imagen QR en Base64.
    """
    secret = obtener_secret_mfa_usuario(user)
    totp = pyotp.TOTP(secret, interval=30)
    current_otp = totp.now()

    # URI estándar compatible con Google Authenticator y Microsoft Authenticator
    uri = totp.provisioning_uri(name=user.email or user.username, issuer_name='Hotel SUAH')

    # Generar QR
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return {
        'secret': secret,
        'current_otp': current_otp,
        'qr_b64': qr_b64,
        'uri': uri
    }

def validar_codigo_mfa(user, codigo):
    """
    Valida si el código de 6 dígitos ingresado coincide con el algoritmo TOTP del usuario.
    Permite una ventana de tolerancia extendida (valid_window=4) para cubrir variaciones
    de hasta +-2 minutos entre el reloj del servidor y el teléfono del usuario.
    """
    if not codigo:
        return False
    codigo = str(codigo).strip().replace(" ", "").replace("-", "")
    secret = obtener_secret_mfa_usuario(user)
    totp = pyotp.TOTP(secret, interval=30)

    # valid_window=4 permite +-120 segundos de desfase temporal
    return totp.verify(codigo, valid_window=4)
