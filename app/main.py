# ============================================
#   VALCORE — MAIN APP
#   app/main.py
# ============================================

import os
from flask import Flask
from flask_cors import CORS
from app.core.database import init_db
from app.routes.auth      import auth_bp
from app.routes.storefront import storefront_bp
from app.routes.account   import account_bp
from app.routes.admin     import admin_bp
from app.routes.api       import api_bp
from app.routes.public    import public_bp
from app.routes.checkout  import checkout_bp


def create_app():
    app = Flask(__name__, template_folder='../templates')

    app.secret_key = os.environ.get('SECRET_KEY', 'VALCORE-DEV-SECRET-CHANGE-ME')

    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE']   = os.environ.get('RENDER', '') != ''
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_NAME']     = 'valcore_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 days for customer accounts

    CORS(app, supports_credentials=True)

    init_db()

    app.register_blueprint(public_bp)       # frontend asset serving
    app.register_blueprint(auth_bp)         # signup/login/logout
    app.register_blueprint(storefront_bp)   # home/product/collection/search
    app.register_blueprint(account_bp)      # customer account area
    app.register_blueprint(admin_bp)        # admin dashboard
    app.register_blueprint(api_bp)          # public read API
    app.register_blueprint(checkout_bp)     # payments + downloads

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '') == '1')
