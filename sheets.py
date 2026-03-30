"""
Google Sheets writer for Auto-Responder
Writes qualified leads to Paripesa sheet in Base spreadsheet
"""
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
from config import SPREADSHEET_ID, TARGET_SHEET, GOOGLE_CREDENTIALS, COLUMNS


class SheetsManager:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._sheet = None
        self._connect()

    def _connect(self):
        """Establish connection to Google Sheets"""
        try:
            if GOOGLE_CREDENTIALS.startswith('{'):
                creds_dict = json.loads(GOOGLE_CREDENTIALS)
                credentials = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                credentials = Credentials.from_service_account_file(
                    GOOGLE_CREDENTIALS,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )

            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            self._sheet = self.spreadsheet.worksheet(TARGET_SHEET)
            print("[OK] Connected to Google Sheets")
        except Exception as e:
            print(f"[ERROR] Failed to connect to Google Sheets: {e}")
            raise

    def check_duplicate(self, telegram_username):
        """Check if telegram username already exists in Paripesa sheet"""
        try:
            telegram_col = self._sheet.col_values(COLUMNS['telegram'] + 1)
            formatted = f"t.me/{telegram_username.lstrip('@')}"
            for idx, value in enumerate(telegram_col[1:], start=2):
                if value and formatted.lower() in value.lower():
                    return True, idx
            return False, None
        except Exception as e:
            print(f"[ERROR] Error checking duplicates: {e}")
            return False, None

    def add_lead(self, lead_data):
        """
        Add a qualified inbound lead to Paripesa sheet.

        lead_data keys: partner_name, type, geo, links, telegram, notes
        Auto-fills: first_touch=Inbound, status=NEW
        Date Contacted left empty for NEW status (filled later when status changes to CONTACTED+)
        """
        try:
            row = [''] * 16  # Paripesa: 16 columns A-P

            row[COLUMNS['partner_name']] = lead_data.get('partner_name', '')
            row[COLUMNS['type']] = lead_data.get('type', '')
            row[COLUMNS['geo']] = lead_data.get('geo', '')
            row[COLUMNS['links']] = lead_data.get('links', '')
            row[COLUMNS['first_touch']] = 'Inbound'
            row[COLUMNS['status']] = 'NEW'
            row[COLUMNS['notes']] = lead_data.get('notes', '')

            # Telegram field
            telegram = lead_data.get('telegram', '')
            if telegram:
                row[COLUMNS['telegram']] = f"t.me/{telegram.lstrip('@')}"

            last_row = len(self._sheet.get_all_values())
            self._sheet.update(
                f'A{last_row + 1}', [row],
                value_input_option='USER_ENTERED'
            )
            print(f"[OK] Added inbound lead: {lead_data.get('partner_name')}")
            return True

        except Exception as e:
            print(f"[ERROR] Error adding lead: {e}")
            return False
