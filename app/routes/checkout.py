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
from app.core.layout import NAVBAR, FOOTER, HEAD, SCRIPT_TAG
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
#   CART CHECKOUT — multiple products, one Paystack charge
# ============================================

@checkout_bp.route('/checkout/cart', methods=['POST'])
@login_required
def start_cart_checkout():
    db = get_db()

    cart_rows = db.execute('''
        SELECT ci.product_id, ci.qty, p.name, p.price, p.promo_percent, p.status, p.deleted_at
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id=?
    ''', (session['user_id'],)).fetchall()

    if not cart_rows:
        db.close()
        return jsonify({'ok': False, 'error': 'Your cart is empty.'}), 400

    if not is_paystack_configured():
        db.close()
        return jsonify({'ok': False, 'error': 'Payments not configured yet. Check back soon, or book an appointment instead.'}), 503

    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    # Re-validate every cart item against the DB — never trust stale prices.
    # A product could've changed price/promo/status since it was added to cart.
    valid_items = []
    total = 0
    for row in cart_rows:
        if row['status'] != 'live' or row['deleted_at']:
            continue  # Skip items that got deleted/hidden since being added

        price = row['price'] or 0
        promo = row['promo_percent'] or 0
        real_price = round(price - (price * promo / 100)) if promo > 0 else price
        qty = row['qty']

        valid_items.append({'product_id': row['product_id'], 'name': row['name'], 'price': real_price, 'qty': qty})
        total += real_price * qty

    if not valid_items:
        db.close()
        return jsonify({'ok': False, 'error': 'No valid items in cart — they may have been removed.'}), 400

    # One shared reference for the whole cart, used by every purchase row
    reference = make_payment_reference(session['user_id'], 0) + '-cart'

    # Create one pending purchase row PER UNIT (so qty=2 of a product makes 2 rows,
    # each gets its own license key once payment confirms)
    for item in valid_items:
        for _ in range(item['qty']):
            db.execute('''
                INSERT INTO purchases (user_id, product_id, price_paid, payment_ref, status)
                VALUES (?,?,?,?,'pending')
            ''', (session['user_id'], item['product_id'], item['price'], reference))
    db.commit()

    callback_url = request.host_url.rstrip('/') + '/checkout/callback'

    result = initialize_transaction(
        email=user['email'],
        amount_naira=total,
        reference=reference,
        callback_url=callback_url,
        metadata={
            'user_id': session['user_id'],
            'cart_items': [i['product_id'] for i in valid_items],
            'is_cart_checkout': True,
        },
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
    purchases = db.execute('SELECT * FROM purchases WHERE payment_ref=?', (reference,)).fetchall()

    if not purchases:
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Purchase record not found.', license_key=None)

    # Already processed (e.g. webhook beat us to it, or double callback)
    if purchases[0]['status'] == 'completed':
        db.close()
        first_key = purchases[0]['license_key']
        msg = 'Payment already confirmed. Your download is ready.' if len(purchases) == 1 \
              else f'Payment already confirmed for {len(purchases)} items. Your downloads are ready.'
        return render_template_string(CALLBACK_PAGE, success=True, message=msg, license_key=first_key)

    # VERIFY server-side — never trust the redirect alone
    result = verify_transaction(reference)

    if not result['ok'] or result['status'] != 'success':
        db.execute("UPDATE purchases SET status='failed' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment was not successful. No charge was made to your downloads.', license_key=None)

    # Double-check amount matches what we expected (anti-fraud) — sum ALL rows for this reference
    expected_kobo = sum(p['price_paid'] for p in purchases) * 100
    if result['amount'] != expected_kobo:
        db.execute("UPDATE purchases SET status='flagged' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment amount mismatch. Please contact support.', license_key=None)

    # All good — finalize EVERY purchase row tied to this reference (1 for single-product, N for cart)
    first_license_key = None
    product_names = []
    for purchase in purchases:
        license_key = generate_license_key()
        if first_license_key is None:
            first_license_key = license_key
        token, expires_at = generate_download_token(purchase['id'])

        db.execute('''
            UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
            WHERE id=?
        ''', (license_key, token, expires_at, purchase['id']))

        db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

        product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
        pname = product['name'] if product else 'product'
        product_names.append(pname)
        log_activity(db, 'purchase', purchase['id'], f'New purchase: {pname}')

    # Clear the account's cart now that checkout succeeded
    # (only relevant for cart-based purchases — single-product purchases never touched the cart)
    if session.get('user_id'):
        db.execute('DELETE FROM cart_items WHERE user_id=?', (session['user_id'],))

    db.commit()
    db.close()

    # Discord notification — fails silently if not configured, never blocks the purchase
    total_paid = sum(p['price_paid'] for p in purchases)
    notify_purchase(
        product_name=', '.join(product_names) if len(product_names) <= 3 else f'{len(product_names)} items',
        customer_email=result.get('email', 'unknown'),
        amount_naira=total_paid,
    )

    success_msg = 'Your purchase is confirmed. Save your license key below and head to your downloads.' if len(purchases) == 1 \
                  else f'Your purchase of {len(purchases)} items is confirmed. Each has its own license key — head to your downloads to see them all.'

    return render_template_string(
        CALLBACK_PAGE, success=True,
        message=success_msg,
        license_key=first_license_key
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
        purchases = db.execute('SELECT * FROM purchases WHERE payment_ref=?', (reference,)).fetchall()

        if purchases and purchases[0]['status'] != 'completed':
            product_names = []
            total_paid = 0
            for purchase in purchases:
                license_key = generate_license_key()
                token, expires_at = generate_download_token(purchase['id'])

                db.execute('''
                    UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
                    WHERE id=?
                ''', (license_key, token, expires_at, purchase['id']))
                db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

                product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
                pname = product['name'] if product else 'product'
                product_names.append(pname)
                total_paid += purchase['price_paid']
                log_activity(db, 'purchase', purchase['id'], f'New purchase (webhook): {pname}')

            notify_purchase(
                product_name=', '.join(product_names) if len(product_names) <= 3 else f'{len(product_names)} items',
                customer_email=data.get('customer', {}).get('email', 'unknown'),
                amount_naira=total_paid,
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
''' + HEAD + '''
</head>
<body>
''' + NAVBAR + '''

  <div class="product-page" style="max-width:600px">
    <h1 class="pp-name">My <span class="gold">Downloads</span></h1>
    {% for p in purchases %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem;margin-bottom:1rem">
      <h3 style="font-size:0.95rem;margin-bottom:0.4rem">{{ p.product_name }}</h3>
      <div style="font-family:monospace;color:var(--gold);font-size:0.78rem;margin-bottom:0.75rem">License: {{ p.license_key }}</div>
      <a href="/account/download/{{ p.id }}" class="btn btn-gold" style="margin-right:0.5rem">Download &darr;</a>
      {% if p.github_repo_url %}<a href="{{ p.github_repo_url }}" target="_blank" class="btn btn-outline">GitHub Repo</a>{% endif %}
    </div>
    {% else %}
    <p style="color:var(--muted);font-size:0.85rem">No purchases yet. Browse the <a href="/" style="color:var(--gold)">store</a>.</p>
    {% endfor %}
  </div>

''' + FOOTER + SCRIPT_TAG + '''
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

    return render_template_string(
        DOWNLOADS_PAGE, purchases=[dict(r) for r in rows],
        session_user=session.get('user_id'), session_username=session.get('username', ''),
    )


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
