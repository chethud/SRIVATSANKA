# Kannans Catering Management Platform

Single-owner catering platform: customers use **WhatsApp**, owner uses **React dashboard**.

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

## WhatsApp Bot Flow

1. Collects event details (name, phone, event, date, location, guests, callback)
2. Customer selects **dish categories** (South Indian, North Indian, Chinese, etc.)
3. Customer picks **dishes** from each category
4. Customer adds **customizations** (No Milk, Less Spice, etc.)
5. Enquiry saved → shows on **Enquiries** page
6. Owner gets **instant WhatsApp alert** to `917899102165`
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

Full steps: **[docs/DEPLOY_VERCEL_RENDER.md](docs/DEPLOY_VERCEL_RENDER.md)**

## Environment (`whatsapp/.env`)

```env
GEMINI_API_KEY=your-key
WHATSAPP_TOKEN=meta-token
WHATSAPP_PHONE_NUMBER_ID=phone-id
WHATSAPP_VERIFY_TOKEN=kannans-verify-token
OWNER_PHONE_NUMBER=917899102165
```
