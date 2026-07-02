# ============================================
#   VALCORE — SHARED LAYOUT
#   app/core/layout.py
#
#   Single source of truth for NAVBAR, FOOTER, HEAD,
#   SCRIPT_TAG. Every page in every route file
#   (storefront, account, checkout) imports these
#   instead of rolling its own — this is the fix
#   for the "menu bar missing on some pages" bug:
#   there was no shared component before, so each
#   file's pages could silently drift out of sync.
#
#   Any page using NAVBAR must pass these to
#   render_template_string:
#     session_user      (session.get('user_id'))
#     session_username   (session.get('username', ''))
# ============================================

NAVBAR = '''
<nav class="navbar">
  <button class="nav-menu-btn" id="menuBtn">&#9776;</button>

  <a href="/" class="nav-logo-img-wrap">
    <span class="nav-logo">VALCORE <span>&lt;/&gt;</span></span>
  </a>

  <div class="nav-right-group">
    {% if session_user %}
    <a href="/cart" class="nav-cart-link" title="Cart">
      &#128722;<span class="cart-count-badge" id="cartCountBadge" style="display:none">0</span>
    </a>
    <a href="/valcore" class="nav-avatar" title="VALCORE Profile">
      <img src="/assets/logo.png" alt="VALCORE" class="nav-logo-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" style="width:100%; height:100%; border-radius:inherit; object-fit:cover;"/>
      <span class="nav-logo-fallback" style="display:none">&#9889;</span>
    </a>
    {% else %}
    <a href="/login" class="btn btn-gold" style="font-size:0.78rem;padding:0.45rem 1rem">Sign In</a>
    {% endif %}
  </div>
</nav>

<div class="menu-overlay" id="menuOverlay"></div>
<div class="menu-drawer" id="menuDrawer">
  <a href="/">&#127968; Home</a>
  <a href="/search">&#128269; Search</a>
  <a href="/valcore">&#9889; VALCORE Profile</a>
  <a href="/appointment">&#128197; Book Appointment</a>
  {% if session_user %}
  <a href="/cart">&#128722; Cart</a>
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
