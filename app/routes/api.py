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
