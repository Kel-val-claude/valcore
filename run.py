# ============================================
#   VALCORE — LOCAL DEV ENTRY POINT
#   Usage: python run.py
# ============================================

import os
from app.main import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"""
╔══════════════════════════════════════╗
║   VALCORE COMMERCE ENGINE            ║
║   Phase 1 — Foundation               ║
╠══════════════════════════════════════╣
║   Storefront →  http://localhost:{port} ║
║   Login      →  http://localhost:{port}/login
║   Signup     →  http://localhost:{port}/signup
║   Admin      →  http://localhost:{port}/admin
╚══════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=True)
