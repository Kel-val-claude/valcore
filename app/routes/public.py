# ============================================
#   VALCORE — PUBLIC/STATIC ROUTES
#   app/routes/public.py
#   Serves CSS/JS/assets. Storefront pages
#   themselves live in storefront.py
# ============================================

from flask import Blueprint, send_from_directory
import os

public_bp = Blueprint('public', __name__)

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), '../../frontend')


@public_bp.route('/css/<path:filename>')
def css(filename):
    return send_from_directory(os.path.join(FRONTEND_PATH, 'css'), filename)


@public_bp.route('/js/<path:filename>')
def js(filename):
    return send_from_directory(os.path.join(FRONTEND_PATH, 'js'), filename)


@public_bp.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(os.path.join(FRONTEND_PATH, 'assets'), filename)
