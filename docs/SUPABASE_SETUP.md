# Supabase setup — data + authentication

Use Supabase for **all dashboard data** (PostgreSQL) and **sign-in** (Supabase Auth).

Project example: `https://hlzndlmcvpmsxzkawsbz.supabase.co`

---

## What goes where

| What | Where to get it in Supabase | Used on |
|------|-----------------------------|---------|
| **Database** (`DATABASE_URL`) | Settings → **Database** → Connection string → **Session pooler** (for Render) | Render + `whatsapp/.env` |
| **Sign-in** (`VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY`) | Settings → **API** → Project URL + **anon / publishable** key | Vercel + `website/.env` |
| **API token check** (`SUPABASE_JWT_SECRET`) | Settings → **API** → **JWT Settings** → JWT Secret | Render + `whatsapp/.env` |

**Do not** use API keys as `DATABASE_URL`.  
**Do not** use the database password for sign-in.

---

## 1. Create dashboard users (Supabase Auth)

1. Supabase → **Authentication** → **Users**
2. **Add user** → email + password (e.g. `admin@yourcompany.com`)
3. Share these credentials with your team — they sign in on the website with **email**, not `Admin`.

Enable **Email** provider under **Authentication** → **Providers** if it is off.

---

## 2. Render (API backend)

Render → **srivatsanka-api** → **Environment**:

```env
PYTHON_VERSION=3.12.8
DATABASE_URL=postgresql://postgres.hlzndlmcvpmsxzkawsbz:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
SUPABASE_ANON_KEY=sb_publishable_your-key-here
SUPABASE_JWT_SECRET=
GEMINI_API_KEY=your-gemini-key
CORS_ORIGINS=https://YOUR-VERCEL-APP.vercel.app,http://localhost:5173
OWNER_PHONE_NUMBER=917899410254
SEED_DEMO_ON_STARTUP=true
```

- **SUPABASE_URL** — required for API auth (JWKS + Auth API verification).
- **SUPABASE_ANON_KEY** — publishable/anon key from Supabase → API (set on Render).
- **SUPABASE_JWT_SECRET** — optional; only for legacy HS256 projects.

- **PYTHON_VERSION** — set to `3.12.8` (Render defaults to 3.14; `runtime.txt` is ignored).
- **DATABASE_URL** — Supabase → **Connect** → **Session pooler** (port **5432**). Replace `YOUR_PASSWORD`; encode `@` as `%40`. If deploy fails with `tenant/user not found`, try `aws-1-ap-southeast-1` instead of `aws-0` in the host (or copy the exact host from Connect).

Save → redeploy. Tables are created on first API start.

---

## 3. Vercel (React dashboard)

Vercel → Project → **Settings** → **Environment Variables**:

```env
VITE_SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

- **VITE_API_URL** — leave **empty** on Vercel (built-in `/api` proxy to Render). Only set if you host the dashboard elsewhere.

- **VITE_SUPABASE_ANON_KEY** — Settings → API → **anon public** or **publishable** key (safe in the browser)

Redeploy Vercel after saving.

---

## 4. Local development

**`whatsapp/.env`**

```env
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@db.hlzndlmcvpmsxzkawsbz.supabase.co:5432/postgres
SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
```

**`website/.env`**

```env
VITE_SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

```bash
cd whatsapp && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd website && npm install && npm run dev
```

Sign in at http://localhost:5173 with the Supabase user email/password.

---

## 5. Verify

1. **Health:** `https://YOUR-API.onrender.com/api/health` → `{"status":"ok"}`
2. **Sign in** on the dashboard with your Supabase user email
3. **Supabase → Table Editor** — `Enquiry`, `Dish`, `Vendor`, etc. after demo data or real use
4. **Authentication → Users** — your signed-in user appears there

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Invalid username/password on login | User must exist in Supabase **Authentication → Users** |
| API returns 401 after login | Set `SUPABASE_URL` + `SUPABASE_ANON_KEY` on Render and redeploy |
| Database connection failed | Check `DATABASE_URL` uses **database password**, URL-encode special chars |
| Render crash: `Name or service not known` | Wrong `DATABASE_URL` host, or `@` in password breaks the URI — encode `@` as `%40` |
| Render crash: `Network is unreachable` | Switch from **Direct** to **Session pooler** URI in `DATABASE_URL` (Supabase → Connect) |
| `tenant/user postgres.xxx not found` | Wrong pooler hostname — paste Session pooler URI from **Connect** (not a guessed `aws-0-ap-southeast-1`) |
| Build uses Python 3.14 / pip hangs forever | Set `PYTHON_VERSION=3.12.8` in Render Environment and redeploy |
| Still shows old Admin login | Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` on Vercel and redeploy |

---

## Security

- Never commit `.env` files
- **anon key** — OK in Vercel (public)
- **JWT secret** + **database password** — server only (Render), never in the website
- **service_role / secret key** — do not put in the React app