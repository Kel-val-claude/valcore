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
