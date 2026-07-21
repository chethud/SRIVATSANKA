"""Brand knowledge from https://srivatsanka.com/ for the WhatsApp agent."""

import re

WEBSITE_URL = "https://srivatsanka.com/"

COMPANY = {
    "legal_name": "Srivatsanka Events & Services",
    "brand_name": "SRIVATSANKA EVENTS",
    "established": "2017",
    "managing_director": "Mr. Kannan Sharangapani",
    "founder": "Sri R. V. Sharangapani",
    "director_culture": "Mrs. Sangeetha K. S.",
    "phone": "+91-9945607074",
    "whatsapp": "+91-9945607074",
    "phone_alt": "+91-9945927101",
    "email": "srivatsankas@gmail.com",
    "address": "#1, 4th Cross, 4th Main, N R Colony, Bengaluru 560019",
    "tagline": "Where Celebrations Become Beautiful Memories",
    "experience_center": "Eat Repeat (Eat Rep Eat) — authentic Brahmin / vegetarian dining & hospitality experience center",
}

SERVICES = [
    "Catering — curated menus, authentic flavors, seamless celebration service",
    "Decor for Celebrations — elegant, immersive décor concepts",
    "Event Ritual Support — traditional pooja / ritual arrangements",
    "Venues for Celebrations — handpicked venue options for your event scale",
    "Guest hospitality & end-to-end event coordination",
]

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
    "Hygiene & food safety in cooking and serving",
    "Catering expertise — consistent taste, presentation, and service",
    "End-to-end support from planning to day-of execution",
    "Customized menus for preferences, diet, and cultural traditions",
    "Reliable, on-time coordination",
    "Attention to detail for guest experience",
    "Authentic cuisine from Karnataka, Andhra Pradesh, Tamil Nadu, and Kerala",
    "Three generations of culinary heritage and hospitality",
]

SOCIAL_PROOF = [
    "Trusted since 2017 in Bengaluru for weddings and family celebrations",
    "Google Verified — about 4.6★ rating",
    "GST registered and FSSAI certified",
    "Families praise food quality, décor, ritual setup, and stress-free execution",
    "Experience with large gatherings (1000+ guests)",
    "Led by Managing Director Mr. Kannan Sharangapani",
]

TESTIMONIALS = [
    "Suresh & Lakshmi Narayanan — catering exceeded expectations with exceptional taste and presentation",
    "Raghavan Iyer — every detail handled perfectly; stress-free celebration",
    "Priya Subramanian — décor to catering executed flawlessly",
    "Arun Kumar & Divya — professionalism and quality made the event unforgettable",
    "Meenakshi Sundaram — food, service, and overall execution outstanding",
    "Karthik & Shalini — understood requirements and delivered an elegant, organized event",
]

FAQS = [
    "End-to-end support: planning, venue, catering, décor, rituals, and day-of coordination",
    "Large gatherings: experienced with 1000+ guests",
    "Customized catering: South Indian, North Indian, fusion, and dietary needs",
    "Traditional rituals: purohits, pooja materials, mandaps, nadaswara / music support",
    "Flexible packages that work within family budgets",
]

WEBSITE_ABOUT = (
    "What began as a family legacy of traditional cooking and hospitality has evolved into a trusted "
    "catering and celebration services brand serving families across Bengaluru and beyond. "
    "With three generations of culinary expertise, Srivatsanka Events & Services specializes in catering "
    "for weddings, upanayanam, baby showers, engagements, birthdays, housewarming functions, and family "
    "gatherings. Along with authentic cuisine from Karnataka, Andhra Pradesh, Tamil Nadu, and Kerala, "
    "we also provide décor, ritual support, and event coordination. Our journey is built on tradition, "
    "trust, relationships, and bringing people together through exceptional food and meaningful celebrations."
)

WEBSITE_VIDEOS = [
    "Video portfolio on the website — catering experiences, traditional celebrations, hospitality, and media mentions",
]

POPULAR_DISHES = [
    "Authentic Karnataka, Andhra, Tamil Nadu & Kerala delicacies",
    "Traditional Brahmin / sattvic pure-veg menus",
    "Live food counters",
    "Custom wedding and multi-day celebration spreads",
    "Homely snacks, sweets, and festive meals",
]

# Full-size gallery from https://srivatsanka.com/ (featured gallery + event photos)
GALLERY_ITEMS: list[dict[str, str]] = [
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/1620985900177-1.jpeg",
        "caption": "Wedding catering — pure veg celebration spread",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/1657811033159-1.png",
        "caption": "Past celebration — guests enjoying our hospitality",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/1714968534703-1.png",
        "caption": "Beautiful food presentation at a family celebration",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20231229125945-scaled.jpg",
        "caption": "Traditional wedding hospitality service",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20231229145338-scaled.jpg",
        "caption": "Wedding planning and celebration arrangements",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240103203446-scaled.jpg",
        "caption": "Traditional wedding catering arrangement",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/Wedding-Pooja-Setup-img-scaled.jpg",
        "caption": "Wedding pooja / ritual setup",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/swing-img.png",
        "caption": "Traditional wedding swing decorations",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/venues-for-celebration-img-scaled.jpg",
        "caption": "Venues for celebrations",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250209202303-scaled.jpg",
        "caption": "Elegant wedding venue décor",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250311203649-scaled.jpg",
        "caption": "Traditional wedding ceremony arrangements",
    },
    {
        "url": "https://srivatsanka.com/wp-content/uploads/2026/05/banner-img-banana-leaf.jpg",
        "caption": "Authentic South Indian banana-leaf hospitality",
    },
]

GALLERY_IMAGE_URLS = [item["url"] for item in GALLERY_ITEMS]

WELCOME_IMAGE_CAPTIONS = [item["caption"] for item in GALLERY_ITEMS[:3]]


def gallery_urls() -> list[str]:
    return list(GALLERY_IMAGE_URLS)

EVENT_TYPE_DETAILS: dict[str, dict] = {
    "Wedding": {
        "title": "Wedding Events",
        "short_reply": "We handle wedding catering, décor, rituals, and venue support 🌿",
        "description": (
            "Multi-day wedding catering with authentic South Indian regional cuisines, "
            "live counters, décor, ritual support, and smooth guest hospitality."
        ),
        "image_captions": [
            "Wedding catering — pure veg celebration spread",
            "Traditional wedding hospitality service",
            "Wedding pooja / ritual setup",
        ],
    },
    "House Warming": {
        "title": "House Warming",
        "short_reply": "Warm menus and ritual support for house warming / griha pravesham 🏠",
        "description": (
            "Homely menus with snacks, meals, and desserts — plus traditional setup for "
            "griha pravesham with neighbours and close family."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Baby Shower": {
        "title": "Baby Shower",
        "short_reply": "Light festive menus perfect for baby showers 🎀",
        "description": (
            "Light, festive menus with snacks, sweets, and refreshing beverages — "
            "beautiful presentation for celebrating the new arrival."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Engagement": {
        "title": "Engagement",
        "short_reply": "Elegant engagement catering and celebration support 💍",
        "description": (
            "Custom engagement menus and hospitality so family and guests enjoy a warm, well-organized celebration."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Birthday": {
        "title": "Birthday",
        "short_reply": "Homely birthday menus and guest hospitality 🎂",
        "description": (
            "Family birthday catering with authentic vegetarian menus and thoughtful service."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Reception": {
        "title": "Reception",
        "short_reply": "Grand veg reception spreads with smooth service for big guest lists ✨",
        "description": (
            "Grand reception dining with multi-cuisine veg spreads, live counters, and "
            "smooth service for large guest lists."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Corporate events": {
        "title": "Corporate Events",
        "short_reply": "On-time pure-veg food for office & corporate events 💼",
        "description": (
            "Professional food & hospitality for office lunches, conferences, and team events — "
            "hygienic, on-time, and customisable pure-veg menus."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Naming Ceremony": {
        "title": "Naming Ceremony",
        "short_reply": "Traditional naming ceremony menus with homely veg meals 🙏",
        "description": (
            "Traditional naming ceremony menus with homely meals, sweets, and snacks for family and guests."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "Upanayanam": {
        "title": "Upanayanam",
        "short_reply": "Sattvic pure-veg meals and ritual support for upanayanam 🙏",
        "description": (
            "Sacred ceremony menus with sattvic pure-veg meals and traditional ritual arrangements."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
    "General": {
        "title": "Celebration Events",
        "short_reply": "We plan custom pure-veg menus for all family celebrations 🌿",
        "description": (
            "Custom pure-veg menus for naming ceremonies, upanayanam, birthdays, engagements, "
            "and family functions — we plan every detail with you."
        ),
        "image_captions": WELCOME_IMAGE_CAPTIONS,
    },
}


def match_event_type(text: str) -> str:
    """Map customer text to a known occasion type (tolerates common spelling mistakes)."""
    import difflib

    lower = re.sub(r"\s+", " ", (text or "").lower().strip())
    if len(lower) < 2:
        return "General"

    skip = {"ok", "okay", "yes", "yeah", "sure", "fine", "continue", "proceed", "go ahead", "hi", "hello"}
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
        "naming": "Naming Ceremony",
        "naming ceremony": "Naming Ceremony",
        "namimg": "Naming Ceremony",
        "upanayanam": "Upanayanam",
        "upanayan": "Upanayanam",
        "engagement": "Engagement",
        "birthday": "Birthday",
        "corporate": "Corporate events",
        "office": "Corporate events",
        "office lunch": "Corporate events",
        "corporate lunch": "Corporate events",
        "anniversary": "General",
        "occasion": "General",
        "function": "General",
        "celebration": "General",
    }
    for key, canonical in aliases.items():
        if key in lower:
            return canonical

    for event in EVENT_TYPES:
        if event.lower() in lower:
            return event

    words = re.findall(r"[a-z]+", lower)
    alias_keys = list(aliases.keys()) + [e.lower() for e in EVENT_TYPES]
    for word in words:
        if len(word) < 4:
            continue
        matches = difflib.get_close_matches(word, alias_keys, n=1, cutoff=0.78)
        if matches:
            matched = matches[0]
            if matched in aliases:
                return aliases[matched]
            for event in EVENT_TYPES:
                if event.lower() == matched:
                    return event

    if len(lower) >= 4 and lower not in {"general", "other", "others"}:
        return text.strip().title()
    return "General"


def build_short_company_context() -> str:
    """Brief company facts for natural Q&A replies."""
    return (
        f"{COMPANY['brand_name']} ({COMPANY['legal_name']}) — celebration catering & event services in Bengaluru "
        f"since {COMPANY['established']}, led by {COMPANY['managing_director']}. "
        f"Phone {COMPANY['phone']}. Website {WEBSITE_URL}. "
        f"Services: catering, décor, ritual support, and venues. "
        f"Cuisines from Karnataka, Andhra Pradesh, Tamil Nadu, and Kerala."
    )


def build_agent_context() -> str:
    """Compact knowledge block injected into the Gemini system prompt."""
    services = "\n".join(f"- {s}" for s in SERVICES)
    events = ", ".join(EVENT_TYPES)
    specialties = "\n".join(f"- {s}" for s in SPECIALTIES)
    proof = "\n".join(f"- {s}" for s in SOCIAL_PROOF)
    dishes = ", ".join(POPULAR_DISHES)
    videos = "; ".join(WEBSITE_VIDEOS)
    faqs = "\n".join(f"- {f}" for f in FAQS)
    quotes = "\n".join(f"- {t}" for t in TESTIMONIALS[:4])

    return f"""
COMPANY (official website: {WEBSITE_URL})
- {COMPANY['legal_name']} ({COMPANY['brand_name']}), established {COMPANY['established']}
- Managing Director: {COMPANY['managing_director']}
- Founder: {COMPANY['founder']}; Director – Culture: {COMPANY['director_culture']}
- Tagline: {COMPANY['tagline']}
- Pure vegetarian / traditional celebration catering — Bengaluru
- Contact: {COMPANY['phone']} | WhatsApp {COMPANY['whatsapp']} | Alt {COMPANY['phone_alt']} | {COMPANY['email']}
- Address: {COMPANY['address']}
- Experience center: {COMPANY['experience_center']}

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

CUSTOMER FEEDBACK (from website)
{quotes}

FAQS (from website)
{faqs}

GALLERY & VIDEOS
- We have {len(GALLERY_ITEMS)} event photos from past weddings and celebrations on our website.
- When customers ask for photos, our WhatsApp system shares real gallery images from past events automatically.
- Website gallery & videos: {WEBSITE_URL} — includes "{videos}".

WHATSAPP CAPABILITIES
- You CAN share event photos directly on WhatsApp — the system sends gallery images when customers ask.
- Never say you cannot share photos on WhatsApp. Say you are sharing sample photos from past events now.
- Also share {WEBSITE_URL} for the full gallery, services, and enquiry form.
- Base every company answer on this website knowledge. If unsure, invite them to visit {WEBSITE_URL} or speak with our team.
""".strip()
