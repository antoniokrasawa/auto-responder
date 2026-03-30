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
  -> Step 2: "What regions?" (numbers, names, or mixed: 1 3 / T1, LATAM / Tier 1)
  -> Step 3a: If Tier 1 selected -> ask specific countries (codes/numbers/names/ALL)
  -> Step 3b: If Tier 2 selected -> ask specific countries
  -> Step 3c: If LATAM selected -> ask specific countries
  -> Step 4: "Share your link" (skipped for PPC/MEDIABUY/NETWORK/FB types)
  -> Save to Paripesa sheet: 1st Touch=Inbound, Status=NEW, Date Contacted=empty
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
- **Owner takeover**: when Anton sends any message in a chat with active bot conversation, bot stops for that user immediately. Bot's own replies are tracked via `_bot_message_ids` set to avoid false positives (Pyrogram fires `filters.me` handler for outgoing messages from the same session).
- **Smart input parsing**: Region accepts numbers (1 3), names (T1, LATAM, Tier 1), abbreviations (EU, EE), and mixed (1, LATAM). GEO accepts codes (ES DE), numbers (1 3), country names in EN/ES/RU (Spain, Brasil, Германия), or ALL. Input sanitized via `_clean_input()` which strips invisible Unicode characters. Unrecognized input still stops the bot.
- **No retries on invalid input**: if user gives genuinely off-script input at any step, bot stops responding entirely (no "please try again" messages).
- **Dedup**: checks Telegram username in sheet before writing
- **Sheet filtering**: All GEOs saved to sheet (Asia/Africa stored as region name in GEO field since no country drill-down)
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
| `Dockerfile` | Python 3.11-slim container, PYTHONUNBUFFERED=1 |

## Conversation Steps

1. `STEP_ASK_TRAFFIC` — free text, detects types via keywords
2. `STEP_ASK_REGION` — numbers (1 3), names (T1, LATAM, Tier 1), abbreviations (EU, EE), or mixed
3. `STEP_ASK_GEO_TIER1` — country codes (ES DE), numbers (1 3), names (Spain, Испания), or ALL
4. `STEP_ASK_GEO_TIER2` — same formats as Tier 1
5. `STEP_ASK_GEO_LATAM` — same formats as Tier 1
6. `STEP_ASK_LINKS` — free text (skipped for NO_LINK_TYPES)
7. `STEP_DONE` / `STEP_DONE_OTHER` — finished
8. `STEP_STOPPED` — bot stopped (off-script input or owner took over)

## Type Detection Keywords

Traffic source text is matched against ~170 keywords in 3 languages (EN/ES/RU) including industry slang. Full list in `config.py` `TYPE_KEYWORDS`. Key examples per type:
- SEO: seo, organic, сео, сеошник, сеошка, органика, posicionamiento
- PPC: ppc, google ads, sem, ппс, контекст, контекстолог, директ, pago por clic
- STREAMER: stream, twitch, kick, стрим, стример, стримлю, transmision en vivo
- INFLUENCER: influencer, blogger, youtuber, инфлюенсер, блогер, тиктокер, инстаблогер, influenciador
- MEDIABUY: media buy, push, popunder, медиабайер, байер, арбитраж, лью, залив, заливала, compra de medios
- NETWORK: affiliate network, cpa network, партнерка, партнерская сеть, red de afiliados
- EMAIL: email, newsletter, mailing, емейл, рассылка, correo, lista de correo
- TIPSTER: tipster, picks, handicapper, каппер, типстер, прогнозы, ставочник, pronosticos
- FB: fb, facebook, meta ads, фб, фейсбук, фейс, таргет, таргетолог, лью с фб
- InApp/ASO: in-app, aso, mobile app, инапп, мобайл, мобилка, прилка, trafico movil

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
- No NLP/AI for message analysis — keyword matching in 3 languages (EN/ES/RU) with industry slang (~170 keywords)
- No auto-classification to NOT RELEVANT — all leads saved as NEW
- No Vertical detection (not asked in flow)
- Inline keyboards not available for userbots — all input is text-based
- Chat history check adds ~0.5s latency on first message from new contacts (Telegram API call)
- Bot stops on first genuinely invalid input — no second chances (prevents trolling). But recognizes flexible formats (T1, LATAM, Spain, EU etc.)
