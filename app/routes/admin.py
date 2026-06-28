# ============================================
#   VALCORE — ADMIN DASHBOARD
#   app/routes/admin.py
#
#   Built using the PROVEN Kel HQ pattern:
#   - Server-side rendered stats (no fetch dependency for core numbers)
#   - XHR (not fetch) for all dynamic actions — works on mobile w/o internet quirks
#   - data-section nav with addEventListener — no inline onclick fragility
#   - Mobile topbar + overlay sidebar from day one
# ============================================

from flask import Blueprint, render_template_string, session, jsonify, request
from app.core.database import get_db, get_all_settings, set_setting
from app.core.auth import admin_required, log_audit, hash_password

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ADMIN_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>VALCORE Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0A0A0A;--surface:#111;--card:#141414;
  --border:rgba(255,255,255,0.06);--gold:#D4AF37;
  --gold-soft:rgba(212,175,55,0.08);--text:#F0F0F0;
  --muted:#666;--green:#2ECC71;--red:#E74C3C;--yellow:#F1C40F
}
body{background:var(--bg);color:var(--text);font-family:Inter,sans-serif;font-size:14px}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:100vh}
.sidebar{background:var(--surface);border-right:1px solid var(--border);padding:1.25rem 0.75rem;
  position:fixed;top:0;left:0;height:100vh;width:220px;overflow-y:auto;
  display:flex;flex-direction:column;gap:2px;z-index:50;transition:left 0.28s ease}
.sidebar-logo{font-size:1.05rem;font-weight:700;color:var(--gold);margin-bottom:1.25rem;padding:0 0.5rem}
.nav-item{display:block;width:100%;padding:0.6rem 0.75rem;border-radius:8px;cursor:pointer;
  font-size:0.82rem;font-weight:500;color:var(--muted);background:none;border:none;text-align:left;transition:all 0.18s}
.nav-item:hover,.nav-item.active{background:var(--gold-soft);color:var(--gold)}
.nav-divider{height:1px;background:var(--border);margin:0.5rem 0}
.logout-link{display:block;margin-top:auto;padding:0.6rem 0.75rem;background:rgba(231,76,60,0.08);
  border:1px solid rgba(231,76,60,0.15);border-radius:8px;color:#E74C3C;font-size:0.78rem;font-weight:600;
  text-decoration:none;text-align:center}
.main{margin-left:220px;padding:1.5rem;min-height:100vh}
.page-header{margin-bottom:1.5rem}
.page-header h1{font-size:1.4rem;font-weight:700;margin-bottom:0.2rem}
.page-header p{font-size:0.78rem;color:var(--muted)}
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem}
.stat-box strong{display:block;font-size:1.6rem;font-weight:700;color:var(--gold);margin-bottom:0.2rem}
.stat-box span{font-size:0.7rem;color:var(--muted)}
.panel{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.25rem;margin-bottom:1rem}
.panel-title{font-size:0.85rem;font-weight:700;margin-bottom:0.85rem;display:flex;align-items:center;justify-content:space-between}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:0.78rem;min-width:400px}
th{text-align:left;padding:0.5rem 0.6rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);
  text-transform:uppercase;font-size:0.62rem;letter-spacing:0.06em}
td{padding:0.6rem 0.6rem;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
.badge{font-size:0.6rem;font-weight:700;padding:0.15rem 0.5rem;border-radius:4px;text-transform:uppercase;display:inline-block}
.bg{background:rgba(46,204,113,0.1);color:var(--green)}
.by{background:rgba(241,196,15,0.08);color:var(--yellow)}
.br{background:rgba(231,76,60,0.08);color:var(--red)}
.bo{background:var(--gold-soft);color:var(--gold);border:1px solid rgba(212,175,55,0.2)}
.form-group{margin-bottom:0.85rem}
.form-group label{display:block;font-size:0.7rem;color:var(--muted);margin-bottom:0.3rem;font-weight:600;
  text-transform:uppercase;letter-spacing:0.05em}
.form-group input,.form-group select,.form-group textarea{width:100%;background:var(--bg);
  border:1px solid var(--border);border-radius:7px;padding:0.6rem 0.8rem;color:var(--text);
  font-family:Inter,sans-serif;font-size:0.82rem;outline:none}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:0.85rem}
.btn{display:inline-block;padding:0.55rem 1.1rem;border-radius:7px;font-size:0.78rem;font-weight:600;
  cursor:pointer;border:none;font-family:Inter,sans-serif}
.btn-gold{background:var(--gold);color:#0A0A0A}
.btn-gold:hover{background:#c9a227}
.btn-danger{background:rgba(231,76,60,0.1);color:var(--red);border:1px solid rgba(231,76,60,0.2)}
.btn-sm{padding:0.28rem 0.65rem;font-size:0.7rem}
.section{display:none}
.section.active{display:block}
.toast{position:fixed;bottom:20px;right:20px;background:var(--gold);color:#0A0A0A;padding:0.6rem 1.1rem;
  border-radius:8px;font-size:0.82rem;font-weight:700;opacity:0;transform:translateY(10px);
  transition:all 0.25s;pointer-events:none;z-index:9999}
.toast.show{opacity:1;transform:translateY(0)}
.topbar{display:none;position:fixed;top:0;left:0;right:0;height:50px;background:var(--surface);
  border-bottom:1px solid var(--border);align-items:center;justify-content:space-between;padding:0 1rem;z-index:200}
.topbar-menu{background:none;border:none;color:var(--gold);font-size:1.5rem;cursor:pointer;padding:0.3rem}
.topbar-title{font-size:0.9rem;font-weight:700}
.topbar-logout{color:var(--muted);text-decoration:none;font-size:0.8rem}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:49}
.overlay.open{display:block}
@media(max-width:900px){
  .topbar{display:flex}
  .layout{grid-template-columns:1fr}
  .sidebar{left:-240px}
  .sidebar.open{left:0}
  .main{margin-left:0;padding:1rem;margin-top:54px}
  .stat-row{grid-template-columns:1fr 1fr}
  .form-row{grid-template-columns:1fr}
}
</style>
</head>
<body>

<div class="topbar">
  <button class="topbar-menu" id="menuBtn">&#9776;</button>
  <span class="topbar-title">VALCORE Admin</span>
  <a class="topbar-logout" href="/logout">Logout</a>
</div>
<div class="overlay" id="overlay"></div>

<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-logo">VALCORE &lt;/&gt;</div>
    <a href="/" target="_blank" class="nav-item" style="color:var(--green);margin-bottom:0.5rem">&#127968; View Store</a>
    <button class="nav-item active" data-section="dashboard">&#127968; Dashboard</button>
    <button class="nav-item" data-section="products">&#128230; Products</button>
    <button class="nav-item" data-section="collections">&#128193; Collections</button>
    <button class="nav-item" data-section="users">&#128101; Users</button>
    <button class="nav-item" data-section="orders">&#128176; Purchases</button>
    <button class="nav-item" data-section="analytics">&#128202; Analytics</button>
    <button class="nav-item" data-section="support">&#128172; Support</button>
    <button class="nav-item" data-section="appointments">&#128197; Appointments</button>
    <button class="nav-item" data-section="questions">&#10067; Product Q&amp;A</button>
    <div class="nav-divider"></div>
    <button class="nav-item" data-section="settings">&#128279; Settings</button>
    <button class="nav-item" data-section="audit">&#128272; Audit Log</button>
    <div class="nav-divider"></div>
    <a class="logout-link" href="/logout">&#9211; Logout</a>
  </aside>

  <main class="main">
    <div id="sec-dashboard" class="section active">
      <div class="page-header">
        <h1>VALCORE Dashboard</h1>
        <p>Welcome back, {{ username }}</p>
      </div>
      <div class="stat-row">
        <div class="stat-box"><strong>{{ stats.total_products }}</strong><span>Total Products</span></div>
        <div class="stat-box"><strong>{{ stats.total_users }}</strong><span>Total Customers</span></div>
        <div class="stat-box"><strong>{{ stats.pending_tickets }}</strong><span>Pending Tickets</span></div>
        <div class="stat-box"><strong>{{ stats.pending_appointments }}</strong><span>Pending Appointments</span></div>
      </div>
      <div class="panel">
        <div class="panel-title">Recent Activity</div>
        {% if activity %}
          {% for a in activity %}
          <div style="padding:0.5rem 0;border-bottom:1px solid var(--border);font-size:0.8rem">
            <strong>{{ a.type }}</strong> — {{ a.summary }}
            <div style="color:var(--muted);font-size:0.65rem">{{ a.created_at }}</div>
          </div>
          {% endfor %}
        {% else %}
          <p style="color:var(--muted);font-size:0.78rem">No activity yet.</p>
        {% endif %}
      </div>
    </div>

    <div id="sec-products" class="section">
      <div class="page-header"><h1>Products</h1><p>Add, edit, and manage your catalog</p></div>
      <div class="panel">
        <div class="panel-title">
          Products
          <button class="btn btn-gold btn-sm" onclick="openProductForm()">+ Add Product</button>
        </div>

        <div id="productFormWrap" style="display:none;margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)">
          <input type="hidden" id="pf-id" value=""/>
          <div class="form-row">
            <div class="form-group"><label>Name</label><input type="text" id="pf-name" placeholder="Product name"/></div>
            <div class="form-group"><label>Collection</label>
              <select id="pf-collection"></select>
            </div>
          </div>
          <div class="form-group"><label>Short Description</label><input type="text" id="pf-short" placeholder="One-line summary"/></div>
          <div class="form-group"><label>Full Description</label><textarea id="pf-desc" rows="3" placeholder="Full description"></textarea></div>

          <div class="form-row">
            <div class="form-group"><label>Price (₦)</label><input type="number" id="pf-price" placeholder="5000"/></div>
            <div class="form-group"><label>Compare Price (₦, optional)</label><input type="number" id="pf-compare" placeholder="7000"/></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Gain Price (₦, your cut)</label><input type="number" id="pf-gain" placeholder="4500"/></div>
            <div class="form-group"><label>Promo % (0-100)</label><input type="number" id="pf-promo" placeholder="0" min="0" max="100"/></div>
          </div>

          <div class="form-row">
            <div class="form-group"><label>Delivery Type</label>
              <select id="pf-delivery">
                <option value="zip">ZIP File</option>
                <option value="github">GitHub Repo</option>
                <option value="both">ZIP + GitHub</option>
                <option value="external">External Link</option>
              </select>
            </div>
            <div class="form-group"><label>Status</label>
              <select id="pf-status">
                <option value="draft">Draft</option>
                <option value="live">Live</option>
                <option value="hidden">Hidden</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div class="form-group"><label>GitHub Repo URL (if applicable)</label><input type="text" id="pf-github" placeholder="https://github.com/..."/></div>

          <div class="form-group">
            <label>Product Images (up to 10)</label>
            <input type="file" id="pf-images" multiple accept="image/*" onchange="handleImageSelect(event)"/>
            <div id="pf-image-preview" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.6rem"></div>
            <p id="pf-image-note" style="font-size:0.7rem;color:var(--muted);margin-top:0.4rem"></p>
          </div>

          <div class="form-group">
            <label>ZIP File (if delivery type includes ZIP)</label>
            <input type="file" id="pf-zip" accept=".zip" onchange="handleZipSelect(event)"/>
            <p id="pf-zip-note" style="font-size:0.7rem;color:var(--muted);margin-top:0.4rem"></p>
          </div>

          <div class="form-row">
            <button class="btn btn-gold" onclick="saveProduct()">Save Product</button>
            <button class="btn btn-danger" onclick="closeProductForm()">Cancel</button>
          </div>
          <p id="pf-note" style="font-size:0.78rem;margin-top:0.5rem"></p>
        </div>

        <div class="tbl-wrap"><table>
          <thead><tr><th>Name</th><th>Collection</th><th>Price</th><th>Status</th><th>Views</th><th>Action</th></tr></thead>
          <tbody id="productsBody"><tr><td colspan="6" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-collections" class="section">
      <div class="page-header"><h1>Collections</h1></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Name</th><th>Slug</th><th>Active</th></tr></thead>
          <tbody id="collectionsBody"><tr><td colspan="3" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-users" class="section">
      <div class="page-header"><h1>Users</h1><p>Phase 3+ builds full customer detail view.</p></div>
      <div class="panel"><p style="color:var(--muted);font-size:0.82rem">Coming soon.</p></div>
    </div>

    <div id="sec-orders" class="section">
      <div class="page-header"><h1>Purchases</h1><p>All completed transactions</p></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Product</th><th>Customer</th><th>Amount</th><th>Status</th><th>License</th><th>Date</th></tr></thead>
          <tbody id="purchasesBody"><tr><td colspan="6" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-analytics" class="section">
      <div class="page-header"><h1>Analytics</h1><p>Revenue and growth at a glance</p></div>
      <div class="stat-row">
        <div class="stat-box"><strong id="an-revenue-today">-</strong><span>Revenue Today</span></div>
        <div class="stat-box"><strong id="an-revenue-week">-</strong><span>Revenue This Week</span></div>
        <div class="stat-box"><strong id="an-revenue-month">-</strong><span>Revenue This Month</span></div>
        <div class="stat-box"><strong id="an-revenue-total">-</strong><span>Total Revenue</span></div>
      </div>
      <div class="stat-row">
        <div class="stat-box"><strong id="an-customers">-</strong><span>Total Customers</span></div>
        <div class="stat-box"><strong id="an-purchases">-</strong><span>Total Purchases</span></div>
        <div class="stat-box"><strong id="an-avg-order">-</strong><span>Avg Order Value</span></div>
        <div class="stat-box"><strong id="an-conversion">-</strong><span>Visitor &rarr; Buyer %</span></div>
      </div>
      <div class="panel">
        <div class="panel-title">Top Products</div>
        <div class="tbl-wrap"><table>
          <thead><tr><th>Product</th><th>Purchases</th><th>Revenue</th><th>Rating</th></tr></thead>
          <tbody id="topProductsBody"><tr><td colspan="4" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-support" class="section">
      <div class="page-header"><h1>Support Tickets</h1><p>Reply to customer tickets, mark as resolved</p></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Subject</th><th>Customer</th><th>Status</th><th>Date</th><th>Action</th></tr></thead>
          <tbody id="ticketsBody"><tr><td colspan="5" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
      <div id="ticketDetailPanel" class="panel" style="display:none;max-width:560px">
        <div class="panel-title">
          <span id="td-subject"></span>
          <button class="btn btn-sm btn-danger" onclick="closeTicketDetail()">✕ Close</button>
        </div>
        <p style="font-size:0.78rem;color:var(--muted);margin-bottom:0.5rem">From: <span id="td-customer"></span></p>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:1rem;margin-bottom:1rem">
          <p id="td-message" style="font-size:0.85rem;line-height:1.7"></p>
        </div>
        <div class="form-group"><label>Reply</label><textarea id="td-reply" rows="3" placeholder="Type your reply..."></textarea></div>
        <div class="form-row">
          <button class="btn btn-gold" onclick="sendTicketReply()">Send Reply &amp; Mark Resolved</button>
          <button class="btn btn-outline" onclick="markTicketStatus('pending')">Mark Pending</button>
        </div>
        <p id="td-note" style="font-size:0.75rem;color:var(--green);margin-top:0.5rem"></p>
      </div>
    </div>

    <div id="sec-appointments" class="section">
      <div class="page-header"><h1>Appointments</h1><p>Manage booking requests</p></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Name</th><th>Contact</th><th>Project Type</th><th>Status</th><th>Date</th><th>Action</th></tr></thead>
          <tbody id="appointmentsBody"><tr><td colspan="6" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-questions" class="section">
      <div class="page-header"><h1>Product Q&amp;A</h1><p>Answer customer questions — public on the product page</p></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Product</th><th>Question</th><th>Answer</th><th>Status</th><th>Action</th></tr></thead>
          <tbody id="questionsBody"><tr><td colspan="5" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>

    <div id="sec-settings" class="section">
      <div class="page-header"><h1>Settings</h1><p>Discord webhook, Paystack keys, site config — all here.</p></div>
      <div class="panel" style="max-width:520px">
        <div class="panel-title">External Integrations</div>
        <div class="form-group"><label>Discord Webhook URL</label><input type="text" id="s-discord" placeholder="https://discord.com/api/webhooks/..."/></div>
        <div class="form-group"><label>Discord Server Invite</label><input type="text" id="s-discord-server" placeholder="https://discord.gg/..."/></div>
        <div class="form-group"><label>Paystack Public Key</label><input type="text" id="s-pk" placeholder="pk_live_..."/></div>
        <div class="form-group"><label>Paystack Secret Key</label><input type="password" id="s-sk" placeholder="sk_live_..."/></div>
      </div>
      <div class="panel" style="max-width:520px">
        <div class="panel-title">File Storage (Cloudflare R2)</div>
        <div class="form-group"><label>R2 Account ID</label><input type="text" id="s-r2-account"/></div>
        <div class="form-group"><label>R2 Access Key ID</label><input type="text" id="s-r2-key"/></div>
        <div class="form-group"><label>R2 Secret Access Key</label><input type="password" id="s-r2-secret"/></div>
        <div class="form-group"><label>R2 Bucket Name</label><input type="text" id="s-r2-bucket"/></div>
        <div class="form-group"><label>R2 Public URL</label><input type="text" id="s-r2-url" placeholder="https://pub-xxx.r2.dev"/></div>
      </div>
      <div class="panel" style="max-width:520px">
        <div class="panel-title">Site Info</div>
        <div class="form-group"><label>Site Name</label><input type="text" id="s-name"/></div>
        <div class="form-group"><label>Site Description</label><textarea id="s-desc" rows="2"></textarea></div>
        <div class="form-group"><label>Founder Website (Kel HQ)</label><input type="text" id="s-founder" placeholder="https://kel-hq.onrender.com"/></div>
        <div class="form-group"><label>Support Email</label><input type="text" id="s-email"/></div>
      </div>
      <button class="btn btn-gold" onclick="saveSettings()">&#128190; Save Settings</button>
      <p id="settingsNote" style="font-size:0.75rem;color:var(--green);margin-top:0.5rem"></p>
    </div>

    <div id="sec-audit" class="section">
      <div class="page-header"><h1>Audit Log</h1><p>Private security trail of admin actions.</p></div>
      <div class="panel">
        <div class="tbl-wrap"><table>
          <thead><tr><th>Action</th><th>IP</th><th>Time</th></tr></thead>
          <tbody id="auditBody"><tr><td colspan="3" style="color:var(--muted)">Loading...</td></tr></tbody>
        </table></div>
      </div>
    </div>
  </main>
</div>

<div class="toast" id="toast"></div>

<script>
var sections = document.querySelectorAll('.section');
var navBtns  = document.querySelectorAll('.nav-item[data-section]');

navBtns.forEach(function(btn) {
  btn.addEventListener('click', function() {
    var name = btn.getAttribute('data-section');
    sections.forEach(function(s) { s.classList.remove('active'); });
    var sec = document.getElementById('sec-' + name);
    if (sec) sec.classList.add('active');
    navBtns.forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    closeSidebar();
    loadSection(name);
  });
});

var sidebar = document.getElementById('sidebar');
var overlay = document.getElementById('overlay');
document.getElementById('menuBtn').addEventListener('click', function() {
  sidebar.classList.add('open'); overlay.classList.add('open');
});
overlay.addEventListener('click', closeSidebar);
function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('open'); }

function xhr(method, url, data, callback) {
  var req = new XMLHttpRequest();
  req.open(method, url, true);
  req.withCredentials = true;
  if (method === 'POST') req.setRequestHeader('Content-Type', 'application/json');
  req.onreadystatechange = function() {
    if (req.readyState === 4) {
      if (req.status === 401) { window.location.href = '/login'; return; }
      try { callback(JSON.parse(req.responseText)); } catch(e) { callback([]); }
    }
  };
  req.send(data ? JSON.stringify(data) : null);
}
function get(url, cb) { xhr('GET', url, null, cb); }
function post(url, data, cb) { xhr('POST', url, data, cb || function(){}); }

function toast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, 2500);
}

function loadSection(name) {
  if (name === 'products')      loadProducts();
  if (name === 'collections')   loadCollections();
  if (name === 'questions')     loadQuestions();
  if (name === 'orders')        loadPurchases();
  if (name === 'analytics')     loadAnalytics();
  if (name === 'support')       loadTickets();
  if (name === 'appointments')  loadAppointments();
  if (name === 'settings')      loadSettings();
  if (name === 'audit')         loadAudit();
}

// ============================================
//   PRODUCT MANAGEMENT
// ============================================
var pendingImageUrls = [];
var pendingZipUrl = '';

function loadProducts() {
  get('/admin/data/products', function(data) {
    var tbody = document.getElementById('productsBody');
    tbody.innerHTML = data.map(function(p) {
      return '<tr>' +
        '<td><strong>' + p.name + '</strong></td>' +
        '<td style="color:var(--muted)">' + (p.collection_name || '-') + '</td>' +
        '<td>₦' + (p.price || 0).toLocaleString() + '</td>' +
        '<td><span class="badge ' + (p.status==='live'?'bg':p.status==='hidden'?'by':p.status==='archived'?'br':'bo') + '">' + p.status + '</span></td>' +
        '<td style="color:var(--muted)">' + (p.views||0) + '</td>' +
        '<td><button class="btn btn-sm btn-gold" onclick="editProduct(' + p.id + ')">Edit</button> ' +
            '<button class="btn btn-sm btn-danger" onclick="deleteProduct(' + p.id + ')">Delete</button></td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="6" style="color:var(--muted);padding:0.8rem">No products yet.</td></tr>';
  });

  // Also populate collection dropdown
  get('/admin/data/collections', function(cols) {
    var sel = document.getElementById('pf-collection');
    sel.innerHTML = cols.map(function(c) {
      return '<option value="' + c.id + '">' + c.icon + ' ' + c.name + '</option>';
    }).join('');
  });
}

function openProductForm() {
  document.getElementById('pf-id').value = '';
  document.getElementById('pf-name').value = '';
  document.getElementById('pf-short').value = '';
  document.getElementById('pf-desc').value = '';
  document.getElementById('pf-price').value = '';
  document.getElementById('pf-compare').value = '';
  document.getElementById('pf-gain').value = '';
  document.getElementById('pf-promo').value = '0';
  document.getElementById('pf-delivery').value = 'zip';
  document.getElementById('pf-status').value = 'draft';
  document.getElementById('pf-github').value = '';
  document.getElementById('pf-note').textContent = '';
  document.getElementById('pf-image-preview').innerHTML = '';
  document.getElementById('pf-image-note').textContent = '';
  document.getElementById('pf-zip-note').textContent = '';
  pendingImageUrls = [];
  pendingZipUrl = '';
  document.getElementById('productFormWrap').style.display = 'block';
}

function closeProductForm() {
  document.getElementById('productFormWrap').style.display = 'none';
}

function editProduct(id) {
  get('/admin/data/product/' + id, function(p) {
    if (!p || !p.id) { toast('Could not load product'); return; }
    openProductForm();
    document.getElementById('pf-id').value = p.id;
    document.getElementById('pf-name').value = p.name || '';
    document.getElementById('pf-collection').value = p.collection_id || '';
    document.getElementById('pf-short').value = p.short_desc || '';
    document.getElementById('pf-desc').value = p.description || '';
    document.getElementById('pf-price').value = p.price || '';
    document.getElementById('pf-compare').value = p.compare_price || '';
    document.getElementById('pf-gain').value = p.gain_price || '';
    document.getElementById('pf-promo').value = p.promo_percent || 0;
    document.getElementById('pf-delivery').value = p.delivery_type || 'zip';
    document.getElementById('pf-status').value = p.status || 'draft';
    document.getElementById('pf-github').value = p.github_repo_url || '';
    pendingZipUrl = p.zip_file_url || '';
    if (pendingZipUrl) document.getElementById('pf-zip-note').textContent = 'Current file: ' + pendingZipUrl;
  });
}

function handleImageSelect(event) {
  var files = event.target.files;
  if (!files.length) return;
  if (files.length > 10) { toast('Max 10 images'); return; }

  var note = document.getElementById('pf-image-note');
  note.textContent = 'Uploading ' + files.length + ' image(s)...';
  pendingImageUrls = [];

  var uploaded = 0;
  Array.prototype.forEach.call(files, function(file) {
    var formData = new FormData();
    formData.append('file', file);
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/admin/upload/image', true);
    xhr.withCredentials = true;
    xhr.onreadystatechange = function() {
      if (xhr.readyState === 4) {
        uploaded++;
        try {
          var res = JSON.parse(xhr.responseText);
          if (res.ok) {
            pendingImageUrls.push(res.url);
            var preview = document.getElementById('pf-image-preview');
            preview.innerHTML += '<div style="width:50px;height:50px;background:var(--surface);border:1px solid var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:0.6rem;color:var(--green)">✓</div>';
          } else {
            note.textContent = res.error || 'Upload failed';
          }
        } catch(e) {}
        if (uploaded === files.length) {
          note.textContent = pendingImageUrls.length + ' image(s) ready.';
        }
      }
    };
    xhr.send(formData);
  });
}

function handleZipSelect(event) {
  var file = event.target.files[0];
  if (!file) return;

  var note = document.getElementById('pf-zip-note');
  note.textContent = 'Uploading...';

  var formData = new FormData();
  formData.append('file', file);
  var slug = (document.getElementById('pf-name').value || 'product').toLowerCase().replace(/[^a-z0-9]+/g, '-');
  formData.append('slug', slug);

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/admin/upload/zip', true);
  xhr.withCredentials = true;
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      try {
        var res = JSON.parse(xhr.responseText);
        if (res.ok) {
          pendingZipUrl = res.url;
          note.textContent = '✓ Uploaded: ' + file.name;
          note.style.color = 'var(--green)';
        } else {
          note.textContent = res.error || 'Upload failed';
          note.style.color = 'var(--red)';
        }
      } catch(e) {}
    }
  };
  xhr.send(formData);
}

function saveProduct() {
  var id = document.getElementById('pf-id').value;
  var payload = {
    name:            document.getElementById('pf-name').value,
    collection_id:   parseInt(document.getElementById('pf-collection').value) || null,
    short_desc:      document.getElementById('pf-short').value,
    description:     document.getElementById('pf-desc').value,
    price:           parseInt(document.getElementById('pf-price').value) || 0,
    compare_price:   parseInt(document.getElementById('pf-compare').value) || null,
    gain_price:      parseInt(document.getElementById('pf-gain').value) || null,
    promo_percent:   parseInt(document.getElementById('pf-promo').value) || 0,
    delivery_type:   document.getElementById('pf-delivery').value,
    status:          document.getElementById('pf-status').value,
    github_repo_url: document.getElementById('pf-github').value,
    zip_file_url:    pendingZipUrl,
    images:          pendingImageUrls,
  };

  if (!payload.name) { document.getElementById('pf-note').textContent = 'Name is required.'; return; }

  var url = id ? '/admin/update/product' : '/admin/add/product';
  if (id) payload.id = parseInt(id);

  post(url, payload, function(res) {
    if (res && res.ok) {
      toast(id ? '✓ Product updated!' : '✓ Product added!');
      closeProductForm();
      loadProducts();
    } else {
      document.getElementById('pf-note').textContent = (res && res.error) || 'Save failed.';
    }
  });
}

function deleteProduct(id) {
  if (!confirm('Delete this product? (Soft delete — existing buyers keep access)')) return;
  post('/admin/delete/product', {id: id}, function() {
    toast('Product deleted');
    loadProducts();
  });
}

function loadCollections() {
  get('/admin/data/collections', function(data) {
    var tbody = document.getElementById('collectionsBody');
    tbody.innerHTML = data.map(function(c) {
      return '<tr><td><strong>' + c.name + '</strong></td><td style="color:var(--muted)">' + c.slug + '</td>' +
        '<td><span class="badge ' + (c.active ? 'bg' : 'by') + '">' + (c.active ? 'Active' : 'Hidden') + '</span></td></tr>';
    }).join('') || '<tr><td colspan="3" style="color:var(--muted)">No collections.</td></tr>';
  });
}

function loadSettings() {
  get('/admin/data/settings', function(d) {
    document.getElementById('s-discord').value        = d.discord_webhook || '';
    document.getElementById('s-discord-server').value = d.discord_server || '';
    document.getElementById('s-pk').value              = d.paystack_public_key || '';
    document.getElementById('s-sk').value               = d.paystack_secret_key || '';
    document.getElementById('s-r2-account').value       = d.r2_account_id || '';
    document.getElementById('s-r2-key').value            = d.r2_access_key_id || '';
    document.getElementById('s-r2-secret').value         = d.r2_secret_access_key || '';
    document.getElementById('s-r2-bucket').value         = d.r2_bucket_name || '';
    document.getElementById('s-r2-url').value            = d.r2_public_url || '';
    document.getElementById('s-name').value             = d.site_name || '';
    document.getElementById('s-desc').value             = d.site_description || '';
    document.getElementById('s-founder').value          = d.founder_website || '';
    document.getElementById('s-email').value            = d.support_email || '';
  });
}

function saveSettings() {
  var payload = {
    discord_webhook:     document.getElementById('s-discord').value,
    discord_server:      document.getElementById('s-discord-server').value,
    paystack_public_key: document.getElementById('s-pk').value,
    paystack_secret_key: document.getElementById('s-sk').value,
    r2_account_id:        document.getElementById('s-r2-account').value,
    r2_access_key_id:     document.getElementById('s-r2-key').value,
    r2_secret_access_key: document.getElementById('s-r2-secret').value,
    r2_bucket_name:       document.getElementById('s-r2-bucket').value,
    r2_public_url:        document.getElementById('s-r2-url').value,
    site_name:           document.getElementById('s-name').value,
    site_description:    document.getElementById('s-desc').value,
    founder_website:     document.getElementById('s-founder').value,
    support_email:       document.getElementById('s-email').value,
  };
  post('/admin/update/settings', payload, function() {
    document.getElementById('settingsNote').textContent = '✓ Settings saved!';
    toast('✓ Settings saved!');
  });
}

function loadAudit() {
  get('/admin/data/audit', function(data) {
    var tbody = document.getElementById('auditBody');
    tbody.innerHTML = data.map(function(a) {
      return '<tr><td><strong>' + a.action + '</strong></td><td style="color:var(--muted)">' + (a.ip_address||'-') + '</td>' +
        '<td style="color:var(--muted)">' + (a.created_at||'').slice(0,16) + '</td></tr>';
    }).join('') || '<tr><td colspan="3" style="color:var(--muted)">No audit entries yet.</td></tr>';
  });
}

// ============================================
//   PRODUCT Q&A MANAGEMENT
// ============================================
function loadQuestions() {
  get('/admin/data/questions', function(data) {
    var tbody = document.getElementById('questionsBody');
    tbody.innerHTML = data.map(function(q) {
      return '<tr>' +
        '<td style="color:var(--muted)">' + (q.product_name || 'Product #' + q.product_id) + '</td>' +
        '<td>' + q.question + '</td>' +
        '<td>' + (q.answer ? '<span style="color:var(--gold)">' + q.answer + '</span>' : '<input type="text" id="ans-' + q.id + '" placeholder="Type answer..." style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:0.3rem 0.5rem;color:var(--text);font-size:0.75rem;width:140px"/>') + '</td>' +
        '<td><span class="badge ' + (q.status==='answered'?'bg':'by') + '">' + q.status + '</span></td>' +
        '<td>' + (q.answer ? '-' : '<button class="btn btn-sm btn-gold" onclick="answerQuestion(' + q.id + ')">Answer</button>') + '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="5" style="color:var(--muted);padding:0.8rem">No questions yet.</td></tr>';
  });
}

function answerQuestion(id) {
  var input = document.getElementById('ans-' + id);
  var answer = input ? input.value.trim() : '';
  if (!answer) { toast('Type an answer first'); return; }
  post('/admin/answer/question', { id: id, answer: answer }, function() {
    toast('✓ Answered!');
    loadQuestions();
  });
}

// ============================================
//   SUPPORT TICKETS
// ============================================
var currentTicketId = null;
var ticketsCache = [];

function loadTickets() {
  get('/admin/data/tickets', function(data) {
    ticketsCache = data;
    var tbody = document.getElementById('ticketsBody');
    tbody.innerHTML = data.map(function(t) {
      return '<tr>' +
        '<td><strong>' + t.subject + '</strong></td>' +
        '<td style="color:var(--muted)">' + (t.username || 'User #' + t.user_id) + '</td>' +
        '<td><span class="badge ' + (t.status==='resolved'?'bg':t.status==='pending'?'by':'bo') + '">' + t.status + '</span></td>' +
        '<td style="color:var(--muted)">' + (t.created_at||'').slice(0,10) + '</td>' +
        '<td><button class="btn btn-sm btn-gold" onclick="openTicketDetail(' + t.id + ')">View</button></td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="5" style="color:var(--muted);padding:0.8rem">No tickets yet.</td></tr>';
  });
}

function openTicketDetail(id) {
  var t = null;
  for (var i = 0; i < ticketsCache.length; i++) {
    if (ticketsCache[i].id === id) { t = ticketsCache[i]; break; }
  }
  if (!t) return;

  currentTicketId = id;
  document.getElementById('td-subject').textContent = t.subject;
  document.getElementById('td-customer').textContent = t.username || ('User #' + t.user_id);
  document.getElementById('td-message').textContent = t.message;
  document.getElementById('td-reply').value = t.admin_reply || '';
  document.getElementById('td-note').textContent = '';
  document.getElementById('ticketDetailPanel').style.display = 'block';
}

function closeTicketDetail() {
  document.getElementById('ticketDetailPanel').style.display = 'none';
  currentTicketId = null;
}

function sendTicketReply() {
  if (!currentTicketId) return;
  var reply = document.getElementById('td-reply').value.trim();
  if (!reply) { toast('Type a reply first'); return; }

  post('/admin/reply/ticket', { id: currentTicketId, reply: reply, status: 'resolved' }, function() {
    document.getElementById('td-note').textContent = '✓ Reply sent, ticket resolved!';
    toast('✓ Ticket resolved!');
    loadTickets();
  });
}

function markTicketStatus(status) {
  if (!currentTicketId) return;
  post('/admin/update/ticket-status', { id: currentTicketId, status: status }, function() {
    toast('✓ Status updated to ' + status);
    loadTickets();
  });
}

// ============================================
//   APPOINTMENTS
// ============================================
function loadAppointments() {
  get('/admin/data/appointments', function(data) {
    var tbody = document.getElementById('appointmentsBody');
    tbody.innerHTML = data.map(function(a) {
      return '<tr>' +
        '<td><strong>' + a.name + '</strong></td>' +
        '<td style="color:var(--muted)">' + a.contact + '</td>' +
        '<td style="color:var(--muted)">' + (a.project_type || '-') + '</td>' +
        '<td><span class="badge ' + (a.status==='approved'?'bg':a.status==='pending'?'by':'br') + '">' + a.status + '</span></td>' +
        '<td style="color:var(--muted)">' + (a.created_at||'').slice(0,10) + '</td>' +
        '<td>' +
          '<button class="btn btn-sm btn-gold" data-id="' + a.id + '" data-status="approved" onclick="handleApptClick(this)">Approve</button> ' +
          '<button class="btn btn-sm btn-danger" data-id="' + a.id + '" data-status="cancelled" onclick="handleApptClick(this)">Cancel</button>' +
        '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="6" style="color:var(--muted);padding:0.8rem">No appointments yet.</td></tr>';
  });
}

function handleApptClick(btn) {
  var id = parseInt(btn.getAttribute('data-id'));
  var status = btn.getAttribute('data-status');
  updateAppointment(id, status);
}

function updateAppointment(id, status) {
  post('/admin/update/appointment', { id: id, status: status }, function() {
    toast('✓ Appointment ' + status);
    loadAppointments();
  });
}

// ============================================
//   PURCHASES
// ============================================
function loadPurchases() {
  get('/admin/data/purchases', function(data) {
    var tbody = document.getElementById('purchasesBody');
    tbody.innerHTML = data.map(function(p) {
      return '<tr>' +
        '<td><strong>' + (p.product_name || '-') + '</strong></td>' +
        '<td style="color:var(--muted)">' + (p.username || 'User #' + p.user_id) + '</td>' +
        '<td>₦' + (p.price_paid || 0).toLocaleString() + '</td>' +
        '<td><span class="badge ' + (p.status==='completed'?'bg':p.status==='pending'?'by':'br') + '">' + p.status + '</span></td>' +
        '<td style="color:var(--gold);font-family:monospace;font-size:0.68rem">' + (p.license_key || '-') + '</td>' +
        '<td style="color:var(--muted)">' + (p.created_at||'').slice(0,10) + '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="6" style="color:var(--muted);padding:0.8rem">No purchases yet.</td></tr>';
  });
}

// ============================================
//   ANALYTICS
// ============================================
function loadAnalytics() {
  get('/admin/data/analytics-summary', function(d) {
    document.getElementById('an-revenue-today').textContent = '₦' + (d.revenue_today||0).toLocaleString();
    document.getElementById('an-revenue-week').textContent  = '₦' + (d.revenue_week||0).toLocaleString();
    document.getElementById('an-revenue-month').textContent = '₦' + (d.revenue_month||0).toLocaleString();
    document.getElementById('an-revenue-total').textContent = '₦' + (d.revenue_total||0).toLocaleString();
    document.getElementById('an-customers').textContent     = d.total_customers || 0;
    document.getElementById('an-purchases').textContent     = d.total_purchases || 0;
    document.getElementById('an-avg-order').textContent     = '₦' + (d.avg_order||0).toLocaleString();
    document.getElementById('an-conversion').textContent    = (d.conversion_rate||0) + '%';

    var tbody = document.getElementById('topProductsBody');
    tbody.innerHTML = (d.top_products || []).map(function(p) {
      return '<tr>' +
        '<td><strong>' + p.name + '</strong></td>' +
        '<td>' + p.purchase_count + '</td>' +
        '<td>₦' + (p.revenue||0).toLocaleString() + '</td>' +
        '<td><span style="color:var(--gold)">★</span> ' + (p.rating_avg||0).toFixed(1) + '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="4" style="color:var(--muted);padding:0.8rem">No sales data yet.</td></tr>';
  });
}
</script>
</body>
</html>
'''


@admin_bp.route('/')
@admin_required
def dashboard():
    db = get_db()
    total_products = db.execute(
        "SELECT COUNT(*) as c FROM products WHERE deleted_at IS NULL"
    ).fetchone()['c']
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    pending_tickets = db.execute(
        "SELECT COUNT(*) as c FROM support_tickets WHERE status='open'"
    ).fetchone()['c']
    pending_appointments = db.execute(
        "SELECT COUNT(*) as c FROM appointments WHERE status='pending'"
    ).fetchone()['c']
    activity = db.execute(
        'SELECT * FROM activity_log ORDER BY id DESC LIMIT 10'
    ).fetchall()
    db.close()

    stats = {
        'total_products': total_products,
        'total_users': total_users,
        'pending_tickets': pending_tickets,
        'pending_appointments': pending_appointments,
    }

    return render_template_string(
        ADMIN_PAGE,
        username=session.get('username'),
        stats=stats,
        activity=[dict(a) for a in activity],
    )


@admin_bp.route('/data/collections')
@admin_required
def data_collections():
    db = get_db()
    rows = db.execute('SELECT * FROM collections ORDER BY sort_order').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/data/settings')
@admin_required
def data_settings():
    return jsonify(get_all_settings())


@admin_bp.route('/update/settings', methods=['POST'])
@admin_required
def update_settings():
    data = request.get_json() or {}
    for key, value in data.items():
        set_setting(key, value)
    db = get_db()
    log_audit(db, session['user_id'], 'Settings Updated')
    db.commit()
    db.close()
    return jsonify({'ok': True})


@admin_bp.route('/data/audit')
@admin_required
def data_audit():
    db = get_db()
    rows = db.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ============================================
#   PRODUCT CRUD ROUTES
# ============================================

def _make_slug(name):
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or 'product'


@admin_bp.route('/data/products')
@admin_required
def data_products():
    db = get_db()
    rows = db.execute('''
        SELECT p.*, c.name as collection_name
        FROM products p
        LEFT JOIN collections c ON p.collection_id = c.id
        WHERE p.deleted_at IS NULL
        ORDER BY p.id DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/data/product/<int:product_id>')
@admin_required
def data_product_single(product_id):
    db = get_db()
    row = db.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
    db.close()
    return jsonify(dict(row) if row else {})


@admin_bp.route('/add/product', methods=['POST'])
@admin_required
def add_product():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400

    db = get_db()
    slug = _make_slug(name)
    # Ensure slug uniqueness
    existing = db.execute('SELECT id FROM products WHERE slug=?', (slug,)).fetchone()
    if existing:
        slug = f'{slug}-{uuid_suffix()}'

    db.execute('''
        INSERT INTO products
        (name, slug, short_desc, description, price, compare_price, gain_price,
         promo_percent, collection_id, delivery_type, github_repo_url, zip_file_url, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        name, slug, data.get('short_desc',''), data.get('description',''),
        data.get('price',0), data.get('compare_price'), data.get('gain_price'),
        data.get('promo_percent',0), data.get('collection_id'),
        data.get('delivery_type','zip'), data.get('github_repo_url',''),
        data.get('zip_file_url',''), data.get('status','draft')
    ))

    product = db.execute('SELECT id FROM products WHERE slug=?', (slug,)).fetchone()
    product_id = product['id']

    # Save images
    images = data.get('images', [])
    for i, img_url in enumerate(images[:10]):
        db.execute(
            'INSERT INTO product_images (product_id, image_url, sort_order) VALUES (?,?,?)',
            (product_id, img_url, i)
        )

    # Initial version record
    db.execute(
        'INSERT INTO product_versions (product_id, version, zip_file_url, release_notes) VALUES (?,?,?,?)',
        (product_id, '1.0', data.get('zip_file_url',''), 'Initial release')
    )

    log_activity_admin(db, 'Product Added', name)
    log_audit(db, session['user_id'], f'Product Added: {name}')
    db.commit()
    db.close()
    return jsonify({'ok': True, 'id': product_id})


@admin_bp.route('/update/product', methods=['POST'])
@admin_required
def update_product():
    data = request.get_json() or {}
    product_id = data.get('id')
    if not product_id:
        return jsonify({'ok': False, 'error': 'Missing product id'}), 400

    db = get_db()
    db.execute('''
        UPDATE products SET
          name=?, short_desc=?, description=?, price=?, compare_price=?,
          gain_price=?, promo_percent=?, collection_id=?, delivery_type=?,
          github_repo_url=?, zip_file_url=?, status=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (
        data.get('name'), data.get('short_desc',''), data.get('description',''),
        data.get('price',0), data.get('compare_price'), data.get('gain_price'),
        data.get('promo_percent',0), data.get('collection_id'),
        data.get('delivery_type','zip'), data.get('github_repo_url',''),
        data.get('zip_file_url',''), data.get('status','draft'), product_id
    ))

    # Replace images if new ones were uploaded
    images = data.get('images', [])
    if images:
        db.execute('DELETE FROM product_images WHERE product_id=?', (product_id,))
        for i, img_url in enumerate(images[:10]):
            db.execute(
                'INSERT INTO product_images (product_id, image_url, sort_order) VALUES (?,?,?)',
                (product_id, img_url, i)
            )

    log_audit(db, session['user_id'], f'Product Updated: ID {product_id}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


@admin_bp.route('/delete/product', methods=['POST'])
@admin_required
def delete_product():
    """Soft delete — sets deleted_at, never removes the row.
    Existing purchasers keep access to their downloads."""
    data = request.get_json() or {}
    product_id = data.get('id')

    db = get_db()
    db.execute(
        "UPDATE products SET deleted_at=CURRENT_TIMESTAMP, status='archived' WHERE id=?",
        (product_id,)
    )
    log_audit(db, session['user_id'], f'Product Soft-Deleted: ID {product_id}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


def uuid_suffix():
    import uuid
    return uuid.uuid4().hex[:6]


def log_activity_admin(db, action_type, summary):
    db.execute(
        "INSERT INTO activity_log (type, summary) VALUES (?,?)",
        (action_type.lower().replace(' ', '_'), summary)
    )


# ============================================
#   FILE UPLOAD ROUTES (R2-backed)
# ============================================

@admin_bp.route('/upload/image', methods=['POST'])
@admin_required
def upload_image():
    from app.services.storage import upload_file

    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    result = upload_file(file, folder='products')
    return jsonify(result)


@admin_bp.route('/upload/zip', methods=['POST'])
@admin_required
def upload_zip_route():
    from app.services.storage import upload_zip

    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    slug = request.form.get('slug', 'product')
    result = upload_zip(file, slug)
    return jsonify(result)


# ============================================
#   PRODUCT Q&A ADMIN ROUTES
# ============================================

@admin_bp.route('/data/questions')
@admin_required
def data_questions():
    db = get_db()
    rows = db.execute('''
        SELECT q.*, p.name as product_name
        FROM product_questions q
        LEFT JOIN products p ON q.product_id = p.id
        ORDER BY q.id DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/answer/question', methods=['POST'])
@admin_required
def answer_question():
    data = request.get_json() or {}
    question_id = data.get('id')
    answer = data.get('answer', '').strip()

    if not answer:
        return jsonify({'ok': False, 'error': 'Answer cannot be empty'}), 400

    db = get_db()
    db.execute(
        "UPDATE product_questions SET answer=?, status='answered' WHERE id=?",
        (answer, question_id)
    )
    log_audit(db, session['user_id'], f'Answered question ID {question_id}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ============================================
#   SUPPORT TICKET ADMIN ROUTES
# ============================================

@admin_bp.route('/data/tickets')
@admin_required
def data_tickets():
    db = get_db()
    rows = db.execute('''
        SELECT t.*, u.username
        FROM support_tickets t
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.id DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/reply/ticket', methods=['POST'])
@admin_required
def reply_ticket():
    data = request.get_json() or {}
    ticket_id = data.get('id')
    reply = data.get('reply', '').strip()
    status = data.get('status', 'resolved')

    if not reply:
        return jsonify({'ok': False, 'error': 'Reply cannot be empty'}), 400

    db = get_db()
    db.execute(
        "UPDATE support_tickets SET admin_reply=?, status=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
        (reply, status, ticket_id)
    )
    log_audit(db, session['user_id'], f'Replied to ticket ID {ticket_id}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


@admin_bp.route('/update/ticket-status', methods=['POST'])
@admin_required
def update_ticket_status():
    data = request.get_json() or {}
    db = get_db()
    db.execute(
        "UPDATE support_tickets SET status=? WHERE id=?",
        (data.get('status'), data.get('id'))
    )
    log_audit(db, session['user_id'], f'Ticket status changed: ID {data.get("id")} → {data.get("status")}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ============================================
#   APPOINTMENT ADMIN ROUTES
# ============================================

@admin_bp.route('/data/appointments')
@admin_required
def data_appointments():
    db = get_db()
    rows = db.execute('SELECT * FROM appointments ORDER BY id DESC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/update/appointment', methods=['POST'])
@admin_required
def update_appointment():
    data = request.get_json() or {}
    db = get_db()
    db.execute(
        'UPDATE appointments SET status=? WHERE id=?',
        (data.get('status'), data.get('id'))
    )
    log_audit(db, session['user_id'], f'Appointment updated: ID {data.get("id")} → {data.get("status")}')
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ============================================
#   PURCHASES + ANALYTICS ROUTES
# ============================================

@admin_bp.route('/data/purchases')
@admin_required
def data_purchases():
    db = get_db()
    rows = db.execute('''
        SELECT pu.*, p.name as product_name, u.username
        FROM purchases pu
        LEFT JOIN products p ON pu.product_id = p.id
        LEFT JOIN users u ON pu.user_id = u.id
        ORDER BY pu.id DESC
        LIMIT 100
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route('/data/analytics-summary')
@admin_required
def data_analytics_summary():
    db = get_db()

    def revenue_since(date_filter):
        row = db.execute(
            f"SELECT COALESCE(SUM(price_paid),0) as total FROM purchases WHERE status='completed' AND {date_filter}"
        ).fetchone()
        return row['total'] or 0

    revenue_today = revenue_since("date(created_at) = date('now')")
    revenue_week  = revenue_since("date(created_at) >= date('now', '-7 days')")
    revenue_month = revenue_since("date(created_at) >= date('now', '-30 days')")

    total_row = db.execute(
        "SELECT COALESCE(SUM(price_paid),0) as total, COUNT(*) as cnt FROM purchases WHERE status='completed'"
    ).fetchone()
    revenue_total = total_row['total'] or 0
    total_purchases = total_row['cnt'] or 0

    total_customers = db.execute('SELECT COUNT(*) as c FROM users WHERE is_admin=0').fetchone()['c']

    avg_order = round(revenue_total / total_purchases) if total_purchases > 0 else 0

    # Simple conversion: completed purchases / total signups (rough estimate, no separate visitor tracking yet)
    conversion_rate = round((total_purchases / total_customers * 100), 1) if total_customers > 0 else 0

    top_products = db.execute('''
        SELECT p.name, p.purchase_count, p.rating_avg,
               COALESCE(SUM(pu.price_paid), 0) as revenue
        FROM products p
        LEFT JOIN purchases pu ON pu.product_id = p.id AND pu.status='completed'
        WHERE p.deleted_at IS NULL
        GROUP BY p.id
        ORDER BY revenue DESC
        LIMIT 5
    ''').fetchall()

    db.close()

    return jsonify({
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
        'revenue_total': revenue_total,
        'total_customers': total_customers,
        'total_purchases': total_purchases,
        'avg_order': avg_order,
        'conversion_rate': conversion_rate,
        'top_products': [dict(r) for r in top_products],
    })
