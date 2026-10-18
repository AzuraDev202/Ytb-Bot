"""Extract concrete public contact details from a channel description."""
import html
import re
from urllib.parse import urlsplit

CONTACT_COLUMNS = ["Email", "Facebook", "Liên Hệ Khác"]
_EMAIL = re.compile(r"(?<![\w.+-])[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,63}(?![\w-])", re.I)
_SOCIAL = re.compile(
    r"(?<![\w@./-])(?:https?://)?(?:(?:www|m)\.)?"
    r"(?:facebook\.com|fb\.com|fb\.me|instagram\.com|linkedin\.com|tiktok\.com|"
    r"twitter\.com|x\.com|t\.me|telegram\.me|zalo\.me|wa\.me|api\.whatsapp\.com)"
    r"/[^\s<>\"\u201c\u201d]+", re.I)
_NON_CONTACT = {"share", "sharer", "sharer.php", "intent", "login", "help", "privacy", "policies", "terms"}


def extract_contacts(description):
    """Return contact fields, or an empty dict when no concrete contact exists.

    Only inspect supplied text; never fetch links or infer unlisted addresses.
    """
    text = html.unescape(description or "")
    emails, facebook, others = {}, {}, {}
    for match in _EMAIL.finditer(text):
        value = match.group().rstrip(".")
        emails.setdefault(value.casefold(), value)
    for match in _SOCIAL.finditer(text):
        value = match.group().rstrip(".,;:!?)]}'\u3002\u2026")
        value = value if re.match(r"https?://", value, re.I) else "https://" + value
        parsed = urlsplit(value)
        path = parsed.path.strip("/")
        if not path or path.split("/")[0].casefold() in _NON_CONTACT:
            continue
        host = parsed.hostname.removeprefix("www.").removeprefix("m.")
        target = facebook if host in {"facebook.com", "fb.com", "fb.me"} else others
        target.setdefault(value.casefold(), value)
    if not (emails or facebook or others):
        return {}
    return dict(zip(CONTACT_COLUMNS, ("\n".join(values.values()) for values in (emails, facebook, others))))
