"""
Auto-Responder - Telegram userbot for qualifying inbound leads
All input is text-based (userbots can't send inline keyboards).
"""
import asyncio
import json
import logging
import re
import time

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters
from pyrogram.types import Message

from config import (
    API_ID, API_HASH, PHONE, NOTIFY_CHAT_ID,
    TYPE_KEYWORDS, REGION_OPTIONS, NO_LINK_TYPES,
    TIER1_GEOS, TIER1_CODES, TIER2_GEOS, TIER2_CODES,
    LATAM_GEOS, LATAM_CODES, load_whitelist,
    CONVERSATION_TIMEOUT
)
from lang import detect_language, get_message
from state import (
    ConversationState,
    STEP_ASK_TRAFFIC, STEP_ASK_REGION,
    STEP_ASK_GEO_TIER1, STEP_ASK_GEO_TIER2, STEP_ASK_GEO_LATAM,
    STEP_ASK_LINKS, STEP_DONE, STEP_DONE_OTHER, STEP_EXPIRED, STEP_STOPPED
)
from sheets import SheetsManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

app = Client(
    "auto_responder_session",
    api_id=API_ID,
    api_hash=API_HASH,
    phone_number=PHONE
)

state = ConversationState()
whitelist = load_whitelist()
sheets = None


# --- Helpers ---

def detect_type(text):
    """Detect all matching traffic source types from free text"""
    text_lower = text.lower()
    matched = []
    for type_name, keywords in TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(type_name)
    return matched


def parse_region_input(text):
    """Parse region selection from numbers like '1 3' or '1,3'.
    Strict: each part must be exactly one digit 1-5. Rejects '2525' etc."""
    stripped = text.strip()
    if len(stripped) > 30:
        return []
    parts = re.split(r'[,\s]+', stripped)
    regions = []
    for p in parts:
        if not p:
            continue
        if not re.match(r'^[1-5]$', p):
            return []  # any non-matching part = invalid
        idx = int(p) - 1
        region = REGION_OPTIONS[idx]
        if region not in regions:
            regions.append(region)
    return regions


def parse_geo_input(text, valid_codes):
    """Parse country codes from text. Accepts codes (ES DE) or numbers (1 3) or ALL.
    Strict: each part must be a valid code or number. Any garbage = reject all."""
    stripped = text.strip().upper()
    if stripped == 'ALL':
        return list(valid_codes)
    if len(stripped) > 100:
        return []

    parts = re.split(r'[,\s]+', stripped)
    geos = []
    for p in parts:
        if not p:
            continue
        # Try as country code
        if p in valid_codes:
            if p not in geos:
                geos.append(p)
            continue
        # Try as number (1-2 digits only)
        if re.match(r'^\d{1,2}$', p):
            idx = int(p) - 1
            if 0 <= idx < len(valid_codes):
                code = valid_codes[idx]
                if code not in geos:
                    geos.append(code)
                continue
        # Any non-matching part = invalid input
        return []
    return geos


def get_display_name(conv):
    first = conv.get('first_name', '')
    last = conv.get('last_name', '')
    name = (first + " " + last).strip()
    return name if name else conv.get('username', 'Unknown')


def format_notification(conv):
    name = get_display_name(conv)
    username = conv.get('username', '')
    at_user = "@" + username if username else 'no username'
    traffic = conv.get('traffic_source', '?')
    detected_type = detect_type(traffic)
    regions = ', '.join(conv.get('selected_regions', []))
    geos = ', '.join(conv.get('selected_geos', []))
    links = conv.get('links', '')

    lines = ["New inbound lead:",
             "Name: " + name + " (" + at_user + ")",
             "Traffic: " + traffic]
    if detected_type:
        lines.append("Type: " + ', '.join(detected_type))
    if regions:
        lines.append("Regions: " + regions)
    if geos:
        lines.append("GEO: " + geos)
    if links:
        lines.append("Links: " + links)
    lines.append("\nFirst message: " + conv.get('first_message', '')[:200])
    return '\n'.join(lines)


# Ordered list of geo steps to try after region selection
GEO_STEPS = [
    ('Tier 1', STEP_ASK_GEO_TIER1, 'ask_geo_tier1'),
    ('Tier 2', STEP_ASK_GEO_TIER2, 'ask_geo_tier2'),
    ('LATAM', STEP_ASK_GEO_LATAM, 'ask_geo_latam'),
]


def find_next_geo_step(regions, after_step=None):
    """Find the next geo step based on selected regions.
    If after_step is given, return the step AFTER that one."""
    found_current = after_step is None
    for region_name, step_const, msg_key in GEO_STEPS:
        if not found_current:
            if step_const == after_step:
                found_current = True
            continue
        if region_name in regions:
            return step_const, msg_key
    return None, None


# --- Admin commands (send to Saved Messages) ---

ACTIVE_STEPS = (
    STEP_ASK_TRAFFIC, STEP_ASK_REGION,
    STEP_ASK_GEO_TIER1, STEP_ASK_GEO_TIER2, STEP_ASK_GEO_LATAM,
    STEP_ASK_LINKS
)


@app.on_message(filters.private & filters.me)
async def handle_admin_command(client: Client, message: Message):
    text = (message.text or '').strip()
    if not text.startswith('!'):
        # Owner sent a normal message in a private chat — stop bot for this user
        chat_id = message.chat.id
        conv = state.conversations.get(chat_id)
        if conv and conv.get('step') in ACTIVE_STEPS:
            state.update(chat_id, step=STEP_STOPPED)
            log.info("Owner took over conversation, bot stopped: " + str(chat_id))
        return

    if text == '!resetall':
        count = len(state.conversations)
        state.conversations.clear()
        state._save()
        await message.reply("Reset " + str(count) + " conversations.")
        return

    if text.startswith('!reset '):
        try:
            uid = int(text.split()[1])
        except (IndexError, ValueError):
            await message.reply("Usage: !reset <user_id>")
            return
        if uid in state.conversations:
            state.remove(uid)
            await message.reply("Reset user " + str(uid))
        else:
            await message.reply("User " + str(uid) + " not found")
        return

    if text == '!status':
        total = len(state.conversations)
        done = sum(1 for c in state.conversations.values() if c.get('step') in ('done', 'done_other'))
        expired = sum(1 for c in state.conversations.values() if c.get('step') == 'expired')
        stopped = sum(1 for c in state.conversations.values() if c.get('step') == 'stopped')
        active = total - done - expired - stopped
        try:
            with open(FAILED_LEADS_FILE, 'r') as f:
                failed_count = len(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            failed_count = 0
        msg = "Active: " + str(active) + "\nDone: " + str(done) + "\nExpired: " + str(expired) + "\nStopped: " + str(stopped) + "\nTotal: " + str(total)
        if failed_count:
            msg += "\nFailed leads pending: " + str(failed_count) + " (use !retry)"
        await message.reply(msg)
        return

    if text == '!active' or text == '!expired':
        show_expired = text == '!expired'
        target_step = 'expired' if show_expired else None
        lines = []
        now = time.time()
        for uid, c in state.conversations.items():
            step = c.get('step', '')
            if show_expired:
                if step != 'expired':
                    # Also check if timed out but not yet marked
                    if now - c.get('started_at', 0) <= CONVERSATION_TIMEOUT:
                        continue
            else:
                if step in ('done', 'done_other', 'expired', 'stopped'):
                    continue
                if now - c.get('started_at', 0) > CONVERSATION_TIMEOUT:
                    continue
            name = (c.get('first_name', '') + ' ' + c.get('last_name', '')).strip()
            uname = c.get('username', '')
            at = '@' + uname if uname else 'no username'
            traffic = c.get('traffic_source', '') or '-'
            lines.append('- ' + name + ' (' + at + ') step=' + step + ' traffic=' + traffic)
        label = 'Expired' if show_expired else 'Active'
        if not lines:
            await message.reply('No ' + label.lower() + ' conversations')
        else:
            await message.reply(label + ' (' + str(len(lines)) + '):\n' + '\n'.join(lines))
        return

    if text == '!retry':
        if not sheets:
            await message.reply("Sheets not connected")
            return
        ok, total = _retry_failed_leads()
        if total == 0:
            await message.reply("No failed leads to retry")
        else:
            await message.reply("Retried: " + str(ok) + "/" + str(total) + " saved")
        return

    if text == '!failed':
        try:
            with open(FAILED_LEADS_FILE, 'r') as f:
                failed = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            failed = []
        if not failed:
            await message.reply("No failed leads")
        else:
            lines = []
            for lead in failed:
                lines.append("- " + lead.get('partner_name', '?') + " (@" + lead.get('telegram', '?') + ") " + lead.get('geo', ''))
            await message.reply("Failed leads (" + str(len(failed)) + "):\n" + '\n'.join(lines))
        return


# --- Handler ---

@app.on_message(filters.private & filters.incoming & ~filters.me & ~filters.bot)
async def handle_private_message(client: Client, message: Message):
    global sheets

    user = message.from_user
    if not user:
        return

    user_id = user.id
    username = (user.username or '').lower()

    log.info("MSG from " + str(user.first_name) + " (@" + str(user.username) + ", id=" + str(user_id) + "), is_contact=" + str(user.is_contact) + ", wl=" + str(username in whitelist))

    if username and username in whitelist:
        log.info("  -> skipped: whitelist")
        return

    if user.is_contact:
        log.info("  -> skipped: is_contact")
        return

    if state.is_done(user_id):
        log.info("  -> skipped: already done")
        return

    conv = state.get(user_id)
    if conv:
        step = conv['step']
        lang = conv['lang']
        text = message.text or ''

        # --- Traffic source ---
        if step == STEP_ASK_TRAFFIC:
            state.update(user_id, traffic_source=text, step=STEP_ASK_REGION)
            await message.reply(get_message(lang, 'ask_region'))
            return

        # --- Region selection ---
        if step == STEP_ASK_REGION:
            regions = parse_region_input(text)
            if not regions:
                # Off-script input — stop responding
                state.update(user_id, step=STEP_STOPPED)
                log.info("Off-script at region step, stopped: " + str(user_id))
                return

            state.update(user_id, selected_regions=regions)

            # Find first geo sub-step
            next_step, msg_key = find_next_geo_step(regions)
            if next_step is None:
                # Only Asia/Africa — no country drill-down, go to links or finish
                traffic_types = detect_type(conv.get('traffic_source', ''))
                if any(t in NO_LINK_TYPES for t in traffic_types):
                    state.update(user_id, step=STEP_DONE_OTHER)
                    conv = state.get(user_id)
                    await _save_lead(conv)
                    await _notify(client, conv)
                    await _send_finish(message, lang, 'done_other')
                    log.info("Lead passed to colleagues (no link): " + get_display_name(conv))
                else:
                    state.update(user_id, step=STEP_ASK_LINKS)
                    await message.reply(get_message(lang, 'ask_links'))
                return

            state.update(user_id, step=next_step)
            await message.reply(get_message(lang, msg_key))
            return

        # --- Tier 1 / Tier 2 / LATAM countries ---
        if step in (STEP_ASK_GEO_TIER1, STEP_ASK_GEO_TIER2, STEP_ASK_GEO_LATAM):
            # Determine which geo list to validate against
            if step == STEP_ASK_GEO_TIER1:
                valid = TIER1_CODES
            elif step == STEP_ASK_GEO_TIER2:
                valid = TIER2_CODES
            else:
                valid = LATAM_CODES

            geos = parse_geo_input(text, valid)
            if not geos:
                # Off-script input — stop responding
                state.update(user_id, step=STEP_STOPPED)
                log.info("Off-script at geo step, stopped: " + str(user_id))
                return

            existing = conv.get('selected_geos', [])
            state.update(user_id, selected_geos=existing + geos)

            # Find next geo step after current
            regions = conv.get('selected_regions', [])
            next_step, msg_key = find_next_geo_step(regions, after_step=step)
            if next_step is None:
                # No more geo steps -> ask links or finish
                traffic_types = detect_type(conv.get('traffic_source', ''))
                if any(t in NO_LINK_TYPES for t in traffic_types):
                    # Has our geos (Tier1/2/LATAM) since we're in geo step
                    state.update(user_id, step=STEP_DONE)
                    conv = state.get(user_id)
                    await _save_lead(conv)
                    await _notify(client, conv)
                    await _send_finish(message, lang, 'done')
                    log.info("Qualified lead (no link): " + get_display_name(conv))
                else:
                    state.update(user_id, step=STEP_ASK_LINKS)
                    await message.reply(get_message(lang, 'ask_links'))
            else:
                state.update(user_id, step=next_step)
                await message.reply(get_message(lang, msg_key))
            return

        # --- Links ---
        if step == STEP_ASK_LINKS:
            state.update(user_id, links=text)
            regions = conv.get('selected_regions', [])
            has_our_geos = any(r in regions for r in ('Tier 1', 'Tier 2', 'LATAM'))

            if has_our_geos:
                state.update(user_id, step=STEP_DONE)
                conv = state.get(user_id)
                await _save_lead(conv)
                await _notify(client, conv)
                await _send_finish(message, lang, 'done')
                log.info("Qualified lead: " + get_display_name(conv))
            else:
                state.update(user_id, step=STEP_DONE_OTHER)
                conv = state.get(user_id)
                await _save_lead(conv)
                await _notify(client, conv)
                await _send_finish(message, lang, 'done_other')
                log.info("Lead passed to colleagues: " + get_display_name(conv))
            return

        return

    # --- New contact: check chat history first ---
    try:
        history = []
        async for msg in client.get_chat_history(user_id, limit=2):
            history.append(msg)
        if len(history) > 1:
            log.info("  -> skipped: existing chat history (not a new conversation)")
            return
    except Exception as e:
        log.warning("  -> could not check chat history: " + str(e))

    first_message = message.text or '[media/sticker]'
    lang = detect_language(first_message)

    state.start(
        user_id=user_id,
        username=user.username or '',
        first_name=user.first_name or '',
        last_name=user.last_name or '',
        lang=lang,
        first_message=first_message
    )

    await message.reply(get_message(lang, 'greeting'))
    await asyncio.sleep(1)
    await message.reply(get_message(lang, 'ask_traffic'))
    log.info("New inbound from " + str(user.first_name) + " (@" + str(user.username) + "), lang=" + lang)


# --- Save & notify ---

# Set to True to send vacation notice after qualification. Set to False when back.
VACATION_MODE = False

OUR_REGIONS = ('Tier 1', 'Tier 2', 'LATAM')
OTHER_REGIONS = ('Asia', 'Africa')


FAILED_LEADS_FILE = 'failed_leads.json'


def _reconnect_sheets():
    """Try to reconnect to Google Sheets (e.g. after token expiry)"""
    try:
        new_sheets = SheetsManager()
        log.info("Sheets reconnected successfully")
        return new_sheets
    except Exception as e:
        log.error("Sheets reconnection failed: " + str(e))
        return None


def _save_failed_lead(lead_data):
    """Save lead to local file when Sheets is unavailable"""
    try:
        try:
            with open(FAILED_LEADS_FILE, 'r') as f:
                failed = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            failed = []
        failed.append(lead_data)
        with open(FAILED_LEADS_FILE, 'w') as f:
            json.dump(failed, f, indent=2, ensure_ascii=False)
        log.warning("Lead saved to " + FAILED_LEADS_FILE + " for retry: " + lead_data.get('partner_name', '?'))
    except Exception as e:
        log.error("CRITICAL: could not save failed lead even to file: " + str(e))


def _retry_failed_leads():
    """Try to push failed leads to Sheets. Returns (success, total) count."""
    try:
        with open(FAILED_LEADS_FILE, 'r') as f:
            failed = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0

    if not failed:
        return 0, 0

    success = 0
    remaining = []
    for lead in failed:
        ok = sheets.add_lead(lead)
        if ok:
            success += 1
            log.info("Retried lead OK: " + lead.get('partner_name', '?'))
        else:
            remaining.append(lead)

    with open(FAILED_LEADS_FILE, 'w') as f:
        json.dump(remaining, f, indent=2, ensure_ascii=False)

    return success, len(failed)


async def _save_lead(conv):
    global sheets

    if not sheets:
        log.warning("Sheets not connected, trying to reconnect...")
        sheets = _reconnect_sheets()
        if not sheets:
            log.error("Sheets unavailable, saving lead to file")
            # Build lead_data minimally to save to file
            _save_failed_lead({
                'partner_name': get_display_name(conv),
                'type': ', '.join(detect_type(conv.get('traffic_source', ''))),
                'geo': ', '.join([g for g in conv.get('selected_geos', []) if g != 'Other']),
                'links': conv.get('links', ''),
                'telegram': conv.get('username', ''),
                'notes': 'Traffic: ' + conv.get('traffic_source', ''),
            })
            return

    regions = conv.get('selected_regions', [])
    geos = conv.get('selected_geos', [])
    has_our = any(r in regions for r in OUR_REGIONS)
    has_other = any(r in regions for r in OTHER_REGIONS)

    # Only Asia/Africa — don't import to sheet
    if not has_our:
        log.info("Lead NOT saved to sheet (no relevant GEO): " + get_display_name(conv))
        return

    traffic = conv.get('traffic_source', '')
    detected_types = detect_type(traffic)
    type_str = ', '.join(detected_types)

    # Filter GEOs: only real country codes, no "Other"
    real_geos = [g for g in geos if g != 'Other']
    has_other_countries = 'Other' in geos

    # Build notes
    notes_parts = []
    if not detected_types:
        notes_parts.append("Traffic: " + traffic)
    if has_other:
        other_names = [r for r in regions if r in OTHER_REGIONS]
        notes_parts.append("Also works with: " + ', '.join(other_names))
    if has_other_countries:
        from config import TIER1_CODES, TIER2_CODES, LATAM_CODES
        other_tiers = []
        if 'Other' in geos:
            other_tiers.append("other GEOs not in our list")
        if other_tiers:
            notes_parts.append("+ " + ', '.join(other_tiers))

    geo_str = ', '.join(real_geos)

    username = conv.get('username', '')
    if username:
        try:
            exists, _ = sheets.check_duplicate(username)
        except Exception as e:
            log.error("Duplicate check failed, reconnecting: " + str(e))
            sheets = _reconnect_sheets()
            if not sheets:
                return
            exists, _ = sheets.check_duplicate(username)
        if exists:
            log.info("Duplicate lead skipped: @" + username)
            return

    lead_data = {
        'partner_name': get_display_name(conv),
        'type': type_str,
        'geo': geo_str,
        'links': conv.get('links', ''),
        'telegram': username,
        'notes': '; '.join(notes_parts),
    }

    saved = False
    try:
        saved = sheets.add_lead(lead_data)
        if saved:
            log.info("Lead saved to sheet: " + get_display_name(conv))
    except Exception as e:
        log.error("Failed to save lead: " + str(e))

    if not saved:
        log.error("First attempt failed, reconnecting...")
        sheets = _reconnect_sheets()
        if sheets:
            try:
                saved = sheets.add_lead(lead_data)
                if saved:
                    log.info("Lead saved to sheet after reconnect: " + get_display_name(conv))
            except Exception as e2:
                log.error("Retry also failed: " + str(e2))

    if not saved:
        _save_failed_lead(lead_data)


async def _send_finish(message, lang, msg_key):
    """Send final message + vacation notice if enabled"""
    await message.reply(get_message(lang, msg_key))
    if VACATION_MODE:
        await asyncio.sleep(2)
        await message.reply(get_message(lang, 'vacation'))


async def _notify(client, conv):
    if not NOTIFY_CHAT_ID:
        return
    try:
        await client.send_message(NOTIFY_CHAT_ID, format_notification(conv))
    except Exception as e:
        log.error("Failed to send notification: " + str(e))


# --- Startup ---

async def main():
    global sheets
    log.info("Starting Auto-Responder...")
    try:
        sheets = SheetsManager()
    except Exception as e:
        log.error("Sheets connection failed: " + str(e) + ". Will run without saving.")

    log.info("Whitelist: " + str(len(whitelist)) + " contacts")
    log.info("Listening for incoming messages...")

    await app.start()
    from pyrogram import idle
    await idle()
    await app.stop()


if __name__ == '__main__':
    app.run(main())
