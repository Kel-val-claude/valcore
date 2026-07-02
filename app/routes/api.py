# ============================================
#   VALCORE — PUBLIC API
#   app/routes/api.py
# ============================================

from flask import Blueprint, jsonify, request
from app.core.database import get_db
import random

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/products')
def get_products():
    db = get_db()
    collection_slug = request.args.get('collection', '')
    shuffle = request.args.get('shuffle', '') == '1'

    if collection_slug:
        rows = db.execute('''
            SELECT p.*, c.name as collection_name
            FROM products p
            LEFT JOIN collections c ON p.collection_id = c.id
            WHERE c.slug=? AND p.status='live' AND p.deleted_at IS NULL
        ''', (collection_slug,)).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM products WHERE status='live' AND deleted_at IS NULL ORDER BY id DESC"
        ).fetchall()
    db.close()

    result = [dict(r) for r in rows]
    if shuffle:
        random.shuffle(result)
    return jsonify(result)


@api_bp.route('/collections')
def get_collections():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM collections WHERE active=1 ORDER BY sort_order"
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ============================================
#   CART API (account-persisted via cart_items table —
#   NOT session-only, so it survives logout/login and
#   works across devices once signed in)
# ============================================

@api_bp.route('/cart/add', methods=['POST'])
def cart_add():
    from flask import session
    if not session.get('user_id'):
        return jsonify({'ok': False, 'login_required': True, 'error': 'Please sign in to add items to your cart.'}), 401

    data = request.get_json() or {}
    product_id = data.get('product_id')

    if not product_id:
        return jsonify({'ok': False, 'error': 'No product specified'}), 400

    db = get_db()
    product = db.execute(
        "SELECT id FROM products WHERE id=? AND status='live' AND deleted_at IS NULL",
        (product_id,)
    ).fetchone()

    if not product:
        db.close()
        return jsonify({'ok': False, 'error': 'Product not found'}), 404

    user_id = session['user_id']
    existing = db.execute(
        'SELECT id, qty FROM cart_items WHERE user_id=? AND product_id=?',
        (user_id, product_id)
    ).fetchone()

    if existing:
        db.execute('UPDATE cart_items SET qty = qty + 1 WHERE id=?', (existing['id'],))
    else:
        db.execute(
            'INSERT INTO cart_items (user_id, product_id, qty) VALUES (?,?,1)',
            (user_id, product_id)
        )
    db.commit()

    count = db.execute(
        'SELECT COALESCE(SUM(qty),0) as c FROM cart_items WHERE user_id=?', (user_id,)
    ).fetchone()['c']
    db.close()

    return jsonify({'ok': True, 'count': count})


@api_bp.route('/cart/count')
def cart_count():
    from flask import session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'count': 0})

    db = get_db()
    count = db.execute(
        'SELECT COALESCE(SUM(qty),0) as c FROM cart_items WHERE user_id=?', (user_id,)
    ).fetchone()['c']
    db.close()
    return jsonify({'count': count})


@api_bp.route('/cart/items')
def cart_items():
    from flask import session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'items': [], 'total': 0, 'count': 0})

    db = get_db()
    rows = db.execute('''
        SELECT ci.product_id, ci.qty, p.name, p.price, p.promo_percent
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id=? AND p.status='live' AND p.deleted_at IS NULL
        ORDER BY ci.id DESC
    ''', (user_id,)).fetchall()
    db.close()

    items = []
    total = 0
    for r in rows:
        price = r['price'] or 0
        promo = r['promo_percent'] or 0
        display_price = round(price - (price * promo / 100)) if promo > 0 else price
        items.append({'product_id': r['product_id'], 'name': r['name'], 'price': display_price, 'qty': r['qty']})
        total += display_price * r['qty']

    count = sum(i['qty'] for i in items)
    return jsonify({'items': items, 'total': total, 'count': count})


@api_bp.route('/cart/remove', methods=['POST'])
def cart_remove():
    from flask import session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'ok': False, 'error': 'Login required'}), 401

    data = request.get_json() or {}
    product_id = data.get('product_id')

    db = get_db()
    db.execute('DELETE FROM cart_items WHERE user_id=? AND product_id=?', (user_id, product_id))
    db.commit()

    count = db.execute(
        'SELECT COALESCE(SUM(qty),0) as c FROM cart_items WHERE user_id=?', (user_id,)
    ).fetchone()['c']
    db.close()

    return jsonify({'ok': True, 'count': count})


@api_bp.route('/cart/clear', methods=['POST'])
def cart_clear():
    from flask import session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'ok': False, 'error': 'Login required'}), 401

    db = get_db()
    db.execute('DELETE FROM cart_items WHERE user_id=?', (user_id,))
    db.commit()
    db.close()

    return jsonify({'ok': True, 'count': 0})

