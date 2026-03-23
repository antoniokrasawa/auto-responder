"""
Conversation state persistence for Auto-Responder
"""
import json
import time
from config import STATE_FILE, CONVERSATION_TIMEOUT

# Conversation steps
STEP_ASK_TRAFFIC = 'traffic'
STEP_ASK_REGION = 'region'
STEP_ASK_GEO_TIER1 = 'geo_tier1'
STEP_ASK_GEO_TIER2 = 'geo_tier2'
STEP_ASK_GEO_LATAM = 'geo_latam'
STEP_ASK_LINKS = 'links'
STEP_DONE = 'done'
STEP_DONE_OTHER = 'done_other'
STEP_EXPIRED = 'expired'


class ConversationState:
    def __init__(self):
        self.conversations = {}
        self._load()

    def _load(self):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                self.conversations = {int(k): v for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.conversations = {}

    def _save(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.conversations, f, indent=2, ensure_ascii=False)

    def get(self, user_id):
        conv = self.conversations.get(user_id)
        if not conv:
            return None
        if conv.get('step') == STEP_EXPIRED:
            return None
        if time.time() - conv.get('started_at', 0) > CONVERSATION_TIMEOUT:
            conv['step'] = STEP_EXPIRED
            self._save()
            return None
        return conv

    def start(self, user_id, username, first_name, last_name, lang, first_message):
        self.conversations[user_id] = {
            'step': STEP_ASK_TRAFFIC,
            'username': username or '',
            'first_name': first_name or '',
            'last_name': last_name or '',
            'lang': lang,
            'first_message': first_message,
            'traffic_source': '',
            'selected_regions': [],
            'selected_geos': [],
            'links': '',
            'started_at': time.time(),
        }
        self._save()

    def update(self, user_id, **kwargs):
        if user_id in self.conversations:
            self.conversations[user_id].update(kwargs)
            self._save()

    def remove(self, user_id):
        self.conversations.pop(user_id, None)
        self._save()

    def is_done(self, user_id):
        conv = self.conversations.get(user_id)
        return conv is not None and conv.get('step') in (STEP_DONE, STEP_DONE_OTHER, STEP_EXPIRED)
