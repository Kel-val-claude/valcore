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
//   ADD TO CART
// ============================================
function addToCart(productId, productName, price, btnEl) {
  if (!btnEl) return;
  const original = btnEl.textContent;
  btnEl.textContent = 'Adding...';
  btnEl.classList.add('btn-adding');

  fetch('/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId, quantity: 1 })
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok || data.success) {
      btnEl.textContent = '✓ Added!';
      btnEl.classList.remove('btn-adding');
      btnEl.classList.add('btn-added');
      // Update cart badge if present
      const badge = document.querySelector('.cart-count, .cart-badge, [data-cart-count]');
      if (badge && data.cart_count !== undefined) {
        badge.textContent = data.cart_count;
      }
      setTimeout(() => {
        btnEl.textContent = original;
        btnEl.classList.remove('btn-added');
      }, 1800);
    } else {
      // Not logged in or error — redirect to login
      if (data.redirect) {
        window.location.href = data.redirect;
      } else {
        btnEl.textContent = original;
        btnEl.classList.remove('btn-adding');
      }
    }
  })
  .catch(() => {
    btnEl.textContent = original;
    btnEl.classList.remove('btn-adding');
  });
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
          <span class="product-price">₦${Number(p.display_price).toLocaleString('en-NG')}</span>
        </div>
        <button class="btn btn-gold" style="width:100%;margin-top:0.5rem;font-size:0.78rem;padding:0.45rem 0"
          onclick="event.preventDefault();addToCart(${p.id}, '${p.name.replace(/'/g,"\\'")}', ${p.display_price}, this)">+ Add to Cart</button>
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
})();
