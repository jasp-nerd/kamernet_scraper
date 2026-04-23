# Notifications

Radar ships three notifiers. Configure as many as you want. A matching listing fans out to each active channel.

| Notifier | Activation                                           | Strengths                                                    |
| -------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| Discord  | `DISCORD_WEBHOOK_URL`                                | Native rich embeds with image, full detail, batched nicely.  |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_PASSWORD`           | Multi-user subscriptions with a shared password. Good for notifying a partner or roommate. |
| Apprise  | `APPRISE_URLS`                                       | 100+ channels via a single env var. No code changes to add channels. |

---

## Discord (native rich embeds)

1. Open your Discord server → **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**.
2. Choose a channel, name the bot, copy the webhook URL.
3. Set it in `.env`:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/.../...
```

Each new listing becomes a rich embed: thumbnail, price, surface, landlord info, AI score. Up to 10 embeds per message (Discord's hard limit), so Radar auto-batches.

---

## Telegram (subscriber flow)

Useful when multiple people (you + partner + roommate) want their own DM.

### 1. Create the bot
- Open Telegram, message [**@BotFather**](https://t.me/BotFather).
- `/newbot`, pick a name, pick a username ending in `_bot`.
- Copy the token BotFather gives you.

### 2. Configure
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_PASSWORD=your-long-shared-password     # anything, don't reuse
TELEGRAM_SCORE_THRESHOLD=80                     # optional, default 80
```

### 3. Subscribe
Anyone with the password can DM the bot:
- `/start your-long-shared-password` → subscribed
- `/stop` → unsubscribed

Radar sends high-scoring (`ai_score >= TELEGRAM_SCORE_THRESHOLD`) listings to each subscriber.

> 🔐 **The password gate is mandatory.** Radar refuses to start with a Telegram token but no password. Otherwise anyone who finds the bot's username could flood your DB with subscribers.

---

## Apprise (one env var, 100+ channels)

[Apprise](https://github.com/caronc/apprise) is a notification library that speaks every common protocol. Radar passes through to it.

Set `APPRISE_URLS` to a single URL, or comma-separate multiple:

```bash
APPRISE_URLS=ntfy://my-private-topic,slack://TokenA/TokenB/TokenC
APPRISE_SCORE_THRESHOLD=0     # 0 = send everything, higher = only good listings
```

### Recipes

#### ntfy.sh (free push notifications to your phone)

Free, no account, self-hostable. The easiest option for a phone notification.

```bash
APPRISE_URLS=ntfy://my-random-topic-name-nobody-guesses
```

Install the [ntfy app](https://ntfy.sh/app) and subscribe to the same topic. Done.

For a private self-hosted ntfy:

```bash
APPRISE_URLS=ntfy://user:pass@ntfy.example.com/mytopic
```

#### Slack

Create an incoming webhook at https://api.slack.com/messaging/webhooks, then split the URL:

```
https://hooks.slack.com/services/T000/B000/XXXX
                                 ↑    ↑    ↑
                                 A    B    C
```

```bash
APPRISE_URLS=slack://T000/B000/XXXX
```

#### Email (any SMTP)

Gmail example (requires an [app password](https://myaccount.google.com/apppasswords)):

```bash
APPRISE_URLS=mailto://you%40gmail.com:APP_PASSWORD@smtp.gmail.com?to=you@gmail.com
```

Note the URL-encoded `@` in the username as `%40`.

For Mailgun, Resend, etc., see [Apprise's email wiki](https://github.com/caronc/apprise/wiki/Notify_email).

#### Pushover (one-time $5 iOS/Android push)

1. Buy the app and get a user key at https://pushover.net.
2. Create an application at https://pushover.net/apps/build, copy the token.

```bash
APPRISE_URLS=pover://USER_KEY@APP_TOKEN
```

#### WhatsApp (via Twilio)

WhatsApp via Twilio works, with a paid Twilio account and some sandbox setup. See [Apprise's Twilio wiki](https://github.com/caronc/apprise/wiki/Notify_twilio) for the full flow.

```bash
APPRISE_URLS=twilio://AccountSID:AuthToken@FromNumber/whatsapp:%2BYourNumber
```

Skip this if you have another option. The setup is fiddly and it's not free.

#### Matrix

```bash
APPRISE_URLS=matrixs://user:pass@matrix.example.com/!roomid%3Amatrix.example.com
```

#### Home Assistant

```bash
APPRISE_URLS=hassio://your-ha-host/LONG_LIVED_TOKEN
```

---

## Combining notifiers

The three notifiers coexist. The rich Discord post goes to your server, the Telegram DM goes to your subscribers, the ntfy topic pings your phone, all for the same listing.

## Thresholds

Each notifier has its own minimum-score threshold:

| Variable                     | Default | Behavior                                          |
| ---------------------------- | :-----: | ------------------------------------------------- |
| Discord (always sends all new listings, no threshold)     |         |                                                   |
| `TELEGRAM_SCORE_THRESHOLD`   | 80      | Telegram subscribers hear about strong listings only. |
| `APPRISE_SCORE_THRESHOLD`    | 0       | Apprise sends everything by default. Raise to filter. |

Set `TELEGRAM_SCORE_THRESHOLD=0` to hear about each new listing on Telegram, or set `APPRISE_SCORE_THRESHOLD=80` to use Apprise as a quality filter.

---

## Adding a new notifier

If the existing options don't fit (say, you want a custom integration with an internal tool), two paths:

- **Use an Apprise custom webhook** (`APPRISE_URLS=json://your-server.example.com/hook`). Sends JSON to any HTTP endpoint.
- **Write a new `radar/notify/<yourname>.py`.** Follow the `DiscordNotifier` pattern, register it in `notify/__init__.py::build_notifiers`. PRs welcome.
