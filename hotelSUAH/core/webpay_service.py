import os
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

def obtener_transaccion_webpay():
    """
    Inicializa la transacción de Webpay Plus apuntando a los servidores oficiales
    de integración y pruebas de Transbank Developers (webpay3gint.transbank.cl).
    """
    commerce_code = os.getenv('TRANSBANK_COMMERCE_CODE', IntegrationCommerceCodes.WEBPAY_PLUS)
    api_key = os.getenv('TRANSBANK_API_KEY', IntegrationApiKeys.WEBPAY)
    return Transaction.build_for_integration(commerce_code, api_key)

def iniciar_pago_webpay(buy_order, session_id, amount, return_url):
    """
    Crea la transacción en Transbank Developers y retorna el token y la URL de redirección.
    """
    tx = obtener_transaccion_webpay()
    response = tx.create(
        buy_order=str(buy_order),
        session_id=str(session_id),
        amount=int(amount),
        return_url=str(return_url)
    )
    return {
        'url': response['url'],
        'token': response['token']
    }

def confirmar_pago_webpay(token_ws):
    """
    Confirma la transacción con Transbank recibiendo el token_ws enviado en el retorno.
    Retorna el estado de la transacción (código de autorización, monto, respuesta, etc.).
    """
    tx = obtener_transaccion_webpay()
    response = tx.commit(token=token_ws)
    return response
