# VALCORE — Phase 1 Setup Guide

## What's built in Phase 1

- Full 16-table database schema (auto-creates on first run)
- Real auth: signup, login, logout — passwords are salted + hashed (not plaintext)
- Admin dashboard skeleton (Dashboard, Products, Collections, Users, Purchases, Support, Appointments, Product Q&A, Settings, Audit Log) — most sections show "Coming in Phase X" placeholders, Dashboard/Collections/Settings/Audit are fully wired
- Customer account page (basic stats: purchases, wishlist, tickets)
- Storefront foundation routes (home, product page, collection page, search, VALCORE profile, appointment) — placeholder rendering, real UI comes in Phase 2
- Settings system — Discord webhook, Paystack keys, site info all editable from `/admin` → Settings, nothing hardcoded
- 6 live collections seeded (Business Websites, E-Commerce Templates, SaaS/Landing Pages, Telegram Bots, Automation Scripts, Admin Dashboards) + 3 reserved-hidden (UI Kits, Flask Projects, Premium Components)

---

## Run it locally

```bash
cd valcore
pip install -r requirements.txt
python run.py
```

Opens on `http://localhost:5050` (different port from Kel HQ's 5000, so you can run both at once if needed).

---

## Creating your admin account

There's no seeded admin user — for real security, you create your account through normal signup, then we promote it to admin via direct DB access (same idea as changing Kel HQ's password, just once).

**Step 1 — Sign up normally:**
```
http://localhost:5050/signup
```
Pick the username/email/password you'll actually use.

**Step 2 — Promote yourself to admin:**

Locally (SQLite), in a Python shell from the `valcore/` folder:
```python
from app.core.database import get_db
db = get_db()
db.execute("UPDATE users SET is_admin=1 WHERE username=?", ("your_username",))
db.commit()
db.close()
```

**Step 3 — Log out and log back in** (session needs to refresh to pick up `is_admin=1`):
```
http://localhost:5050/logout
http://localhost:5050/login
```

You'll be redirected straight to `/admin` instead of `/account`.

---

## Folder structure

```
valcore/
├── app/
│   ├── main.py              ← app factory
│   ├── core/
│   │   ├── database.py      ← all 16 tables + get_setting/set_setting
│   │   └── auth.py          ← password hashing, login_required, admin_required
│   ├── routes/
│   │   ├── auth.py          ← signup/login/logout
│   │   ├── storefront.py    ← home/product/collection/search (Phase 1 = placeholders)
│   │   ├── account.py       ← customer account area
│   │   ├── admin.py         ← admin dashboard
│   │   ├── api.py           ← public read API
│   │   └── public.py        ← serves css/js/assets
│   ├── models/               (empty, reserved for Phase 2+ if we split logic out)
│   └── services/              (empty, reserved for Paystack/Discord/R2 service modules)
├── frontend/
│   ├── css/
│   ├── js/
│   └── assets/
├── database/                 (SQLite file lives here locally, gitignored)
├── requirements.txt
└── run.py
```

---

## What's deliberately NOT built yet

- Real home page UI (search bar, Hot section, horizontal collection scroll) — Phase 2
- Product CRUD in admin — Phase 3
- Payments / Paystack integration — Phase 4
- Ratings, wishlist, Product Q&A UI — Phase 5
- Support ticket + appointment full flow — Phase 6
- Revenue analytics, Discord webhook firing — Phase 7
- VALCORE profile page real design — Phase 8

This is intentional — foundation first, proven to work, before any UI polish. Same lesson learned from Kel HQ's early-stage chaos.

---

## Next step

Once you confirm Phase 1 runs clean (signup works, login works, admin promotion works, dashboard loads with real numbers) — say the word and we move to **Phase 2: Storefront UI**, building the actual home page layout from your original spec (search, Hot, collections scroll, recommended, new releases, all products).
