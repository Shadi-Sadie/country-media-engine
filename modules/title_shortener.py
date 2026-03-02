# modules/title_shortener.py

import re

def short_fa_title(category: str, title: str, channel: str) -> str:
    t = (title or "").lower()
    c = (channel or "").lower()

    # HISTORY: tag by outlet when possible
    if category == "history":
        if "bbc" in c or "bbc" in t:
            return "مستند بی‌بی‌سی"
        if "dw" in c or "dw" in t:
            return "مستند دویچه‌وله"
        if "pbs" in c or "pbs" in t:
            return "مستند PBS"
        if "arte" in c or "arte" in t:
            return "مستند ARTE"
        if "al jazeera" in c or "aljazeera" in c or "al jazeera" in t:
            return "مستند الجزیره"
        return "مستند اجتماعی"

    # LIFE: detect subtopics from title
    if category == "life":
        if "wedding" in t:
            return "عروسی"
        if "street food" in t or "food tour" in t:
            return "غذای خیابانی"
        if "recipe" in t or "cooking" in t:
            return "دستور پخت"
        if "village" in t or "rural" in t or "countryside" in t:
            return "زندگی روستایی"
        if "day in" in t or "daily life" in t:
            return "یک روز از زندگی"
        return "زندگی روزمره"

    # NATURE
    if category == "nature":
        if "4k" in t:
            return "طبیعت 4K"
        if "travel" in t:
            return "سفر و مناظر"
        return "مناظر و طبیعت"

    # MUSIC
    if category == "music":
        if "live" in t:
            return "اجرای زنده"
        if "folk" in t or "traditional" in t:
            return "موسیقی سنتی"
        return "موسیقی"

    return "ویدئو"