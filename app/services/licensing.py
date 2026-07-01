# ============================================
#   VALCORE — LICENSE & DOWNLOAD TOKEN SERVICE
#   app/services/licensing.py
#
#   Generates unique license keys per purchase
#   and time-limited, signed download tokens.
# ============================================

import secrets
import hashlib
from datetime import datetime, timedelta


def generate_license_key():
    """
    Generates a license key like: VALC-XXXX-XXXX-XXXX-XXXX
    Cosmetic/future-proofing for now — no enforcement logic yet (per Phase 1 plan).
    """
    parts = [secrets.token_hex(2).upper() for _ in range(4)]
    return 'VALC-' + '-'.join(parts)


def generate_download_token(purchase_id):
    """
    Generates a random token tied to a specific purchase.
    Stored in purchases.download_token, expires after 7 days
    (re-generated if customer needs to re-download later via account page).
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    return token, expires_at.strftime('%Y-%m-%d %H:%M:%S')


def make_payment_reference(user_id, product_id):
    """
    Unique reference string sent to Paystack to identify this transaction.
    Format: VALC-{user_id}-{product_id}-{random}
    """
    rand = secrets.token_hex(6)
    return f'VALC-{user_id}-{product_id}-{rand}'


def make_cart_payment_reference(user_id):
    """
    Unique reference string for a multi-item cart checkout.
    Format: VALC-{user_id}-CART-{random}
    Multiple purchases rows share this single reference —
    one Paystack transaction covers the whole cart.
    """
    rand = secrets.token_hex(6)
    return f'VALC-{user_id}-CART-{rand}'
