# ============================================
#   VALCORE — CUSTOMER ACCOUNT ROUTES
#   app/routes/account.py
#
#   Phase 1: route structure only.
#   Phase 5/6 add wishlist, reviews, tickets UI.
# ============================================

from flask import Blueprint, render_template_string, session, jsonify, request
from app.core.database import get_db
from app.core.auth import login_required
from app.services.notifications import notify_support_ticket

account_bp = Blueprint('account', __name__, url_prefix='/account')

ACCOUNT_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>My Account — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
  <style>
    .profile-wrap { max-width: 480px; margin: 0 auto; padding: 1.5rem 5%; }

    /* PROFILE HEADER */
    .profile-header {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1.25rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      margin-bottom: 1.25rem;
      position: relative;
    }
    .profile-v {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--gold);
      color: #0A0A0A;
      font-weight: 800;
      font-size: 1.6rem;
      font-family: 'Space Grotesk', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      box-shadow: 0 0 20px var(--gold-glow);
    }
    .profile-info { flex: 1 }
    .profile-info strong {
      display: block;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 0.15rem;
    }
    .profile-info span { font-size: 0.75rem; color: var(--muted); }
    .profile-dots {
      position: relative;
    }
    .dots-btn {
      background: none;
      border: none;
      color: var(--muted);
      font-size: 1.3rem;
      cursor: pointer;
      padding: 0.3rem 0.5rem;
      border-radius: 6px;
      letter-spacing: 2px;
    }
    .dots-btn:hover { color: var(--text); background: var(--surface); }
    .dots-menu {
      display: none;
      position: absolute;
      right: 0;
      top: 110%;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      min-width: 170px;
      z-index: 100;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }
    .dots-menu.open { display: block; }
    .dots-menu a {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.75rem 1rem;
      color: var(--text);
      text-decoration: none;
      font-size: 0.85rem;
      border-bottom: 1px solid var(--border);
      transition: background 0.15s;
    }
    .dots-menu a:last-child { border-bottom: none; }
    .dots-menu a:hover { background: var(--gold-soft); color: var(--gold); }
    .dots-menu a.danger { color: #E74C3C; }
    .dots-menu a.danger:hover { background: rgba(231,76,60,0.08); }

    /* QUICK STATS ROW */
    .acct-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.6rem;
      margin-bottom: 1.25rem;
    }
    .acct-stat {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.85rem 0.6rem;
      text-align: center;
    }
    .acct-stat strong {
      display: block;
      font-size: 1.3rem;
      font-weight: 800;
      color: var(--gold);
      font-family: 'Space Grotesk', sans-serif;
    }
    .acct-stat span { font-size: 0.62rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }

    /* SECTION CARDS */
    .acct-sections { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; }
    .acct-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.1rem;
      text-decoration: none;
      color: var(--text);
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      transition: all 0.2s;
    }
    .acct-card:hover { border-color: var(--border-gold); transform: translateY(-2px); }
    .acct-card-icon { font-size: 1.4rem; }
    .acct-card-label { font-size: 0.85rem; font-weight: 600; }
    .acct-card-sub { font-size: 0.7rem; color: var(--muted); }

    /* CART SECTION */
    .acct-cart {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.25rem;
    }
    .acct-cart-title {
      font-size: 0.85rem;
      font-weight: 700;
      margin-bottom: 0.85rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .acct-cart-empty { color: var(--muted); font-size: 0.82rem; text-align: center; padding: 1.5rem 0; }
  </style>
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account" class="nav-avatar">V</a>
  </nav>

  <div class="profile-wrap">

    <!-- PROFILE HEADER -->
    <div class="profile-header">
      <div class="profile-v">V</div>
      <div class="profile-info">
        <strong>{{ username }}</strong>
        <span>@{{ username }}</span>
      </div>
      <div class="profile-dots">
        <button class="dots-btn" id="dotsBtn" onclick="toggleDots()">&#8226;&#8226;&#8226;</button>
        <div class="dots-menu" id="dotsMenu">
          <a href="/account/settings">&#9881;&#65039; Settings</a>
          <a href="/account/support/new">&#128172; Contact Support</a>
          <a href="/valcore">&#9889; VALCORE Profile</a>
          <a href="/appointment">&#128197; Book Appointment</a>
          <a href="/logout" class="danger">&#9211; Logout</a>
        </div>
      </div>
    </div>

    <!-- QUICK STATS -->
    <div class="acct-stats">
      <div class="acct-stat"><strong>{{ purchase_count }}</strong><span>Purchases</span></div>
      <div class="acct-stat"><strong>{{ wishlist_count }}</strong><span>Wishlist</span></div>
      <div class="acct-stat"><strong>{{ ticket_count }}</strong><span>Tickets</span></div>
    </div>

    <!-- SECTION CARDS -->
    <div class="acct-sections">
      <a href="/account/downloads" class="acct-card">
        <div class="acct-card-icon">&#128230;</div>
        <div class="acct-card-label">Purchases</div>
        <div class="acct-card-sub">Downloads &amp; licenses</div>
      </a>
      <a href="/account/wishlist" class="acct-card">
        <div class="acct-card-icon">&#9825;</div>
        <div class="acct-card-label">Wishlist</div>
        <div class="acct-card-sub">Saved products</div>
      </a>
      <a href="/account/support" class="acct-card">
        <div class="acct-card-icon">&#128172;</div>
        <div class="acct-card-label">Support</div>
        <div class="acct-card-sub">Your tickets</div>
      </a>
      <a href="/account/reviews" class="acct-card">
        <div class="acct-card-icon">&#11088;</div>
        <div class="acct-card-label">My Reviews</div>
        <div class="acct-card-sub">Products you rated</div>
      </a>
    </div>

    <!-- CART -->
    <div class="acct-cart">
      <div class="acct-cart-title">
        <span>&#128722; Cart</span>
        {% if cart_count > 0 %}<span style="color:var(--gold);font-size:0.78rem">{{ cart_count }} items</span>{% endif %}
      </div>
      {% if cart_items %}
        {% for item in cart_items %}
        <div style="display:flex;justify-content:space-between;padding:0.6rem 0;border-bottom:1px solid var(--border);font-size:0.82rem">
          <span>{{ item.name }}</span>
          <span style="color:var(--gold)">&#8358;{{ "{:,}".format(item.price) }}</span>
        </div>
        {% endfor %}
        <a href="/" class="btn btn-gold" style="width:100%;text-align:center;display:block;margin-top:1rem">Checkout</a>
      {% else %}
        <div class="acct-cart-empty">
          Cart is empty. <a href="/" style="color:var(--gold)">Browse products</a>
        </div>
      {% endif %}
    </div>

  </div>

  <script>
  function toggleDots() {
    var menu = document.getElementById('dotsMenu');
    menu.classList.toggle('open');
  }
  document.addEventListener('click', function(e) {
    var btn = document.getElementById('dotsBtn');
    var menu = document.getElementById('dotsMenu');
    if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.remove('open');
    }
  });
  </script>
</body>
</html>
'''


@account_bp.route('/')
@login_required
def dashboard():
    db = get_db()
    user_id = session['user_id']

    purchase_count = db.execute(
        'SELECT COUNT(*) as c FROM purchases WHERE user_id=?', (user_id,)
    ).fetchone()['c']

    wishlist_count = db.execute(
        'SELECT COUNT(*) as c FROM wishlist WHERE user_id=?', (user_id,)
    ).fetchone()['c']

    ticket_count = db.execute(
        'SELECT COUNT(*) as c FROM support_tickets WHERE user_id=?', (user_id,)
    ).fetchone()['c']

    db.close()

    return render_template_string(
        ACCOUNT_PAGE,
        username=session.get('username'),
        purchase_count=purchase_count,
        wishlist_count=wishlist_count,
        ticket_count=ticket_count,
        cart_items=[],   # Cart phase — empty for now, session-based cart comes later
        cart_count=0,
    )


@account_bp.route('/wishlist/toggle', methods=['POST'])
@login_required
def toggle_wishlist():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    user_id = session['user_id']

    db = get_db()
    existing = db.execute(
        'SELECT id FROM wishlist WHERE user_id=? AND product_id=?',
        (user_id, product_id)
    ).fetchone()

    if existing:
        db.execute('DELETE FROM wishlist WHERE id=?', (existing['id'],))
        added = False
    else:
        db.execute(
            'INSERT INTO wishlist (user_id, product_id) VALUES (?,?)',
            (user_id, product_id)
        )
        added = True

    db.commit()
    db.close()
    return jsonify({'ok': True, 'added': added})


WISHLIST_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>My Wishlist — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account" class="btn btn-outline" style="font-size:0.78rem;padding:0.45rem 1rem">My Account</a>
  </nav>

  <section class="store-section">
    <div class="section-title-row">
      <span class="section-title">&#9825; My Wishlist</span>
    </div>
    <div class="product-grid">
      {% for p in products %}
      <a href="/product/{{ p.slug }}" class="product-card">
        <div class="product-img">&#128230;</div>
        <div class="product-info">
          <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
          <div class="product-name">{{ p.name }}</div>
          <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.price) }}</span></div>
        </div>
      </a>
      {% else %}
      <div class="empty-state">Your wishlist is empty. <a href="/" style="color:var(--gold)">Browse products</a></div>
      {% endfor %}
    </div>
  </section>
</body>
</html>
'''


@account_bp.route('/wishlist')
@login_required
def wishlist_page():
    db = get_db()
    rows = db.execute('''
        SELECT p.*, c.name as collection_name
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        LEFT JOIN collections c ON p.collection_id = c.id
        WHERE w.user_id=? AND p.deleted_at IS NULL
        ORDER BY w.id DESC
    ''', (session['user_id'],)).fetchall()
    db.close()

    return render_template_string(WISHLIST_PAGE, products=[dict(r) for r in rows])


# ============================================
#   SUPPORT TICKETS
# ============================================

SUPPORT_LIST_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>Support — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account" class="btn btn-outline" style="font-size:0.78rem;padding:0.45rem 1rem">My Account</a>
  </nav>

  <section class="store-section">
    <div class="section-title-row">
      <span class="section-title">&#128172; Support Tickets</span>
      <a href="/account/support/new" class="btn btn-gold" style="font-size:0.8rem">+ New Ticket</a>
    </div>

    <div style="display:flex;flex-direction:column;gap:0.75rem">
      {% for t in tickets %}
      <a href="/account/support/{{ t.id }}" style="text-decoration:none;color:inherit">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem 1.25rem;display:flex;justify-content:space-between;align-items:center">
          <div>
            <strong style="font-size:0.9rem">{{ t.subject }}</strong>
            <p style="font-size:0.78rem;color:var(--muted);margin-top:0.2rem">{{ (t.created_at or '')[:16] }}</p>
          </div>
          <span class="badge {{ 'bg' if t.status=='resolved' else 'by' if t.status=='pending' else 'bo' }}"
            style="font-size:0.65rem;padding:0.25rem 0.7rem;border-radius:50px;text-transform:uppercase;font-weight:700">{{ t.status }}</span>
        </div>
      </a>
      {% else %}
      <div class="empty-state">No support tickets yet.</div>
      {% endfor %}
    </div>
  </section>
</body>
</html>
'''


@account_bp.route('/support')
@login_required
def support_list():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM support_tickets WHERE user_id=? ORDER BY id DESC',
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template_string(SUPPORT_LIST_PAGE, tickets=[dict(r) for r in rows])


SUPPORT_NEW_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>New Ticket — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account/support" class="btn btn-outline" style="font-size:0.78rem;padding:0.45rem 1rem">All Tickets</a>
  </nav>

  <div class="product-page" style="max-width:520px">
    <h1 class="pp-name">New Support Ticket</h1>
    <form id="ticketForm" onsubmit="submitTicket(event)" style="display:flex;flex-direction:column;gap:1rem;margin-top:1rem">
      <input type="text" id="tSubject" placeholder="Subject" required
        style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"/>
      <textarea id="tMessage" rows="5" placeholder="Describe your issue..." required
        style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"></textarea>
      <button type="submit" class="btn btn-gold">Submit Ticket</button>
      <p id="ticketNote" style="font-size:0.8rem"></p>
    </form>
  </div>

  <script>
  function submitTicket(e) {
    e.preventDefault();
    var note = document.getElementById('ticketNote');
    note.textContent = 'Submitting...';
    note.style.color = 'var(--muted)';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/account/support/create', true);
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function() {
      if (xhr.readyState === 4) {
        try {
          var res = JSON.parse(xhr.responseText);
          if (res.ok) {
            window.location.href = '/account/support/' + res.id;
          } else {
            note.textContent = res.error || 'Could not submit ticket.';
            note.style.color = 'var(--red)';
          }
        } catch(err) {
          note.textContent = 'Something went wrong.';
          note.style.color = 'var(--red)';
        }
      }
    };
    xhr.send(JSON.stringify({
      subject: document.getElementById('tSubject').value,
      message: document.getElementById('tMessage').value,
    }));
  }
  </script>
</body>
</html>
'''


@account_bp.route('/support/new')
@login_required
def support_new():
    return render_template_string(SUPPORT_NEW_PAGE)


@account_bp.route('/support/create', methods=['POST'])
@login_required
def support_create():
    data = request.get_json() or {}
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not subject or not message:
        return jsonify({'ok': False, 'error': 'Subject and message are required.'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO support_tickets (user_id, subject, message) VALUES (?,?,?)',
        (session['user_id'], subject, message)
    )
    ticket = db.execute(
        'SELECT id FROM support_tickets WHERE user_id=? ORDER BY id DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()

    db.execute(
        "INSERT INTO activity_log (type, summary) VALUES ('support', ?)",
        (f'New support ticket: {subject}',)
    )
    db.commit()
    db.close()

    notify_support_ticket(subject, session.get('username', 'Unknown'))

    return jsonify({'ok': True, 'id': ticket['id']})


SUPPORT_DETAIL_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>{{ ticket.subject }} — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account/support" class="btn btn-outline" style="font-size:0.78rem;padding:0.45rem 1rem">All Tickets</a>
  </nav>

  <div class="product-page" style="max-width:600px">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <h1 class="pp-name" style="margin:0">{{ ticket.subject }}</h1>
      <span class="badge {{ 'bg' if ticket.status=='resolved' else 'by' if ticket.status=='pending' else 'bo' }}"
        style="font-size:0.65rem;padding:0.25rem 0.7rem;border-radius:50px;text-transform:uppercase;font-weight:700">{{ ticket.status }}</span>
    </div>
    <p style="font-size:0.75rem;color:var(--muted);margin-bottom:1.5rem">Opened {{ (ticket.created_at or '')[:16] }}</p>

    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem;margin-bottom:1rem">
      <strong style="font-size:0.82rem;color:var(--muted)">You wrote:</strong>
      <p style="font-size:0.88rem;margin-top:0.5rem;line-height:1.7">{{ ticket.message }}</p>
    </div>

    {% if ticket.admin_reply %}
    <div style="background:var(--gold-soft);border:1px solid var(--border-gold);border-radius:12px;padding:1.25rem">
      <strong style="font-size:0.82rem;color:var(--gold)">VALCORE replied:</strong>
      <p style="font-size:0.88rem;margin-top:0.5rem;line-height:1.7">{{ ticket.admin_reply }}</p>
    </div>
    {% else %}
    <p style="color:var(--muted2);font-size:0.82rem">Awaiting a reply from VALCORE support...</p>
    {% endif %}
  </div>
</body>
</html>
'''


@account_bp.route('/support/<int:ticket_id>')
@login_required
def support_detail(ticket_id):
    db = get_db()
    ticket = db.execute(
        'SELECT * FROM support_tickets WHERE id=? AND user_id=?',
        (ticket_id, session['user_id'])
    ).fetchone()
    db.close()

    if not ticket:
        return 'Ticket not found', 404

    return render_template_string(SUPPORT_DETAIL_PAGE, ticket=dict(ticket))


# ============================================
#   ACCOUNT SETTINGS PAGE
# ============================================

SETTINGS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>Settings — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account" class="nav-avatar">V</a>
  </nav>

  <div style="max-width:480px;margin:0 auto;padding:1.5rem 5%">
    <h2 style="font-family:'Space Grotesk',sans-serif;font-size:1.2rem;margin-bottom:1.25rem">&#9881;&#65039; Settings</h2>

    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <a href="/account" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--border)">
        <span>&#128100; My Profile</span><span style="color:var(--muted)">&rsaquo;</span>
      </a>
      <a href="/account/downloads" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--border)">
        <span>&#128230; My Purchases</span><span style="color:var(--muted)">&rsaquo;</span>
      </a>
      <a href="/account/wishlist" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--border)">
        <span>&#9825; Wishlist</span><span style="color:var(--muted)">&rsaquo;</span>
      </a>
      <a href="/account/support" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--border)">
        <span>&#128172; Support Tickets</span><span style="color:var(--muted)">&rsaquo;</span>
      </a>
      <a href="/account/support/new" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--border)">
        <span>&#128172; Contact Support</span><span style="color:var(--muted)">&rsaquo;</span>
      </a>
      <a href="/logout" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;color:#E74C3C;text-decoration:none">
        <span>&#9211; Logout</span><span style="color:#E74C3C">&rsaquo;</span>
      </a>
    </div>

    <p style="font-size:0.72rem;color:var(--muted2);text-align:center;margin-top:1.5rem">VALCORE Commerce Engine</p>
  </div>
</body>
</html>
'''


@account_bp.route('/settings')
@login_required
def account_settings():
    return render_template_string(SETTINGS_PAGE)


# ============================================
#   MY REVIEWS PAGE
# ============================================

MY_REVIEWS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>My Reviews — VALCORE</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/css/store.css">
</head>
<body>
  <nav class="navbar">
    <a href="/" class="nav-logo">VALCORE <span>&lt;/&gt;</span></a>
    <a href="/account" class="nav-avatar">V</a>
  </nav>

  <section class="store-section">
    <div class="section-title-row">
      <span class="section-title">&#11088; My Reviews</span>
    </div>
    {% for r in reviews %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.1rem;margin:0 5% 0.75rem">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
        <a href="/product/{{ r.slug }}" style="color:var(--gold);font-size:0.88rem;font-weight:600;text-decoration:none">{{ r.product_name }}</a>
        <span style="color:var(--gold)">{{ "★" * r.rating }}{{ "☆" * (5 - r.rating) }}</span>
      </div>
      <p style="font-size:0.82rem;color:var(--muted)">{{ r.comment or "No comment left." }}</p>
      <span style="font-size:0.68rem;color:var(--muted2)">{{ (r.created_at or "")[:10] }}</span>
    </div>
    {% else %}
    <div class="empty-state" style="padding:3rem 5%">No reviews yet. Buy a product and share your experience!</div>
    {% endfor %}
  </section>
</body>
</html>
'''


@account_bp.route('/reviews')
@login_required
def my_reviews():
    db = get_db()
    rows = db.execute('''
        SELECT r.*, p.name as product_name, p.slug
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        WHERE r.user_id=?
        ORDER BY r.id DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template_string(MY_REVIEWS_PAGE, reviews=[dict(r) for r in rows])
