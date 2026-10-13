"""Rule-based intent recognition. No external APIs or invented availability."""
import re
from difflib import SequenceMatcher

BOOKING = re.compile(r"(?:запис(?:аться|ать|ывай|ывайте|ите|ь|ься|ку|ки)|запиш(?:и|ите|усь|емся)|заявк\w*|брон(?:ь|ировать|ируй|ируйте)|хочу\s+к\s+вам|можно\s+к\s+вам|жазыл\w*|жазып\s+қой\w*|бронд\w*)", re.I)
CANCEL = re.compile(r"^(?:отмена(?:\s+(?:заказа|заявки|брони))?|отменить\s+(?:заказ|заявку|бронь)|стоп\s+заявка|жазылудан\s+бас\s+тарту|бас\s+тарту|cancel)$", re.I)
SERVICES = re.compile(r"(?:какие|какая|список|перечень|все|қандай|тізім|бар\s*ма).{0,40}(?:услуг\w*|қызмет\w*)|(?:услуг\w*|қызмет\w*).{0,35}(?:есть|оказываете|бар|қандай)|^(?:услуги|қызметтер|прайс(?:-лист)?)\??$", re.I)


def is_booking(text):
    return bool(BOOKING.search(text))


def is_cancel(text):
    return bool(CANCEL.fullmatch(text.strip()))


def asks_services(text):
    return bool(SERVICES.search(text.strip()))


def normalized_words(text):
    return re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)


def similar_word(a, b):
    if a == b:
        return True
    if len(a) < 5 or len(b) < 5:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.84
