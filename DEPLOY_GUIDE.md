# 🚀 VALCORE — Deploy to Render

This guide bakes in every lesson from the Kel HQ deploy saga so we don't repeat any of it.

---

## Before you start — quick checklist

- [ ] GitHub account ready
- [ ] No `Procfile` anywhere in your repo (confirmed already clean)
- [ ] `render.yaml` sits at the **repo root** — same level as `app/`, `requirements.txt`, `run.py`

---

## Step 1 — Push to GitHub

```bash
cd valcore
git init
git add .
git commit -m "VALCORE Commerce Engine - initial deploy"
git branch -M main
```

Create a new repo on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/valcore.git
git push -u origin main
```

**Confirm on GitHub.com** that `app/`, `requirements.txt`, `run.py`, and `render.yaml` are all visible at the repo root — this is exactly the step that got skipped with Kel HQ's `frontend/` folder and caused a "Not Found" error. Double-check before moving on.

---

## Step 2 — Deploy via Blueprint (NOT manual Web Service)

This is the #1 lesson from Kel HQ: **manual service creation = no auto-wired database = broken env vars.**

1. Render Dashboard → **New +** → **Blueprint** (not "Web Service")
2. Connect your GitHub repo
3. Render detects `render.yaml` and shows you a preview: **1 database (`valcore-db`) + 1 web service (`valcore`)**
4. Click **Apply**

This automatically creates the Postgres database AND injects `DATABASE_URL` into the web service — no manual env var typing required.

---

## Step 3 — Watch the build logs

Look for this exact sequence:

```
==> Installing dependencies...
==> Build successful
==> Deploying...
==> Running 'gunicorn app.main:app'
[VALCORE] Database initialised ✓ (Postgres)
==> Your service is live 🎉
==> Available at your primary URL https://valcore.onrender.com
```

If you see `AppImportError: Failed to find attribute 'app' in 'app'` — that's the exact bug we hit on Kel HQ. Means something is overriding the start command. Check:
- Settings → Start Command should show exactly `gunicorn app.main:app`
- No `Procfile` snuck into the repo

---

## Step 4 — First visit

```
https://valcore.onrender.com/
```

You should see the real home page (search bar, Hot section, etc) — not a 404. If you get "Not Found," it means some file is missing from the GitHub push — go back to Step 1 and verify every folder pushed correctly.

---

## Step 5 — Create your admin account

Same flow as local:

```
https://valcore.onrender.com/signup
```

Sign up normally, then promote yourself to admin. Since you don't have shell access on Render's free tier, use a Postgres client instead:

1. Render Dashboard → `valcore-db` → **Connect** tab → copy the **External Connection String**
2. Use a free tool like [TablePlus](https://tableplus.com) or `psql` to connect
3. Run:
```sql
UPDATE users SET is_admin=1 WHERE username='your_username';
```
4. Log out and back in on the live site — session refreshes with admin access

---

## Step 6 — Add your real credentials

Once logged in as admin on the **live** site:

```
https://valcore.onrender.com/admin
```

→ Settings tab → fill in:
- Paystack test keys (or live keys when ready)
- Cloudflare R2 credentials
- Discord webhook URL

Same as local — these are Settings-table values, not environment variables, so they're set through the UI, not through Render's dashboard.

---

## ⚠️ Free tier behaviors to expect

**Sleep on inactivity:** Free web services spin down after 15 minutes idle, take ~30-50 seconds to wake on the next visit. Your data is safe (it's in Postgres, not the ephemeral filesystem) — only the server process sleeps.

**Postgres 30-day expiry:** Render's free Postgres databases expire 30 days after creation. Set a reminder around day 25 to either back up your data or upgrade to a paid Postgres plan (~$6/mo) to keep it permanent.

---

## If something breaks

Send me:
1. A screenshot of the Render build/deploy logs
2. The exact URL you're hitting
3. What you see (blank page, error text, "Not Found", etc)

We'll debug it the same way we cracked every Kel HQ issue — read the actual error, not guess.
