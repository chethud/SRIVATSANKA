"""Brand knowledge scraped from https://srivatsanka.com/ for WhatsApp replies."""

from __future__ import annotations

import re

WEBSITE_URL = "https://srivatsanka.com/"

COMPANY = {
    "legal_name": "Srivatsanka Events and Services",
    "brand_name": "Srivatsanka Events and Services",
    "established": "2017",
    "managing_director": "Mr. Kannan Sharangapani",
    "founder": "Sri R. V. Sharangapani",
    "director_culture": "Mrs. Sangeetha K. S.",
    "phone": "+91-9945607074",
    "whatsapp": "+91-9945927101",
    "email": "srivatsankas@gmail.com",
    "address": "#1, 4th Cross, 4th Main, N R Colony, Bengaluru 560019",
    "tagline": "Where Celebrations Become Beautiful Memories",
    "hero_line": (
        "From wedding catering and ritual arrangements to décor and venue support, "
        "we bring together tradition, warmth, and thoughtful execution."
    ),
    "services_intro": (
        "We offer end-to-end event and catering services designed to make your "
        "celebrations stress-free and enjoyable."
    ),
    "experience_center": "Eat Rep Eat (Eat Repeat) — authentic Brahmin / vegetarian dining",
    "eat_rep_eat_address": "Eat Repeat, No 58, Shrineedam, 4th Cross, 4th Main, N R Colony, Bengaluru - 560019",
    "eat_rep_eat_hours": "Mon–Sun 7am–8pm",
    "eat_rep_eat_phone": "+91-9945927101",
    "eat_rep_eat_url": "https://srivatsanka.com/eat-rep-eat/",
}

SERVICE_PAGES = {
    "catering": "https://srivatsanka.com/catering/",
    "decor": "https://srivatsanka.com/services/wedding-decoration/",
    "rituals": "https://srivatsanka.com/event-ritual-support/",
    "venues": "https://srivatsanka.com/services/wedding-venues/",
    "partner_venues": "https://srivatsanka.com/our-partner-venues/",
    "about": "https://srivatsanka.com/about-us/",
    "gallery": "https://srivatsanka.com/wedding-gallery/",
    "contact": "https://srivatsanka.com/contact-us/",
}

# Matches homepage / About "What We Offer" cards
SERVICE_DETAILS: dict[str, dict] = {
    "catering": {
        "title": "Wedding Catering Services",
        "short": "Authentic, flavorful cuisine prepared with care and served with excellence.",
        "overview": (
            "Catering is at the heart of what we do — three generations of culinary expertise "
            "for intimate gatherings to grand wedding feasts. Pure-veg / traditional South Indian "
            "menus from Karnataka, Andhra Pradesh, Tamil Nadu, and Kerala."
        ),
        "includes": [
            "Customized menus",
            "Traditional wedding feasts",
            "Upanayanam / baby shower / engagement / birthday / housewarming catering",
            "Family & corporate get-togethers",
            "Buffet & traditional service",
            "Professional service staff",
            "Live food counters",
            "Dessert & beverage stations",
        ],
        "live_stations": [
            "Ice cream",
            "Chaat",
            "Live dosa",
            "Live tawa",
            "South Indian snacks",
            "Juice & mocktail",
            "Sweet counter",
            "Coffee & tea",
        ],
        "process": ["Consultation", "Menu planning", "Tasting session", "Event execution"],
        "url": SERVICE_PAGES["catering"],
        "keywords": ("cater", "food", "menu", "cuisine", "meal", "lunch", "dinner", "buffet", "live counter"),
    },
    "decor": {
        "title": "Event Decorations & Setup",
        "short": "Elegant décor tailored to match your event theme and style.",
        "overview": (
            "Stunning décor setups — wedding stages, reception looks, theme-based and floral décor "
            "for birthdays, naming ceremonies, housewarming, baby showers, engagements, and home celebrations."
        ),
        "includes": [
            "Wedding stage décor",
            "Reception décor",
            "Theme-based décor",
            "Floral décor (fresh & artificial)",
            "Birthday / naming / housewarming / baby shower décor",
            "Small engagement & home celebration setups",
        ],
        "process": ["Theme discussion", "Concept & design approval", "Material planning", "Setup & execution"],
        "url": SERVICE_PAGES["decor"],
        "keywords": ("decor", "décor", "decoration", "stage", "floral", "theme", "swing"),
    },
    "rituals": {
        "title": "Traditional Pooja Arrangements",
        "short": "Complete setup for rituals with attention to cultural traditions.",
        "overview": (
            "Complete ritual setup so ceremonies run smoothly and traditionally — "
            "purohit support, pooja materials, mandap, nadaswara, and coordination."
        ),
        "includes": [
            "Purohit / priest coordination",
            "Rangoli / kolam",
            "Floral support & garlands",
            "Mandap setup",
            "Pooja materials",
            "Nadaswara / music support",
            "Ritual coordination",
            "Traditional props, brass & heritage elements",
        ],
        "process": [
            "Ritual requirement discussion",
            "Planning & item arrangement",
            "Setup preparation",
            "Ceremony support",
        ],
        "url": SERVICE_PAGES["rituals"],
        "keywords": ("pooja", "puja", "ritual", "purohit", "priest", "mandap", "nadaswara", "ceremony"),
    },
    "venues": {
        "title": "Venue Assistance & Planning",
        "short": "Helping you choose and organize the perfect venue for your event.",
        "overview": (
            "We help find venues that match guest count, style, and budget — banquet halls, "
            "outdoor lawns, destination options, and budget-friendly spaces across Bengaluru."
        ),
        "includes": [
            "Venue shortlisting",
            "Budget-based recommendations",
            "Site visit coordination",
            "Booking assistance",
            "Vendor coordination",
            "Decor / catering / parking & logistics planning",
            "Guest accommodation support",
        ],
        "process": ["Requirement discussion", "Venue shortlisting", "Site visits", "Booking & coordination"],
        "url": SERVICE_PAGES["venues"],
        "keywords": ("venue", "hall", "banquet", "lawn", "location", "place", "farmhouse", "resort"),
    },
    "hospitality": {
        "title": "Guest Hospitality & Management",
        "short": "Ensuring every guest is welcomed and served with care.",
        "overview": (
            "End-to-end guest care — warm welcome, smooth service, and thoughtful coordination "
            "so families can enjoy the celebration stress-free."
        ),
        "includes": [
            "Guest welcome & service",
            "Day-of coordination",
            "Professional hospitality staff",
            "Smooth dining & guest flow",
        ],
        "process": [],
        "url": WEBSITE_URL,
        "keywords": ("hospitality", "guest", "welcome", "staff", "service team", "management"),
    },
}

SERVICES = [f"{d['title']} — {d['short']}" for d in SERVICE_DETAILS.values()]

PARTNER_VENUES = {
    "North Bengaluru": [
        "Peacock Groove (Hesaraghatta)",
        "Tharavadu Mane (Hesaraghatta)",
        "Nature Knots (Hesaraghatta)",
        "Samaya Leisure (Hesaraghatta)",
        "Samavana (Hesaraghatta)",
        "Aadya Farms (Hesaraghatta)",
        "TTK Lawns & Leisure (Hesaraghatta)",
        "AmitaRasa (Nandi Hills)",
        "Secret Groove (Yelahanka)",
        "Leroma Gardenia (Yelahanka)",
    ],
    "South Bengaluru": [
        "Tamarind Tree (Kanakapura Road)",
        "Angana Courtyard (Kanakapura Road)",
        "Pachavati (Kanakapura Road)",
        "Sarang (Kanakapura Road)",
        "Sristi Vilas (Kanakapura Road)",
        "Kalyani Courtyard (Kanakapura Road)",
        "Brindavan Bliss (Kanakapura Road)",
        "Sambhrama (Kanakapura Road)",
        "Tamara (Kanakapura Road)",
        "Fireflies (Kanakapura Road)",
        "MLR Convention (JP Nagar)",
        "Temple Tree Leisure (Electronic City)",
        "Royalton Leisure (Bannerghatta Road)",
        "Miraya Greens (Bannerghatta Road)",
        "Magnolia Leisure (Chandapura)",
    ],
    "East Bengaluru": [
        "Farm House Collective (Hoskote, Budigere Cross)",
    ],
    "West Bengaluru": [
        "The Beginning (Surgepur Road)",
        "MR Convention (Nayandahalli)",
        "Chamara Vajra Muktha (Palace Grounds)",
        "Ananthya Palace (Palace Grounds)",
    ],
}

EVENT_TYPES = [
    "Wedding",
    "House Warming",
    "Naming Ceremony",
    "Upanayanam",
    "Baby Shower",
    "Engagement",
    "Birthday",
    "Reception",
    "Corporate events",
]

SPECIALTIES = [
    "Hygiene & food safety",
    "Catering expertise — taste, presentation, service",
    "End-to-end support from planning to day-of execution",
    "Customized solutions for vision, scale, and preferences",
    "Reliable, on-time coordination",
    "Attention to detail for guest experience",
    "Authentic Karnataka, Andhra, Tamil Nadu & Kerala cuisine",
    "Three generations of culinary heritage",
]

LEGACY = [
    "2017 — Srivatsanka Wedding & Events Services founded",
    "2022 — Expanded to complete event solutions (catering, décor, venue coordination)",
    "2026 — Crafting fuller celebration experiences",
]

SOCIAL_PROOF = [
    "Trusted since 2017 in Bengaluru for weddings and family celebrations",
    "Google Verified — about 4.6★ rating",
    "GST registered and FSSAI certified",
    "Experience with large gatherings (1000+ guests)",
    "Led by Managing Director Mr. Kannan Sharangapani",
]

TESTIMONIALS = [
    "Suresh & Lakshmi — food authentic & delicious; team handled everything professionally",
    "Raghavan Iyer — grahapravesham pooja setup, catering & service perfectly arranged",
    "Priya Subramanian — décor to food presentation beautifully planned",
    "Arun Kumar & Divya — outstanding taste; handles large gatherings well",
    "Meenakshi Sundaram — maintained tradition; smooth arrangements",
    "Karthik & Shalini — décor & catering customized; very responsive team",
]

FAQS = [
    "End-to-end: planning, venue, catering, décor, rituals, day-of coordination",
    "Large gatherings: experienced with 1000+ guests",
    "Menus: customizable — South Indian, North Indian, fusion, dietary needs",
    "Rituals: purohits, pooja materials, mandaps, nadaswara / music",
    "Budgets: flexible packages; we work within family budgets",
    "Not only weddings — upanayanam, baby shower, engagement, birthday, housewarming, corporate & more",
    "Live stations available (dosa, chaat, ice cream, sweets, juices, etc.)",
    "Partner venues across Bengaluru — or we can work at a venue the client chooses",
    "Tasting sessions available before the event",
]

WEBSITE_ABOUT = (
    "Family legacy of traditional cooking and hospitality, now a trusted catering and celebration "
    "brand across Bengaluru. Three generations of culinary expertise for weddings, upanayanam, baby "
    "showers, engagements, birthdays, housewarming, and family gatherings. Cuisines from Karnataka, "
    "Andhra Pradesh, Tamil Nadu, and Kerala — plus décor, ritual support, venue help, and guest hospitality. "
    "Experience center: Eat Rep Eat at N R Colony."
)

POPULAR_DISHES = [
    "Karnataka wedding meals & local specialties",
    "Andhra regional dishes",
    "Tamil Nadu festive & ceremonial dining",
    "Kerala delicacies",
    "Traditional Brahmin / sattvic pure-veg menus",
    "Live counters — dosa, chaat, tawa, sweets, juices",
]

# Gallery from https://srivatsanka.com/ (home + service pages). category helps photo matching.
GALLERY_ITEMS: list[dict[str, str]] = [
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/1620985900177-1.jpeg", "caption": "Wedding catering spread", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/1657811033159-1.png", "caption": "Guests enjoying our hospitality", "category": "hospitality"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/1714968534703-1.png", "caption": "Food presentation at a celebration", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20231229125945-scaled.jpg", "caption": "Traditional wedding hospitality", "category": "hospitality"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20231229145338-scaled.jpg", "caption": "Wedding celebration arrangements", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240103203446-scaled.jpg", "caption": "Traditional wedding catering", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/Wedding-Pooja-Setup-img-scaled.jpg", "caption": "Wedding pooja / ritual setup", "category": "rituals"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/swing-img.png", "caption": "Traditional wedding swing décor", "category": "decor"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/venues-for-celebration-img-scaled.jpg", "caption": "Celebration venue setup", "category": "venues"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250209202303-scaled.jpg", "caption": "Elegant wedding venue décor", "category": "venues"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250311203649-scaled.jpg", "caption": "Traditional ceremony arrangements", "category": "rituals"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/Decor-for-Celebrations-img.jpg", "caption": "Event décor for celebrations", "category": "decor"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240827170330-Copy-scaled.jpg", "caption": "Celebration décor setup", "category": "decor"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240911195637-Copy-scaled.jpg", "caption": "Decor & celebration styling", "category": "decor"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250129201422-scaled.jpg", "caption": "Catering service moment", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250120130855-scaled.jpg", "caption": "Celebration dining", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240828092141-Copy-scaled.jpg", "caption": "Live catering experience", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250216072908-Copy-scaled.jpg", "caption": "Ritual / ceremony support", "category": "rituals"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/05/banner-img-banana-leaf.jpg", "caption": "South Indian banana-leaf hospitality", "category": "catering"},
    {"url": "https://srivatsanka.com/wp-content/uploads/2026/03/hero-img-scaled.jpg", "caption": "Srivatsanka celebration moment", "category": "hospitality"},
]

GALLERY_IMAGE_URLS = [item["url"] for item in GALLERY_ITEMS]
WELCOME_IMAGE_CAPTIONS = [item["caption"] for item in GALLERY_ITEMS[:3]]


def gallery_urls() -> list[str]:
    return list(GALLERY_IMAGE_URLS)


def match_service_key(text: str) -> str | None:
    """Detect which service the customer is asking about."""
    t = (text or "").lower()
    best: str | None = None
    for key, detail in SERVICE_DETAILS.items():
        if any(k in t for k in detail["keywords"]):
            best = key
            break
    if "what do you offer" in t or "your services" in t or "what services" in t:
        return "all"
    return best


def short_services_reply() -> str:
    return (
        "Yes — catering, décor, pooja/ritual setup, venue help, and guest hospitality.\n"
        "What type of event are you planning?"
    )


def service_answer(key: str) -> str:
    if key == "all":
        return short_services_reply()
    detail = SERVICE_DETAILS.get(key)
    if not detail:
        return short_services_reply()
    return f"{detail['title']}: {detail['short']}\nWant more detail, or shall we note your event details?"


EVENT_TYPE_DETAILS: dict[str, dict] = {
    "Wedding": {
        "title": "Wedding Events",
        "short_reply": "We handle wedding catering, décor, rituals, and venue support 🌿",
        "description": (
            "Multi-day wedding catering, live counters, décor, ritual support, venue help, and guest hospitality."
        ),
        "image_captions": ["Wedding catering spread", "Wedding pooja / ritual setup", "Traditional wedding swing décor"],
    },
    "House Warming": {
        "title": "House Warming",
        "short_reply": "Warm menus and ritual support for house warming / griha pravesham 🏠",
        "description": "Homely menus plus traditional griha pravesham setup for family and neighbours.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Baby Shower": {
        "title": "Baby Shower",
        "short_reply": "Light festive menus and décor for baby showers 🎀",
        "description": "Festive menus, sweets, and celebration décor for the new arrival.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Engagement": {
        "title": "Engagement",
        "short_reply": "Elegant engagement catering and celebration support 💍",
        "description": "Custom engagement menus, décor setups, and hospitality.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Birthday": {
        "title": "Birthday",
        "short_reply": "Homely birthday menus and guest hospitality 🎂",
        "description": "Family birthday catering with authentic vegetarian menus.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Reception": {
        "title": "Reception",
        "short_reply": "Grand veg reception spreads with smooth service ✨",
        "description": "Multi-cuisine veg spreads, live counters, and service for large guest lists.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Corporate events": {
        "title": "Corporate Events",
        "short_reply": "On-time pure-veg food for office & corporate events 💼",
        "description": "Hygienic, on-time pure-veg menus for office lunches and team events.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Naming Ceremony": {
        "title": "Naming Ceremony",
        "short_reply": "Traditional naming ceremony menus with homely veg meals 🙏",
        "description": "Homely meals, sweets, snacks, and ritual support for naming ceremonies.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Upanayanam": {
        "title": "Upanayanam",
        "short_reply": "Sattvic pure-veg meals and ritual support for upanayanam 🙏",
        "description": "Sacred ceremony menus with sattvic meals and traditional ritual arrangements.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "General": {
        "title": "Celebration Events",
        "short_reply": "End-to-end catering & celebration support for family functions 🌿",
        "description": "Custom pure-veg menus plus décor, rituals, venues, and hospitality.",
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
}


def match_event_type(text: str) -> str:
    """Map customer text to a known occasion type. Never invents custom types from names."""
    import difflib

    lower = re.sub(r"\s+", " ", (text or "").lower().strip())
    if len(lower) < 2:
        return "General"

    skip = {
        "ok",
        "okay",
        "yes",
        "yeah",
        "sure",
        "fine",
        "continue",
        "proceed",
        "go ahead",
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
    }
    if lower in skip:
        return "General"

    aliases: dict[str, str] = {
        "wedding": "Wedding",
        "weddign": "Wedding",
        "weding": "Wedding",
        "marriage": "Wedding",
        "marraige": "Wedding",
        "reception": "Reception",
        "receiption": "Reception",
        "house warming": "House Warming",
        "housewarming": "House Warming",
        "house worming": "House Warming",
        "griha": "House Warming",
        "griha pravesham": "House Warming",
        "grahapravesham": "House Warming",
        "baby shower": "Baby Shower",
        "babyshower": "Baby Shower",
        "seemantham": "Baby Shower",
        "seemanth": "Baby Shower",
        "naming ceremony": "Naming Ceremony",
        "namimg ceremony": "Naming Ceremony",
        "name ceremony": "Naming Ceremony",
        "upanayanam": "Upanayanam",
        "upanayan": "Upanayanam",
        "engagement": "Engagement",
        "birthday": "Birthday",
        "corporate": "Corporate events",
        "office lunch": "Corporate events",
        "corporate lunch": "Corporate events",
    }
    # Prefer longer / multi-word keys first
    for key, canonical in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        if key in lower:
            return canonical

    for event in EVENT_TYPES:
        if event.lower() in lower:
            return event

    # Fuzzy match only against known occasion words — never free-text names
    occasion_keys = list(aliases.keys()) + [e.lower() for e in EVENT_TYPES]
    words = re.findall(r"[a-z]+", lower)
    for word in words:
        if len(word) < 5:
            continue
        matches = difflib.get_close_matches(word, occasion_keys, n=1, cutoff=0.86)
        if matches:
            matched = matches[0]
            if matched in aliases:
                return aliases[matched]
            for event in EVENT_TYPES:
                if event.lower() == matched:
                    return event

    return "General"


def is_known_event_type(event_type: str | None) -> bool:
    if not event_type:
        return False
    return event_type in EVENT_TYPE_DETAILS and event_type != "General"



def _partner_venues_blurb() -> str:
    lines = []
    for region, venues in PARTNER_VENUES.items():
        sample = ", ".join(venues[:3])
        lines.append(f"- {region}: e.g. {sample} (+ more)")
    return "\n".join(lines)


def build_short_company_context() -> str:
    return (
        f"{COMPANY['legal_name']} — Bengaluru since {COMPANY['established']}, "
        f"led by {COMPANY['managing_director']}. "
        f"Phone {COMPANY['phone']}. Site {WEBSITE_URL}. "
        f"Offers: catering, décor, pooja/rituals, venues, guest hospitality. "
        f"Cuisines: Karnataka, Andhra, Tamil Nadu, Kerala. "
        f"Always introduce the company as \"{COMPANY['legal_name']}\" (full name). "
        f"Reply only from this website knowledge."
    )


def build_agent_context() -> str:
    """Full website knowledge for Gemini — answers must come from this data."""
    services_block = "\n".join(
        f"- {d['title']}: {d['short']} | Includes: {', '.join(d['includes'][:6])}"
        f"{'…' if len(d['includes']) > 6 else ''} | More: {d['url']}"
        for d in SERVICE_DETAILS.values()
    )
    catering = SERVICE_DETAILS["catering"]
    live = ", ".join(catering["live_stations"])
    specialties = "\n".join(f"- {s}" for s in SPECIALTIES)
    proof = "\n".join(f"- {s}" for s in SOCIAL_PROOF)
    faqs = "\n".join(f"- {f}" for f in FAQS)
    quotes = "\n".join(f"- {t}" for t in TESTIMONIALS[:4])
    legacy = "; ".join(LEGACY)
    venues = _partner_venues_blurb()

    return f"""
OFFICIAL WEBSITE KNOWLEDGE (source of truth: {WEBSITE_URL})
Answer customer questions ONLY using this data. Keep replies short (WhatsApp style).
If unsure, share {WEBSITE_URL} or offer a callback — never invent prices or packages.

COMPANY
- {COMPANY['legal_name']}, est. {COMPANY['established']}
- Always say the full company name: Srivatsanka Events and Services (not a short brand only)
- Tagline: {COMPANY['tagline']}
- {COMPANY['hero_line']}
- {COMPANY['services_intro']}
- MD: {COMPANY['managing_director']} | Founder: {COMPANY['founder']} | Culture: {COMPANY['director_culture']}
- Phone {COMPANY['phone']} | WhatsApp {COMPANY['whatsapp']} | {COMPANY['email']}
- Address: {COMPANY['address']}
- Eat Rep Eat: {COMPANY['experience_center']} | {COMPANY['eat_rep_eat_address']} | {COMPANY['eat_rep_eat_hours']} | {COMPANY['eat_rep_eat_phone']} | {COMPANY['eat_rep_eat_url']}

ABOUT
{WEBSITE_ABOUT}

LEGACY
{legacy}

SERVICES (end-to-end)
{services_block}

CATERING HIGHLIGHTS
- Live stations: {live}
- Process: {' → '.join(catering['process'])}
- Page: {catering['url']}

OCCASIONS
{', '.join(EVENT_TYPES)}

PARTNER VENUES (examples — full list on {SERVICE_PAGES['partner_venues']})
{venues}
Note: Preferred partners; we can also work at a venue the client chooses.

STRENGTHS
{specialties}

REPUTATION
{proof}

CUSTOMER FEEDBACK
{quotes}

FAQS
{faqs}

PHOTOS
- {len(GALLERY_ITEMS)} real event photos from the website (catering, décor, rituals, venues).
- When customers ask for photos, WhatsApp shares gallery images automatically.
- Full gallery: {SERVICE_PAGES['gallery']}

REPLY GUIDANCE (internal — never show these headings or this block to the customer)
- Answer only from the knowledge above, in short natural WhatsApp sentences.
- Never paste section titles like COMPANY, SERVICES, FAQS, RULES, or markdown like **.
- Prefer short natural replies; link {WEBSITE_URL} when useful.
- Never say you cannot share photos — gallery images are sent when asked.
""".strip()
