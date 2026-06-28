# ============================================
#   VALCORE — PAYSTACK PAYMENT SERVICE
#   app/services/payments.py
#
#   Keys come from Settings, never hardcoded.
#   Same graceful-degradation pattern as storage.py:
#   if not configured, functions return a clear
#   error instead of crashing.
# ============================================

import hashlib
import hmac
import requests
from app.core.database import get_setting

PAYSTACK_BASE = 'https://api.paystack.co'


def is_paystack_configured():
    """Check if both Paystack keys are set."""
    public = get_setting('paystack_public_key')
    secret = get_setting('paystack_secret_key')
    return bool(public and secret)


def initialize_transaction(email, amount_naira, reference, callback_url, metadata=None):
    """
    Starts a Paystack transaction.
    amount_naira: price in whole Naira (e.g. 5000 for ₦5,000)
    Paystack expects amount in kobo (smallest unit), so we *100 here.

    Returns: {'ok': True, 'authorization_url': '...', 'access_code': '...', 'reference': '...'}
          or {'ok': False, 'error': '...'}
    """
    if not is_paystack_configured():
        return {'ok': False, 'error': 'Payments not configured. Add Paystack keys in Admin → Settings.'}

    secret_key = get_setting('paystack_secret_key')

    try:
        resp = requests.post(
            f'{PAYSTACK_BASE}/transaction/initialize',
            headers={
                'Authorization': f'Bearer {secret_key}',
                'Content-Type': 'application/json',
            },
            json={
                'email': email,
                'amount': int(amount_naira * 100),  # kobo
                'reference': reference,
                'callback_url': callback_url,
                'metadata': metadata or {},
            },
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200 and data.get('status'):
            return {
                'ok': True,
                'authorization_url': data['data']['authorization_url'],
                'access_code': data['data']['access_code'],
                'reference': data['data']['reference'],
            }
        return {'ok': False, 'error': data.get('message', 'Failed to initialize transaction')}

    except requests.exceptions.RequestException as e:
        return {'ok': False, 'error': f'Network error contacting Paystack: {str(e)}'}


def verify_transaction(reference):
    """
    Confirms a transaction's real status directly from Paystack's server.
    This is the source of truth — never trust the frontend alone.

    Returns: {'ok': True, 'status': 'success'/'failed'/..., 'amount': int (kobo), 'email': str}
          or {'ok': False, 'error': '...'}
    """
    if not is_paystack_configured():
        return {'ok': False, 'error': 'Payments not configured.'}

    secret_key = get_setting('paystack_secret_key')

    try:
        resp = requests.get(
            f'{PAYSTACK_BASE}/transaction/verify/{reference}',
            headers={'Authorization': f'Bearer {secret_key}'},
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200 and data.get('status'):
            tx = data['data']
            return {
                'ok': True,
                'status': tx.get('status'),  # 'success', 'failed', 'abandoned', etc
                'amount': tx.get('amount'),  # in kobo
                'email': tx.get('customer', {}).get('email'),
                'reference': tx.get('reference'),
                'paid_at': tx.get('paid_at'),
            }
        return {'ok': False, 'error': data.get('message', 'Verification failed')}

    except requests.exceptions.RequestException as e:
        return {'ok': False, 'error': f'Network error contacting Paystack: {str(e)}'}


def verify_webhook_signature(request_body_bytes, signature_header):
    """
    Confirms a webhook actually came from Paystack (not a forged request).
    Paystack signs the payload with your secret key using HMAC-SHA512.
    """
    secret_key = get_setting('paystack_secret_key')
    if not secret_key:
        return False

    computed = hmac.new(
        secret_key.encode('utf-8'),
        request_body_bytes,
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(computed, signature_header or '')
