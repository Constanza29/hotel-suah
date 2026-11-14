import os
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

def obtener_transaccion_webpay():
    commerce_code = os.getenv('TRANSBANK_COMMERCE_CODE', IntegrationCommerceCodes.WEBPAY_PLUS)
    api_key = os.getenv('TRANSBANK_API_KEY', IntegrationApiKeys.WEBPAY)
    return Transaction.build_for_integration(commerce_code, api_key)

def iniciar_pago_webpay(buy_order, session_id, amount, return_url):
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
    tx = obtener_transaccion_webpay()
    return tx.commit(token=token_ws)
