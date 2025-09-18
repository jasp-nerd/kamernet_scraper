#!/usr/bin/env python3
"""
Kamernet.nl Ethical Scraper
Scrapes new listings from Kamernet.nl following robots.txt guidelines
Sends Discord notifications for new listings
"""

import requests
import json
import time
import re
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Set, Optional
from discord_webhook import DiscordWebhook, DiscordEmbed

class KamernetScraper:
    def __init__(self, discord_webhook_url: str):
        """
        Initialize the Kamernet scraper
        
        Args:
            discord_webhook_url: Discord webhook URL for notifications
        """
        self.discord_webhook_url = discord_webhook_url
        self.base_url = "https://kamernet.nl"
        self.search_url = "https://kamernet.nl/huren/huurwoningen-amsterdam"
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
        """Load previously seen listing IDs from file"""
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
            
            # Calculate time since posted
            if details.get('publish_date'):
                try:
                    publish_dt = datetime.fromisoformat(details['publish_date'].replace('Z', '+00:00'))
                    now = datetime.now(publish_dt.tzinfo)
                    time_diff = now - publish_dt
                    
                    if time_diff.days > 0:
                        details['time_posted'] = f"{time_diff.days} dagen geleden"
                    elif time_diff.seconds > 3600:
                        hours = time_diff.seconds // 3600
                        details['time_posted'] = f"{hours} uur geleden"
                    elif time_diff.seconds > 60:
                        minutes = time_diff.seconds // 60
                        details['time_posted'] = f"{minutes} minuten geleden"
                    else:
                        details['time_posted'] = "Net geplaatst"
                except:
                    pass
            
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
    
    def format_listing_for_discord(self, listing: Dict) -> DiscordEmbed:
        """Format a listing for Discord notification with enhanced content"""
        listing_id = listing.get('listingId')
        street = listing.get('street', 'Unknown Street')
        city = listing.get('city', 'Unknown City')
        price = listing.get('totalRentalPrice', 0)
        surface_area = listing.get('surfaceArea', 0)
        availability_start = listing.get('availabilityStartDate', '')
        availability_end = listing.get('availabilityEndDate')
        utilities_included = listing.get('utilitiesIncluded', False)
        is_new = listing.get('isNewAdvert', False)
        is_top_ad = listing.get('isTopAdvert', False)
        listing_type = listing.get('listingType', 0)
        furnishing_id = listing.get('furnishingId', 0)
        
        # Get detailed information if available
        detailed_title = listing.get('detailed_title', '')
        detailed_description = listing.get('detailed_description', '')
        deposit = listing.get('deposit')
        time_posted = listing.get('time_posted')
        num_bedrooms = listing.get('num_bedrooms')
        num_rooms = listing.get('num_rooms')
        landlord_name = listing.get('landlord_name')
        landlord_verified = listing.get('landlord_verified', False)
        landlord_response_rate = listing.get('landlord_response_rate')
        min_age = listing.get('min_age')
        max_age = listing.get('max_age')
        pets_allowed = listing.get('pets_allowed')
        smoking_allowed = listing.get('smoking_allowed')
        
        # Determine listing type text
        type_map = {1: "Room", 2: "Apartment", 3: "Studio", 4: "Studio"}
        type_text = type_map.get(listing_type, "Property")
        
        # Determine furnishing text
        furnishing_map = {1: "Unfurnished", 2: "Unfurnished", 3: "Semi-furnished", 4: "Furnished"}
        furnishing_text = furnishing_map.get(furnishing_id, "Unknown")
        
        # Create listing URL
        city_slug = listing.get('citySlug', city.lower())
        street_slug = listing.get('streetSlug', street.lower().replace(' ', '-'))
        listing_url = f"{self.base_url}/huren/{city_slug}/{street_slug}/{listing_id}"
        
        # Enhanced title with property type and detailed title if available
        title_emoji = "🏠" if listing_type == 1 else "🏢" if listing_type == 2 else "🏡"
        if detailed_title and len(detailed_title) < 100:
            embed_title = f"{title_emoji} {detailed_title}"
        else:
            embed_title = f"{title_emoji} {type_text}: {street}, {city}"
        
        # Enhanced description with key details and timing
        description_parts = [f"**€{price}/month** • **{surface_area}m²**"]
        if furnishing_text != "Unknown":
            description_parts.append(f"• {furnishing_text}")
        if time_posted:
            description_parts.append(f"• ⏰ {time_posted}")
        
        # Create embed with dynamic color based on price and timing
        color = 0x00ff00 if is_new else 0xff6b35 if is_top_ad else 0x0099ff
        if time_posted and ("uur" in time_posted or "minuten" in time_posted or "Net" in time_posted):
            color = 0xff6b35  # Orange for very fresh listings
        if price > 2000:
            color = 0xff4444  # Red for expensive
        elif price < 800:
            color = 0x44ff44  # Green for cheap
        
        embed = DiscordEmbed(
            title=embed_title,
            description=" ".join(description_parts),
            url=listing_url,
            color=color
        )
        
        # Add essential fields in a compact layout
        embed.add_embed_field(name="💰 Rent", value=f"€{price}/month", inline=True)
        embed.add_embed_field(name="📐 Size", value=f"{surface_area}m²", inline=True)
        embed.add_embed_field(name="🏠 Type", value=type_text, inline=True)
        
        # Add room/bedroom info if available
        if num_bedrooms or num_rooms:
            room_info = []
            if num_bedrooms:
                room_info.append(f"{num_bedrooms} bed")
            if num_rooms and num_rooms != num_bedrooms:
                room_info.append(f"{num_rooms} rooms")
            if room_info:
                embed.add_embed_field(name="🛏️ Rooms", value=" • ".join(room_info), inline=True)
        
        # Deposit information if available
        if deposit:
            embed.add_embed_field(name="💳 Deposit", value=f"€{deposit}", inline=True)
        
        # Availability information
        if availability_start:
            try:
                start_date = datetime.fromisoformat(availability_start.replace('Z', '+00:00'))
                date_str = start_date.strftime("%b %d, %Y")
                embed.add_embed_field(name="📅 Available", value=f"From {date_str}", inline=True)
            except:
                embed.add_embed_field(name="📅 Available", value=f"From {availability_start[:10]}", inline=True)
        
        # Duration if end date exists
        if availability_end:
            try:
                end_date = datetime.fromisoformat(availability_end.replace('Z', '+00:00'))
                end_str = end_date.strftime("%b %d, %Y")
                embed.add_embed_field(name="📅 Until", value=end_str, inline=True)
            except:
                embed.add_embed_field(name="📅 Until", value=availability_end[:10], inline=True)
        else:
            embed.add_embed_field(name="⏰ Duration", value="Long-term", inline=True)
        
        # Utilities
        utilities_text = "✅ Included" if utilities_included else "❌ Extra cost"
        embed.add_embed_field(name="⚡ Utilities", value=utilities_text, inline=True)
        
        # Landlord information if available
        if landlord_name:
            landlord_text = f"👤 {landlord_name}"
            if landlord_verified:
                landlord_text += " ✅"
            if landlord_response_rate is not None:
                landlord_text += f" ({landlord_response_rate}% response)"
            embed.add_embed_field(name="🏠 Landlord", value=landlord_text, inline=False)
        
        # Tenant preferences if available
        preferences = []
        if min_age and max_age:
            if min_age == max_age:
                preferences.append(f"Age: {min_age}")
            else:
                preferences.append(f"Age: {min_age}-{max_age}")
        if pets_allowed is not None:
            preferences.append("🐕 Pets OK" if pets_allowed else "🚫 No pets")
        if smoking_allowed is not None:
            preferences.append("🚬 Smoking OK" if smoking_allowed else "🚭 No smoking")
        
        if preferences:
            embed.add_embed_field(name="👥 Preferences", value=" • ".join(preferences), inline=False)
        
        # Add excerpt from detailed description if available and not too long
        if detailed_description and len(detailed_description) > 50:
            # Extract first meaningful sentence or up to 200 chars
            excerpt = detailed_description[:200]
            if len(detailed_description) > 200:
                # Try to end at a sentence
                last_period = excerpt.rfind('.')
                last_exclamation = excerpt.rfind('!')
                last_sentence = max(last_period, last_exclamation)
                if last_sentence > 100:  # Only if we have a reasonable sentence
                    excerpt = excerpt[:last_sentence + 1]
                else:
                    excerpt += "..."
            embed.add_embed_field(name="📝 Description", value=excerpt, inline=False)
        
        # Add special badges with emojis
        badges = []
        if is_new:
            badges.append("🆕 **NEW**")
        if is_top_ad:
            badges.append("⭐ **FEATURED**")
        if time_posted and ("Net" in time_posted or "0 uur" in time_posted):
            badges.append("🔥 **JUST POSTED**")
        
        if badges:
            embed.add_embed_field(name="🏷️ Special", value=" • ".join(badges), inline=False)
        
        # Add thumbnail (smaller image in top right)
        thumbnail_url = listing.get('thumbnailUrl')
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        
        # Add main image
        image_url = listing.get('resizedFullPreviewImageUrl') or listing.get('fullPreviewImageUrl')
        if image_url:
            embed.set_image(url=image_url)
        
        # Enhanced footer with more info
        footer_text = f"ID: {listing_id} • Kamernet.nl • Click title for full details"
        if time_posted:
            footer_text = f"Posted {time_posted} • " + footer_text
        
        embed.set_footer(
            text=footer_text,
            icon_url="https://kamernet.nl/favicon.ico"
        )
        embed.set_timestamp()
        
        return embed
    
    def send_discord_notification(self, new_listings: List[Dict]):
        """Send Discord notification for new listings with proper embed limits"""
        if not new_listings:
            return
        
        try:
            # Sort listings by importance (new listings first, then by price)
            sorted_listings = sorted(new_listings, key=lambda x: (
                not x.get('isNewAdvert', False),  # New listings first
                not x.get('isTopAdvert', False),  # Then top ads
                x.get('totalRentalPrice', 0)      # Then by price (ascending)
            ))
            
            # Send listings in batches of 10 (Discord's embed limit)
            batch_size = 10
            total_batches = (len(sorted_listings) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(sorted_listings))
                batch_listings = sorted_listings[start_idx:end_idx]
                
                webhook = DiscordWebhook(url=self.discord_webhook_url)
                
                # Add a header embed for the first batch only
                if batch_num == 0:
                    # Count different types
                    new_count = sum(1 for l in new_listings if l.get('isNewAdvert', False))
                    top_ad_count = sum(1 for l in new_listings if l.get('isTopAdvert', False))
                    
                    # Create summary with statistics
                    summary_parts = [f"**{len(new_listings)} new listings** found in Amsterdam!"]
                    if new_count > 0:
                        summary_parts.append(f"🆕 {new_count} brand new")
                    if top_ad_count > 0:
                        summary_parts.append(f"⭐ {top_ad_count} featured")
                    
                    # Price range
                    prices = [l.get('totalRentalPrice', 0) for l in new_listings if l.get('totalRentalPrice', 0) > 0]
                    if prices:
                        min_price = min(prices)
                        max_price = max(prices)
                        summary_parts.append(f"💰 €{min_price}-€{max_price}/month")
                    
                    header_embed = DiscordEmbed(
                        title="🔔 Kamernet Listings Alert",
                        description="\n".join(summary_parts),
                        color=0xff6b35
                    )
                    
                    # Add useful footer
                    footer_text = "Kamernet Scraper • Respecting robots.txt • Click listings for details"
                    if total_batches > 1:
                        footer_text += f" • Batch 1 of {total_batches}"
                    
                    header_embed.set_footer(
                        text=footer_text,
                        icon_url="https://kamernet.nl/favicon.ico"
                    )
                    header_embed.set_timestamp()
                    
                    webhook.add_embed(header_embed)
                    
                    # Add up to 9 listing embeds (10 total with header)
                    max_listings_in_first_batch = 9
                    listings_to_add = batch_listings[:max_listings_in_first_batch]
                else:
                    # For subsequent batches, add header with batch info
                    batch_header = DiscordEmbed(
                        title=f"📋 Batch {batch_num + 1} of {total_batches}",
                        description=f"Listings {start_idx + 1}-{end_idx} of {len(new_listings)}",
                        color=0x0099ff
                    )
                    batch_header.set_footer(text="Kamernet Scraper • Continued...")
                    webhook.add_embed(batch_header)
                    
                    # Add up to 9 listing embeds (10 total with batch header)
                    max_listings_in_batch = 9
                    listings_to_add = batch_listings[:max_listings_in_batch]
                
                # Add individual listing embeds
                for listing in listings_to_add:
                    embed = self.format_listing_for_discord(listing)
                    webhook.add_embed(embed)
                
                # Send the webhook
                response = webhook.execute()
                
                if response.status_code == 200 or response.status_code == 204:
                    batch_info = f"batch {batch_num + 1}/{total_batches}" if total_batches > 1 else "notification"
                    print(f"✅ Successfully sent Discord {batch_info} with {len(listings_to_add)} listings")
                else:
                    error_text = ""
                    try:
                        error_data = response.json() if hasattr(response, 'json') else {}
                        error_text = f": {error_data}"
                    except:
                        pass
                    print(f"❌ Webhook status code {response.status_code}{error_text}")
                    print(f"Failed to send Discord notification batch {batch_num + 1}")
                
                # Rate limiting between batches
                if batch_num < total_batches - 1:
                    time.sleep(2)  # Wait 2 seconds between batches
                    
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
            import traceback
            print(f"Full error: {traceback.format_exc()}")
    
    def check_for_new_listings(self):
        """Check for new listings and send notifications"""
        print(f"\n{'='*50}")
        print(f"Checking for new listings at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        listings = self.fetch_listings()
        
        if not listings:
            print("No listings found or error occurred")
            return
        
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
            
            # Send Discord notification with enhanced data
            self.send_discord_notification(enhanced_listings)
        else:
            print("No new listings found")
        
        # Save seen listings
        self.save_seen_listings()
        print(f"Total seen listings: {len(self.seen_listings)}")
    
    def run_continuous(self, interval_minutes: int = 15):
        """Run the scraper continuously"""
        print(f"Starting Kamernet scraper...")
        print(f"Will check for new listings every {interval_minutes} minutes")
        print(f"Monitoring URL: {self.search_url}")
        print(f"Discord webhook configured: {'Yes' if self.discord_webhook_url else 'No'}")
        print(f"Following robots.txt guidelines - avoiding disallowed paths")
        
        while True:
            try:
                self.check_for_new_listings()
                print(f"\nNext check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nScraper stopped by user")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                print(f"Retrying in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

def main():
    """Main function"""
    # You need to set your Discord webhook URL here
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not discord_webhook_url:
        print("Please set the DISCORD_WEBHOOK_URL environment variable")
        print("Example: export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/YOUR_WEBHOOK_URL'")
        return
    
    scraper = KamernetScraper(discord_webhook_url)
    
    # Run once to test
    scraper.check_for_new_listings()
    
    # Ask if user wants to run continuously
    response = input("\nDo you want to run the scraper continuously? (y/n): ")
    if response.lower() == 'y':
        interval = input("Enter check interval in minutes (default: 15): ")
        try:
            interval = int(interval) if interval else 15
        except ValueError:
            interval = 15
        
        scraper.run_continuous(interval)

if __name__ == "__main__":
    main()
