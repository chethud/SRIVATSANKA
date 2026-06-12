"""Brand knowledge from https://kannansharangapani.com/ for the WhatsApp agent."""

WEBSITE_URL = "https://kannansharangapani.com/"

COMPANY = {
    "legal_name": "Srivatsanka Events and Services Pvt Ltd",
    "brand_name": "SRIVATSANKA",
    "established": "2017",
    "managing_director": "Mr. Kannan Sharangapani",
    "phone": "+91-9945607074",
    "whatsapp": "+91-9945607074",
    "email": "srivatsankas@gmail.com",
    "address": "#1, 4th Cross, 4th Main, N R Colony, Bengaluru 560019",
    "tagline": "Pure Veg Catering Services for All Occasions",
}

SERVICES = [
    "Wedding Catering",
    "Decor for Celebrations",
    "Wedding Pooja Setup",
    "Venues for Celebrations",
    "Full event food & hospitality",
]

EVENT_TYPES = [
    "Wedding",
    "House Warming",
    "Naming Ceremony",
    "Upanayanam",
    "Baby Shower",
    "Reception",
    "Corporate events",
]

SPECIALTIES = [
    "Food safety & hygiene in cooking and serving",
    "100% transparency on requirements and delivery",
    "Customer-centric solutions",
    "Lifetime customer relationships",
    "Innovative menus while keeping traditional cuisine",
    "Excellence in execution with a personal touch",
    "Biodegradable cutlery — environmentally sensitive",
]

SOCIAL_PROOF = [
    "Trusted since 2017 in Bengaluru for weddings and family celebrations",
    "Guests praise our South Indian, North Indian & Kerala menus, live counters, and warm service",
    "Mr. Kannan personally oversees events — many families call him part of their celebration story",
    "Known for Dumrot, Badam Puri, Pal Payasam, Pani Puri, chaat counters, and multi-day wedding catering",
    "5-star feedback on food quality, presentation, and stress-free execution",
]

WEBSITE_ABOUT = (
    "We believe great stories are told of celebrations in every family — weddings, house warmings, "
    "naming ceremonies, upanayanam, and baby showers filled with joy, satisfaction, and lifelong memories. "
    "Srivatsanka Events and Services Pvt Ltd is a one-stop solution for wedding catering, decor, pooja setup, "
    "and venues. We execute with operational excellence, outstanding hospitality, innovative menus, and a "
    "traditional touch. Our vision is to make your celebration an ecstatic event in reality."
)

WEBSITE_VIDEOS = [
    "Wedding Serving Attire & Style — see our professional service on our website gallery",
]

POPULAR_DISHES = [
    "Dumrot",
    "Badam Puri",
    "Pal Payasam",
    "Pani Puri & chaat counters",
    "Live dosa and counter specials",
    "South Indian, North Indian & Kerala wedding spreads",
    "Multi-cuisine pure veg menus",
]

# Full-size gallery from https://kannansharangapani.com/ (website gallery section)
GALLERY_ITEMS: list[dict[str, str]] = [
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1620985900177-1.jpeg",
        "caption": "Wedding feast — pure veg celebration spread 🍽️",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1714968534695-1.png",
        "caption": "Elegant plating & live counter setup ✨",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1714968534700-1.png",
        "caption": "Traditional touch with premium hospitality 💚",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1714968534703-1.png",
        "caption": "Beautiful food presentation at a family celebration",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1714968534705-1.png",
        "caption": "Grand reception-style veg spread",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1657811033159-1.png",
        "caption": "Past event — guests enjoying our catering",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1657811142282-1.png",
        "caption": "Live counter & festive wedding service",
    },
    {
        "url": "https://kannansharangapani.com/wp-content/uploads/2024/11/1694611435098-1.png",
        "caption": "Another glimpse from events we have catered",
    },
]

GALLERY_IMAGE_URLS = [item["url"] for item in GALLERY_ITEMS]

WELCOME_IMAGE_CAPTIONS = [item["caption"] for item in GALLERY_ITEMS[:3]]


def gallery_urls() -> list[str]:
    return list(GALLERY_IMAGE_URLS)

EVENT_TYPE_DETAILS: dict[str, dict] = {
    "Wedding": {
        "title": "Wedding Catering",
        "description": (
            "Multi-day wedding menus with South Indian, North Indian & Kerala favourites — "
            "live counters, Dumrot, Badam Puri, chaat, and elegant service for family & guests."
        ),
        "image_captions": [
            "Wedding feast — pure veg spread 🍽️",
            "Live counters & traditional sweets ✨",
            "Elegant plating for your big day 💚",
        ],
    },
    "House Warming": {
        "title": "House Warming",
        "description": (
            "Warm homely menus with snacks, meals, and desserts — perfect for griha pravesham "
            "with neighbours and close family."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Baby Shower": {
        "title": "Baby Shower",
        "description": (
            "Light, festive menus with snacks, sweets, and refreshing beverages — "
            "beautiful presentation for celebrating the new arrival."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Reception": {
        "title": "Reception",
        "description": (
            "Grand reception dining with multi-cuisine veg spreads, live counters, and "
            "smooth service for large guest lists."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Corporate events": {
        "title": "Corporate Events",
        "description": (
            "Professional catering for office lunches, conferences, and team events — "
            "hygienic, on-time, and customisable pure-veg menus."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Naming Ceremony": {
        "title": "Naming Ceremony",
        "description": (
            "Traditional naming ceremony menus with homely meals, sweets, and snacks for family and guests."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Upanayanam": {
        "title": "Upanayanam",
        "description": (
            "Sacred ceremony catering with sattvic pure-veg meals prepared with care for family gatherings."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "General": {
        "title": "Celebration Catering",
        "description": (
            "Custom pure-veg menus for naming ceremonies, upanayanam, birthdays, and family functions — "
            "we plan every detail with you."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
}


def match_event_type(text: str) -> str:
    """Map customer text to a known event type."""
    lower = text.lower().strip()
    aliases = {
        "wedding": "Wedding",
        "marriage": "Wedding",
        "reception": "Reception",
        "house warming": "House Warming",
        "housewarming": "House Warming",
        "griha": "House Warming",
        "baby shower": "Baby Shower",
        "seemantham": "Baby Shower",
        "naming": "Naming Ceremony",
        "naming ceremony": "Naming Ceremony",
        "upanayanam": "Upanayanam",
        "corporate": "Corporate events",
        "office": "Corporate events",
        "lunch": "Corporate events",
        "birthday": "General",
    }
    for key, canonical in aliases.items():
        if key in lower:
            if canonical == "Naming Ceremony" or canonical == "Upanayanam":
                return canonical
            return canonical
    for event in EVENT_TYPES:
        if event.lower() in lower:
            return event
    return "General"


def build_short_company_context() -> str:
    """Brief company facts for natural Q&A replies."""
    return (
        f"{COMPANY['brand_name']} ({COMPANY['legal_name']}) — pure vegetarian catering in Bengaluru "
        f"since {COMPANY['established']}, led by {COMPANY['managing_director']}. "
        f"Phone {COMPANY['phone']}. Website {WEBSITE_URL}. "
        f"We handle weddings, house warmings, corporate events, and multi-cuisine veg menus with live counters."
    )


def build_agent_context() -> str:
    """Compact knowledge block injected into the Gemini system prompt."""
    services = "\n".join(f"- {s}" for s in SERVICES)
    events = ", ".join(EVENT_TYPES)
    specialties = "\n".join(f"- {s}" for s in SPECIALTIES)
    proof = "\n".join(f"- {s}" for s in SOCIAL_PROOF)
    dishes = ", ".join(POPULAR_DISHES)
    videos = "; ".join(WEBSITE_VIDEOS)

    return f"""
COMPANY (official website: {WEBSITE_URL})
- {COMPANY['legal_name']} ({COMPANY['brand_name']}), established {COMPANY['established']}
- Managing Director: {COMPANY['managing_director']}
- Tagline: {COMPANY['tagline']}
- Pure vegetarian catering & events — Bengaluru
- Contact: {COMPANY['phone']} | WhatsApp {COMPANY['whatsapp']} | {COMPANY['email']}
- Address: {COMPANY['address']}

ABOUT US (from website)
{WEBSITE_ABOUT}

WHAT WE DO
{services}

EVENTS WE SPECIALISE IN
{events}

POPULAR MENU HIGHLIGHTS
{dishes}

OUR STRENGTHS
{specialties}

EXPERIENCE & REPUTATION
{proof}

GALLERY & VIDEOS
- We have {len(GALLERY_ITEMS)} event photos from past weddings and celebrations on our website.
- When customers ask for photos, our WhatsApp system shares real gallery images from past events automatically.
- Website gallery & videos: {WEBSITE_URL} — includes "{videos}".

WHATSAPP CAPABILITIES
- You CAN share event photos directly on WhatsApp — the system sends gallery images when customers ask.
- Never say you cannot share photos on WhatsApp. Say you are sharing sample photos from past events now.
- Also share {WEBSITE_URL} for the full gallery, feedback, and enquiry form.
""".strip()
