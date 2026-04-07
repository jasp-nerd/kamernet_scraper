#!/usr/bin/env python3
"""
Helper script to get your Telegram chat_id.

Usage:
1. Create a bot via @BotFather on Telegram and get the bot token
2. Send /start to your new bot in Telegram
3. Run: python get_telegram_chat_id.py
   (or set TELEGRAM_BOT_TOKEN env var first)
"""
import os
import requests

token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    token = input("Enter your Telegram bot token: ").strip()

if not token:
    print("Error: No token provided")
    exit(1)

resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates")
data = resp.json()

if not data.get("ok"):
    print(f"Error from Telegram API: {data.get('description', 'Unknown error')}")
    exit(1)

if not data.get("result"):
    print("No messages found. Make sure you:")
    print("1. Opened a chat with your bot in Telegram")
    print("2. Sent /start to the bot")
    print("3. Then run this script again")
    exit(1)

seen = set()
for update in data["result"]:
    chat = update.get("message", {}).get("chat", {})
    if chat and chat["id"] not in seen:
        seen.add(chat["id"])
        name = f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
        print(f"Chat ID: {chat['id']}  (from: {name or 'Unknown'})")

print(f"\nSet this as your TELEGRAM_CHAT_ID environment variable.")
