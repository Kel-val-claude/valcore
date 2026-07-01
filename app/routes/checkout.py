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
from app.services.licensing import generate_license_key, generate_download_token, make_payment_reference, make_cart_payment_reference
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
#   START CART CHECKOUT — multi-item
#   Creates one purchase row per cart item, all
#   sharing ONE payment_ref. Single Paystack charge
#   for the summed total. Callback/webhook handle
#   N rows sharing that reference.
# ============================================

@checkout_bp.route('/checkout/start-cart', methods=['POST'])
@login_required
def start_cart_checkout():
    db = get_db()
    user_id = session['user_id']

    cart_rows = db.execute('''
        SELECT ci.product_id, p.name, p.price, p.promo_percent
        FROM cart_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.user_id=? AND p.status='live' AND p.deleted_at IS NULL
    ''', (user_id,)).fetchall()

    if not cart_rows:
        db.close()
        return jsonify({'ok': False, 'error': 'Your cart is empty.'}), 400

    if not is_paystack_configured():
        db.close()
        return jsonify({'ok': False, 'error': 'Payments not configured yet. Check back soon, or book an appointment instead.'}), 503

    user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()

    reference = make_cart_payment_reference(user_id)
    total = 0
    product_names = []

    for row in cart_rows:
        price = row['price'] or 0
        promo = row['promo_percent'] or 0
        final_price = round(price - (price * promo / 100)) if promo > 0 else price
        total += final_price
        product_names.append(row['name'])

        # One purchase row per cart item, all sharing the same payment_ref
        db.execute('''
            INSERT INTO purchases (user_id, product_id, price_paid, payment_ref, status)
            VALUES (?,?,?,?,'pending')
        ''', (user_id, row['product_id'], final_price, reference))

    db.commit()

    callback_url = request.host_url.rstrip('/') + '/checkout/callback'

    result = initialize_transaction(
        email=user['email'],
        amount_naira=total,
        reference=reference,
        callback_url=callback_url,
        metadata={'user_id': user_id, 'cart': True, 'product_names': product_names},
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
    .box{max-width:420px}
    .icon{font-size:3rem;margin-bottom:1rem}
    h1{font-size:1.3rem;margin-bottom:0.5rem}
    p{color:#888;font-size:0.88rem;margin-bottom:1.5rem;line-height:1.6}
    .license{background:#141414;border:1px solid rgba(212,175,55,0.2);border-radius:10px;padding:0.85rem 1rem;
      font-family:monospace;color:#D4AF37;font-size:0.85rem;margin-bottom:0.6rem;word-break:break-all;text-align:left}
    .license small{display:block;color:#666;font-family:Inter,sans-serif;font-size:0.68rem;margin-bottom:0.3rem}
    .btn{display:inline-block;background:#D4AF37;color:#0A0A0A;padding:0.75rem 1.5rem;border-radius:8px;
      text-decoration:none;font-weight:700;font-size:0.85rem;margin-top:0.5rem}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">{{ "✅" if success else "⚠️" }}</div>
    <h1>{{ "Payment Successful!" if success else "Payment Not Confirmed" }}</h1>
    <p>{{ message }}</p>
    {% if license_keys %}
      {% for lk in license_keys %}
      <div class="license">
        <small>{{ lk.product_name }}</small>
        {{ lk.key }}
      </div>
      {% endfor %}
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
        return render_template_string(CALLBACK_PAGE, success=False, message='No payment reference found.', license_keys=None)

    db = get_db()
    purchases = db.execute('SELECT * FROM purchases WHERE payment_ref=?', (reference,)).fetchall()

    if not purchases:
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Purchase record not found.', license_keys=None)

    # Already processed (e.g. webhook beat us to it, or double callback)
    if all(p['status'] == 'completed' for p in purchases):
        existing_keys = []
        for p in purchases:
            prod = db.execute('SELECT name FROM products WHERE id=?', (p['product_id'],)).fetchone()
            existing_keys.append({'product_name': prod['name'] if prod else 'Product', 'key': p['license_key']})
        db.close()
        return render_template_string(CALLBACK_PAGE, success=True, message='Payment already confirmed. Your download is ready.', license_keys=existing_keys)

    # VERIFY server-side — never trust the redirect alone
    result = verify_transaction(reference)

    if not result['ok'] or result['status'] != 'success':
        db.execute("UPDATE purchases SET status='failed' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment was not successful. No charge was made to your downloads.', license_keys=None)

    # Double-check amount matches what we expected (anti-fraud)
    # Sums across ALL purchase rows sharing this reference — covers both
    # single-product checkout (1 row) and cart checkout (N rows).
    expected_kobo = sum(p['price_paid'] for p in purchases) * 100
    if result['amount'] != expected_kobo:
        db.execute("UPDATE purchases SET status='flagged' WHERE payment_ref=?", (reference,))
        db.commit()
        db.close()
        return render_template_string(CALLBACK_PAGE, success=False, message='Payment amount mismatch. Please contact support.', license_keys=None)

    # All good — finalize every purchase row tied to this reference
    license_keys = []
    for purchase in purchases:
        license_key = generate_license_key()
        token, expires_at = generate_download_token(purchase['id'])

        db.execute('''
            UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
            WHERE id=?
        ''', (license_key, token, expires_at, purchase['id']))

        db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

        product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
        product_name = product['name'] if product else 'product'
        log_activity(db, 'purchase', purchase['id'], f'New purchase: {product_name}')

        license_keys.append({'product_name': product_name, 'key': license_key})

        notify_purchase(
            product_name=product_name,
            customer_email=result.get('email', 'unknown'),
            amount_naira=purchase['price_paid'],
        )

    # If this was a cart checkout, clear the cart now that payment is confirmed
    user_id = purchases[0]['user_id']
    if 'CART' in reference:
        db.execute('DELETE FROM cart_items WHERE user_id=?', (user_id,))

    db.commit()
    db.close()

    return render_template_string(
        CALLBACK_PAGE, success=True,
        message='Your purchase is confirmed. Save your license key(s) below and head to your downloads.',
        license_keys=license_keys
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

        pending = [p for p in purchases if p['status'] != 'completed']

        if pending:
            for purchase in pending:
                license_key = generate_license_key()
                token, expires_at = generate_download_token(purchase['id'])

                db.execute('''
                    UPDATE purchases SET status='completed', license_key=?, download_token=?, download_expires_at=?
                    WHERE id=?
                ''', (license_key, token, expires_at, purchase['id']))
                db.execute('UPDATE products SET purchase_count = purchase_count + 1 WHERE id=?', (purchase['product_id'],))

                product = db.execute('SELECT name FROM products WHERE id=?', (purchase['product_id'],)).fetchone()
                product_name = product['name'] if product else 'product'
                log_activity(db, 'purchase', purchase['id'], f'New purchase (webhook): {product_name}')

                notify_purchase(
                    product_name=product_name,
                    customer_email=data.get('customer', {}).get('email', 'unknown'),
                    amount_naira=purchase['price_paid'],
                )

            # Clear cart on confirmed cart checkout (covers the case where
            # the browser closed before /checkout/callback ever fired)
            if purchases and 'CART' in (reference or ''):
                db.execute('DELETE FROM cart_items WHERE user_id=?', (purchases[0]['user_id'],))

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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <button class="nav-menu-btn" id="menuBtn">&#9776;</button>
    <a href="/" class="nav-logo-img-wrap">
      <span class="nav-logo">VALCORE <span>&lt;/&gt;</span></span>
    </a>
    <a href="/valcore" class="nav-valcore-logo" title="VALCORE">
      <img src="/assets/logo.png" alt="VALCORE" class="nav-logo-img" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';" />
      <span class="nav-logo-fallback">V</span>
    </a>
  </nav>
  <div class="menu-overlay" id="menuOverlay"></div>
  <div class="menu-drawer" id="menuDrawer">
    <a href="/">&#127968; Home</a>
    <a href="/search">&#128269; Search</a>
    <a href="/valcore">&#9889; VALCORE Profile</a>
    <a href="/account">&#128100; My Account</a>
    <a href="/account/downloads">&#128230; My Purchases</a>
    <a href="/account/wishlist">&#9825; Wishlist</a>
    <a href="/account/support">&#128172; Support</a>
    <a href="/logout" style="color:#E74C3C">&#9211; Logout</a>
  </div>
  <script>
  document.addEventListener(\'DOMContentLoaded\', function(){
    var btn=document.getElementById(\'menuBtn\');
    var drawer=document.getElementById(\'menuDrawer\');
    var overlay=document.getElementById(\'menuOverlay\');
    if(btn&&drawer&&overlay){
      btn.addEventListener(\'click\',function(){drawer.classList.toggle(\'open\');overlay.classList.toggle(\'open\');});
      overlay.addEventListener(\'click\',function(){drawer.classList.remove(\'open\');overlay.classList.remove(\'open\');});
    }
  });
  </script>

  <section class="store-section">
  <div class="section-title-row">
    <span class="section-title">&#128230; My Downloads</span>
  </div>
  <div style="display:flex;flex-direction:column;gap:0.85rem">
  {% for p in purchases %}
  <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.25rem">
    <div style="font-size:0.92rem;font-weight:700;margin-bottom:0.3rem">{{ p.product_name }}</div>
    <div style="font-family:monospace;color:var(--gold);font-size:0.75rem;margin-bottom:0.85rem;opacity:0.8">
      License: {{ p.license_key }}
    </div>
    <div style="display:flex;gap:0.6rem;flex-wrap:wrap">
      <a href="/account/download/{{ p.id }}" class="btn btn-gold" style="font-size:0.8rem;padding:0.5rem 1.1rem">Download &#8595;</a>
      {% if p.github_repo_url %}
      <a href="{{ p.github_repo_url }}" target="_blank" class="btn btn-outline" style="font-size:0.8rem;padding:0.5rem 1.1rem">&#128025; GitHub</a>
      {% endif %}
    </div>
  </div>
  {% else %}
  <div class="empty-state" style="padding:3rem 0">No purchases yet. <a href="/" style="color:var(--gold)">Browse the store</a></div>
  {% endfor %}
  </div>
  </section>
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
