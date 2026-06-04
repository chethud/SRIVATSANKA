# Kannans Website – React Dashboard

Green-themed owner dashboard connected to FastAPI.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173

Requires FastAPI on port 8000 (`../start-backend.bat`).

## Live Features

- **Dashboard** – stats, recent enquiries, notifications
- **Enquiries** – live table with dishes, status updates
- **Dish Management** – full menu from API
- **Bot Tester** – simulate WhatsApp flow
- **AI Assistant** – query upcoming events, wedding enquiries, etc.
- **Orders** – shows CONTACTED/CONVERTED enquiries

## API Proxy

Vite proxies `/api` and `/dev` to `http://localhost:8000` in development.
