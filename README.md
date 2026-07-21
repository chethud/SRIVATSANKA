# SRIVATSANKA EVENTS Management Platform

Single-owner events platform: customers use **WhatsApp**, owner uses **React dashboard**.

## Structure

```
Kannans/
├── whatsapp/     # FastAPI – WhatsApp bot + REST API + database
├── website/      # React dashboard (Vite + Tailwind)
├── shared/       # Prisma schema reference
└── docs/         # Setup guides
```

## Tech Stack

| Layer | Stack |
|-------|--------|
| WhatsApp Bot | FastAPI + Gemini AI + Meta Cloud API |
| Dashboard | React + Vite + Tailwind (green theme) |
| Database | SQLite (dev) / PostgreSQL (production) |

## Quick Start (Windows)

**Terminal 1 – Backend**
```bash
cd whatsapp
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env – add GEMINI_API_KEY, Meta WhatsApp credentials
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 – Dashboard**
```bash
cd website
npm install
npm run dev
```

Or double-click: `start-backend.bat` and `start-frontend.bat`

- API docs: http://localhost:8000/docs  
- Dashboard: http://localhost:5173  

## WhatsApp Agent Flow

Conversational AI (Gemini) using [srivatsanka.com](https://srivatsanka.com/) — services, gallery, and reviews.

1. Welcomes customer, shares sample event photos, explains what SRIVATSANKA offers
2. Natural chat — asks what they are looking for, collects event details
3. Cuisine styles only (Multi Cuisine, South Indian, etc.) — no individual dishes on WhatsApp
4. Enquiry saved → **Enquiries** page + owner WhatsApp alert
6. Owner gets **instant WhatsApp alert** to `919945927101`
7. **Callback reminder** 15–20 min before preferred time

## Dashboard Modules

| Module | Status |
|--------|--------|
| Dashboard | Live stats + notifications |
| Enquiries | Live list with dishes + status update |
| Dish Management | Full menu from database |
| Bot Tester | Simulate WhatsApp conversations |
| AI Assistant | Query enquiries & events |
| Orders, Vendors, Workers, Invoices, Expenses | UI ready – backend coming |

## Meta WhatsApp Setup

See `docs/META_WHATSAPP_SETUP.md`

## Deploy (share with client)

- **Dashboard:** [Vercel](https://vercel.com) — root folder `website`, env `VITE_API_URL`
- **API:** [Render](https://render.com) — root folder `whatsapp`, use `render.yaml`
- **Database:** [Supabase](https://supabase.com) (PostgreSQL) — see `docs/SUPABASE_SETUP.md`

Full steps: **[docs/DEPLOY_VERCEL_RENDER.md](docs/DEPLOY_VERCEL_RENDER.md)**

## Environment (`whatsapp/.env`)

```env
GEMINI_API_KEY=your-key
WHATSAPP_TOKEN=meta-token
WHATSAPP_PHONE_NUMBER_ID=phone-id
WHATSAPP_VERIFY_TOKEN=kannans-verify-token
OWNER_PHONE_NUMBER=919945927101
```
