import uuid
import requests
from .client import MTNMomoClient

def transfer(client, phone, amount, currency, external_id, payer_message, payee_note):
    reference_id = str(uuid.uuid4())
    url = f'{client.base_url}/disbursement/v1_0/transfer'
    headers = client.get_headers('disbursement')
    headers['X-Reference-Id'] = reference_id
    data = {
        'amount': str(amount),
        'currency': currency,
        'externalId': external_id,
        'payee': {
            'partyIdType': 'MSISDN',
            'partyId': phone,
        },
        'payerMessage': payer_message,
        'payeeNote': payee_note,
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return reference_id

def get_transfer_status(client, reference_id):
    url = f'{client.base_url}/disbursement/v1_0/transfer/{reference_id}'
    headers = client.get_headers('disbursement')
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json() 