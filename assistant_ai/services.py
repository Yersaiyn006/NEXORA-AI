import re

from .models import KnowledgeItem


STOP_WORDS = {
    "сколько", "стоит", "какая", "какой", "какие",
    "можно", "ваш", "ваша", "ваши", "есть",
    "мен", "қанша", "бағасы", "сіздерде",
    "the", "what", "does", "have",
}

CATEGORY_HINTS = {
    "schedule": [
        "время", "работаете", "работы", "открыты",
        "график", "часов", "қашан", "уақыт",
    ],
    "price": [
        "цена", "стоимость", "прайс", "баға",
    ],
}


def tokenize(text):
    return {
        word
        for word in re.findall(r"\w+", text.lower())
        if len(word) >= 3 and word not in STOP_WORDS
    }


def find_answer(business, question):
    question_tokens = tokenize(question)

    if not question_tokens:
        return None

    items = KnowledgeItem.objects.filter(
        business=business,
        is_active=True,
    )

    best_item = None
    best_score = 0
    second_score = 0

    for item in items:
        title_tokens = tokenize(item.title)
        content_tokens = tokenize(item.content)

        title_matches = len(question_tokens & title_tokens)
        content_matches = len(question_tokens & content_tokens)

        score = title_matches * 4 + content_matches

        for category, hints in CATEGORY_HINTS.items():
            if item.category == category:
                if any(hint in question.lower() for hint in hints):
                    score += 2

        if score > best_score:
            second_score = best_score
            best_score = score
            best_item = item
        elif score > second_score:
            second_score = score

    if best_item and best_score >= 2 and best_score > second_score:
        return best_item.content

    return None