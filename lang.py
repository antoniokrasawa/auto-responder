"""
Language detection and message templates for Auto-Responder
"""
import re
from config import TIER1_GEOS, TIER2_GEOS, LATAM_GEOS


def detect_language(text):
    if not text:
        return 'en'
    if re.search(r'[\u0400-\u04FF]', text):
        return 'ru'
    spanish_words = ['hola', 'buenas', 'somos', 'tenemos', 'trafico',
                     'ofrecemos', 'colaborar', 'propuesta', 'contacto',
                     'empresa', 'agencia', 'estamos']
    if any(w in text.lower() for w in spanish_words):
        return 'es'
    return 'en'


def _geo_list(geos_dict):
    """Format geo dict as numbered list with flags"""
    lines = []
    for i, (code, flag_label) in enumerate(geos_dict.items(), 1):
        lines.append(str(i) + ") " + flag_label)
    return '\n'.join(lines)


TIER1_LIST = _geo_list(TIER1_GEOS)
TIER2_LIST = _geo_list(TIER2_GEOS)
LATAM_LIST = _geo_list(LATAM_GEOS)


MESSAGES = {
    'en': {
        'greeting': (
            "Hi! Thanks for reaching out. I'll review your message and get back to you shortly.\n\n"
            "Meanwhile, could you answer a few quick questions to speed things up?"
        ),
        'ask_traffic': (
            "What's your traffic source / what do you do?\n"
            "(SEO, PPC, FB, media buying, streaming, tipster, affiliate network, etc.)"
        ),
        'ask_region': (
            "What regions do you work with?\n\n"
            "1) Tier 1 (Western Europe, Scandinavia, AU, NZ, CA)\n"
            "2) Tier 2 (Eastern Europe, Baltics, Balkans)\n"
            "3) LATAM\n"
            "4) Asia\n"
            "5) Africa\n\n"
            "Reply with numbers, e.g.: 1 3"
        ),
        'ask_geo_tier1': (
            "Which Tier 1 countries?\n\n"
            + TIER1_LIST + "\n\n"
            "Reply with codes (ES DE IT) or numbers (1 3 6), or ALL"
        ),
        'ask_geo_tier2': (
            "Which Tier 2 countries?\n\n"
            + TIER2_LIST + "\n\n"
            "Reply with codes (PL CZ RO) or numbers (1 2 3), or ALL"
        ),
        'ask_geo_latam': (
            "Which LATAM countries?\n\n"
            + LATAM_LIST + "\n\n"
            "Reply with codes (BR MX) or numbers (1 2), or ALL"
        ),
        'ask_links': (
            "Please share your website, channel, or portfolio link:"
        ),
        'done': (
            "Thanks! I've noted everything down. I'll review and get back to you soon."
        ),
        'done_other': (
            "Thanks for the info! I'll pass this to a colleague who covers those regions. They'll reach out soon."
        ),
        'already_qualified': (
            "Thanks, I already have your info. I'll get back to you soon!"
        ),
        'vacation': (
            "P.S. I'm currently on vacation until the end of this week. "
            "I'll definitely get back to you next week and we'll continue our conversation about the partnership!"
        ),
        'invalid_region': (
            "Please reply with numbers 1-5, e.g.: 1 3"
        ),
        'invalid_geo': (
            "Please reply with country codes or numbers from the list, or ALL"
        ),
    },
    'es': {
        'greeting': (
            "Hola! Gracias por escribir. Revisare tu mensaje y te respondo pronto.\n\n"
            "Mientras tanto, podrias responder unas preguntas rapidas?"
        ),
        'ask_traffic': (
            "Cual es tu fuente de trafico / a que te dedicas?\n"
            "(SEO, PPC, FB, media buying, streaming, tipster, red de afiliados, etc.)"
        ),
        'ask_region': (
            "Con que regiones trabajas?\n\n"
            "1) Tier 1 (Europa Occidental, Escandinavia, AU, NZ, CA)\n"
            "2) Tier 2 (Europa del Este, Balticos, Balcanes)\n"
            "3) LATAM\n"
            "4) Asia\n"
            "5) Africa\n\n"
            "Responde con numeros, ej: 1 3"
        ),
        'ask_geo_tier1': (
            "Cuales paises de Tier 1?\n\n"
            + TIER1_LIST + "\n\n"
            "Responde con codigos (ES DE IT) o numeros (1 3 6), o ALL"
        ),
        'ask_geo_tier2': (
            "Cuales paises de Tier 2?\n\n"
            + TIER2_LIST + "\n\n"
            "Responde con codigos (PL CZ RO) o numeros (1 2 3), o ALL"
        ),
        'ask_geo_latam': (
            "Cuales paises de LATAM?\n\n"
            + LATAM_LIST + "\n\n"
            "Responde con codigos (BR MX) o numeros (1 2), o ALL"
        ),
        'ask_links': (
            "Comparte el link de tu sitio web, canal o portafolio:"
        ),
        'done': (
            "Gracias! Ya tengo toda la info. Te respondo pronto."
        ),
        'done_other': (
            "Gracias por la info! Se la paso a un colega que cubre esas regiones. Te contactara pronto."
        ),
        'already_qualified': (
            "Gracias, ya tengo tu info. Te respondo pronto!"
        ),
        'vacation': (
            "P.D. Ahora mismo estoy de vacaciones hasta el final de esta semana. "
            "Te respondo la semana que viene sin falta y seguimos hablando sobre la colaboracion!"
        ),
        'invalid_region': (
            "Responde con numeros del 1 al 5, ej: 1 3"
        ),
        'invalid_geo': (
            "Responde con codigos de pais o numeros de la lista, o ALL"
        ),
    },
    'ru': {
        'greeting': (
            "Привет! Спасибо за сообщение. Я посмотрю и отвечу в ближайшее время.\n\n"
            "Пока можешь ответить на пару быстрых вопросов?"
        ),
        'ask_traffic': (
            "Какой у тебя источник трафика / чем занимаешься?\n"
            "(SEO, PPC, FB, медиабаинг, стриминг, типстер, партнерская сеть и т.д.)"
        ),
        'ask_region': (
            "С какими регионами работаешь?\n\n"
            "1) Tier 1 (Зап. Европа, Скандинавия, AU, NZ, CA)\n"
            "2) Tier 2 (Вост. Европа, Балтика, Балканы)\n"
            "3) LATAM\n"
            "4) Asia\n"
            "5) Africa\n\n"
            "Ответь цифрами, напр.: 1 3"
        ),
        'ask_geo_tier1': (
            "Какие конкретно страны Tier 1?\n\n"
            + TIER1_LIST + "\n\n"
            "Ответь кодами (ES DE IT) или номерами (1 3 6), или ALL"
        ),
        'ask_geo_tier2': (
            "Какие конкретно страны Tier 2?\n\n"
            + TIER2_LIST + "\n\n"
            "Ответь кодами (PL CZ RO) или номерами (1 2 3), или ALL"
        ),
        'ask_geo_latam': (
            "Какие конкретно страны LATAM?\n\n"
            + LATAM_LIST + "\n\n"
            "Ответь кодами (BR MX) или номерами (1 2), или ALL"
        ),
        'ask_links': (
            "Скинь ссылку на сайт, канал или портфолио:"
        ),
        'done': (
            "Спасибо! Всё записал. Скоро вернусь с ответом."
        ),
        'done_other': (
            "Спасибо за инфо! Передам коллеге, который работает с этими регионами. Скоро свяжется."
        ),
        'already_qualified': (
            "Спасибо, у меня уже есть твоя инфо. Скоро отвечу!"
        ),
        'vacation': (
            "P.S. Я сейчас в отпуске до конца этой недели. "
            "Обязательно отвечу на следующей неделе и продолжим диалог о сотрудничестве!"
        ),
        'invalid_region': (
            "Ответь цифрами от 1 до 5, напр.: 1 3"
        ),
        'invalid_geo': (
            "Ответь кодами стран или номерами из списка, или ALL"
        ),
    },
}


def get_message(lang, key):
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'][key])
