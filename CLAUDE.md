# Auto-Responder — Telegram Userbot for Inbound Lead Qualification

## Status: DEPLOYED (24/7 on Hetzner VPS)

## What This Does

Pyrogram userbot running from Anton's work Telegram account (+34643057756). When someone new writes a DM, the bot auto-replies and qualifies them through a multi-step text flow, then saves the lead to Google Sheets (Paripesa tab) and sends a notification.

## Flow

```
New DM from unknown contact
  -> Check whitelist (colleagues) -> skip if whitelisted
  -> Check is_contact -> skip if in Telegram contacts
  -> Check if already qualified -> skip
  -> Check chat history -> skip if prior messages exist (not a truly new conversation)
  -> Detect language (EN/ES/RU) from first message
  -> Step 1: Greeting + "What's your traffic source?" (free text, multi-type detection)
  -> Step 2: "What regions?" (numbered 1-5: Tier1, Tier2, LATAM, Asia, Africa)
  -> Step 3a: If Tier 1 selected -> ask specific countries (codes/numbers/ALL)
  -> Step 3b: If Tier 2 selected -> ask specific countries
  -> Step 3c: If LATAM selected -> ask specific countries
  -> Step 4: "Share your link" (skipped for PPC/MEDIABUY/NETWORK/FB types)
  -> Save to Paripesa sheet: 1st Touch=Inbound, Status=NEW
  -> Notify admin chat (if NOTIFY_CHAT_ID configured)
  -> "Thanks, I'll get back to you soon"
```

## Admin Commands

Write these to yourself in **Saved Messages** (Избранное) in Telegram:

| Command | What it does |
|---------|-------------|
| `!status` | Show active/done/expired/total counts + failed leads |
| `!active` | List active conversations (in progress, not expired) |
| `!expired` | List expired conversations (didn't finish within 24h) |
| `!failed` | List leads that failed to save to Sheets |
| `!retry` | Retry saving failed leads to Sheets |
| `!reset <user_id>` | Reset specific user by Telegram ID |
| `!resetall` | Reset all conversations (for testing) |

To find a user's ID: check bot logs (`docker logs auto-responder`) — every message logs the user ID.

## Key Design Decisions

- **Userbot (Pyrogram)**, NOT a regular bot — runs as personal account to answer DMs
- **All text-based input** — userbots can't send inline keyboards (Telegram API limitation)
- **Traffic source = free text** with multi-type detection (e.g. "SEO and PPC" detects both)
- **Region -> Country drill-down**: Tier1/Tier2/LATAM get specific country selection; Asia/Africa don't
- **NO_LINK_TYPES**: PPC, MEDIABUY, NETWORK, FB skip the "share your link" step
- **Language detection**: Cyrillic -> RU, Spanish keywords -> ES, default EN
- **Conversation timeout**: 24 hours — if no reply, state expires
- **State persistence**: conversations.json survives restarts
- **Whitelist**: whitelist.json — colleague usernames to ignore
- **is_contact check**: skips people already in Telegram contacts
- **Chat history check**: before starting flow, fetches last 2 messages from chat — if >1 message exists, it's an existing conversation, skip auto-reply
- **Dedup**: checks Telegram username in sheet before writing
- **Sheet filtering**: Only Tier1/Tier2/LATAM leads saved to sheet; Asia/Africa only = not saved
- **VACATION_MODE**: When True, sends a P.S. vacation message after qualification (currently OFF)

## Files

| File | Purpose |
|------|---------|
| `responder.py` | Main Pyrogram client + message handlers + admin commands |
| `sheets.py` | Google Sheets writer — same pattern as telegram-leads-bot |
| `config.py` | All config: API creds, keywords, GEO lists, column mapping |
| `lang.py` | Language detection + EN/ES/RU message templates |
| `state.py` | Conversation state machine with JSON persistence |
| `whitelist.json` | List of colleague usernames to ignore (20 entries) |
| `conversations.json` | Active conversation states (auto-managed) |
| `start.sh` | Docker start script (on server at /tmp/r.sh) |
| `.env` | API_ID, API_HASH, PHONE, NOTIFY_CHAT_ID, GOOGLE_CREDENTIALS |
| `Dockerfile` | Python 3.11-slim container |

## Conversation Steps

1. `STEP_ASK_TRAFFIC` — free text, detects types via keywords
2. `STEP_ASK_REGION` — numbers 1-5 (multi-select)
3. `STEP_ASK_GEO_TIER1` — country codes/numbers/ALL (if Tier 1 selected)
4. `STEP_ASK_GEO_TIER2` — country codes/numbers/ALL (if Tier 2 selected)
5. `STEP_ASK_GEO_LATAM` — country codes/numbers/ALL (if LATAM selected)
6. `STEP_ASK_LINKS` — free text (skipped for NO_LINK_TYPES)
7. `STEP_DONE` / `STEP_DONE_OTHER` — finished

## Type Detection Keywords

Traffic source text is matched against keywords to auto-detect Type (multiple can match):
- SEO: seo, organic, search engine
- PPC: ppc, google ads, adwords, cpc, paid search
- STREAMER: stream, twitch, kick, youtube live
- INFLUENCER: influenc, blog, content creator, instagram, tiktok
- MEDIABUY: media buy, mediabuy, media buying, facebook ads, fb ads, push, popunder, native ads, buying
- NETWORK: network, affiliate network, cpa network, aff network
- EMAIL: email, newsletter, mailing
- TIPSTER: tipster, tips, betting tips, predictions
- FB: facebook group, fb group, fb
- InApp/ASO: app, aso, mobile app, in-app

If no keyword matches: Type left empty, raw traffic text saved in Notes.

## Deploy to Hetzner

**Server**: 77.42.69.208 (same VPS as telegram-bot and n8n)
**GitHub**: `antoniokrasawa/auto-responder` (public)
**Server path**: `/opt/bots/auto-responder` (git repo linked to GitHub)

### How to deploy (after ANY code change)

```bash
cd auto-responder
bash deploy.sh
```

That's it. The script will: commit + push to GitHub + pull on server + rebuild Docker + restart + show logs.

**IMPORTANT**: Always use `deploy.sh`. Do NOT scp files manually - the server pulls from GitHub now.

### What deploy.sh does

1. `git add -A` + `git commit` (asks for message, or uses default)
2. `git push` to GitHub
3. SSH to server: `git pull` + `docker build` + restart container
4. Shows last 15 lines of logs to verify

### First time setup (already done)

1. Create session locally: `python responder.py` (enter code + 2FA password)
2. Copy session to server: `scp auto_responder_session.session root@77.42.69.208:/opt/bots/auto-responder/`
3. Server git repo initialized and linked to GitHub

### Start script (`/tmp/r.sh` on server)

```bash
docker rm -f auto-responder
D=/opt/bots/auto-responder
docker run -d --name auto-responder --restart unless-stopped \
  --env-file $D/.env \
  -v $D/whitelist.json:/app/whitelist.json \
  -v $D/conversations.json:/app/conversations.json \
  -v $D/auto_responder_session.session:/app/auto_responder_session.session \
  -v $D/failed_leads.json:/app/failed_leads.json \
  auto-responder-img
```

### Useful commands (run in separate terminal)

```bash
ssh root@77.42.69.208 "docker logs auto-responder --tail 30"   # View recent logs
ssh root@77.42.69.208 "docker logs -f auto-responder"          # Follow logs live
ssh root@77.42.69.208 "docker restart auto-responder"          # Restart without rebuild
ssh root@77.42.69.208 "bash /tmp/r.sh"                         # Full restart
```

## Tech Stack

- Python 3.11
- Pyrogram 2.0 (Telegram User API)
- gspread + google-auth (Google Sheets)
- python-dotenv (.env loading)

## Configuration

- `VACATION_MODE` in responder.py — set to `False` when back from vacation
- `NOTIFY_CHAT_ID` in .env — set to group chat ID for lead notifications (currently 0 = disabled)
- `whitelist.json` — add/remove colleague usernames

## Known Limitations

- Userbot can only be run on ONE device/server at a time (Telegram session constraint)
- First login requires interactive code input — can't be fully automated
- 2FA password required if enabled on the account
- No NLP/AI for message analysis — simple keyword matching only
- No auto-classification to NOT RELEVANT — all leads saved as NEW
- No Vertical detection (not asked in flow)
- Inline keyboards not available for userbots — all input is text-based
- Chat history check adds ~0.5s latency on first message from new contacts (Telegram API call)
