# Deploy: Vercel (dashboard) + Render (API)

Temporary hosting to share with your client.

| Part | Platform | URL example |
|------|----------|-------------|
| React dashboard | [Vercel](https://vercel.com) | `https://your-app.vercel.app` |
| FastAPI backend | [Render](https://render.com) | `https://srivatsanka.onrender.com` |

---

## 1. Backend on Render

### Option A – Blueprint (recommended)

1. Push this repo to GitHub (already at `chethud/SRIVATSANKA`).
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the **SRIVATSANKA** repository.
4. Render reads `render.yaml` and creates the **srivatsanka** web service (URL may be `https://srivatsanka.onrender.com`).
5. Set **secret** environment variables in the service:
   - `GEMINI_API_KEY` – required for AI + bill OCR
   - `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` – optional for live WhatsApp
6. After deploy, copy the service URL from Render, e.g. `https://srivatsanka.onrender.com`.

### Option B – Manual Web Service

1. **New** → **Web Service** → connect repo.
2. **Root Directory:** `whatsapp`
3. **Runtime:** Python 3
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. **Health Check Path:** `/api/health`
7. Add the same env vars as in `whatsapp/.env.example`.

### CORS (required)

In Render → **Environment**, set:

```env
CORS_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:5173
```

Replace with your real Vercel URL after step 2.  
Vercel preview URLs (`*.vercel.app`) are also allowed automatically.

### Data on live

- **Menu dish names** are seeded automatically (kept).
- **Demo/dummy enquiries, vendors, workers, expenses** are cleared on each API startup.
- Leave `SEED_DEMO_ON_STARTUP=false` on Render (default in `render.yaml`).

**Vercel:** Leave `VITE_API_URL` empty (uses `/api` proxy), or set it to `https://srivatsanka.onrender.com` (no trailing slash).

### Notes

- **Free tier** sleeps after ~15 min idle; first request may take 30–60s.
- **SQLite** data resets on redeploy unless you add a [Render persistent disk](https://render.com/docs/disks).
- WhatsApp webhook URL: `https://YOUR-RENDER-URL/webhook` (configure in Meta Developer Console).

---

## 2. Frontend on Vercel

1. Go to [Vercel](https://vercel.com) → **Add New** → **Project**.
2. Import **chethud/SRIVATSANKA** from GitHub.
3. **Root Directory:** `website` (click Edit).
4. **Framework Preset:** Vite
5. **Build Command:** `npm run build`
6. **Output Directory:** `dist`

### Environment variable (required before first deploy)

| Name | Value |
|------|--------|
| `VITE_API_URL` | `https://srivatsanka.onrender.com` (your Render URL from the dashboard, **no** trailing slash) |

7. Click **Deploy**.

After deploy, open the Vercel URL and confirm the dashboard loads data (not “API offline”).

### Update Render CORS

Copy the final Vercel URL and add it to Render `CORS_ORIGINS`, then **Manual Deploy** → **Clear build cache & deploy** on Vercel if you change `VITE_API_URL`.

---

## 3. Quick checklist

- [ ] Render service live: `https://YOUR-API.onrender.com/api/health` returns `{"status":"ok"}`
- [ ] Render `DATABASE_URL` = Supabase **Session pooler** URI (see `docs/SUPABASE_SETUP.md`)
- [ ] Render `SUPABASE_JWT_SECRET` set (Supabase → API → JWT Secret)
- [ ] Vercel `VITE_API_URL` points to Render URL
- [ ] Vercel `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` set
- [ ] Render `CORS_ORIGINS` includes your Vercel URL
- [ ] `GEMINI_API_KEY` set on Render (for AI features)
- [ ] Share Vercel link with client

---

## 4. Local development (unchanged)

```bash
# Terminal 1
cd whatsapp && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd website && npm run dev
```

Uses Vite proxy; no `VITE_API_URL` needed locally.
