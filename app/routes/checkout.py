# ============================================
#   VALCORE — CHECKOUT / PURCHASE ROUTES
#   app/routes/checkout.py
#
#   Flow:
#   1. POST /checkout/start          → initializes Paystack transaction
#   2. customer redirected to Paystack, pays
#   3. GET  /checkout/callback       → Paystack sends them back here
#      → we VERIFY server-side (never trust the redirect alone)
#      → on success: create purchase record, license key, download token
#   4. POST /webhooks/paystack       → backup confirmation (signature-verified)
#   5. GET  /account/download/<id>   → serves the actual file, logs to download_logs
# ============================================

import json
from flask import Blueprint, request, redirect, session, jsonify, render_template_string, abort, send_file
from app.core.database import get_db
from app.core.auth import login_required, log_activity
from app.services.payments import initialize_transaction, verify_transaction, verify_webhook_signature, is_paystack_configured
from app.services.licensing import generate_license_key, generate_download_token, make_payment_reference
from app.services.notifications import notify_purchase

checkout_bp = Blueprint('checkout', __name__)


# ============================================
#   START CHECKOUT
# ============================================

@checkout_bp.route('/checkout/start/<int:product_id>', methods=['POST'])
@login_required
def start_checkout(product_id):
    db = get_db()
    product = db.execute(
        "SELECT * FROM products WHERE id=? AND status='live' AND deleted_at IS NULL",
        (product_id,)
    ).fetchone()

    if not product:
        db.close()
        return jsonify({'ok': False, 'error': 'Product not found or unavailable.'}), 404

    if not is_paystack_configured():
        db.close()
        return jsonify({'ok': False, 'error': 'Payments not configured yet. Check back soon, or book an appointment instead.'}), 503

    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    price = product['price'] or 0
    promo = product['promo_percent'] or 0
    final_price = round(price - (price * promo / 100)) if promo > 0 else price

    reference = make_payment_reference(session['user_id'], product_id)

    # Create a pending purchase record BEFORE redirecting to Paystack
    # so we have something to update once payment confirms
    db.execute('''
        INSERT INTO purchases (user_id, product_id, price_paid, payment_ref, status)
        VALUES (?,?,?,?,'pending')
    ''', (session['user_id'], product_id, final_price, reference))
    db.commit()

    callback_url = request.host_url.rstrip('/') + '/checkout/callback'

    result = initialize_transaction(
        email=user['email'],
        amount_naira=final_price,
        reference=reference,
        callback_url=callback_url,
        metadata={'product_id': product_id, 'user_id': session['user_id'], 'product_name': product['name']},
    )

    db.close()

    if not result['ok']:
        return jsonify({'ok': False, 'error': result['error']}), 502

    return jsonify({'ok': True, 'authorization_url': result['authorization_url']})


# ============================================
#   CALLBACK — customer returns here after paying
# ============================================

CALLBACK_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>{{ "Payment Successful" if success else "Payment Status" }} — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{background:#0A0A0A;color:#F0F0F0;font-family:Inter,sans-serif;display:flex;align-items:center;
      justify-content:center;min-height:100vh;text-align:center;padding:1.5rem}
    .box{max-width:380px}
    .icon{font-size:3rem;margin-bottom:1rem}
    h1{font-size:1.3rem;margin-bottom:0.5rem}
    p{color:#888;font-size:0.88rem;margin-bottom:1.5rem;line-height:1.6}
    .license{background:#141414;border:1px solid rgba(212,175,55,0.2);border-radius:10px;padding:1rem;
      font-family:monospace;color:#D4AF37;font-size:0.9rem;margin-bottom:1.5rem;word-break:break-all}
    .btn{display:inline-block;background:#D4AF37;color:#0A0A0A;padding:0.75rem 1.5rem;border-radius:8px;
      text-decoration:none;font-weight:700;font-size:0.85rem}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">{{ "✅" if success else "⚠️" }}</div>
    <h1>{{ "Payment Successful!" if success else "Payment Not Confirmed" }}</h1>
    <p>{{ message }}</p>
    {% if license_key %}
    <div class="license">{{ license_key }}</div>
    {% endif %}
    <a href="{{ '/account/downloads' if success else '/' }}" class="btn">{{ "Go to My Downloads" if success else "Back to Store" }}</a>
  </div>
</body>
</html>
'''


@checkout_bp.route('/checkout/callback')
def checkout_callback():
    reference = request.args.get('reference') or request.args.get('trxref')

    if not reference:
        return render_template_string(CALLBACK_PAGE, success=False, message='No payment reference found.', license_key=None)

    db = get_db()
    purchase = db.execute('SELECT * FROM purchases WHERE payment_ref=?', (reference,)).fetchone()

    if not purchase:
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Purchase record not found.', license_key=None)

    # Already processed (e.g. webhook beat us to it, or double callback)
    if purchase['status'] == 'completed':
        db.close()
        return render_template_string(CALLBACK_PAGE, success=True, message='Payment already confirmed. Your download is ready.', license_key=purchase['license_key'])

    # VERIFY server-side — never trust the redirect alone
    result = verify_transaction(reference)

    if not result['ok'] or result['status'] != 'success':
        db.execute("UPDATE purchases SET status='failed' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment was not successful. No charge was made to your downloads.', license_key=None)

    # Double-check amount matches what we expected (anti-fraud)
    expected_kobo = purchase['price_paid'] * 100
    if result['amount'] != expected_kobo:
        db.execute("UPDATE purchases SET status='flagged' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment amount mismatch. Please contact support.', license_key=None)

    # All good — finalize the purchase
    license_key = generate_license_key()
    token, expires_at = generate_download_token(purchase['id'])

    db.execute('''
        UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
        WHERE id=?
    ''', (license_key, token, expires_at, purchase['id']))

    db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

    product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
    log_activity(db, 'purchase', purchase['id'], f'New purchase: {product["name"] if product else "product"}')

    db.commit()
    db.close()

    # Discord notification — fails silently if not configured, never blocks the purchase
    notify_purchase(
        product_name=product['name'] if product else 'Unknown product',
        customer_email=result.get('email', 'unknown'),
        amount_naira=purchase['price_paid'],
    )

    return render_template_string(
        CALLBACK_PAGE, success=True,
        message='Your purchase is confirmed. Save your license key below and head to your downloads.',
        license_key=license_key
    )


# ============================================
#   WEBHOOK — backup confirmation from Paystack
#   (in case customer closes browser before callback fires)
# ============================================

@checkout_bp.route('/webhooks/paystack', methods=['POST'])
def paystack_webhook():
    signature = request.headers.get('X-Paystack-Signature', '')
    raw_body = request.get_data()

    if not verify_webhook_signature(raw_body, signature):
        return jsonify({'error': 'Invalid signature'}), 401

    event = request.get_json() or {}

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        reference = data.get('reference')

        db = get_db()
        purchase = db.execute('SELECT * FROM purchases WHERE payment_ref=?', (reference,)).fetchone()

        if purchase and purchase['status'] != 'completed':
            license_key = generate_license_key()
            token, expires_at = generate_download_token(purchase['id'])

            db.execute('''
                UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
                WHERE id=?
            ''', (license_key, token, expires_at, purchase['id']))
            db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

            product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
            log_activity(db, 'purchase', purchase['id'], f'New purchase (webhook): {product["name"] if product else "product"}')

            notify_purchase(
                product_name=product['name'] if product else 'Unknown product',
                customer_email=data.get('customer', {}).get('email', 'unknown'),
                amount_naira=purchase['price_paid'],
            )

            db.commit()

        db.close()

    return jsonify({'ok': True})


# ============================================
#   DOWNLOADS
# ============================================

DOWNLOADS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>My Downloads — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{background:#0A0A0A;color:#F0F0F0;font-family:Inter,sans-serif;padding:1.5rem}
    .gold{color:#D4AF37}
    h1{font-size:1.3rem;margin-bottom:1.5rem}
    .item{background:#141414;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:1.25rem;margin-bottom:1rem}
    .item h3{font-size:0.95rem;margin-bottom:0.4rem}
    .license{font-family:monospace;color:#D4AF37;font-size:0.78rem;margin-bottom:0.75rem}
    .btn{display:inline-block;background:#D4AF37;color:#0A0A0A;padding:0.55rem 1.2rem;border-radius:7px;
      text-decoration:none;font-weight:700;font-size:0.82rem;margin-right:0.5rem}
    .empty{color:#666;font-size:0.85rem}
  </style>
</head>
<body>
  <h1>My <span class="gold">Downloads</span></h1>
  {% for p in purchases %}
  <div class="item">
    <h3>{{ p.product_name }}</h3>
    <div class="license">License: {{ p.license_key }}</div>
    <a href="/account/download/{{ p.id }}" class="btn">Download &darr;</a>
    {% if p.github_repo_url %}<a href="{{ p.github_repo_url }}" target="_blank" class="btn" style="background:transparent;border:1px solid #333;color:#fff">GitHub Repo</a>{% endif %}
  </div>
  {% else %}
  <p class="empty">No purchases yet. Browse the <a href="/" style="color:#D4AF37">store</a>.</p>
  {% endfor %}
</body>
</html>
'''


@checkout_bp.route('/account/downloads')
@login_required
def my_downloads():
    db = get_db()
    rows = db.execute('''
        SELECT pu.*, p.name as product_name, p.github_repo_url, p.delivery_type
        FROM purchases pu
        JOIN products p ON pu.product_id = p.id
        WHERE pu.user_id=? AND pu.status='completed'
        ORDER BY pu.id DESC
    ''', (session['user_id'],)).fetchall()
    db.close()

    return render_template_string(DOWNLOADS_PAGE, purchases=[dict(r) for r in rows])


@checkout_bp.route('/account/download/<int:purchase_id>')
@login_required
def download_file(purchase_id):
    db = get_db()
    purchase = db.execute('''
        SELECT pu.*, p.zip_file_url, p.delivery_type, p.name as product_name
        FROM purchases pu
        JOIN products p ON pu.product_id = p.id
        WHERE pu.id=? AND pu.user_id=? AND pu.status='completed'
    ''', (purchase_id, session['user_id'])).fetchone()

    if not purchase:
        db.close()
        abort(404)

    # Log the download attempt
    db.execute(
        'INSERT INTO download_logs (purchase_id, ip_address) VALUES (?,?)',
        (purchase_id, request.remote_addr)
    )
    db.commit()
    db.close()

    if purchase['delivery_type'] == 'external' or not purchase['zip_file_url']:
        return jsonify({'error': 'No direct file for this product. Check the GitHub link on your downloads page.'}), 400

    # Redirect to the R2-hosted file URL
    return redirect(purchase['zip_file_url'])
