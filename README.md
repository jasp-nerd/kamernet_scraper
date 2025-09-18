# Kamernet.nl Ethical Scraper

An ethical web scraper for Kamernet.nl that monitors new rental listings in Amsterdam and sends Discord notifications when new properties become available.

## Features

- ✅ **Ethical scraping** - Follows robots.txt guidelines
- 🏠 **Real-time monitoring** - Checks for new listings periodically
- 📱 **Enhanced Discord notifications** - Beautiful rich embeds with comprehensive listing details
- 🔍 **Deep listing analysis** - Fetches detailed info from individual pages for new listings only
- 💾 **Persistent tracking** - Remembers seen listings to avoid duplicates
- 🔄 **Continuous operation** - Runs indefinitely with configurable intervals
- 🎯 **Targeted search** - Focuses on Amsterdam rentals with your specific criteria
- ⏰ **Fresh listing detection** - Shows exact posting time ("33 minuten geleden")

## Robots.txt Compliance

This scraper strictly follows the robots.txt guidelines from Kamernet.nl:
- ✅ Uses allowed public search URLs only
- ❌ Avoids all disallowed paths (API endpoints, admin areas, etc.)
- 🕐 Implements respectful rate limiting
- 🤖 Uses appropriate user agent

## Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Discord webhook:**
   - Go to your Discord server settings
   - Navigate to Integrations > Webhooks
   - Create a new webhook and copy the URL
   - Set the environment variable:
   ```bash
   export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/YOUR_WEBHOOK_URL'
   ```

## Usage

### Run once to test:
```bash
python3 kamernet_scraper.py
```

### Run continuously:
The script will ask if you want to run continuously and what interval to use (default: 15 minutes).

### Environment Variables:
- `DISCORD_WEBHOOK_URL` - Your Discord webhook URL (required)

## How it Works

1. **Fetches listings** from the Kamernet.nl search page using the provided URL parameters
2. **Extracts JSON data** embedded in the HTML (no API calls to respect robots.txt)
3. **Identifies new listings** by comparing listing IDs with previously seen ones
4. **Sends enhanced Discord notifications** with beautiful rich embeds containing:
   - 🏠 **Comprehensive property details** (price, size, location, type, furnishing, rooms, deposit)
   - ⏰ **Real-time posting information** ("33 minuten geleden", "Net geplaatst")
   - 👤 **Landlord information** (name, verification status, response rate)
   - 👥 **Tenant requirements** (age range, pet/smoking policies)
   - 📝 **Property descriptions** (intelligently excerpted from full text)
   - 📅 **Availability dates and duration**
   - 🔗 **Direct links to listings with thumbnails**
   - 🖼️ **High-quality property images**
   - 🏷️ **Smart badges** (🆕 NEW, ⭐ FEATURED, 🔥 JUST POSTED)
   - 🎨 **Dynamic colors** based on price, status, and freshness
   - 📊 **Smart batching** (respects Discord's 10-embed limit)
   - ⚡ **Rate limiting** between messages

## Search Parameters

The scraper monitors listings with these criteria:
- **Location:** Amsterdam + 5km radius
- **Sort:** Newest first
- **Price:** No maximum limit
- **Size:** No minimum size
- **Type:** All housing types (rooms, studios, apartments)

## File Structure

- `kamernet_scraper.py` - Main scraper script
- `requirements.txt` - Python dependencies
- `seen_listings.json` - Tracks processed listings (auto-created)
- `README.md` - This documentation

## Rate Limiting & Ethics

- Respects robots.txt completely
- Uses reasonable delays between requests
- Only accesses public search pages
- Implements proper error handling
- Uses respectful user agent strings

## Troubleshooting

**No listings found:**
- Check your internet connection
- Verify the search URL is still valid
- Check if Kamernet.nl structure has changed

**Discord notifications not working:**
- Verify your webhook URL is correct
- Check Discord server permissions
- Ensure webhook URL environment variable is set

**Permission errors:**
- Make sure you have write permissions in the script directory
- Check if `seen_listings.json` can be created/modified

## Legal & Ethical Notice

This scraper:
- ✅ Only accesses publicly available data
- ✅ Follows robots.txt guidelines strictly
- ✅ Implements respectful rate limiting
- ✅ Does not overload the server
- ✅ Is for personal use only

Please use responsibly and in accordance with Kamernet.nl's terms of service.
