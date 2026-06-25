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
DATABASE_URL=postgresql://postgres.hlzndlmcvpmsxzkawsbz:YOUR_DB_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
SUPABASE_JWT_SECRET=paste-jwt-secret-from-supabase-api-settings
GEMINI_API_KEY=your-gemini-key
CORS_ORIGINS=https://YOUR-VERCEL-APP.vercel.app,http://localhost:5173
OWNER_PHONE_NUMBER=917899410254
SEED_DEMO_ON_STARTUP=true
```

- **DATABASE_URL** — Settings → Database → URI → **Session pooler** (port **5432**).  
  **Do not use Direct** (`db.xxx.supabase.co`) on Render — it often fails with `Network is unreachable`.
- Copy the **exact** URI from Supabase (region in host may differ, e.g. `aws-0-ap-south-1`).
- If password has `@`, `#`, etc., URL-encode it (`@` → `%40`).

Save → redeploy. Tables are created on first API start.

---

## 3. Vercel (React dashboard)

Vercel → Project → **Settings** → **Environment Variables**:

```env
VITE_API_URL=https://srivatsanka.onrender.com
VITE_SUPABASE_URL=https://hlzndlmcvpmsxzkawsbz.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

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
| API returns 401 after login | `SUPABASE_JWT_SECRET` on Render must match Supabase JWT Secret |
| Database connection failed | Check `DATABASE_URL` uses **database password**, URL-encode special chars |
| Render crash: `Name or service not known` | Wrong `DATABASE_URL` host, or `@` in password breaks the URI — encode `@` as `%40` |
| Render crash: `Network is unreachable` | Switch from **Direct** to **Session pooler** URI in `DATABASE_URL` (Supabase → Database) |
| Still shows old Admin login | Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` on Vercel and redeploy |

---

## Security

- Never commit `.env` files
- **anon key** — OK in Vercel (public)
- **JWT secret** + **database password** — server only (Render), never in the website
- **service_role / secret key** — do not put in the React app