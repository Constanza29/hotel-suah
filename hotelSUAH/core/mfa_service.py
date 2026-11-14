import pyotp
import qrcode
import io
import base64
import hashlib
import time
import datetime
import urllib.request
import email.utils

_INTERNET_TIME_OFFSET = None
_LAST_OFFSET_CHECK = 0

def _obtener_timestamp_real_internet():
    global _INTERNET_TIME_OFFSET, _LAST_OFFSET_CHECK
    now_local = time.time()
    if _INTERNET_TIME_OFFSET is not None and (now_local - _LAST_OFFSET_CHECK) < 600:
        return now_local + _INTERNET_TIME_OFFSET

    for url in ('https://www.google.com', 'https://www.cloudflare.com'):
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                date_str = resp.headers.get('Date')
                if date_str:
                    net_dt = email.utils.parsedate_to_datetime(date_str)
                    _INTERNET_TIME_OFFSET = net_dt.timestamp() - time.time()
                    _LAST_OFFSET_CHECK = time.time()
                    return time.time() + _INTERNET_TIME_OFFSET
        except Exception:
            continue
    return now_local

def _generar_secret_desde_seed(seed):
    h = hashlib.sha256(seed.encode('utf-8')).digest()
    return base64.b32encode(h[:10]).decode('utf-8')

def obtener_secret_mfa_usuario(user):
    seed = f"suah-mfa-{user.id}-{user.username}"
    return _generar_secret_desde_seed(seed)

def generar_datos_mfa(user):
    secret = obtener_secret_mfa_usuario(user)
    totp = pyotp.TOTP(secret, interval=30)
    real_ts = _obtener_timestamp_real_internet()
    current_otp = totp.at(int(real_ts))

    uri = totp.provisioning_uri(name=user.email or user.username, issuer_name='Hotel SUAH')

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
    if not codigo:
        return False
    codigo = str(codigo).strip().replace(" ", "").replace("-", "")
    if not (codigo.isdigit() and len(codigo) == 6):
        return False

    posibles_secrets = [obtener_secret_mfa_usuario(user)]
    for possible_id in range(1, 25):
        s = _generar_secret_desde_seed(f"suah-mfa-{possible_id}-{user.username}")
        if s not in posibles_secrets:
            posibles_secrets.append(s)

    real_ts = _obtener_timestamp_real_internet()
    real_dt = datetime.datetime.fromtimestamp(real_ts, tz=datetime.timezone.utc)
    local_dt = datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc)

    for secret in posibles_secrets:
        totp = pyotp.TOTP(secret, interval=30)
        if totp.verify(codigo, for_time=real_dt, valid_window=4):
            return True
        if totp.verify(codigo, for_time=local_dt, valid_window=4):
            return True

    return False
