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
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not discord_webhook_url:
        print("Please set the DISCORD_WEBHOOK_URL environment variable")
        print("Example: export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/YOUR_WEBHOOK_URL'")
        return
    
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
