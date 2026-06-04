# Kannans WhatsApp AI Agent (FastAPI)

Backend for WhatsApp bot, REST API, and SQLite/PostgreSQL database.

## Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## WhatsApp Bot Phases

1. **Enquiry** – event details (AI or step-by-step fallback)
2. **Cuisine preferences** – customer picks menu styles only (Multi Cuisine, South Indian, etc.) — no individual dish selection
3. **Save** – enquiry + preferences → database + owner WhatsApp alert

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /webhook | Meta verification |
| POST | /webhook | Incoming WhatsApp |
| POST | /dev/message | Test bot locally |
| GET | /api/enquiries | List enquiries + dishes |
| PATCH | /api/enquiries/{id}/status | Update status |
| GET | /api/dishes | Full menu |
| GET | /api/stats | Dashboard stats |
| POST | /api/ai-assistant | Dashboard AI queries |
| GET | /api/whatsapp/status | Meta connection check |

## Menu

35+ dishes seeded automatically on first run across 6 categories.

## Meta Setup

See `../docs/META_WHATSAPP_SETUP.md`
