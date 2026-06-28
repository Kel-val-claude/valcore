# ============================================
#   VALCORE — AUTH CORE
#   app/core/auth.py
#
#   Real password hashing (not the Kel HQ
#   plaintext-password pattern — this handles
#   real customer accounts + payments).
# ============================================

import hashlib
import os
import secrets
from functools import wraps
from flask import session, jsonify, redirect, request


def hash_password(password):
    """
    Salted SHA-256 hash. Good enough without extra deps;
    swap for bcrypt/argon2 later if you want stronger guarantees.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'{salt}${digest}'


def verify_password(password, stored_hash):
    try:
        salt, digest = stored_hash.split('$', 1)
    except ValueError:
        return False
    check = hashlib.sha256((salt + password).encode()).hexdigest()
    return secrets.compare_digest(check, digest)


def login_required(f):
    """Any logged-in user (customer or admin) can access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            is_api = (
                request.path.startswith('/api/') or
                'application/json' in request.headers.get('Accept', '')
            )
            if is_api:
                return jsonify({'error': 'Login required.'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Only users with is_admin=1 can access. Same pattern as Kel HQ's owner_required."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            is_api = (
                request.path.startswith('/api/') or
                'application/json' in request.headers.get('Accept', '')
            )
            if is_api:
                return jsonify({'error': 'Admin access required.'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def log_activity(db, type_, ref_id, summary):
    """Public-facing activity feed entry."""
    db.execute(
        'INSERT INTO activity_log (type, ref_id, summary) VALUES (?,?,?)',
        (type_, ref_id, summary)
    )


def log_audit(db, user_id, action):
    """Private security audit trail — admin actions only."""
    ip = request.remote_addr if request else None
    db.execute(
        'INSERT INTO audit_logs (user_id, action, ip_address) VALUES (?,?,?)',
        (user_id, action, ip)
    )
