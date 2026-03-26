"""
Auto-Responder Configuration
Telegram userbot that qualifies inbound leads via personal messages
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- Telegram User API (from my.telegram.org) ---
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE = os.getenv('PHONE', '')

# --- Notification chat ---
NOTIFY_CHAT_ID = int(os.getenv('NOTIFY_CHAT_ID', '0'))

# --- Google Sheets ---
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS', '')
SPREADSHEET_ID = '1YrKC_I7ZZo7BkFI9hKaV5Y-7VGRVMqTOdcm1S66nwdU'
TARGET_SHEET = 'Paripesa'

# --- Whitelist (colleagues to ignore) ---
WHITELIST_FILE = 'whitelist.json'

def load_whitelist():
    try:
        with open(WHITELIST_FILE, 'r') as f:
            data = json.load(f)
            return set(u.lower().lstrip('@') for u in data)
    except FileNotFoundError:
        return set()

# --- Conversation flow ---
CONVERSATION_TIMEOUT = 86400
STATE_FILE = 'conversations.json'

# --- Traffic source keyword mapping (EN / ES / RU + industry slang) ---
TYPE_KEYWORDS = {
    'SEO': [
        # EN
        'seo', 'organic', 'search engine', 'organic traffic', 'search traffic',
        'niche site', 'review site', 'content site', 'seo affiliate',
        # ES
        'trafico organico', 'posicionamiento', 'posicionamiento web',
        # RU
        'сео', 'сеошник', 'сеошка', 'органика', 'органический трафик',
        'поисковый трафик', 'поисковое продвижение', 'вебмастер',
        'контентный сайт', 'обзорный сайт', 'дорвей', 'лью с органики',
    ],
    'PPC': [
        # EN
        'ppc', 'google ads', 'adwords', 'cpc', 'paid search', 'sem',
        'search ads', 'pay per click', 'bing ads',
        # ES
        'pago por clic', 'publicidad en buscadores', 'busqueda pagada',
        # RU
        'ппс', 'контекст', 'контекстная реклама', 'контекстолог',
        'директолог', 'гугл адс', 'адвордс', 'яндекс директ', 'директ',
        'поисковая реклама', 'платный поиск', 'лью с контекста',
    ],
    'STREAMER': [
        # EN
        'stream', 'twitch', 'kick', 'youtube live', 'streamer', 'streaming',
        'live stream', 'livestream', 'casino stream', 'slots stream',
        'gambling stream',
        # ES
        'transmision en vivo', 'en directo', 'directo',
        # RU
        'стрим', 'стример', 'стримы', 'стриминг', 'твич', 'кик',
        'стримлю', 'казино стример', 'слот стример', 'прямой эфир',
    ],
    'INFLUENCER': [
        # EN
        'influencer', 'influenc', 'content creator', 'blogger', 'vlogger',
        'youtuber', 'instagram', 'tiktok', 'ugc', 'kol',
        'influencer marketing', 'brand ambassador',
        # ES
        'influenciador', 'creador de contenido', 'bloguero',
        'marketing de influencia',
        # RU
        'инфлюенсер', 'инфлюэнсер', 'блогер', 'блоггер', 'блог',
        'ютубер', 'тиктокер', 'инстаблогер', 'лидер мнений',
        'тикток', 'инстаграм', 'контент мейкер', 'амбассадор',
        'рекламная интеграция',
    ],
    'MEDIABUY': [
        # EN
        'media buy', 'mediabuy', 'media buying', 'media buyer',
        'facebook ads', 'fb ads', 'push', 'popunder', 'native ads',
        'pop traffic', 'push traffic', 'native traffic', 'display ads',
        'programmatic', 'dsp', 'ad buying', 'paid media',
        # ES
        'compra de medios', 'comprador de medios', 'compra de trafico',
        'arbitraje de trafico', 'publicidad nativa',
        # RU
        'медиабайер', 'медиабаинг', 'медиабай', 'баинг', 'байер', 'баер',
        'медиа баинг', 'медиа байер', 'закуп трафика', 'закупщик',
        'лью трафик', 'лью', 'залив', 'заливаю', 'заливала',
        'арбитраж', 'арбитражник', 'арбитраж трафика',
        'пуши', 'попандер', 'нативка', 'нативная реклама',
        'тизерка', 'тизерная реклама', 'баннерка', 'связка', 'креатив',
    ],
    'NETWORK': [
        # EN
        'affiliate network', 'cpa network', 'aff network',
        'affiliate program', 'partner program',
        # ES
        'red de afiliados', 'red cpa', 'programa de afiliados',
        'red de afiliacion',
        # RU
        'партнерка', 'партнерская сеть', 'партнерская программа',
        'цпа сеть', 'cpa сеть', 'аффилейт', 'афф сеть',
    ],
    'EMAIL': [
        # EN
        'email', 'newsletter', 'mailing', 'email marketing', 'email traffic',
        'email list', 'cold email', 'email blast', 'bulk email',
        # ES
        'correo', 'lista de correo', 'envio masivo', 'boletin',
        # RU
        'емейл', 'имейл', 'рассылка', 'email рассылка', 'почтовая рассылка',
        'спам рассылка', 'лью рассылки', 'емейлер', 'холодные письма',
    ],
    'TIPSTER': [
        # EN
        'tipster', 'tips', 'betting tips', 'predictions', 'picks',
        'betting predictions', 'sports picks', 'handicapper',
        'tipping service', 'paid picks', 'free picks',
        # ES
        'pronosticos', 'pronosticador', 'predicciones',
        'apuestas deportivas', 'analista deportivo',
        # RU
        'типстер', 'каппер', 'капер', 'прогнозист', 'прогнозы',
        'прогнозы на спорт', 'ставки на спорт', 'ставочник',
        'беттинг', 'бетинг', 'беттор', 'бетор',
        'капперский канал', 'продажа прогнозов', 'гандикаппер',
    ],
    'FB': [
        # EN
        'facebook group', 'fb group', 'fb', 'facebook traffic', 'facebook',
        'fb traffic', 'meta ads', 'facebook ads', 'facebook page',
        # ES
        'grupo de facebook', 'trafico facebook', 'anuncios de facebook',
        'publicidad en facebook',
        # RU
        'фб', 'фейсбук', 'фэйсбук', 'фейс', 'фэйс', 'фесбук',
        'фб трафик', 'фб группа', 'лью с фб', 'лью с фейса',
        'залив с фб', 'фб адс', 'мета', 'группа фб',
        'таргет', 'таргетированная реклама', 'таргетолог', 'лью таргет',
    ],
    'InApp/ASO': [
        # EN
        'in-app', 'inapp', 'aso', 'mobile app', 'app store', 'play store',
        'mobile traffic', 'app traffic', 'app install', 'mobile ads',
        'uac', 'rewarded traffic',
        # ES
        'aplicacion', 'trafico movil', 'publicidad movil',
        'instalaciones de apps',
        # RU
        'инапп', 'ин-апп', 'мобильный трафик', 'мобилка', 'мобайл',
        'приложение', 'мобильное приложение', 'прилка', 'аппка', 'апп',
        'асо', 'юак', 'установки приложений', 'мобильная реклама',
        'лью с инаппа', 'лью мобайл', 'мотив', 'мотивированный трафик',
    ],
}

# --- Region options (first level) ---
REGION_OPTIONS = ['Tier 1', 'Tier 2', 'LATAM', 'Asia', 'Africa']

# --- GEO options with flags ---
TIER1_GEOS = {
    'ES': '\U0001f1ea\U0001f1f8 ES',
    'PT': '\U0001f1f5\U0001f1f9 PT',
    'DE': '\U0001f1e9\U0001f1ea DE',
    'AT': '\U0001f1e6\U0001f1f9 AT',
    'CH': '\U0001f1e8\U0001f1ed CH',
    'IT': '\U0001f1ee\U0001f1f9 IT',
    'IE': '\U0001f1ee\U0001f1ea IE',
    'DK': '\U0001f1e9\U0001f1f0 DK',
    'FI': '\U0001f1eb\U0001f1ee FI',
    'NO': '\U0001f1f3\U0001f1f4 NO',
    'SE': '\U0001f1f8\U0001f1ea SE',
    'AU': '\U0001f1e6\U0001f1fa AU',
    'NZ': '\U0001f1f3\U0001f1ff NZ',
    'CA': '\U0001f1e8\U0001f1e6 CA',
    'Other': '\U0001f310 Other',
}
TIER1_CODES = list(TIER1_GEOS.keys())

TIER2_GEOS = {
    'PL': '\U0001f1f5\U0001f1f1 PL',
    'CZ': '\U0001f1e8\U0001f1ff CZ',
    'RO': '\U0001f1f7\U0001f1f4 RO',
    'BG': '\U0001f1e7\U0001f1ec BG',
    'HU': '\U0001f1ed\U0001f1fa HU',
    'HR': '\U0001f1ed\U0001f1f7 HR',
    'SK': '\U0001f1f8\U0001f1f0 SK',
    'SI': '\U0001f1f8\U0001f1ee SI',
    'GR': '\U0001f1ec\U0001f1f7 GR',
    'EE': '\U0001f1ea\U0001f1ea EE',
    'LT': '\U0001f1f1\U0001f1f9 LT',
    'LV': '\U0001f1f1\U0001f1fb LV',
    'Other': '\U0001f310 Other',
}
TIER2_CODES = list(TIER2_GEOS.keys())

LATAM_GEOS = {
    'BR': '\U0001f1e7\U0001f1f7 BR',
    'MX': '\U0001f1f2\U0001f1fd MX',
    'AR': '\U0001f1e6\U0001f1f7 AR',
    'CL': '\U0001f1e8\U0001f1f1 CL',
    'CO': '\U0001f1e8\U0001f1f4 CO',
    'PE': '\U0001f1f5\U0001f1ea PE',
    'Other': '\U0001f310 Other',
}
LATAM_CODES = list(LATAM_GEOS.keys())

# --- Types that DON'T need a link ---
NO_LINK_TYPES = ['PPC', 'MEDIABUY', 'NETWORK', 'FB']

# --- Column mapping (Paripesa sheet, 0-indexed) ---
COLUMNS = {
    'partner_name': 0,
    'type': 1,
    'vertical': 2,
    'geo': 3,
    'first_touch': 4,
    'status': 5,
    'links': 6,
    'telegram': 7,
    'whatsapp': 8,
    'email': 9,
    'linkedin': 10,
    'other_contacts': 11,
    'other_links': 12,
    'date_contacted': 13,
    'synced': 14,
    'notes': 15,
}
