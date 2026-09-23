# Srivatsanka — short project walkthrough

Client work for **Srivatsanka Events and Services** (catering / celebrations). Customers talk on WhatsApp. The owner runs the business from a web dashboard (enquiries, chats, orders, invoices, workers, etc.).

Public marketing site is still [srivatsanka.com](https://srivatsanka.com/). This repo is the ops stack: WhatsApp bot + API + owner dashboard.

---

## Is this the real message flow?

Yes.

**Customer → us**

```
Customer WhatsApp
  → Meta WhatsApp Cloud API
  → POST /webhook (our FastAPI)
  → conversation / bot logic
  → SQLite or Postgres
  → shows up on dashboard (Enquiries + WhatsApp Chats)
```

**Staff reply → customer**

```
Dashboard (WhatsApp Chats)
  → POST /api/chat/conversations/{phone}/messages
  → FastAPI calls Meta Graph API
  → Customer WhatsApp
```

When staff hits Reply / sends a message, we also **pause the bot** for that number so the AI doesn’t talk over the owner.

---

## 1. What I built

End-to-end on this stack, basically:

- **WhatsApp backend** (FastAPI): webhook verify + receive, Meta send helpers, signature check, idempotency on inbound `wamid`, guided enquiry flow, owner lead alerts, callback reminders
- **AI layer** on WhatsApp (Gemini) with a deterministic / rules-based path when AI isn’t needed or isn’t configured
- **Owner dashboard** (React): login, dashboard home, enquiries, WhatsApp Chats inbox, orders, dishes, vendors, workers, expenses/invoices, analytics bits, settings
- **REST API** the dashboard calls for all of the above
- **Chat handoff**: bot ↔ human — pause/resume per phone
- **Deploy path**: local → Vercel/Render earlier, then AWS EC2 + nginx (backup-first redeploy, keep live DB/uploads)

Business copy and state rules for the bot came from the client rules file (`Kannan.rules`); I wired that into the FSM / reply pack, not invented from scratch.

---

## 2. What others handled

Almost all commits in this repo are from one developer account. There was a small outside commit (UI/expense bill preview tweak).

Outside the code:

- Client: brand, menu knowledge, how the bot should talk, Meta Business / WhatsApp number access
- Marketing site content on srivatsanka.com (we pull / reference it; we didn’t rebuild that public site in this repo)

No separate “frontend team / backend team” split on this project — same person owned bot, API, and dashboard.

---

## 3. Tech used

| Layer | Choice |
|--------|--------|
| Backend | Python, FastAPI, SQLAlchemy (async), uvicorn |
| WhatsApp | Meta Cloud API via `graph.facebook.com` (v21) |
| AI | Google Gemini (chat + some bill OCR / assistant) |
| Frontend | React, TypeScript, Vite, Tailwind |
| DB | SQLite on EC2 / local; Postgres (Supabase) was used on some cloud deploys |
| Auth | Dashboard JWT (admin user/pass on AWS); Supabase auth was optional earlier |
| Hosting | Vercel (dashboard) + Render (API) for sharing; production moved to **AWS EC2** + nginx |

Repo layout:

- `whatsapp/` — API + bot + DB
- `website/` — React dashboard
- `docs/` — Meta setup, deploy notes

---

## 4. Meta WhatsApp API + webhook

**Setup (Meta side)**  
Meta app → WhatsApp product → token + Phone Number ID in `.env`, verify token for webhook, subscribe to `messages`. Locally we used ngrok HTTPS; production webhook is `https://<our-host>/webhook`.

**GET `/webhook`**  
Meta’s challenge: check `hub.verify_token` against `WHATSAPP_VERIFY_TOKEN`, return `hub.challenge`.

**POST `/webhook`**  
- Optional `X-Hub-Signature-256` check with `META_APP_SECRET`
- Parse `entry → changes → value → messages`
- Dedupe with `ProcessedWhatsappMessage` (same `wamid` ignored)
- Log customer text → `WhatsappChatMessage`
- If bot not paused → `handle_conversation(...)` → reply via Graph API (`/{phone-number-id}/messages`)
- Can send text, interactive buttons, images

Outbound helper lives in `whatsapp_client.py` — Bearer token, normalize Indian numbers to `91…`, mock send in local if credentials missing.

---

## 5. Incoming messages → dashboard

1. Webhook stores each inbound line in **`WhatsappChatMessage`** (`role=customer`).
2. Bot replies get `role=bot`.
3. When the enquiry flow finishes, we create an **`Enquiry`** row and ping the owner on WhatsApp.
4. Dashboard:
   - **Enquiries** — leads with status (NEW → SEEN / CONTACTED / CONVERTED / …)
   - **WhatsApp Chats** (`/bot-tester` in the UI) — conversation list + thread, pulled from `GET /api/chat/conversations` and `.../messages`

Polling / refetch from the React page keeps the inbox updated. Link from an enquiry can open the chat for that phone.

---

## 6. Dashboard → WhatsApp

Staff opens a chat, types, send:

1. `POST /api/chat/conversations/{phone}/messages` with `{ "text": "..." }`
2. Backend `send_whatsapp_message` → Meta
3. On success, log `role=owner` and **pause bot** for that phone
4. Customer sees it in normal WhatsApp

Same Graph API path the bot uses — only the sender role and handoff state differ.

---

## 7. History + delivery / read status

**History — yes.** Full thread per phone in `WhatsappChatMessage` (customer / bot / owner), with timestamps. Can delete a conversation from the dashboard.

**Meta delivery / blue ticks — not really.**  
We don’t persist Meta’s `statuses` webhooks (sent / delivered / read) onto each chat bubble. The webhook mostly cares about inbound `messages`. We do keep processing status for **idempotency** (`claimed` / `sent` / `skipped`), and dashboard **notifications** have a simple read flag — that’s not WhatsApp read receipts.

So: conversation history yes; WhatsApp delivery/read ticks in the UI no.

---

## 8. AI or human dashboard?

Both.

- **AI on WhatsApp**: Gemini-driven consultant flow (name, event, date, venue, guests, callback). Falls back to template / rules replies if no key. Button-first guided steps in places.
- **Human ops**: Owner uses Enquiries + WhatsApp Chats. Reply pauses auto-replies.
- **Dashboard AI assistant**: separate page/API to ask about enquiries / events (not the customer-facing bot).
- Extra: bill image OCR for expenses (Gemini again).

So it’s not “only a human inbox” and not “fully autonomous” — bot qualifies leads, humans take over and run the rest of the business in the dashboard.

---

## 9. “Facebook → CRM” — what that means here

There is **no Facebook Lead Ads / Page form → CRM pipeline** in this repo.

What we do have:

1. **Meta (Facebook) Graph API** as the pipe for WhatsApp Cloud API.
2. **CRM-ish product** = our own dashboard: WhatsApp chats → **Enquiry** records → orders / payments / workers.

Rough lead path:

```
WhatsApp chat
  → bot collects fields
  → Enquiry saved (NEW)
  → owner WhatsApp alert + Enquiries list
  → staff call / chat
  → status moves toward CONVERTED → Orders / billing side
```

If someone says “Facebook CRM integration” in a demo, for *this* project it means: Meta WhatsApp into our enquiry CRM — not Ads Manager lead forms.

---

## Event-planner website (owner dashboard)

This is the React app under `website/` — internal tool for running events, not the public brochure site.

**My role**  
Built the UI and wired it to the FastAPI API: auth, enquiries, WhatsApp inbox, orders (Excel import, menu grid, venue, payments), vendors/workers, expenses/invoices, photos, analytics/settings polish, mobile layouts.

**Stack**  
React + TS + Vite + Tailwind. Talks to FastAPI over `/api` (Vite proxy locally; `VITE_API_URL` in hosted builds).

**What I handled**

- Frontend: pages, chat UI, order/billing UX
- Backend: same FastAPI project (shared with the bot)
- DB: models + migrations/alters for enquiries, chat, orders, workers, etc.
- APIs: enquiries, chat, orders, resources, auth, webhooks

**Deploy**  
Yes — docs and scripts for Vercel/Render, then EC2 (nginx, systemd, SSL, S3 DB backups, redeploy script that backups first and never wipes live `kannans.db` / uploads / `.env`).

---

## Quick demo script (2–3 min)

1. Open dashboard → Enquiries / WhatsApp Chats.  
2. Send a WhatsApp to the business number: greeting → name → event → a couple of details.  
3. Show bot replies + thread updating in Chats.  
4. Complete flow → new Enquiry + owner alert.  
5. Reply from dashboard → message arrives on phone; bot stays paused.  
6. Optional: open an order / invoice screen to show the rest of ops.

---

## One-liner

WhatsApp Cloud API in, FastAPI + DB in the middle, React dashboard out — AI qualifies the lead, humans run the event from the same system.
