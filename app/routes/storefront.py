# ============================================
#   VALCORE — STOREFRONT ROUTES
#   app/routes/storefront.py
#   Phase 2: full home/product/collection page UI
# ============================================

from flask import Blueprint, render_template_string, abort, request, jsonify, session
from app.core.database import get_db, get_setting
from app.services.notifications import notify_appointment

storefront_bp = Blueprint('storefront', __name__)

# ============================================
#   SHARED LAYOUT PIECES (navbar, drawer, footer)
#   Injected into every storefront page
# ============================================

NAVBAR = '''
<nav class="navbar">
  <!-- Left Side: Hamburger Menu -->
  <button class="nav-menu-btn" id="menuBtn">&#9776;</button>
  
  <!-- Left-of-Center Brand Text -->
  <a href="/" class="nav-logo-img-wrap">
    <span class="nav-logo">VALCORE <span>&lt;/&gt;</span></span>
  </a>

  <!-- Right Side Slot: Brand Profile Avatar -->
  <a href="/valcore" class="nav-valcore-logo" title="VALCORE">
    <img src="/assets/logo.png" alt="VALCORE" class="nav-logo-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
    <span class="nav-logo-fallback">V</span>
  </a>
</nav>

<div class="menu-overlay" id="menuOverlay"></div>
<div class="menu-drawer" id="menuDrawer">
  <a href="/">&#127968; Home</a>
  <a href="/search">&#128269; Search</a>
  <a href="/valcore">&#9889; VALCORE Profile</a>
  <a href="/appointment">&#128197; Book Appointment</a>
  {% if session_user %}
  <a href="/account/downloads">&#128230; My Purchases</a>
  <a href="/account/wishlist">&#9825; Wishlist</a>
  <a href="/account/support">&#128172; Support Tickets</a>
  <a href="/account/settings">&#9881; Settings</a>
  <a href="/logout" style="color:#E74C3C">&#9211; Logout</a>
  <a href="/account" class="menu-user-card">
    <span class="menu-user-v">V</span>
    <span class="menu-username">{{ session_username or "My Account" }}</span>
  </a>
  {% else %}
  <a href="/login">&#128275; Sign In</a>
  <a href="/signup">&#10133; Create Account</a>
  {% endif %}
</div>
'''

FOOTER = '''
<footer class="store-footer">
  <div class="store-footer-inner">
    <p><span class="gold">VALCORE</span> &lt;/&gt; &middot; Digital products, templates, and automation systems.</p>
    <p>Products not to your liking? <a href="/appointment" style="color:var(--gold)">Book an appointment</a> &rarr;</p>
  </div>
</footer>
'''

HEAD = '''
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/css/store.css"/>
'''

SCRIPT_TAG = '<script src="/js/store.js"></script>'


# ============================================
#   HOME PAGE
# ============================================

HOME_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>VALCORE — Digital Products & Templates</title>''' + HEAD + '''</head>
<body>
''' + NAVBAR + '''

<div class="search-section">
  <div class="search-box">
    <span class="search-icon">&#128269;</span>
    <input type="text" id="searchInput" placeholder="Search templates, bots, automation..."/>
    <button id="searchBtn" class="search-icon" style="background:none;border:none;cursor:pointer">&rarr;</button>
  </div>
</div>


<section class="deals-section" id="dealsSection" style="display:none">
  <div class="hot-title" style="font-size:1.3rem;padding:1.5rem 5% 0.5rem">&#128176; Deals</div>
  <div class="product-grid" id="dealsGrid">
    {% for p in deals %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-badge promo">-{{ p.promo_percent }}%</div>
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }}</div>
        <div class="product-price-row">
          <span class="product-price">&#8358;{{ "{:,}".format(p.display_price) }}</span>
          <span class="product-compare">&#8358;{{ "{:,}".format(p.price) }}</span>
        </div>
        <button class="btn btn-gold" style="width:100%;margin-top:0.5rem;font-size:0.78rem;padding:0.45rem 0"
          onclick="event.preventDefault();addToCart({{ p.id }}, '{{ p.name }}', {{ p.display_price }}, this)">+ Add to Cart</button>
      </div>
    </a>
    {% endfor %}
  </div>
</section>

<section class="hot-section">
  <div class="hot-title">&#128293; HOT</div>
  <div class="product-grid">
    {% for p in hot_products %}
    <a href="/product/{{ p.slug }}" class="product-card">
      {% if p.promo_percent and p.promo_percent > 0 %}<div class="product-badge promo">-{{ p.promo_percent }}%</div>{% endif %}
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }} ({{ p.rating_count or 0 }})</div>
        <div class="product-price-row">
          <span class="product-price">&#8358;{{ "{:,}".format(p.display_price) }}</span>
          {% if p.promo_percent and p.promo_percent > 0 %}<span class="product-compare">&#8358;{{ "{:,}".format(p.price) }}</span>{% endif %}
        </div>
        <button class="btn btn-gold" style="width:100%;margin-top:0.5rem;font-size:0.78rem;padding:0.45rem 0"
          onclick="event.preventDefault();addToCart({{ p.id }}, '{{ p.name }}', {{ p.display_price }}, this)">+ Add to Cart</button>
      </div>
    </a>
    {% else %}
    <div class="empty-state">No hot products yet — add some from the admin dashboard.</div>
    {% endfor %}
  </div>
</section>

<section class="collections-section">
  <div class="collections-header">
    <span class="section-title">Collections</span>
  </div>
  <div class="collections-scroll">
    {% for c in collections %}
    <a href="/collection/{{ c.slug }}" class="collection-chip">{{ c.icon }} {{ c.name }}</a>
    {% endfor %}
  </div>
</section>

<section class="store-section">
  <div class="section-title-row">
    <span class="section-title">&#11088; Recommended For You</span>
  </div>
  <div class="product-grid">
    {% for p in recommended %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }} ({{ p.rating_count or 0 }})</div>
        <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.display_price) }}</span></div>
      </div>
    </a>
    {% else %}
    <div class="empty-state">Recommendations build up as products get views and purchases.</div>
    {% endfor %}
  </div>
</section>

<section class="store-section">
  <div class="section-title-row">
    <span class="section-title">&#127881; New Releases</span>
  </div>
  <div class="product-grid">
    {% for p in new_releases %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-badge">NEW</div>
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }} ({{ p.rating_count or 0 }})</div>
        <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.display_price) }}</span></div>
      </div>
    </a>
    {% else %}
    <div class="empty-state">New releases show up here automatically.</div>
    {% endfor %}
  </div>
</section>

<section class="store-section">
  <div class="section-title-row">
    <span class="section-title">All Products</span>
  </div>
  <div class="product-grid">
    {% for p in all_products %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }} ({{ p.rating_count or 0 }})</div>
        <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.display_price) }}</span></div>
      </div>
    </a>
    {% else %}
    <div class="empty-state">No products live yet. Add some from /admin → Products.</div>
    {% endfor %}
  </div>
</section>


<section class="store-section" id="recentlyViewedSection" style="display:none;padding-top:0">
  <div class="section-title-row">
    <span class="section-title">&#128336; Recently Viewed</span>
    <button onclick="clearRecentlyViewed()" style="background:none;border:none;color:var(--muted);font-size:0.75rem;cursor:pointer">Clear</button>
  </div>
  <div class="product-grid wide" id="recentlyViewedGrid"></div>
</section>

<div class="appt-cta">
  <h3>Products not to your liking?</h3>
  <p>Book an appointment now and create YOUR OWN. &#127801;</p>
  <a href="/appointment" class="btn btn-gold">Book Appointment</a>
</div>

''' + FOOTER + SCRIPT_TAG + '''
</body>
</html>
'''


@storefront_bp.route('/')
def home():
    db = get_db()

    collections = db.execute(
        "SELECT * FROM collections WHERE active=1 ORDER BY sort_order"
    ).fetchall()

    base_query = '''
        SELECT p.*, c.name as collection_name
        FROM products p
        LEFT JOIN collections c ON p.collection_id = c.id
        WHERE p.status='live' AND p.deleted_at IS NULL
    '''

    hot_rows = db.execute(
        base_query + " ORDER BY (p.views*0.2 + p.purchase_count*5 + p.rating_avg*10) DESC LIMIT 4"
    ).fetchall()

    recommended_rows = db.execute(
        base_query + " ORDER BY p.rating_avg DESC, p.purchase_count DESC LIMIT 4"
    ).fetchall()

    new_rows = db.execute(
        base_query + " ORDER BY p.created_at DESC LIMIT 4"
    ).fetchall()

    all_rows = db.execute(
        base_query + " ORDER BY p.id DESC LIMIT 20"
    ).fetchall()

    deals_rows = db.execute(
        base_query + " AND p.promo_percent > 0 ORDER BY p.promo_percent DESC LIMIT 8"
    ).fetchall()

    # Fetch active announcements with product slug if linked
    announcements = db.execute("""
        SELECT a.*, p.slug as product_slug
        FROM announcements a
        LEFT JOIN products p ON p.id = a.product_id
        WHERE a.active = 1
        ORDER BY a.sort_order ASC, a.id DESC
        LIMIT 10
    """).fetchall()

    db.close()

    def with_display_price(rows):
        out = []
        for r in rows:
            d = dict(r)
            price = d.get('price') or 0
            promo = d.get('promo_percent') or 0
            d['display_price'] = round(price - (price * promo / 100)) if promo > 0 else price
            out.append(d)
        return out

    return render_template_string(
        HOME_PAGE,
        session_user=session.get('user_id'),
        session_username=session.get('username', ''),
        collections=[dict(c) for c in collections],
        hot_products=with_display_price(hot_rows),
        recommended=with_display_price(recommended_rows),
        new_releases=with_display_price(new_rows),
        all_products=with_display_price(all_rows),
        deals=with_display_price(deals_rows),
        announcements=announcements,
    )


# ============================================
#   PRODUCT PAGE
# ============================================

PRODUCT_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>{{ product.name }} — VALCORE</title>''' + HEAD + '''</head>
<body>
''' + NAVBAR + '''

<div class="product-page">
  <div class="pp-gallery">&#128230;</div>

  <div class="pp-meta">
    <span class="pp-cat">{{ product.collection_name or "Product" }}</span>
    <span class="pp-views">&#128065; {{ product.views }} views</span>
  </div>

  <h1 class="pp-name">{{ product.name }}</h1>

  <div class="pp-rating-row">
    <span class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</span>
    <span>{{ "%.1f"|format(product.rating_avg or 0) }} ({{ product.rating_count or 0 }} reviews)</span>
  </div>

  <div class="pp-price-block">
    <span class="pp-price">&#8358;{{ "{:,}".format(display_price) }}</span>
    {% if product.promo_percent and product.promo_percent > 0 %}
    <span class="pp-compare">&#8358;{{ "{:,}".format(product.price) }}</span>
    <span class="pp-promo-badge">-{{ product.promo_percent }}% OFF</span>
    {% endif %}
  </div>

  <p class="pp-desc">{{ product.description or product.short_desc or "No description yet." }}</p>

  <div class="pp-actions">
    <button onclick="startCheckout({{ product.id }})" class="btn btn-gold" style="flex:1;text-align:center;border:none;cursor:pointer" id="purchaseBtn">Purchase &rarr;</button>
    <button class="btn btn-outline" style="flex:1;text-align:center;border:none;cursor:pointer"
      onclick="addToCart({{ product.id }}, '{{ product.name }}', {{ display_price }}, this)">+ Add to Cart</button>
    <button class="pp-wishlist-btn" onclick="toggleWishlist({{ product.id }}, this)">&#9825;</button>
    {% if session_admin %}
    <a href="/admin#products" class="btn btn-outline">&#9998; Edit</a>
    {% endif %}
  </div>

  <div class="store-section" style="padding:0">
    <div class="section-title-row" style="padding:0">
      <span class="section-title">&#9733; Reviews ({{ reviews|length }})</span>
    </div>

    {% if session_user %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem">
      <div style="display:flex;gap:0.4rem;margin-bottom:0.85rem" id="reviewStars">
        <span class="rstar" data-val="1" style="font-size:1.6rem;cursor:pointer;color:var(--border)">&#9733;</span>
        <span class="rstar" data-val="2" style="font-size:1.6rem;cursor:pointer;color:var(--border)">&#9733;</span>
        <span class="rstar" data-val="3" style="font-size:1.6rem;cursor:pointer;color:var(--border)">&#9733;</span>
        <span class="rstar" data-val="4" style="font-size:1.6rem;cursor:pointer;color:var(--border)">&#9733;</span>
        <span class="rstar" data-val="5" style="font-size:1.6rem;cursor:pointer;color:var(--border)">&#9733;</span>
      </div>
      <textarea id="reviewComment" rows="2" placeholder="Share your experience with this product..."
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:0.7rem;color:var(--text);font-family:Inter,sans-serif;margin-bottom:0.75rem"></textarea>
      <button class="btn btn-gold" onclick="submitReview({{ product.id }})">Submit Review</button>
      <p id="reviewNote" style="font-size:0.78rem;margin-top:0.5rem"></p>
    </div>
    {% endif %}

    {% for r in reviews %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem;margin-bottom:0.75rem">
      <div style="color:var(--gold);font-size:0.85rem;margin-bottom:0.4rem">{{ '★' * r.rating }}{{ '☆' * (5 - r.rating) }}</div>
      <p style="font-size:0.85rem;color:var(--muted);margin-bottom:0.5rem">{{ r.comment or "No comment left." }}</p>
      <span style="font-size:0.72rem;color:var(--muted2)">{{ r.username or 'Anonymous' }} &middot; {{ (r.created_at or '')[:10] }}</span>
    </div>
    {% else %}
    <p class="empty-state" style="padding:1.5rem 0">No reviews yet. Be the first!</p>
    {% endfor %}
  </div>

  <div class="store-section" style="padding:1.5rem 0 0">
    <div class="section-title-row" style="padding:0">
      <span class="section-title">&#10067; Questions ({{ questions|length }})</span>
    </div>

    {% if session_user %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem">
      <textarea id="questionText" rows="2" placeholder="Ask a question about this product..."
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:0.7rem;color:var(--text);font-family:Inter,sans-serif;margin-bottom:0.75rem"></textarea>
      <button class="btn btn-gold" onclick="submitQuestion({{ product.id }})">Ask Question</button>
      <p id="questionNote" style="font-size:0.78rem;margin-top:0.5rem"></p>
    </div>
    {% endif %}

    {% for q in questions %}
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem;margin-bottom:0.75rem">
      <p style="font-size:0.85rem;margin-bottom:0.5rem"><strong>Q:</strong> {{ q.question }}</p>
      {% if q.answer %}
      <p style="font-size:0.85rem;color:var(--gold)"><strong>A:</strong> {{ q.answer }}</p>
      {% else %}
      <p style="font-size:0.78rem;color:var(--muted2)">Awaiting answer from VALCORE...</p>
      {% endif %}
    </div>
    {% else %}
    <p class="empty-state" style="padding:1.5rem 0">No questions yet. Ask the first one!</p>
    {% endfor %}
  </div>

  <div class="store-section" style="padding:0">
    <div class="section-title-row" style="padding:0">
      <span class="section-title">Related Products</span>
    </div>
    <div class="product-grid">
      {% for p in related %}
      <a href="/product/{{ p.slug }}" class="product-card">
        <div class="product-img">&#128230;</div>
        <div class="product-info">
          <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
          <div class="product-name">{{ p.name }}</div>
          <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.price) }}</span></div>
        </div>
      </a>
      {% else %}
      <div class="empty-state">No related products yet.</div>
      {% endfor %}
    </div>
  </div>
</div>


''' + FOOTER + SCRIPT_TAG + '''
<script>
function startCheckout(productId) {
  var btn = document.getElementById('purchaseBtn');
  {% if session_user %}
  var isLoggedIn = true;
  {% else %}
  var isLoggedIn = false;
  {% endif %}

  if (!isLoggedIn) {
    window.location.href = '/login';
    return;
  }

  btn.textContent = 'Starting checkout...';
  btn.disabled = true;

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/checkout/start/' + productId, true);
  xhr.withCredentials = true;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      btn.disabled = false;
      try {
        var res = JSON.parse(xhr.responseText);
        if (res.ok && res.authorization_url) {
          window.location.href = res.authorization_url;
        } else {
          btn.textContent = 'Purchase →';
          alert(res.error || 'Could not start checkout.');
        }
      } catch(e) {
        btn.textContent = 'Purchase →';
        alert('Something went wrong. Try again.');
      }
    }
  };
  xhr.send(JSON.stringify({}));
}

// ---- STAR RATING SELECTOR ----
var selectedReviewRating = 0;
(function() {
  var stars = document.querySelectorAll('.rstar');
  stars.forEach(function(star) {
    star.addEventListener('mouseover', function() {
      var val = parseInt(star.getAttribute('data-val'));
      stars.forEach(function(s) {
        s.style.color = parseInt(s.getAttribute('data-val')) <= val ? 'var(--gold)' : 'var(--border)';
      });
    });
    star.addEventListener('click', function() {
      selectedReviewRating = parseInt(star.getAttribute('data-val'));
      stars.forEach(function(s) {
        s.style.color = parseInt(s.getAttribute('data-val')) <= selectedReviewRating ? 'var(--gold)' : 'var(--border)';
      });
    });
  });
})();

function submitReview(productId) {
  var note = document.getElementById('reviewNote');
  if (!selectedReviewRating) {
    note.textContent = 'Please select a star rating.';
    note.style.color = 'var(--red)';
    return;
  }
  note.textContent = 'Submitting...';
  note.style.color = 'var(--muted)';

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/product/' + productId + '/review', true);
  xhr.withCredentials = true;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      try {
        var res = JSON.parse(xhr.responseText);
        if (res.ok) {
          note.textContent = '✓ Review submitted!';
          note.style.color = 'var(--green)';
          setTimeout(function() { window.location.reload(); }, 800);
        } else {
          note.textContent = res.error || 'Could not submit review.';
          note.style.color = 'var(--red)';
        }
      } catch(e) {
        note.textContent = 'Something went wrong.';
        note.style.color = 'var(--red)';
      }
    }
  };
  xhr.send(JSON.stringify({ rating: selectedReviewRating, comment: document.getElementById('reviewComment').value }));
}

function submitQuestion(productId) {
  var note = document.getElementById('questionNote');
  var text = document.getElementById('questionText').value.trim();
  if (!text) {
    note.textContent = 'Please enter a question.';
    note.style.color = 'var(--red)';
    return;
  }
  note.textContent = 'Submitting...';
  note.style.color = 'var(--muted)';

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/product/' + productId + '/question', true);
  xhr.withCredentials = true;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      try {
        var res = JSON.parse(xhr.responseText);
        if (res.ok) {
          note.textContent = '✓ Question submitted! VALCORE will answer soon.';
          note.style.color = 'var(--green)';
          setTimeout(function() { window.location.reload(); }, 800);
        } else {
          note.textContent = res.error || 'Could not submit question.';
          note.style.color = 'var(--red)';
        }
      } catch(e) {
        note.textContent = 'Something went wrong.';
        note.style.color = 'var(--red)';
      }
    }
  };
  xhr.send(JSON.stringify({ question: text }));
}
</script>
</body>
</html>
'''


@storefront_bp.route('/product/<slug>')
def product_page(slug):
    db = get_db()

    product = db.execute('''
        SELECT p.*, c.name as collection_name
        FROM products p
        LEFT JOIN collections c ON p.collection_id = c.id
        WHERE p.slug=? AND p.deleted_at IS NULL
    ''', (slug,)).fetchone()

    if not product:
        db.close()
        abort(404)

    # Increment view count
    db.execute('UPDATE products SET views = views + 1 WHERE id=?', (product['id'],))

    related = db.execute('''
        SELECT p.*, c.name as collection_name
        FROM products p
        LEFT JOIN collections c ON p.collection_id = c.id
        WHERE p.collection_id=? AND p.id != ? AND p.status='live' AND p.deleted_at IS NULL
        LIMIT 4
    ''', (product['collection_id'], product['id'])).fetchall()

    reviews = db.execute('''
        SELECT r.*, u.username
        FROM reviews r
        LEFT JOIN users u ON r.user_id = u.id
        WHERE r.product_id=?
        ORDER BY r.id DESC
    ''', (product['id'],)).fetchall()

    questions = db.execute('''
        SELECT * FROM product_questions
        WHERE product_id=?
        ORDER BY id DESC
    ''', (product['id'],)).fetchall()

    db.commit()
    db.close()

    product_dict = dict(product)
    price = product_dict.get('price') or 0
    promo = product_dict.get('promo_percent') or 0
    display_price = round(price - (price * promo / 100)) if promo > 0 else price

    return render_template_string(
        PRODUCT_PAGE,
        product=product_dict,
        display_price=display_price,
        related=[dict(r) for r in related],
        reviews=[dict(r) for r in reviews],
        questions=[dict(q) for q in questions],
        session_user=session.get('user_id'),
        session_username=session.get('username', ''),
        session_admin=session.get('is_admin'),
    )


# ============================================
#   COLLECTION PAGE
# ============================================

COLLECTION_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>{{ collection.name }} — VALCORE</title>''' + HEAD + '''</head>
<body>
''' + NAVBAR + '''

<section class="store-section">
  <div class="section-title-row">
    <span class="section-title">{{ collection.icon }} {{ collection.name }}</span>
  </div>
  <div class="collection-tools">
    <button class="tool-btn" onclick="refreshCollection('{{ collection.slug }}')">&#128260; Refresh</button>
    <button class="tool-btn" id="searchBtnCollection" onclick="window.location.href='/search?q=%23{{ collection.slug }}'">&#128269; Search</button>
  </div>
  <div class="product-grid" id="collectionGrid">
    {% for p in products %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ collection.name }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-rating"><span class="stars">&#9733;</span> {{ "%.1f"|format(p.rating_avg or 0) }} ({{ p.rating_count or 0 }})</div>
        <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.price) }}</span></div>
      </div>
    </a>
    {% else %}
    <div class="empty-state">No products in this collection yet.</div>
    {% endfor %}
  </div>
</section>

''' + FOOTER + SCRIPT_TAG + '''
</body>
</html>
'''


# ============================================
#   REVIEW SUBMISSION
# ============================================

@storefront_bp.route('/product/<int:product_id>/review', methods=['POST'])
def submit_review(product_id):
    if not session.get('user_id'):
        return jsonify({'ok': False, 'error': 'Login required to leave a review.'}), 401

    data = request.get_json() or {}
    rating = int(data.get('rating', 0))
    comment = data.get('comment', '').strip()

    if not 1 <= rating <= 5:
        return jsonify({'ok': False, 'error': 'Rating must be between 1 and 5.'}), 400

    db = get_db()

    # One review per user per product — update if exists, insert if not
    existing = db.execute(
        'SELECT id FROM reviews WHERE product_id=? AND user_id=?',
        (product_id, session['user_id'])
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE reviews SET rating=?, comment=? WHERE id=?',
            (rating, comment, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?,?,?,?)',
            (product_id, session['user_id'], rating, comment)
        )

    # Recompute product's cached rating average + count
    stats = db.execute(
        'SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE product_id=?',
        (product_id,)
    ).fetchone()

    db.execute(
        'UPDATE products SET rating_avg=?, rating_count=? WHERE id=?',
        (round(stats['avg_r'] or 0, 1), stats['cnt'], product_id)
    )

    db.commit()
    db.close()
    return jsonify({'ok': True})


# ============================================
#   PRODUCT Q&A SUBMISSION
# ============================================

@storefront_bp.route('/product/<int:product_id>/question', methods=['POST'])
def submit_question(product_id):
    data = request.get_json() or {}
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'ok': False, 'error': 'Please enter a question.'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO product_questions (product_id, user_id, question) VALUES (?,?,?)',
        (product_id, session.get('user_id'), question)
    )
    db.execute(
        "INSERT INTO activity_log (type, summary) VALUES ('question', ?)",
        (f'New product question on product #{product_id}',)
    )
    db.commit()
    db.close()
    return jsonify({'ok': True})


@storefront_bp.route('/collection/<slug>')
def collection_page(slug):
    db = get_db()
    collection = db.execute("SELECT * FROM collections WHERE slug=?", (slug,)).fetchone()

    if not collection:
        db.close()
        abort(404)

    products = db.execute('''
        SELECT * FROM products
        WHERE collection_id=? AND status='live' AND deleted_at IS NULL
        ORDER BY id DESC
    ''', (collection['id'],)).fetchall()
    db.close()

    return render_template_string(
        COLLECTION_PAGE,
        collection=dict(collection),
        products=[dict(p) for p in products],
        session_user=session.get('user_id'),
        session_username=session.get('username', ''),
    )


# ============================================
#   SEARCH
# ============================================

SEARCH_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>Search — VALCORE</title>''' + HEAD + '''</head>
<body>
''' + NAVBAR + '''

<div class="search-section">
  <div class="search-box">
    <span class="search-icon">&#128269;</span>
    <input type="text" id="searchInput" placeholder="Search templates, bots, automation..." value="{{ query }}"/>
    <button id="searchBtn" class="search-icon" style="background:none;border:none;cursor:pointer">&rarr;</button>
  </div>
</div>

<section class="store-section">
  <div class="section-title-row">
    <span class="section-title">{{ results|length }} result(s) for "{{ query }}"</span>
  </div>
  <div class="product-grid">
    {% for p in results %}
    <a href="/product/{{ p.slug }}" class="product-card">
      <div class="product-img">&#128230;</div>
      <div class="product-info">
        <span class="product-cat">{{ p.collection_name or 'Product' }}</span>
        <div class="product-name">{{ p.name }}</div>
        <div class="product-price-row"><span class="product-price">&#8358;{{ "{:,}".format(p.price) }}</span></div>
      </div>
    </a>
    {% else %}
    <div class="empty-state">No products match "{{ query }}".</div>
    {% endfor %}
  </div>
</section>

''' + FOOTER + SCRIPT_TAG + '''
</body>
</html>
'''


@storefront_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    results = []

    if query:
        db = get_db()
        like = f'%{query}%'
        rows = db.execute('''
            SELECT p.*, c.name as collection_name
            FROM products p
            LEFT JOIN collections c ON p.collection_id = c.id
            WHERE (p.name LIKE ? OR p.short_desc LIKE ? OR p.description LIKE ?)
              AND p.status='live' AND p.deleted_at IS NULL
            ORDER BY p.id DESC
        ''', (like, like, like)).fetchall()
        db.close()
        results = [dict(r) for r in rows]

    return render_template_string(SEARCH_PAGE, query=query, results=results, session_user=session.get('user_id'), session_username=session.get('username', ''))


# ============================================
#   VALCORE PROFILE PAGE
# ============================================

VALCORE_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>VALCORE — Digital Ecosystem</title>''' + HEAD + '''
<style>
.vp-hero{padding:3rem 5% 2rem;text-align:center;position:relative;overflow:hidden}
.vp-hero::before{content:'';position:absolute;top:-50%;left:50%;transform:translateX(-50%);
  width:600px;height:400px;background:radial-gradient(ellipse,rgba(212,175,55,0.08) 0%,transparent 70%);pointer-events:none}
.vp-badge{display:inline-block;background:var(--gold-soft);border:1px solid var(--border-gold);color:var(--gold);
  font-size:0.7rem;font-weight:700;letter-spacing:0.08em;padding:0.35rem 1rem;border-radius:50px;margin-bottom:1.25rem;text-transform:uppercase}
.vp-title{font-family:'Space Grotesk',sans-serif;font-size:clamp(2rem,5vw,3rem);font-weight:800;
  letter-spacing:-0.02em;margin-bottom:0.75rem;position:relative;z-index:1}
.vp-title span{color:var(--gold)}
.vp-tagline{color:var(--muted);font-size:0.95rem;max-width:480px;margin:0 auto 2rem;line-height:1.75;position:relative;z-index:1}

.vp-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:0.85rem;max-width:560px;margin:0 auto 3rem;position:relative;z-index:1}
.vp-stat{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.25rem 0.75rem}
.vp-stat strong{display:block;font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:800;color:var(--gold)}
.vp-stat span{font-size:0.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em}

.vp-links{max-width:600px;margin:0 auto;padding:0 5%;display:grid;gap:0.85rem}
.vp-link-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.1rem 1.4rem;
  display:flex;align-items:center;gap:1rem;text-decoration:none;color:var(--text);transition:all 0.2s}
.vp-link-card:hover{border-color:var(--border-gold);transform:translateX(4px)}
.vp-link-icon{font-size:1.5rem;width:42px;height:42px;background:var(--gold-soft);border-radius:10px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0}
.vp-link-text{flex:1}
.vp-link-text strong{display:block;font-size:0.92rem;margin-bottom:0.15rem}
.vp-link-text span{font-size:0.75rem;color:var(--muted)}
.vp-link-arrow{color:var(--gold);font-size:1.1rem}

.vp-ecosystem{max-width:600px;margin:3rem auto 0;padding:0 5%}
.vp-eco-title{text-align:center;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;
  color:var(--muted);margin-bottom:1.25rem}
.vp-eco-tree{display:flex;flex-direction:column;align-items:center;gap:0.6rem}
.vp-eco-root{background:var(--gold);color:#0A0A0A;font-weight:800;font-family:'Space Grotesk',sans-serif;
  padding:0.6rem 1.4rem;border-radius:10px;font-size:0.95rem;box-shadow:0 0 24px var(--gold-glow)}
.vp-eco-branch{display:flex;gap:0.6rem;flex-wrap:wrap;justify-content:center}
.vp-eco-node{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.5rem 1rem;
  font-size:0.78rem;color:var(--muted)}
.vp-eco-node.gold{border-color:var(--border-gold);color:var(--gold)}
</style>
</head>
<body>
''' + NAVBAR + '''

<section class="vp-hero">
  <span class="vp-badge">✓ Verified Ecosystem</span>
  <h1 class="vp-title">VALCORE <span>&lt;/&gt;</span></h1>
  <p class="vp-tagline">{{ site_description }}</p>

  <div class="vp-stats">
    <div class="vp-stat"><strong>{{ total_products }}+</strong><span>Products</span></div>
    <div class="vp-stat"><strong>{{ total_customers }}+</strong><span>Customers</span></div>
    <div class="vp-stat"><strong>{{ total_purchases }}+</strong><span>Purchases</span></div>
  </div>
</section>

<div class="vp-links">
  {% if founder_website %}
  <a href="{{ founder_website }}" target="_blank" class="vp-link-card">
    <div class="vp-link-icon">&#128100;</div>
    <div class="vp-link-text"><strong>Founder Website</strong><span>Meet the developer behind VALCORE</span></div>
    <span class="vp-link-arrow">&rarr;</span>
  </a>
  {% endif %}
  {% if discord_server %}
  <a href="{{ discord_server }}" target="_blank" class="vp-link-card">
    <div class="vp-link-icon">&#127918;</div>
    <div class="vp-link-text"><strong>Discord Community</strong><span>Join the conversation, get support</span></div>
    <span class="vp-link-arrow">&rarr;</span>
  </a>
  {% endif %}
  <a href="/appointment" class="vp-link-card">
    <div class="vp-link-icon">&#128197;</div>
    <div class="vp-link-text"><strong>Book an Appointment</strong><span>Need something custom built?</span></div>
    <span class="vp-link-arrow">&rarr;</span>
  </a>
  {% if support_email %}
  <a href="mailto:{{ support_email }}" class="vp-link-card">
    <div class="vp-link-icon">&#128172;</div>
    <div class="vp-link-text"><strong>Contact Support</strong><span>Questions about an order or product</span></div>
    <span class="vp-link-arrow">&rarr;</span>
  </a>
  {% endif %}
  <a href="/" class="vp-link-card">
    <div class="vp-link-icon">&#128722;</div>
    <div class="vp-link-text"><strong>Browse the Store</strong><span>Explore all VALCORE products</span></div>
    <span class="vp-link-arrow">&rarr;</span>
  </a>
</div>

<div class="vp-ecosystem">
  <div class="vp-eco-title">The Ecosystem</div>
  <div class="vp-eco-tree">
    <div class="vp-eco-root">VALCORE &lt;/&gt;</div>
    <div class="vp-eco-branch">
      <div class="vp-eco-node gold">Commerce Engine</div>
      <div class="vp-eco-node gold">Kel HQ</div>
      <div class="vp-eco-node">Future Systems</div>
    </div>
  </div>
</div>

''' + FOOTER + SCRIPT_TAG + '''
</body>
</html>
'''


@storefront_bp.route('/valcore')
def valcore_profile():
    db = get_db()
    total_products = db.execute(
        "SELECT COUNT(*) as c FROM products WHERE status='live' AND deleted_at IS NULL"
    ).fetchone()['c']
    total_customers = db.execute('SELECT COUNT(*) as c FROM users WHERE is_admin=0').fetchone()['c']
    total_purchases = db.execute(
        "SELECT COUNT(*) as c FROM purchases WHERE status='completed'"
    ).fetchone()['c']
    db.close()

    return render_template_string(
        VALCORE_PAGE,
        site_description=get_setting('site_description', 'Digital products, templates, and automation systems.'),
        founder_website=get_setting('founder_website', ''),
        discord_server=get_setting('discord_server', ''),
        support_email=get_setting('support_email', ''),
        total_products=total_products,
        total_customers=total_customers,
        total_purchases=total_purchases,
        session_user=session.get('user_id'),
        session_username=session.get('username', ''),
    )


# ============================================
#   APPOINTMENT BOOKING
# ============================================

APPOINTMENT_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head><title>Book Appointment — VALCORE</title>''' + HEAD + '''</head>
<body>
''' + NAVBAR + '''

<div class="product-page" style="max-width:520px">
  <h1 class="pp-name">Book an Appointment</h1>
  <p class="pp-desc">Products not to your liking? Tell us what you need and we'll build it for you. &#127801;</p>

  <form id="apptForm" onsubmit="submitAppointment(event)" style="display:flex;flex-direction:column;gap:1rem;margin-top:1rem">
    <input type="text" id="apptName" placeholder="Your name" required
      style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"/>
    <input type="text" id="apptContact" placeholder="WhatsApp / Telegram / Email" required
      style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"/>
    <input type="text" id="apptType" placeholder="What kind of project?"
      style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"/>
    <textarea id="apptMessage" rows="4" placeholder="Tell us more..."
      style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:0.75rem 1rem;color:var(--text);font-family:Inter,sans-serif"></textarea>
    <button type="submit" class="btn btn-gold">Send Request &#128640;</button>
    <p id="apptNote" style="font-size:0.8rem"></p>
  </form>
</div>

''' + FOOTER + SCRIPT_TAG + '''
<script>
function submitAppointment(e) {
  e.preventDefault();
  var note = document.getElementById('apptNote');
  note.textContent = 'Sending...';
  note.style.color = 'var(--muted)';
  xhrPost('/api/appointment/book', {
    name: document.getElementById('apptName').value,
    contact: document.getElementById('apptContact').value,
    project_type: document.getElementById('apptType').value,
    message: document.getElementById('apptMessage').value,
  }, function(res) {
    if (res && res.ok) {
      note.textContent = '✓ Request sent! We will reach out shortly.';
      note.style.color = 'var(--green)';
      document.getElementById('apptForm').reset();
    } else {
      note.textContent = 'Something went wrong. Try again.';
      note.style.color = 'var(--red)';
    }
  });
}
</script>
</body>
</html>
'''


@storefront_bp.route('/appointment')
def appointment_page():
    return render_template_string(APPOINTMENT_PAGE, session_user=session.get('user_id'), session_username=session.get('username', ''))


@storefront_bp.route('/api/appointment/book', methods=['POST'])
def book_appointment():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    contact = data.get('contact', '').strip()

    if not name or not contact:
        return jsonify({'ok': False, 'error': 'Name and contact required'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO appointments (user_id, name, contact, project_type, message) VALUES (?,?,?,?,?)',
        (session.get('user_id'), name, contact, data.get('project_type', ''), data.get('message', ''))
    )
    db.execute(
        "INSERT INTO activity_log (type, summary) VALUES ('appointment', ?)",
        (f'{name} booked an appointment',)
    )
    db.commit()
    db.close()

    notify_appointment(name, data.get('project_type', ''))

    return jsonify({'ok': True})
