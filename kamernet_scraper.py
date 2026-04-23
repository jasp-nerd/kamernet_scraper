#!/usr/bin/env python3
"""
Kamernet.nl Ethical Scraper
Scrapes new listings from Kamernet.nl following robots.txt guidelines
Sends Discord notifications for new listings

Discord Webhook Limitations (documented for reference):
- Rate Limit: 30 requests per 60 seconds per webhook (global limit)
- Per-webhook limit: 5 requests per 2 seconds
- Max embeds per message: 10 embeds
- Max embed description: 4096 characters
- Max embed title: 256 characters
- Max embed fields: 25 fields per embed
- Max embed field name: 256 characters
- Max embed field value: 1024 characters
- Max total characters per embed: 6000 characters
- 500 errors typically mean: embed is too large/complex or invalid data
"""

import requests
import json
import time
import re
import os
import random
from datetime import datetime
from typing import Dict, List, Set, Optional
from discord_webhook import DiscordWebhook, DiscordEmbed

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

class KamernetScraper:
    def __init__(self, discord_webhook_url: str, database_url: str = None):
        """
        Initialize the Kamernet scraper

        Args:
            discord_webhook_url: Discord webhook URL for notifications
            database_url: Optional Postgres connection string (Neon/Vercel Postgres)

        Search Details:
        - Location: Amsterdam + 5km radius (includes surrounding cities)
        - Sort: Newest listings first (sort=1)
        - Price: No maximum (maxRent=10 means unlimited)
        - Filters: No requirements (accepts all property types and amenities)
        """
        self.discord_webhook_url = discord_webhook_url
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.db_conn = None
        if self.database_url and HAS_PSYCOPG2:
            self._connect_db()
        self.base_url = "https://kamernet.nl"
        self.search_url = "https://kamernet.nl/huren/huurwoningen-amsterdam?pageNo=1&radius=5&minSize=0&maxRent=10&searchView=1&sort=1&hasInternet=false&isBathroomPrivate=false&isKitchenPrivate=false&isToiletPrivate=false&suitableForNumberOfPersons=0&isSmokingInsideAllowed=false&isPetsInsideAllowed=false&nwlat=54.216270703936516&nwlng=-3.267085312500001&selat=50.130263513834905&selng=12.5532271875&mapZoom=7&mapMarkerLat=0&mapMarkerLng=0"
        self.session = requests.Session()
        
        # Set a respectful user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # File to store seen listings
        # WARNING: On Heroku, this file will be lost on dyno restart (every ~24h)
        # Consider using PostgreSQL addon or S3 for persistent storage in production
        self.seen_listings_file = "seen_listings.json"
        self.seen_listings: Set[int] = self.load_seen_listings()

        # AI scoring via OpenRouter
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-120b:free')
        self.openrouter_fallback_model = os.getenv('OPENROUTER_FALLBACK_MODEL', 'deepseek/deepseek-v3.2')

        # Telegram notifications
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_score_threshold = int(os.getenv('TELEGRAM_SCORE_THRESHOLD', '80'))
        self.telegram_password = os.getenv('TELEGRAM_PASSWORD', 'snoezepoes@Sofia')
        self.telegram_last_update_id = 0

        # Search parameters from the provided URL
        self.search_params = {
            'pageNo': 1,
            'radius': 5,
            'minSize': 0,
            'maxRent': 0,
            'searchView': 1,
            'sort': 1,  # Sort by newest first
            'hasInternet': 'false',
            'isBathroomPrivate': 'false',
            'isKitchenPrivate': 'false',
            'isToiletPrivate': 'false',
            'suitableForNumberOfPersons': 0,
            'isSmokingInsideAllowed': 'false',
            'isPetsInsideAllowed': 'false',
            'nwlat': 54.216270703936516,
            'nwlng': -3.267085312500001,
            'selat': 50.130263513834905,
            'selng': 12.5532271875,
            'mapZoom': 7,
            'mapMarkerLat': 0,
            'mapMarkerLng': 0
        }
        
    def load_seen_listings(self) -> Set[int]:
        """Load previously seen listing IDs from DB (preferred) or JSON file (fallback)"""
        # Try database first
        db_listings = self._load_seen_listings_from_db()
        if db_listings:
            print(f"Loaded {len(db_listings)} seen listings from database")
            return db_listings
        # Fallback to JSON file
        if os.path.exists(self.seen_listings_file):
            try:
                with open(self.seen_listings_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('seen_listings', []))
            except Exception as e:
                print(f"Error loading seen listings: {e}")
                return set()
        return set()
    
    def save_seen_listings(self):
        """Save seen listing IDs to file"""
        try:
            data = {
                'seen_listings': list(self.seen_listings),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.seen_listings_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving seen listings: {e}")
    
    # ── Database methods ──────────────────────────────────────────────

    def _connect_db(self):
        """Connect to Neon Postgres. Reconnects if connection is closed."""
        if not self.database_url or not HAS_PSYCOPG2:
            return
        try:
            if self.db_conn and not self.db_conn.closed:
                return
            self.db_conn = psycopg2.connect(
                self.database_url,
                sslmode='require',
                connect_timeout=10
            )
            self.db_conn.autocommit = True
            print("✅ Connected to Postgres")
        except Exception as e:
            print(f"⚠️  DB connection error: {e}")
            self.db_conn = None

    def _ensure_db(self) -> bool:
        """Ensure DB connection is alive. Returns True if connected."""
        if not self.database_url or not HAS_PSYCOPG2:
            return False
        self._connect_db()
        return self.db_conn is not None and not self.db_conn.closed

    def _load_seen_listings_from_db(self) -> Set[int]:
        """Load seen listing IDs from Postgres."""
        if not self._ensure_db():
            return set()
        try:
            cur = self.db_conn.cursor()
            cur.execute("SELECT listing_id FROM listings")
            return {row[0] for row in cur.fetchall()}
        except Exception as e:
            print(f"⚠️  DB load seen listings error: {e}")
            return set()

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse ISO date string to a format Postgres accepts."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).isoformat()
        except Exception:
            return None

    def _parse_date_only(self, date_str: Optional[str]) -> Optional[str]:
        """Parse ISO date string to DATE (no time)."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        except Exception:
            return None

    def _listing_to_params(self, listing: Dict) -> Dict:
        """Map scraped listing dict to SQL parameter dict."""
        return {
            'listing_id': listing.get('listingId'),
            'street': listing.get('street'),
            'city': listing.get('city'),
            'city_slug': listing.get('citySlug'),
            'street_slug': listing.get('streetSlug'),
            'postal_code': listing.get('postal_code'),
            'house_number': listing.get('house_number'),
            'house_number_addition': listing.get('house_number_addition'),
            'listing_type': listing.get('listingType'),
            'furnishing_id': listing.get('furnishingId'),
            'total_rental_price': listing.get('totalRentalPrice'),
            'surface_area': listing.get('surfaceArea'),
            'deposit': listing.get('deposit'),
            'utilities_included': listing.get('utilitiesIncluded'),
            'num_bedrooms': listing.get('num_bedrooms'),
            'num_rooms': listing.get('num_rooms'),
            'energy_label_id': listing.get('energy_label_id'),
            'pets_allowed': listing.get('pets_allowed'),
            'smoking_allowed': listing.get('smoking_allowed'),
            'registration_allowed': listing.get('registration_allowed'),
            'min_age': listing.get('min_age'),
            'max_age': listing.get('max_age'),
            'suitable_for_persons': listing.get('suitable_for_persons'),
            'availability_start': self._parse_date_only(listing.get('availabilityStartDate')),
            'availability_end': self._parse_date_only(listing.get('availabilityEndDate')),
            'detailed_title': listing.get('detailed_title'),
            'detailed_description': listing.get('detailed_description'),
            'thumbnail_url': listing.get('thumbnailUrl'),
            'full_preview_image_url': listing.get('resizedFullPreviewImageUrl') or listing.get('fullPreviewImageUrl'),
            'additional_images': json.dumps(listing.get('additional_images', [])),
            'landlord_name': listing.get('landlord_name'),
            'landlord_verified': listing.get('landlord_verified', False),
            'landlord_response_rate': listing.get('landlord_response_rate'),
            'landlord_response_time': listing.get('landlord_response_time'),
            'landlord_member_since': self._parse_date(listing.get('landlord_member_since')),
            'landlord_last_seen': self._parse_date(listing.get('landlord_last_seen')),
            'landlord_active_listings': listing.get('landlord_active_listings'),
            'create_date': self._parse_date(listing.get('create_date') or listing.get('createDate')),
            'publish_date': self._parse_date(listing.get('publish_date') or listing.get('publishDate')),
            'is_new_advert': listing.get('isNewAdvert', False),
            'is_top_advert': listing.get('isTopAdvert', False),
        }

    def _upsert_listing(self, listing: Dict):
        """Upsert a listing into Postgres."""
        if not self._ensure_db():
            return
        try:
            params = self._listing_to_params(listing)
            cur = self.db_conn.cursor()
            cur.execute("""
                INSERT INTO listings (
                    listing_id, street, city, city_slug, street_slug,
                    postal_code, house_number, house_number_addition,
                    listing_type, furnishing_id,
                    total_rental_price, surface_area, deposit, utilities_included,
                    num_bedrooms, num_rooms, energy_label_id,
                    pets_allowed, smoking_allowed, registration_allowed,
                    min_age, max_age, suitable_for_persons,
                    availability_start, availability_end,
                    detailed_title, detailed_description,
                    thumbnail_url, full_preview_image_url, additional_images,
                    landlord_name, landlord_verified, landlord_response_rate,
                    landlord_response_time, landlord_member_since, landlord_last_seen,
                    landlord_active_listings,
                    create_date, publish_date,
                    is_new_advert, is_top_advert,
                    first_seen_at, last_seen_at
                ) VALUES (
                    %(listing_id)s, %(street)s, %(city)s, %(city_slug)s, %(street_slug)s,
                    %(postal_code)s, %(house_number)s, %(house_number_addition)s,
                    %(listing_type)s, %(furnishing_id)s,
                    %(total_rental_price)s, %(surface_area)s, %(deposit)s, %(utilities_included)s,
                    %(num_bedrooms)s, %(num_rooms)s, %(energy_label_id)s,
                    %(pets_allowed)s, %(smoking_allowed)s, %(registration_allowed)s,
                    %(min_age)s, %(max_age)s, %(suitable_for_persons)s,
                    %(availability_start)s, %(availability_end)s,
                    %(detailed_title)s, %(detailed_description)s,
                    %(thumbnail_url)s, %(full_preview_image_url)s, %(additional_images)s,
                    %(landlord_name)s, %(landlord_verified)s, %(landlord_response_rate)s,
                    %(landlord_response_time)s, %(landlord_member_since)s, %(landlord_last_seen)s,
                    %(landlord_active_listings)s,
                    %(create_date)s, %(publish_date)s,
                    %(is_new_advert)s, %(is_top_advert)s,
                    NOW(), NOW()
                )
                ON CONFLICT (listing_id) DO UPDATE SET
                    total_rental_price = EXCLUDED.total_rental_price,
                    surface_area = EXCLUDED.surface_area,
                    last_seen_at = NOW(),
                    disappeared_at = NULL,
                    updated_at = NOW(),
                    is_new_advert = EXCLUDED.is_new_advert,
                    is_top_advert = EXCLUDED.is_top_advert
            """, params)
        except Exception as e:
            print(f"⚠️  DB upsert error for {listing.get('listingId')}: {e}")

    def _touch_listings(self, listing_ids: List[int]):
        """Update last_seen_at for all listings found in this cycle."""
        if not self._ensure_db() or not listing_ids:
            return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                UPDATE listings
                SET last_seen_at = NOW(), disappeared_at = NULL
                WHERE listing_id = ANY(%s)
            """, (listing_ids,))
        except Exception as e:
            print(f"⚠️  DB touch error: {e}")

    def _mark_disappeared(self):
        """Mark listings as disappeared if not seen for 30+ minutes."""
        if not self._ensure_db():
            return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                UPDATE listings
                SET disappeared_at = NOW()
                WHERE disappeared_at IS NULL
                  AND last_seen_at < NOW() - INTERVAL '30 minutes'
            """)
            if cur.rowcount > 0:
                print(f"📤 Marked {cur.rowcount} listings as disappeared")
        except Exception as e:
            print(f"⚠️  DB mark disappeared error: {e}")

    def _log_scrape_run(self, total_found: int, new_found: int, error: str = None):
        """Log a scrape run for observability."""
        if not self._ensure_db():
            return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                INSERT INTO scrape_runs (started_at, finished_at, total_found, new_found, errors)
                VALUES (NOW(), NOW(), %s, %s, %s)
            """, (total_found, new_found, error))
        except Exception as e:
            print(f"⚠️  DB log scrape run error: {e}")

    # ── End database methods ─────────────────────────────────────────

    # ── AI scoring methods ───────────────────────────────────────────

    ENERGY_LABEL_MAP = {1: "A++", 2: "A+", 3: "A", 4: "B", 5: "C", 6: "D", 7: "E", 8: "F", 9: "G"}

    def _build_scoring_prompt(self, listing: Dict) -> str:
        """Build a structured prompt for AI scoring of a listing."""
        listing_type = listing.get('listingType', 0)
        furnishing_id = listing.get('furnishingId', 0)
        type_text = self.TYPE_MAP.get(listing_type, "Unknown")
        furnishing_text = self.FURNISHING_MAP.get(furnishing_id, "Unknown")
        energy_text = self.ENERGY_LABEL_MAP.get(listing.get('energy_label_id'), "Unknown")

        avail_start = listing.get('availabilityStartDate') or listing.get('availability_start') or 'Unknown'
        avail_end = listing.get('availabilityEndDate') or listing.get('availability_end') or 'Indefinite'
        description = listing.get('detailed_description') or ''

        listing_data = f"""- Title: {listing.get('detailed_title', 'N/A')}
- Price: EUR {listing.get('totalRentalPrice', 'N/A')}/month
- Deposit: EUR {listing.get('deposit', 'N/A')}
- Utilities included: {listing.get('utilitiesIncluded', 'Unknown')}
- Area: {listing.get('surfaceArea', 'N/A')} m2
- City: {listing.get('city', 'N/A')}, Postal Code: {listing.get('postal_code', 'N/A')}
- Street: {listing.get('street', 'N/A')} {listing.get('house_number', '')}
- Type: {type_text} (listingType id={listing_type}; 1=Room in shared house, 2=Apartment self-contained, 3/4=Studio self-contained)
- Furnishing: {furnishing_text}
- Rooms: {listing.get('num_rooms', 'N/A')}, Bedrooms: {listing.get('num_bedrooms', 'N/A')}
- Energy label: {energy_text}
- Pets allowed: {listing.get('pets_allowed', 'Unknown')}
- Smoking allowed: {listing.get('smoking_allowed', 'Unknown')}
- Registration allowed: {listing.get('registration_allowed', 'Unknown')}
- Age range: {listing.get('min_age', 'N/A')}-{listing.get('max_age', 'N/A')}
- Suitable for: {listing.get('suitable_for_persons', 'N/A')} person(s)  [NOTE: this field is unreliable on Kamernet — see rules below]
- Available from: {avail_start}
- Available until: {avail_end}
- Description: {description}"""

        return f"""You are a rental listing evaluator for two people (ages 20 and 24) looking for a long-term home near VU Amsterdam (postal code 1081 BT). Budget: around EUR 2000/month, ideally lower.

## How to read the data
You MUST consider ALL of the structured fields below — listingType, num_bedrooms, num_rooms, surfaceArea, postalCode, city, street — not only the description. Kamernet fields are sometimes ambiguous; cross-check structured fields against the description before drawing conclusions. Examples:
- `suitable_for_persons` is frequently set to 1 by default even on full apartments. Do NOT trust it on its own — verify with listingType, surface_area, num_bedrooms, and the description.
- `num_rooms`/`num_bedrooms` are often null for type=1 (Room) listings; absence doesn't mean a small place.
- ALWAYS check availability dates and description for temporary/short-term indicators — these are deal-breakers.

## STEP 1 — Determine the unit type (this drives everything)

Use `listingType` first, then sanity-check with description and surface area:

**Self-contained units (Apartment / Studio) — listingType = 2, 3, or 4**
- These are entire homes with their own kitchen, bathroom, entrance. They are fit for a couple by default.
- IGNORE `suitable_for_persons` for these. A 40m² apartment marked "1 person" is still fine for 2 people; rate it normally.
- HOWEVER, if the description explicitly forbids living together as a couple, this is a DEAL-BREAKER → score 5-15 max. Look for:
  - Dutch: "samenwonen is niet toegestaan", "samenwonen niet toegestaan", "geen samenwonen", "alleen bewoning door 1 persoon", "niet geschikt voor stellen", "geen stellen"
  - English: "cohabitation not allowed", "no couples", "single occupancy only", "one person only"
- Only penalize for capacity if surface_area is genuinely tiny (under ~20m²) AND the description literally says "single bed only" / "for one person only" / "geen plek voor twee".

**Rooms in shared houses — listingType = 1**
- These are rooms in a shared house with other tenants/roommates. Default assumption: unsuitable → score 0-10.
- The user requires a fully self-contained unit with NO other people living in the same space. Even if a room has its own bathroom, if there are housemates or shared common areas, it is unsuitable.
- ONLY override the low score if the description makes ABSOLUTELY CLEAR that:
  1. There are NO other tenants/housemates in the unit (not just "own entrance" — the entire dwelling must be theirs alone)
  2. It has its own kitchen/cooking area, own bathroom with shower, and own living space
  - Dutch signals: "geen huisgenoten", "geen medebewoners", "hele woning", "geheel appartement", "zelfstandig", "eigen keuken", "eigen badkamer"
  - English signals: "no housemates", "no roommates", "entire apartment", "whole apartment", "self-contained", "own kitchen", "own bathroom"
  - If these appear, treat as self-contained and apply the full rubric.
- Signals that CONFIRM it is shared (keep score 0-10):
  - "shared kitchen", "shared bathroom", "gedeelde keuken", "gedeelde badkamer", "delen we", "huisgenoten", "housemates", "X bedroom apartment with X people", "for girl/woman/man only", "single room", "kamer in huis", any mention of other tenants or roommates

## STEP 2 — Score using the rubric (max 100)

### Price Value (0-30)
Budget ~EUR 2000/month. Lower is better.
- ≤ 1400: 30pts | 1400-1700: 28pts | 1700-1900: 24pts | 1900-2100: 20pts | 2100-2300: 12pts | > 2300: 5pts
- Utilities included: +3 bonus (cap category at 30)
- For listingType=1 (true shared room) the price brackets shift: ≤700: 30pts | 700-900: 22pts | 900-1100: 14pts | >1100: 6pts

### Location — proximity to VU Amsterdam / Zuid (0-25)
Use postal code + city + street. Concrete reference (transit time to VU by bike/public transport):

**Excellent (22-25 pts) — walking/short bike to VU:**
- Amsterdam postal 1081, 1082, 1083 (Buitenveldert, Zuidas, VU campus, De Aker)
- Amsterdam postal 1071-1079 (Oud-Zuid, De Pijp, Rivierenbuurt, Stadionbuurt, Apollobuurt)
- Amstelveen 1181-1185 (Stadshart, Bovenkerk) — Tram 25 (Amstelveenlijn) goes directly to VU station

**Very good (18-22 pts) — 15-25 min door-to-door:**
- Amsterdam 1075-1077 (Oud-Zuid west, Hoofddorppleinbuurt) — bike 10-15 min
- Amsterdam 1054-1058 (Oud-West, Helmersbuurt) — tram 2 / bike 15-20 min
- Amstelveen 1186-1188 (Westwijk, Amstelveen Zuid) — bus / tram 25
- Duivendrecht 1115 — NS Duivendrecht + metro 51/53/54, ~15-20 min total. GOOD CHOICE.
- Ouderkerk aan de Amstel 1191 — bus 175 or 15 min bike along Amstel. GOOD CHOICE.
- Diemen 1111-1112 (Diemen Centrum) — metro 53, ~20 min

**Good (14-18 pts) — 20-30 min:**
- Amsterdam 1011-1018 (Centrum/Grachtengordel) — metro 52 to Zuid
- Amsterdam 1064-1067 (Slotervaart, Geuzenveld) — bus / tram
- Amsterdam 1098-1099 (Watergraafsmeer) — metro 53
- Amsterdam 1102-1108 (Bijlmer/Zuidoost) — metro 50
- Diemen Zuid 1112-1114 — metro 53
- Hoofddorp 2131-2134 — train direct to Amsterdam Zuid (~12 min on train but add walking)

**OK (8-13 pts) — 30-45 min:**
- Amsterdam 1019-1024 (Eastern Docklands, IJburg) — tram/metro
- Amsterdam Noord 1031-1035 — ferry + metro/bus
- Almere 1315-1318 — train direct to Zuid (~25 min)
- Badhoevedorp, Hoofddorp outer

**Poor (3-7 pts) — > 45 min or awkward transit:**
- Haarlem (any postal) — train + transfer
- Zaandam, Purmerend, Edam, Weesp
- Almere Buiten/Poort

If you don't recognize the postal code, lean on the city name and street + Dutch geographic knowledge. Don't blanket-penalize "outside Amsterdam" — Amstelveen, Duivendrecht, Diemen, and Ouderkerk are essentially Amsterdam suburbs with great VU connections.

### Property Quality (0-20)
- Surface area: ≥70m²: 12pts | 50-70m²: 10pts | 35-50m²: 7pts | 25-35m²: 4pts | <25m²: 1pt
- Bedrooms: 2+ bedrooms: 4pts | 1 bedroom: 3pts | studio (0 bedrooms): 2pts
- Energy label A/B: +2pts | C/D: +1pt | E/F/G: 0
- Furnishing: Furnished: +2pts | Semi-furnished: +1pt

### Private & Self-Contained (0-15) — CRITICAL for the user
The user REQUIRES a fully private unit: own kitchen/cooking area, own bathroom with shower, NO roommates or housemates whatsoever. Award:
- 15pts: clearly self-contained apartment/studio with own kitchen + own bathroom + no shared living with others
- 10pts: self-contained but description is vague about whether facilities are shared or private
- 0-3pts: any indication of shared facilities, housemates, roommates, or communal living

### Long-Term Availability (0-10)
The user needs a long-term home, NOT a temporary or short-stay rental. Check the title, description, and availability dates.
- 10pts: indefinite / long-term / permanent / no end date mentioned
- 5pts: end date > 12 months away or description says "minimaal 1 jaar" / "at least 1 year"
- 0pts: temporary, short-stay, or anti-squat (anti-kraak). Penalize heavily if ANY of these appear in title or description:
  - Dutch: "tijdelijk", "korte termijn", "anti-kraak", "anti kraak", "max 6 maanden", "tot en met", "voor de duur van", "tijdelijke huur", "short stay"
  - English: "temporary", "short-term", "short stay", "anti-squat", "max 6 months", "sublet", "subletting"
  - If `availabilityEndDate` is set and is less than 12 months from `availabilityStartDate`, score 0-2pts

## STEP 3 — Final notes
- Cap final score at 100, floor at 0.
- Reasoning must be 1-2 sentences and reference SPECIFIC fields you used (e.g. "78m² apartment in 1081, own kitchen+bathroom, long-term, EUR 1750 — strong all around").
- Do NOT just cite `suitable_for_persons` as the reason for a low score. If you penalize for capacity, name the specific evidence (surface area, listingType, description text).
- If temporary/short-term or shared living is detected, mention it explicitly in reasoning.

## Listing Data
{listing_data}

## Response
Respond with ONLY valid JSON, no markdown code fences, no extra text:
{{"score": <integer 0-100>, "reasoning": "<1-2 sentences referencing specific fields>"}}"""

    def _call_openrouter(self, prompt: str, model: str) -> Optional[Dict]:
        """Make a single OpenRouter API call. Returns parsed response or None."""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.2,
                },
                timeout=30,
            )
            if response.status_code != 200:
                print(f"  ⚠️  OpenRouter {model} returned status {response.status_code}")
                return None
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return json.loads(content)
        except json.JSONDecodeError:
            # Try regex fallback for score extraction
            if content:
                score_match = re.search(r'"score"\s*:\s*(\d+)', content)
                reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', content)
                if score_match:
                    return {
                        "score": int(score_match.group(1)),
                        "reasoning": reasoning_match.group(1) if reasoning_match else "Score extracted from malformed response"
                    }
            print(f"  ⚠️  OpenRouter {model}: failed to parse JSON response")
            return None
        except Exception as e:
            print(f"  ⚠️  OpenRouter {model} error: {e}")
            return None

    def _score_listing(self, listing: Dict) -> tuple:
        """Score a listing using AI via OpenRouter. Returns (score, reasoning) or (None, None)."""
        if not self.openrouter_api_key:
            return (None, None)
        try:
            prompt = self._build_scoring_prompt(listing)

            # Try primary model
            result = self._call_openrouter(prompt, self.openrouter_model)

            # Fallback to secondary model
            if result is None:
                print(f"  🔄 Falling back to {self.openrouter_fallback_model}...")
                result = self._call_openrouter(prompt, self.openrouter_fallback_model)

            if result and "score" in result:
                score = max(0, min(100, int(result["score"])))
                reasoning = str(result.get("reasoning", ""))[:500]
                return (score, reasoning)

            return (None, None)
        except Exception as e:
            print(f"  ⚠️  Scoring error: {e}")
            return (None, None)

    def _update_ai_score(self, listing_id: int, score: int, reasoning: str):
        """Update the AI score for a listing in the database."""
        if not self._ensure_db():
            return
        try:
            cur = self.db_conn.cursor()
            cur.execute(
                "UPDATE listings SET ai_score = %s, ai_score_reasoning = %s WHERE listing_id = %s",
                (score, reasoning, listing_id)
            )
        except Exception as e:
            print(f"  ⚠️  DB ai_score update error for {listing_id}: {e}")

    # ── Telegram methods ─────────────────────────────────────────────

    def _telegram_send(self, chat_id: int, text: str):
        """Send a single Telegram message. Returns True on success."""
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _get_telegram_subscribers(self) -> List[int]:
        """Load all subscriber chat_ids from the database."""
        if not self._ensure_db():
            return []
        try:
            cur = self.db_conn.cursor()
            cur.execute("SELECT chat_id FROM telegram_subscribers")
            return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"  ⚠️  DB load subscribers error: {e}")
            return []

    def _add_telegram_subscriber(self, chat_id: int, username: str, first_name: str):
        """Add a new subscriber to the database."""
        if not self._ensure_db():
            return False
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                INSERT INTO telegram_subscribers (chat_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) DO NOTHING
            """, (chat_id, username, first_name))
            return cur.rowcount > 0
        except Exception as e:
            print(f"  ⚠️  DB add subscriber error: {e}")
            return False

    def _check_telegram_subscriptions(self):
        """Check for new /start messages and subscribe users with correct password."""
        if not self.telegram_bot_token:
            return
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{self.telegram_bot_token}/getUpdates",
                params={"offset": self.telegram_last_update_id + 1, "timeout": 0},
                timeout=10,
            )
            data = resp.json()
            if not data.get("ok") or not data.get("result"):
                return

            for update in data["result"]:
                self.telegram_last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                if not chat_id or not text:
                    continue

                first_name = chat.get("first_name", "")
                username = message.get("from", {}).get("username", "")

                # Check for /start with password
                if text.startswith("/start"):
                    parts = text.split(maxsplit=1)
                    password = parts[1] if len(parts) > 1 else ""

                    if password == self.telegram_password:
                        is_new = self._add_telegram_subscriber(chat_id, username, first_name)
                        if is_new:
                            self._telegram_send(chat_id,
                                "✅ <b>Subscribed!</b>\n\n"
                                "You'll receive notifications for high-scoring apartment listings (≥70/100).\n\n"
                                "Send /stop to unsubscribe."
                            )
                            print(f"  📱 New Telegram subscriber: {first_name} ({chat_id})")
                        else:
                            self._telegram_send(chat_id, "You're already subscribed! 👍")
                    else:
                        self._telegram_send(chat_id,
                            "🔒 Password required.\n\n"
                            "Send: <code>/start yourpassword</code>"
                        )

                elif text == "/stop":
                    if self._ensure_db():
                        try:
                            cur = self.db_conn.cursor()
                            cur.execute("DELETE FROM telegram_subscribers WHERE chat_id = %s", (chat_id,))
                            if cur.rowcount > 0:
                                self._telegram_send(chat_id, "👋 Unsubscribed. Send /start password to resubscribe.")
                                print(f"  📱 Telegram unsubscribe: {first_name} ({chat_id})")
                            else:
                                self._telegram_send(chat_id, "You weren't subscribed.")
                        except Exception as e:
                            print(f"  ⚠️  DB unsubscribe error: {e}")
        except Exception as e:
            print(f"  ⚠️  Telegram subscription check error: {e}")

    def _send_telegram_notification(self, listing: Dict):
        """Send a Telegram notification to all subscribers for high-scoring listings."""
        if not self.telegram_bot_token:
            return
        score = listing.get('ai_score')
        if score is None or score < self.telegram_score_threshold:
            return
        try:
            subscribers = self._get_telegram_subscribers()
            if not subscribers:
                return

            listing_id = listing.get('listingId')
            city_slug = listing.get('citySlug', '')
            street_slug = listing.get('streetSlug', '')
            url = f"https://kamernet.nl/huren/{city_slug}/{street_slug}/{listing_id}"

            price = listing.get('totalRentalPrice', 0)
            area = listing.get('surfaceArea', 0)
            city = listing.get('city', 'Unknown')
            title = listing.get('detailed_title') or listing.get('street') or 'Unknown'
            reasoning = listing.get('ai_score_reasoning', '')

            text = (
                f"🏠 <b>High-scoring listing: {score}/100</b>\n\n"
                f"<b>{title}</b>\n"
                f"💰 €{price}/mo  |  📐 {area}m²  |  📍 {city}\n\n"
                f"💡 <i>{reasoning}</i>\n\n"
                f"🔗 <a href=\"{url}\">View on Kamernet</a>"
            )

            sent = 0
            for chat_id in subscribers:
                if self._telegram_send(chat_id, text):
                    sent += 1
            print(f"  📱 Telegram notification sent to {sent}/{len(subscribers)} subscribers for listing {listing_id} (score: {score})")
        except Exception as e:
            print(f"  ⚠️  Telegram notification failed: {e}")

    # ── End AI/Telegram methods ──────────────────────────────────────

    def extract_listings_from_html(self, html_content: str) -> List[Dict]:
        """Extract listings data from the HTML content"""
        try:
            # Look for the JSON data embedded in the HTML
            # The data is in a script tag with __NEXT_DATA__
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                print("Could not find __NEXT_DATA__ in HTML")
                return []
            
            json_data = json.loads(match.group(1))
            
            # Navigate to the listings data
            props = json_data.get('props', {})
            page_props = props.get('pageProps', {})
            target_page_props = page_props.get('targetPageProps', {})
            find_listings_response = target_page_props.get('findListingsResponse', {})
            listings = find_listings_response.get('listings', [])
            
            # Also get top ad listings
            top_listings = find_listings_response.get('topAdListings', [])
            
            # Combine all listings
            all_listings = listings + top_listings
            
            print(f"Found {len(all_listings)} listings in HTML")
            return all_listings
            
        except Exception as e:
            print(f"Error extracting listings from HTML: {e}")
            return []
    
    def fetch_listing_details(self, listing: Dict) -> Dict:
        """Fetch detailed information from individual listing page"""
        listing_id = listing.get('listingId')
        city_slug = listing.get('citySlug', 'amsterdam')
        street_slug = listing.get('streetSlug', '')
        
        if not listing_id or not street_slug:
            return listing
        
        detail_url = f"{self.base_url}/huren/{city_slug}/{street_slug}/{listing_id}"
        
        try:
            print(f"  📄 Fetching details for listing {listing_id}...")
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            # Extract detailed data from the listing page
            detailed_info = self.extract_listing_details_from_html(response.text)
            
            # Merge detailed info with original listing
            enhanced_listing = {**listing, **detailed_info}
            
            # Add a small delay to be respectful
            time.sleep(1)
            
            return enhanced_listing
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Could not fetch details for listing {listing_id}: {e}")
            return listing
    
    def extract_listing_details_from_html(self, html_content: str) -> Dict:
        """Extract detailed information from individual listing page HTML"""
        details = {}
        
        try:
            # Look for the JSON data in the listing detail page
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                return details
            
            json_data = json.loads(match.group(1))
            
            # Navigate to the listing details
            props = json_data.get('props', {})
            page_props = props.get('pageProps', {})
            target_page_props = page_props.get('targetPageProps', {})
            listing_details = target_page_props.get('listingDetails', {})
            
            if not listing_details:
                return details
            
            # Extract detailed information
            details['detailed_description'] = listing_details.get('dutchDescription', '') or listing_details.get('englishDescription', '')
            details['detailed_title'] = listing_details.get('dutchTitle', '') or listing_details.get('englishTitle', '')
            details['deposit'] = listing_details.get('deposit')
            details['rental_price'] = listing_details.get('rentalPrice')
            details['num_bedrooms'] = listing_details.get('numOfBedrooms')
            details['num_rooms'] = listing_details.get('numOfRooms')
            details['postal_code'] = listing_details.get('postalCode')
            details['house_number'] = listing_details.get('houseNumber')
            details['house_number_addition'] = listing_details.get('houseNumberAddition')
            details['energy_label_id'] = listing_details.get('energyId')
            details['pets_allowed'] = listing_details.get('candidatePetsAllowed')
            details['smoking_allowed'] = listing_details.get('candidateSmokingAllowed')
            details['min_age'] = listing_details.get('candidateMinAgeId')
            details['max_age'] = listing_details.get('candidateMaxAgeId')
            details['suitable_for_persons'] = listing_details.get('suitableForNumberOfPersons')
            details['registration_allowed'] = listing_details.get('isRegistrationAllowed')
            
            # Landlord information
            details['landlord_name'] = listing_details.get('landlordDisplayName')
            details['landlord_member_since'] = listing_details.get('landlordMemberSince')
            details['landlord_last_seen'] = listing_details.get('landlordLastLoggedOn')
            details['landlord_response_rate'] = listing_details.get('responseRate')
            details['landlord_response_time'] = listing_details.get('responseTime')
            details['landlord_verified'] = listing_details.get('isLandlordOBPBankVerified', False)
            details['landlord_active_listings'] = listing_details.get('activeListingsCount', 0)
            
            # Dates and timing
            details['create_date'] = listing_details.get('createDate')
            details['publish_date'] = listing_details.get('publishDate')
            
            # Additional images
            image_list = listing_details.get('imageList', [])
            if image_list:
                details['additional_images'] = [f"https://resources.kamernet.nl/image/{img_id}" for img_id in image_list[:3]]
            
            return details
            
        except Exception as e:
            print(f"  ⚠️  Error parsing listing details: {e}")
            return details

    def fetch_listings(self) -> List[Dict]:
        """Fetch listings from Kamernet.nl"""
        try:
            print(f"Fetching listings from: {self.search_url}")
            response = self.session.get(self.search_url, params=self.search_params, timeout=30)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            
            # Extract listings from HTML
            listings = self.extract_listings_from_html(response.text)
            
            return listings
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching listings: {e}")
            return []
    
    # Maps used for Discord formatting (also used in dashboard/src/lib/utils.ts)
    TYPE_MAP = {1: "Room", 2: "Apartment", 3: "Studio", 4: "Studio"}
    FURNISHING_MAP = {1: "Unfurnished", 2: "Unfurnished", 3: "Semi-furnished", 4: "Furnished"}

    def _embed_color(self, listing: Dict) -> int:
        """Determine embed color based on listing status and price."""
        price = listing.get('totalRentalPrice', 0)
        if listing.get('isNewAdvert', False):
            return 0xff6b35  # Orange for new
        if listing.get('isTopAdvert', False):
            return 0xffd700  # Gold for featured
        if price > 2000:
            return 0xff4444  # Red for expensive
        if price < 800:
            return 0x44ff44  # Green for cheap
        return 0x0099ff  # Blue for normal

    def _embed_title(self, listing: Dict) -> str:
        """Build the embed title line."""
        listing_type = listing.get('listingType', 0)
        title_emoji = "🏠" if listing_type == 1 else "🏢" if listing_type == 2 else "🏡"
        detailed_title = listing.get('detailed_title', '')
        if detailed_title and len(detailed_title) < 100:
            return f"{title_emoji} {detailed_title}"
        type_text = self.TYPE_MAP.get(listing_type, "Property")
        return f"{title_emoji} {type_text}: {listing.get('street', 'Unknown')}, {listing.get('city', 'Unknown')}"

    def _add_availability_fields(self, embed: DiscordEmbed, listing: Dict):
        """Add availability start/end fields to embed."""
        availability_start = listing.get('availabilityStartDate', '')
        availability_end = listing.get('availabilityEndDate')

        if availability_start:
            try:
                start_date = datetime.fromisoformat(availability_start.replace('Z', '+00:00'))
                embed.add_embed_field(name="📅 Available", value=f"From {start_date.strftime('%b %d, %Y')}", inline=True)
            except (ValueError, TypeError):
                embed.add_embed_field(name="📅 Available", value=f"From {availability_start[:10]}", inline=True)

        if availability_end:
            try:
                end_date = datetime.fromisoformat(availability_end.replace('Z', '+00:00'))
                embed.add_embed_field(name="📅 Until", value=end_date.strftime("%b %d, %Y"), inline=True)
            except (ValueError, TypeError):
                embed.add_embed_field(name="📅 Until", value=availability_end[:10], inline=True)
        else:
            embed.add_embed_field(name="⏰ Duration", value="Long-term", inline=True)

    def _add_detail_fields(self, embed: DiscordEmbed, listing: Dict):
        """Add landlord, preferences, and description excerpt fields."""
        landlord_name = listing.get('landlord_name')
        if landlord_name:
            parts = [f"👤 {landlord_name}"]
            if listing.get('landlord_verified', False):
                parts.append("✅")
            rate = listing.get('landlord_response_rate')
            if rate is not None:
                parts.append(f"({rate}% response)")
            embed.add_embed_field(name="🏠 Landlord", value=" ".join(parts), inline=False)

        # Tenant preferences
        preferences = []
        min_age, max_age = listing.get('min_age'), listing.get('max_age')
        if min_age and max_age:
            preferences.append(f"Age: {min_age}-{max_age}" if min_age != max_age else f"Age: {min_age}")
        if listing.get('pets_allowed') is not None:
            preferences.append("🐕 Pets OK" if listing['pets_allowed'] else "🚫 No pets")
        if listing.get('smoking_allowed') is not None:
            preferences.append("🚬 Smoking OK" if listing['smoking_allowed'] else "🚭 No smoking")
        if preferences:
            embed.add_embed_field(name="👥 Preferences", value=" • ".join(preferences), inline=False)

        # Description excerpt (limited to prevent Discord 500 errors)
        desc = listing.get('detailed_description', '')
        if desc and len(desc) > 50:
            excerpt = desc[:150]
            if len(desc) > 150:
                last_sentence = max(excerpt.rfind('.'), excerpt.rfind('!'))
                excerpt = excerpt[:last_sentence + 1] if last_sentence > 80 else excerpt + "..."
            embed.add_embed_field(name="📝 Description", value=excerpt, inline=False)

    def format_listing_for_discord(self, listing: Dict) -> DiscordEmbed:
        """Format a listing as a Discord embed. Kept compact to avoid 500 errors."""
        listing_id = listing.get('listingId')
        price = listing.get('totalRentalPrice', 0)
        surface_area = listing.get('surfaceArea', 0)
        listing_type = listing.get('listingType', 0)
        furnishing_id = listing.get('furnishingId', 0)
        type_text = self.TYPE_MAP.get(listing_type, "Property")
        furnishing_text = self.FURNISHING_MAP.get(furnishing_id, "Unknown")

        # Build listing URL
        city_slug = listing.get('citySlug', listing.get('city', '').lower())
        street_slug = listing.get('streetSlug', listing.get('street', '').lower().replace(' ', '-'))
        listing_url = f"{self.base_url}/huren/{city_slug}/{street_slug}/{listing_id}"

        # Description line
        desc_parts = [f"**€{price}/month** • **{surface_area}m²**"]
        if furnishing_text != "Unknown":
            desc_parts.append(f"• {furnishing_text}")

        embed = DiscordEmbed(
            title=self._embed_title(listing),
            description=" ".join(desc_parts),
            url=listing_url,
            color=self._embed_color(listing),
        )

        # Core fields
        embed.add_embed_field(name="💰 Rent", value=f"€{price}/month", inline=True)
        embed.add_embed_field(name="📐 Size", value=f"{surface_area}m²", inline=True)
        embed.add_embed_field(name="🏠 Type", value=type_text, inline=True)

        # Rooms
        num_bedrooms = listing.get('num_bedrooms')
        num_rooms = listing.get('num_rooms')
        if num_bedrooms or num_rooms:
            room_info = []
            if num_bedrooms:
                room_info.append(f"{num_bedrooms} bed")
            if num_rooms and num_rooms != num_bedrooms:
                room_info.append(f"{num_rooms} rooms")
            if room_info:
                embed.add_embed_field(name="🛏️ Rooms", value=" • ".join(room_info), inline=True)

        if listing.get('deposit'):
            embed.add_embed_field(name="💳 Deposit", value=f"€{listing['deposit']}", inline=True)

        self._add_availability_fields(embed, listing)

        utilities_text = "✅ Included" if listing.get('utilitiesIncluded', False) else "❌ Extra cost"
        embed.add_embed_field(name="⚡ Utilities", value=utilities_text, inline=True)

        self._add_detail_fields(embed, listing)

        # AI Score
        ai_score = listing.get('ai_score')
        if ai_score is not None:
            score_emoji = "🟢" if ai_score >= 70 else "🟡" if ai_score >= 40 else "🔴"
            score_text = f"{score_emoji} **{ai_score}/100**"
            reasoning = listing.get('ai_score_reasoning', '')
            if reasoning:
                score_text += f"\n{reasoning[:200]}"
            embed.add_embed_field(name="🤖 AI Score", value=score_text, inline=False)

        # Badges
        badges = []
        if listing.get('isNewAdvert', False):
            badges.append("🆕 **NEW**")
        if listing.get('isTopAdvert', False):
            badges.append("⭐ **FEATURED**")
        if badges:
            embed.add_embed_field(name="🏷️ Special", value=" • ".join(badges), inline=False)

        # Images
        if listing.get('thumbnailUrl'):
            embed.set_thumbnail(url=listing['thumbnailUrl'])
        image_url = listing.get('resizedFullPreviewImageUrl') or listing.get('fullPreviewImageUrl')
        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(
            text=f"ID: {listing_id} • Kamernet.nl • Click title for full details",
            icon_url="https://kamernet.nl/favicon.ico",
        )
        embed.set_timestamp()

        return embed
    
    def _build_summary_header(self, listings: List[Dict], total_batches: int) -> DiscordEmbed:
        """Build the summary header embed for the first Discord batch."""
        new_count = sum(1 for l in listings if l.get('isNewAdvert', False))
        top_count = sum(1 for l in listings if l.get('isTopAdvert', False))
        n = len(listings)
        s = "listing" if n == 1 else "listings"

        parts = [f"**{n} new {s}** found in Amsterdam!"]
        if new_count > 0:
            parts.append(f"🆕 {new_count} brand new {'listing' if new_count == 1 else 'listings'}")
        if top_count > 0:
            parts.append(f"⭐ {top_count} featured {'listing' if top_count == 1 else 'listings'}")

        prices = [l.get('totalRentalPrice', 0) for l in listings if l.get('totalRentalPrice', 0) > 0]
        if prices:
            parts.append(f"💰 €{min(prices)}-€{max(prices)}/month")

        header = DiscordEmbed(title="🔔 Kamernet Listings Alert", description="\n".join(parts), color=0xff6b35)
        footer = "Kamernet Scraper • Respecting robots.txt • Click listings for details"
        if total_batches > 1:
            footer += f" • Batch 1 of {total_batches}"
        header.set_footer(text=footer, icon_url="https://kamernet.nl/favicon.ico")
        header.set_timestamp()
        return header

    def send_discord_notification(self, new_listings: List[Dict]):
        """Send Discord notification for new listings in batches of 10 embeds."""
        if not new_listings:
            return
        if not self.discord_webhook_url:
            return

        try:
            sorted_listings = sorted(new_listings, key=lambda x: (
                not x.get('isNewAdvert', False),
                not x.get('isTopAdvert', False),
                x.get('totalRentalPrice', 0),
            ))

            batch_size = 10
            total_batches = (len(sorted_listings) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(sorted_listings))
                batch_listings = sorted_listings[start_idx:end_idx]

                webhook = DiscordWebhook(url=self.discord_webhook_url)

                if batch_num == 0:
                    webhook.add_embed(self._build_summary_header(new_listings, total_batches))
                else:
                    batch_header = DiscordEmbed(
                        title=f"📋 Batch {batch_num + 1} of {total_batches}",
                        description=f"Listings {start_idx + 1}-{end_idx} of {len(new_listings)}",
                        color=0x0099ff,
                    )
                    batch_header.set_footer(text="Kamernet Scraper • Continued...")
                    webhook.add_embed(batch_header)

                # 9 listing embeds max (1 slot used by header)
                for listing in batch_listings[:9]:
                    webhook.add_embed(self.format_listing_for_discord(listing))

                response = webhook.execute()
                if response.status_code in (200, 204):
                    label = f"batch {batch_num + 1}/{total_batches}" if total_batches > 1 else "notification"
                    print(f"✅ Successfully sent Discord {label} with {min(len(batch_listings), 9)} listings")
                else:
                    error_text = ""
                    try:
                        error_text = f": {response.json()}"
                    except Exception:
                        pass
                    print(f"❌ Webhook status code {response.status_code}{error_text}")

                if batch_num < total_batches - 1:
                    time.sleep(3)

        except Exception as e:
            import traceback
            print(f"Error sending Discord notification: {e}\n{traceback.format_exc()}")
    
    def check_for_new_listings(self):
        """Check for new listings and send notifications"""
        print(f"\n{'='*50}")
        print(f"Checking for new listings at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        # Process Telegram /start and /stop commands
        self._check_telegram_subscriptions()

        listings = self.fetch_listings()

        if not listings:
            print("No listings found or error occurred")
            self._log_scrape_run(0, 0, "No listings found")
            return

        # Touch all listings in DB (mark as still active)
        all_ids = [l.get('listingId') for l in listings if l.get('listingId')]
        self._touch_listings(all_ids)

        # Find new listings
        new_listings = []
        for listing in listings:
            listing_id = listing.get('listingId')
            if listing_id and listing_id not in self.seen_listings:
                new_listings.append(listing)
                self.seen_listings.add(listing_id)

        print(f"Total listings found: {len(listings)}")
        print(f"New listings: {len(new_listings)}")

        if new_listings:
            print("\nNew listings found:")
            for listing in new_listings:
                street = listing.get('street', 'Unknown')
                city = listing.get('city', 'Unknown')
                price = listing.get('totalRentalPrice', 0)
                listing_id = listing.get('listingId')
                print(f"  - {street}, {city} - €{price}/month (ID: {listing_id})")

            # Fetch detailed information for new listings only
            print(f"\n🔍 Fetching detailed information for {len(new_listings)} new listings...")
            enhanced_listings = []
            for listing in new_listings:
                enhanced_listing = self.fetch_listing_details(listing)
                enhanced_listings.append(enhanced_listing)

            print(f"✅ Enhanced {len(enhanced_listings)} listings with detailed information")

            # Write to database
            for listing in enhanced_listings:
                self._upsert_listing(listing)

            # Score listings with AI (non-blocking)
            if self.openrouter_api_key:
                print(f"\n🤖 Scoring {len(enhanced_listings)} listings with AI...")
                for listing in enhanced_listings:
                    score, reasoning = self._score_listing(listing)
                    if score is not None:
                        listing['ai_score'] = score
                        listing['ai_score_reasoning'] = reasoning
                        self._update_ai_score(listing['listingId'], score, reasoning)
                        print(f"  📊 Listing {listing['listingId']}: {score}/100")
                    time.sleep(1)  # Rate limiting for free model

            # Send Telegram for high-scoring listings
            for listing in enhanced_listings:
                self._send_telegram_notification(listing)

            # Send Discord notification with enhanced data
            self.send_discord_notification(enhanced_listings)
        else:
            print("No new listings found")

        # Mark disappeared listings and log scrape run
        self._mark_disappeared()
        self._log_scrape_run(len(listings), len(new_listings))

        # Save seen listings (JSON fallback)
        self.save_seen_listings()
        print(f"Total seen listings: {len(self.seen_listings)}")
    
    def run_continuous(self, interval_seconds_min: int = 50, interval_seconds_max: int = 70):
        """
        Run the scraper continuously with randomized intervals
        
        Args:
            interval_seconds_min: Minimum seconds between checks (default: 50)
            interval_seconds_max: Maximum seconds between checks (default: 70)
        
        Note: Random intervals help avoid detection patterns and rate limiting.
        For Heroku deployment, configure via CHECK_INTERVAL_MIN and CHECK_INTERVAL_MAX env vars.
        """
        print(f"Starting Kamernet scraper...")
        print(f"Will check for new listings every {interval_seconds_min}-{interval_seconds_max} seconds (randomized)")
        print(f"Monitoring URL: {self.search_url}")
        print(f"Discord webhook configured: {'Yes' if self.discord_webhook_url else 'No'}")
        print(f"Database configured: {'Yes' if self.database_url else 'No'}")
        print(f"AI scoring configured: {'Yes (' + self.openrouter_model + ')' if self.openrouter_api_key else 'No'}")
        print(f"Telegram notifications: {'Yes (threshold: ' + str(self.telegram_score_threshold) + ', password-protected)' if self.telegram_bot_token else 'No'}")
        print(f"Following robots.txt guidelines - avoiding disallowed paths")
        
        while True:
            try:
                self.check_for_new_listings()
                
                # Randomize interval to avoid patterns
                wait_seconds = random.randint(interval_seconds_min, interval_seconds_max)
                print(f"\nNext check in {wait_seconds} seconds...")
                time.sleep(wait_seconds)
            except KeyboardInterrupt:
                print("\nScraper stopped by user")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                wait_seconds = random.randint(interval_seconds_min, interval_seconds_max)
                print(f"Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)

def main():
    """
    Main function for Heroku deployment
    
    Environment Variables:
    - DISCORD_WEBHOOK_URL: Required - Discord webhook for notifications
    - CHECK_INTERVAL_MIN: Optional - Minimum seconds between checks (default: 50)
    - CHECK_INTERVAL_MAX: Optional - Maximum seconds between checks (default: 70)
    """
    # You need to set your Discord webhook URL here
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL') or None

    if not discord_webhook_url:
        print("DISCORD_WEBHOOK_URL not set — Discord notifications disabled (DB writes still happen).")

    scraper = KamernetScraper(discord_webhook_url)
    
    # Get randomized check interval from environment variables
    # Default: 50-70 seconds (fast checking without hammering the server)
    interval_min = int(os.getenv('CHECK_INTERVAL_MIN', '50'))
    interval_max = int(os.getenv('CHECK_INTERVAL_MAX', '70'))
    
    # Run once to test
    scraper.check_for_new_listings()
    
    # Run continuously with randomized intervals (no user input required for Heroku)
    scraper.run_continuous(interval_min, interval_max)

if __name__ == "__main__":
    main()
