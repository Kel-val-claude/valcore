// ============================================
//   VALCORE — STOREFRONT JS
//   frontend/js/store.js
//   Uses XHR (not fetch) — proven pattern from
//   Kel HQ that works on mobile without internet quirks
// ============================================

function xhrGet(url, callback) {
  var req = new XMLHttpRequest();
  req.open('GET', url, true);
  req.withCredentials = true;
  req.onreadystatechange = function() {
    if (req.readyState === 4) {
      try { callback(JSON.parse(req.responseText)); }
      catch (e) { callback(null); }
    }
  };
  req.send();
}

function xhrPost(url, data, callback) {
  var req = new XMLHttpRequest();
  req.open('POST', url, true);
  req.withCredentials = true;
  req.setRequestHeader('Content-Type', 'application/json');
  req.onreadystatechange = function() {
    if (req.readyState === 4) {
      try { callback(JSON.parse(req.responseText)); }
      catch (e) { callback(null); }
    }
  };
  req.send(JSON.stringify(data || {}));
}

// ============================================
//   MOBILE MENU DRAWER
// ============================================
(function() {
  var menuBtn = document.getElementById('menuBtn');
  var drawer  = document.getElementById('menuDrawer');
  var overlay = document.getElementById('menuOverlay');

  if (menuBtn && drawer && overlay) {
    menuBtn.addEventListener('click', function() {
      drawer.classList.add('open');
      overlay.classList.add('open');
    });
    overlay.addEventListener('click', function() {
      drawer.classList.remove('open');
      overlay.classList.remove('open');
    });
  }
})();

// ============================================
//   COLLECTIONS HORIZONTAL SCROLL — refresh button
// ============================================
function refreshCollection(slug) {
  var grid = document.getElementById('collectionGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loading-state">Refreshing...</div>';
  xhrGet('/api/products?collection=' + encodeURIComponent(slug) + '&shuffle=1', function(data) {
    renderProductGrid(grid, data);
  });
}

// ============================================
//   SEARCH — pressing enter or tapping search icon
// ============================================
function doSearch() {
  var input = document.getElementById('searchInput');
  if (!input) return;
  var q = input.value.trim();
  if (q) window.location.href = '/search?q=' + encodeURIComponent(q);
}

(function() {
  var searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doSearch();
    });
  }
  var searchBtn = document.getElementById('searchBtn');
  if (searchBtn) searchBtn.addEventListener('click', doSearch);
})();

// ============================================
//   PRODUCT GRID RENDERER (used by search/refresh/dynamic loads)
// ============================================
function renderProductGrid(container, products) {
  if (!products || !products.length) {
    container.innerHTML = '<div class="empty-state">No products found.</div>';
    return;
  }
  container.innerHTML = products.map(function(p) {
    var price = p.price || 0;
    var promo = p.promo_percent || 0;
    var displayPrice = promo > 0 ? Math.round(price - (price * promo / 100)) : price;
    var priceHtml = '<span class="product-price">₦' + displayPrice.toLocaleString() + '</span>';
    if (promo > 0) {
      priceHtml += '<span class="product-compare">₦' + price.toLocaleString() + '</span>';
    }
    var badge = promo > 0 ? '<div class="product-badge promo">-' + promo + '%</div>' : '';
    return '<a href="/product/' + p.slug + '" class="product-card">' +
      badge +
      '<div class="product-img">📦</div>' +
      '<div class="product-info">' +
        '<span class="product-cat">' + (p.category_name || 'Product') + '</span>' +
        '<div class="product-name">' + p.name + '</div>' +
        '<div class="product-rating"><span class="stars">★</span> ' + (p.rating_avg || 0).toFixed(1) + ' (' + (p.rating_count || 0) + ')</div>' +
        '<div class="product-price-row">' + priceHtml + '</div>' +
      '</div>' +
    '</a>';
  }).join('');
}

// ============================================
//   WISHLIST TOGGLE (product page)
// ============================================
function toggleWishlist(productId, btn) {
  xhrPost('/account/wishlist/toggle', { product_id: productId }, function(res) {
    if (!res) return;
    if (res.added) {
      btn.textContent = '♥';
      btn.style.color = 'var(--red)';
    } else {
      btn.textContent = '♡';
      btn.style.color = 'var(--muted)';
    }
  });
}


// ============================================
//   BUY NOW / QUICK PURCHASE
//   Valcore is a direct-purchase store — no cart.
//   This triggers checkout directly or redirects
//   to the product page if not on it already.
// ============================================
// ============================================
//   ADD TO CART — real, wired to /account/cart/add
//   Valcore supports both:
//     - Buy Now: instant single-product checkout
//     - Add to Cart: batches into the cart shown
//       on the account dashboard, checked out
//       together via /checkout/start-cart
// ============================================
function addToCart(productId, btnEl) {
  if (!btnEl) return;
  const original = btnEl.innerHTML;
  btnEl.disabled = true;
  btnEl.style.opacity = '0.6';

  fetch('/account/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId })
  })
  .then(r => {
    if (r.status === 401 || r.status === 403) {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
      return null;
    }
    return r.json();
  })
  .then(data => {
    if (!data) return;
    btnEl.disabled = false;
    btnEl.style.opacity = '';

    if (data.ok) {
      btnEl.innerHTML = data.already_in_cart ? '&#10003; In Cart' : '&#10003; Added!';
      updateCartBadge(data.cart_count);
      setTimeout(() => { btnEl.innerHTML = original; }, 1600);
    } else {
      btnEl.innerHTML = original;
      if (data.error) showToast(data.error);
    }
  })
  .catch(() => {
    btnEl.disabled = false;
    btnEl.style.opacity = '';
    btnEl.innerHTML = original;
  });
}

function updateCartBadge(count) {
  document.querySelectorAll('.cart-badge, [data-cart-count]').forEach(el => {
    el.textContent = count;
    el.style.display = count > 0 ? '' : 'none';
  });
}

function showToast(msg) {
  let toast = document.getElementById('vcToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'vcToast';
    toast.style.cssText = 'position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);' +
      'background:#1A1A1A;color:#F0F0F0;border:1px solid rgba(212,175,55,0.3);padding:0.7rem 1.2rem;' +
      'border-radius:8px;font-size:0.82rem;z-index:9999;opacity:0;transition:opacity 0.25s;max-width:90vw;text-align:center';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toast.style.opacity = '0'; }, 2400);
}

// ============================================
//   RECENTLY VIEWED — session-based
// ============================================
const RV_KEY = 'vc_recently_viewed';
const RV_MAX = 4;

function getRV() {
  try { return JSON.parse(sessionStorage.getItem(RV_KEY) || '[]'); } catch(e) { return []; }
}

function saveRV(list) {
  try { sessionStorage.setItem(RV_KEY, JSON.stringify(list)); } catch(e) {}
}

function trackProductView(product) {
  // Call this on product page with product data
  if (!product || !product.id) return;
  let list = getRV();
  list = list.filter(p => p.id !== product.id);
  list.unshift(product);
  if (list.length > RV_MAX) list = list.slice(0, RV_MAX);
  saveRV(list);
}

function renderRecentlyViewed() {
  const section = document.getElementById('recentlyViewedSection');
  const grid = document.getElementById('recentlyViewedGrid');
  if (!section || !grid) return;

  const list = getRV();
  if (!list.length) return;

  section.style.display = '';
  grid.innerHTML = list.map(p => `
    <a href="/product/${p.slug}" class="product-card">
      <div class="product-img">${p.emoji || '📦'}</div>
      <div class="product-info">
        <div class="product-name">${p.name}</div>
        <div class="product-price-row">
          <span class="product-price">&#8358;${Number(p.display_price).toLocaleString('en-NG')}</span>
        </div>
        <div style="display:flex;gap:0.4rem;margin-top:0.5rem">
          <span class="btn btn-gold" style="flex:1;font-size:0.78rem;padding:0.45rem 0;text-align:center;display:block">
            Buy Now &rarr;
          </span>
          <button class="btn btn-outline" style="flex:0 0 38px;padding:0.45rem 0;font-size:0.85rem"
            onclick="event.preventDefault();event.stopPropagation();addToCart(${p.id}, this)" title="Add to Cart">&#128722;</button>
        </div>
      </div>
    </a>
  `).join('');
}

function clearRecentlyViewed() {
  saveRV([]);
  const section = document.getElementById('recentlyViewedSection');
  if (section) section.style.display = 'none';
}

// Show deals section if products exist
(function() {
  const dealsSection = document.getElementById('dealsSection');
  if (dealsSection) {
    const cards = dealsSection.querySelectorAll('.product-card');
    if (cards.length > 0) dealsSection.style.display = '';
  }
  // Render recently viewed on home page
  renderRecentlyViewed();

  // Populate cart badge in the drawer — only fires for logged-in users
  // (the menu-user-card only renders server-side when session_user is set)
  document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.menu-user-card')) {
      fetch('/account/cart/count')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data && data.ok) updateCartBadge(data.cart_count);
        })
        .catch(() => {});
    }
  });
})();
