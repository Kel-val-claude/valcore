# ============================================
#   VALCORE — AUTH ROUTES
#   app/routes/auth.py
# ============================================

from flask import Blueprint, request, session, jsonify, redirect, render_template_string
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, log_activity, log_audit
from app.services.notifications import notify_signup

auth_bp = Blueprint('auth', __name__)

AUTH_PAGE = '''
<!DOCTYPE html>
<html>
<head>
  <title>VALCORE — {{ "Sign In" if mode == "login" else "Create Account" }}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      background:#0A0A0A; color:#F0F0F0;
      font-family:'Inter',sans-serif;
      display:flex; align-items:center; justify-content:center;
      min-height:100vh; padding:1.5rem;
    }
    .box {
      background:#111; border:1px solid rgba(212,175,55,0.2);
      border-radius:16px; padding:2.5rem; width:100%; max-width:380px;
      box-shadow:0 0 60px rgba(212,175,55,0.08);
    }
    .logo { font-size:1.4rem; font-weight:700; color:#D4AF37; margin-bottom:0.3rem; }
    .sub  { font-size:0.78rem; color:#666; margin-bottom:2rem; }
    label { font-size:0.75rem; color:#888; display:block; margin-bottom:0.35rem; }
    input {
      width:100%; background:#0A0A0A; border:1px solid rgba(255,255,255,0.08);
      border-radius:8px; padding:0.75rem 1rem; color:#F0F0F0;
      font-family:'Inter',sans-serif; font-size:0.88rem; outline:none;
      margin-bottom:1rem; transition:border-color 0.2s;
    }
    input:focus { border-color:rgba(212,175,55,0.4); }
    button {
      width:100%; background:#D4AF37; color:#0A0A0A; border:none;
      border-radius:8px; padding:0.85rem; font-weight:700; font-size:0.9rem;
      cursor:pointer; transition:background 0.2s;
    }
    button:hover { background:#c9a227; }
    .error { color:#E74C3C; font-size:0.78rem; margin-bottom:1rem; padding:0.5rem; background:rgba(231,76,60,0.08); border-radius:6px; }
    .switch { display:block; text-align:center; margin-top:1.25rem; font-size:0.8rem; color:#666; }
    .switch a { color:#D4AF37; text-decoration:none; }
  </style>
</head>
<body>
  <div class="box">
    <div class="logo">VALCORE &lt;/&gt;</div>
    <div class="sub">{{ "Sign in to your account" if mode == "login" else "Create your free account" }}</div>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}

    {% if mode == "login" %}
    <form method="POST" action="/login">
      <label>Username or Email</label>
      <input type="text" name="identity" required autofocus />
      <label>Password</label>
      <input type="password" name="password" required />
      <button type="submit">Sign In →</button>
    </form>
    <span class="switch">No account? <a href="/signup">Create one</a></span>
    {% else %}
    <form method="POST" action="/signup">
      <label>Username</label>
      <input type="text" name="username" required autofocus />
      <label>Email</label>
      <input type="email" name="email" required />
      <label>Password</label>
      <input type="password" name="password" required minlength="6" />
      <button type="submit">Create Account →</button>
    </form>
    <span class="switch">Already have an account? <a href="/login">Sign in</a></span>
    {% endif %}
  </div>
</body>
</html>
'''


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect('/admin' if session.get('is_admin') else '/account')

    error = None
    if request.method == 'POST':
        identity = request.form.get('identity', '').strip()
        password = request.form.get('password', '').strip()

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username=? OR email=?',
            (identity, identity)
        ).fetchone()

        if user and verify_password(password, user['password_hash']):
            session.permanent    = True
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['is_admin']  = bool(user['is_admin'])
            log_audit(db, user['id'], 'Login')
            db.commit()
            db.close()
            return redirect('/admin' if user['is_admin'] else '/account')
        else:
            error = 'Invalid username/email or password.'
        db.close()

    return render_template_string(AUTH_PAGE, mode='login', error=error)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect('/admin' if session.get('is_admin') else '/account')

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not username or not email or len(password) < 6:
            error = 'Please fill all fields. Password must be at least 6 characters.'
        else:
            db = get_db()
            existing = db.execute(
                'SELECT id FROM users WHERE username=? OR email=?',
                (username, email)
            ).fetchone()

            if existing:
                error = 'Username or email already taken.'
                db.close()
            else:
                pw_hash = hash_password(password)
                db.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (?,?,?)',
                    (username, email, pw_hash)
                )
                user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()

                session.permanent   = True
                session['user_id']  = user['id']
                session['username'] = user['username']
                session['is_admin'] = False

                log_activity(db, 'signup', user['id'], f'{username} joined VALCORE')
                db.commit()
                db.close()

                notify_signup(username, email)

                return redirect('/account')

    return render_template_string(AUTH_PAGE, mode='signup', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@auth_bp.route('/api/auth/status')
def auth_status():
    return jsonify({
        'logged_in': bool(session.get('user_id')),
        'username':  session.get('username', ''),
        'is_admin':  bool(session.get('is_admin')),
    })
