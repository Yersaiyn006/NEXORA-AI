"""Business-neutral requests: purchase, booking, callback, service enquiry."""
import re

INTENT = re.compile(r'(?:хочу\s+(?:заказ\w*|купит\w*|покупк\w*|брон\w*|запис\w*|оставит\w*\s+заявк\w*)|(?:оформит\w*|оставит\w*|сделат\w*)\s+(?:заказ\w*|заявк\w*|брон\w*)|запиш(?:ите|и|усь|емся)|закаж(?:у|ите|ем)|куплю|брон(?:ируйте|ировать)|перезвоните|тапсырыс\s*бер\w*|сатып\s*ал\w*|жазыл\w*|^(?:запись|заявка|заказ|бронь|тапсырыс)[!.? ]*$)', re.I)

def wants_request(text):
    return bool(INTENT.search(text))

def request_label(business):
    return 'заявку'

def extract_subject(text):
    # Only extract a clearly stated subject; otherwise ask, never guess.
    match = re.search(r'(?:на|заказать|купить|заказ|бронь|бронь на|тапсырыс)\s+(.+)', text, re.I)
    if not match:
        return None
    value = re.split(r'\b(?:завтра|сегодня|послезавтра|ертең|бүгін|на\s+завтра)\b|\d{2}\.\d{2}\.\d{4}', match.group(1), maxsplit=1, flags=re.I)[0].strip(' .,!?')
    return value if 2 <= len(value) <= 200 and value.casefold() not in ('заявку', 'заказ', 'бронь', 'запись') else None
