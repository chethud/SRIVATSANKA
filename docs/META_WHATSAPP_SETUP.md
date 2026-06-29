# Connect WhatsApp Bot via Meta (Cloud API)

Step-by-step guide to connect Kannans Catering bot to Meta WhatsApp Business.

## What you need

1. A [Meta Developer](https://developers.facebook.com) account  
2. A Meta Business app with **WhatsApp** product added  
3. A **public HTTPS URL** for webhooks (use [ngrok](https://ngrok.com) for local testing)  
4. Your FastAPI server running on port **8000**

---

## Step 1 – Create Meta App

1. Go to [developers.facebook.com](https://developers.facebook.com)  
2. **My Apps** → **Create App** → choose **Business** type  
3. Add product: **WhatsApp** → **Set up**

---

## Step 2 – Get API credentials

In **WhatsApp → API Setup**:

| Meta dashboard field | Your `.env` variable |
|----------------------|----------------------|
| Temporary / Permanent token | `WHATSAPP_TOKEN` |
| Phone number ID | `WHATSAPP_PHONE_NUMBER_ID` |

Also copy **App Secret** from **App Settings → Basic** → `META_APP_SECRET`

Update `whatsapp/.env`:

```env
WHATSAPP_TOKEN=EAAxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=kannans-verify-token
META_APP_SECRET=your-app-secret
OWNER_PHONE_NUMBER=917899102165
GEMINI_API_KEY=your-gemini-key
```

---

## Step 3 – Expose your server (local dev)

Meta requires a public **HTTPS** webhook. Use ngrok:

```bash
# Terminal 1 – start FastAPI
cd whatsapp
.\venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 – expose to internet
ngrok http 8000
```

Copy the ngrok HTTPS URL, e.g. `https://abc123.ngrok-free.app`

Your webhook URL is:

```
https://abc123.ngrok-free.app/webhook
```

---

## Step 4 – Configure webhook in Meta

1. **WhatsApp → Configuration** (or API Setup → Webhook)  
2. Click **Edit** on Callback URL  
3. Enter:

   | Field | Value |
   |-------|-------|
   | **Callback URL** | `https://YOUR-NGROK-URL/webhook` |
   | **Verify token** | `kannans-verify-token` (must match `.env`) |

4. Click **Verify and save**  
5. Subscribe to webhook field: **`messages`**

If verification fails, check:
- FastAPI is running  
- `WHATSAPP_VERIFY_TOKEN` on Render is **not empty** (must be `kannans-verify-token` or your chosen string)  
- Token in Meta matches Render **exactly** (no quotes, no spaces)  
- ngrok URL is correct and uses **HTTPS**

**Important:** Configure under **WhatsApp → Configuration** (or API Setup → Webhook), not the generic **Webhooks** product for Facebook Pages.

---

## Step 5 – Test on WhatsApp

1. In Meta **API Setup**, add your phone as a **test recipient**  
2. Send a WhatsApp message to the business test number  
3. The AI bot should reply and collect enquiry details  
4. Owner alert goes to **917899102165**

Check connection status:

```
GET http://localhost:8000/api/whatsapp/status
```

---

## Step 6 – Go live (production)

1. Complete Meta **Business Verification**  
2. Add and verify your own business phone number  
3. Generate a **permanent System User token** (not temporary 24h token)  
4. Deploy FastAPI to a server with HTTPS (Railway, Render, VPS, etc.)  
5. Set webhook URL to your production domain: `https://yourdomain.com/webhook`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Webhook verify fails (403) | `WHATSAPP_VERIFY_TOKEN` mismatch |
| Bot receives but doesn't reply | Check `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` |
| Send failed 401 | Token expired – generate new permanent token |
| Send failed 131030 | Recipient not in test list (dev mode) |
| No owner alert | `OWNER_PHONE_NUMBER=917899102165` must be a registered test number in dev |

---

## Webhook endpoints in this project

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/webhook` | Meta verification |
| POST | `/webhook` | Incoming messages |
| GET | `/api/whatsapp/status` | Check if Meta credentials are set |

---

## Security

- Never commit `.env` to git  
- Use `META_APP_SECRET` to verify webhook signatures  
- Use permanent tokens via System User for production  
- Rotate tokens if exposed
