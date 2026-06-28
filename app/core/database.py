# ============================================
#   VALCORE COMMERCE ENGINE
#   app/core/database.py
#
#   SQLAlchemy-based, works with SQLite (local)
#   and Postgres (Render) via DATABASE_URL.
#   Same pattern proven on Kel HQ.
# ============================================

import os
from sqlalchemy import create_engine, text

# ---- DATABASE URL ----
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    IS_POSTGRES = True
else:
    db_path = os.path.join(os.path.dirname(__file__), '../../database/valcore.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    DATABASE_URL = f'sqlite:///{db_path}'
    IS_POSTGRES = False

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class RowWrapper:
    """Makes SQLAlchemy Row support dict(row) and row['key'] like sqlite3.Row did."""
    def __init__(self, row):
        self._row = row
        self._mapping = row._mapping

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()

    def __iter__(self):
        return iter(self._mapping.keys())

    def items(self):
        return self._mapping.items()


class ResultWrapper:
    def __init__(self, result):
        self._result = result

    def fetchall(self):
        return [RowWrapper(r) for r in self._result.fetchall()]

    def fetchone(self):
        r = self._result.fetchone()
        return RowWrapper(r) if r is not None else None


class DBConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        if params is not None and '?' in query:
            if isinstance(params, (list, tuple)):
                parts = query.split('?')
                new_query = ''
                bind = {}
                for i, part in enumerate(parts[:-1]):
                    key = f'p{i}'
                    new_query += part + f':{key}'
                    bind[key] = params[i]
                new_query += parts[-1]
                query = new_query
                params = bind
        result = self._conn.execute(text(query), params or {})
        return ResultWrapper(result)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def executemany(self, query, seq_of_params):
        for params in seq_of_params:
            self.execute(query, params)


def get_db():
    conn = engine.connect()
    return DBConnection(conn)


def _pk():
    return 'SERIAL PRIMARY KEY' if IS_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'


# ============================================
#   SETTINGS HELPER — single source of truth
#   for all external config (Discord, Paystack, etc)
# ============================================

def get_setting(key, default=''):
    """Read a single setting value. Returns default if not set or empty."""
    db = get_db()
    row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    db.close()
    if row and row['value']:
        return row['value']
    return default


def set_setting(key, value):
    """Write a setting value (insert or update)."""
    db = get_db()
    db.execute(
        'INSERT INTO settings (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP',
        (key, value)
    )
    db.commit()
    db.close()


def get_all_settings():
    """Read all settings as a dict — used by Admin Settings page."""
    db = get_db()
    rows = db.execute('SELECT key, value FROM settings').fetchall()
    db.close()
    return {r['key']: r['value'] for r in rows}


# ============================================
#   INIT DB — create all 16 tables
# ============================================

def init_db():
    db = get_db()
    pk = _pk()

    # ---- USERS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id             {pk},
            username       TEXT NOT NULL UNIQUE,
            email          TEXT NOT NULL UNIQUE,
            password_hash  TEXT NOT NULL,
            is_admin       INTEGER DEFAULT 0,
            avatar_url     TEXT,
            email_verified INTEGER DEFAULT 0,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- COLLECTIONS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS collections (
            id         {pk},
            name       TEXT NOT NULL,
            slug       TEXT NOT NULL UNIQUE,
            icon       TEXT,
            sort_order INTEGER DEFAULT 0,
            active     INTEGER DEFAULT 1
        )
    ''')
    count = db.execute('SELECT COUNT(*) as c FROM collections').fetchone()
    if count[0] == 0:
        defaults = [
            ('Business Websites',     'business-websites',     '🌐', 1, 1),
            ('E-Commerce Templates',  'ecommerce-templates',   '🛒', 2, 1),
            ('SaaS / Landing Pages',  'saas-landing-pages',    '🚀', 3, 1),
            ('Telegram Bots',         'telegram-bots',         '📱', 4, 1),
            ('Automation Scripts',    'automation-scripts',    '⚙️', 5, 1),
            ('Admin Dashboards',      'admin-dashboards',      '📊', 6, 1),
            ('UI Kits',               'ui-kits',               '🎨', 7, 0),
            ('Flask Projects',        'flask-projects',        '🐍', 8, 0),
            ('Premium Components',    'premium-components',    '💎', 9, 0),
        ]
        db.executemany(
            'INSERT INTO collections (name,slug,icon,sort_order,active) VALUES (?,?,?,?,?)',
            defaults
        )

    # ---- PRODUCTS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS products (
            id              {pk},
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL UNIQUE,
            short_desc      TEXT,
            description     TEXT,
            price           INTEGER NOT NULL DEFAULT 0,
            compare_price   INTEGER,
            gain_price      INTEGER,
            promo_percent   INTEGER DEFAULT 0,
            collection_id   INTEGER,
            delivery_type   TEXT DEFAULT 'zip',
            github_repo_url TEXT,
            zip_file_url    TEXT,
            views           INTEGER DEFAULT 0,
            purchase_count  INTEGER DEFAULT 0,
            rating_avg      REAL DEFAULT 0,
            rating_count    INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'draft',
            version         TEXT DEFAULT '1.0',
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at      TEXT
        )
    ''')

    # ---- PRODUCT IMAGES ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS product_images (
            id         {pk},
            product_id INTEGER NOT NULL,
            image_url  TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # ---- PRODUCT VERSIONS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS product_versions (
            id            {pk},
            product_id    INTEGER NOT NULL,
            version       TEXT NOT NULL,
            zip_file_url  TEXT,
            release_notes TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- TAGS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS tags (
            id   {pk},
            name TEXT NOT NULL UNIQUE
        )
    ''')

    # ---- PRODUCT_TAGS (join table) ----
    db.execute('''
        CREATE TABLE IF NOT EXISTS product_tags (
            product_id INTEGER NOT NULL,
            tag_id     INTEGER NOT NULL
        )
    ''')

    # ---- PURCHASES ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS purchases (
            id                  {pk},
            user_id             INTEGER NOT NULL,
            product_id          INTEGER NOT NULL,
            price_paid          INTEGER NOT NULL,
            license_key         TEXT UNIQUE,
            payment_ref         TEXT,
            status              TEXT DEFAULT 'pending',
            download_token      TEXT,
            download_expires_at TEXT,
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- DOWNLOAD LOGS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS download_logs (
            id            {pk},
            purchase_id   INTEGER NOT NULL,
            ip_address    TEXT,
            downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- REVIEWS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS reviews (
            id            {pk},
            product_id    INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            rating        INTEGER DEFAULT 5,
            ease_of_use   INTEGER DEFAULT 5,
            documentation INTEGER DEFAULT 5,
            design        INTEGER DEFAULT 5,
            value         INTEGER DEFAULT 5,
            comment       TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- WISHLIST ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS wishlist (
            id         {pk},
            user_id    INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- SUPPORT TICKETS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id          {pk},
            user_id     INTEGER NOT NULL,
            subject     TEXT NOT NULL,
            message     TEXT NOT NULL,
            status      TEXT DEFAULT 'open',
            admin_reply TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        )
    ''')

    # ---- APPOINTMENTS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS appointments (
            id           {pk},
            user_id      INTEGER,
            name         TEXT NOT NULL,
            contact      TEXT NOT NULL,
            project_type TEXT,
            message      TEXT,
            status       TEXT DEFAULT 'pending',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- PRODUCT QUESTIONS ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS product_questions (
            id         {pk},
            product_id INTEGER NOT NULL,
            user_id    INTEGER,
            question   TEXT NOT NULL,
            answer     TEXT,
            status     TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- ACTIVITY LOG (public-facing feed) ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS activity_log (
            id         {pk},
            type       TEXT NOT NULL,
            ref_id     INTEGER,
            summary    TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- AUDIT LOG (private security trail) ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id         {pk},
            user_id    INTEGER,
            action     TEXT NOT NULL,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---- ANALYTICS DAILY ----
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS analytics_daily (
            id            {pk},
            date          TEXT NOT NULL,
            revenue       INTEGER DEFAULT 0,
            gain          INTEGER DEFAULT 0,
            new_users     INTEGER DEFAULT 0,
            new_purchases INTEGER DEFAULT 0,
            page_views    INTEGER DEFAULT 0
        )
    ''')

    # ---- SETTINGS ----
    db.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id         INTEGER PRIMARY KEY,
            key        TEXT UNIQUE NOT NULL,
            value      TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''' if not IS_POSTGRES else f'''
        CREATE TABLE IF NOT EXISTS settings (
            id         {pk},
            key        TEXT UNIQUE NOT NULL,
            value      TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    seed_settings = [
        ('site_name',           'VALCORE'),
        ('site_description',    'Digital products, templates, and automation systems.'),
        ('discord_webhook',     ''),
        ('discord_server',      ''),
        ('paystack_public_key', ''),
        ('paystack_secret_key', ''),
        ('r2_account_id',       ''),
        ('r2_access_key_id',    ''),
        ('r2_secret_access_key',''),
        ('r2_bucket_name',      ''),
        ('r2_public_url',       ''),
        ('maintenance_mode',    '0'),
        ('founder_website',     ''),
        ('support_email',       ''),
    ]
    for key, val in seed_settings:
        existing = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        if not existing:
            db.execute('INSERT INTO settings (key,value) VALUES (?,?)', (key, val))

    db.commit()
    db.close()
    print('[VALCORE] Database initialised ✓', '(Postgres)' if IS_POSTGRES else '(SQLite)')
