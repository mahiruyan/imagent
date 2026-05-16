from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

COMPANY_SUFFIXES = {
    "ltd",
    "limited",
    "sti",
    "şti",
    "sirketi",
    "şirketi",
    "san",
    "tic",
    "as",
    "aş",
    "anonim",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    lowered = strip_accents(value.lower())
    lowered = lowered.replace("ı", "i").replace("ğ", "g").replace("ş", "s")
    lowered = lowered.replace("ç", "c").replace("ö", "o").replace("ü", "u")
    tokens = re.findall(r"[a-z0-9]+", lowered)
    cleaned = [token for token in tokens if token not in COMPANY_SUFFIXES]
    return " ".join(cleaned)


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)
    if not digits:
        return None
    if digits.startswith("90"):
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+90{digits[1:]}"
    if len(digits) == 10:
        return f"+90{digits}"
    return f"+{digits}" if value.strip().startswith("+") else digits


def normalize_website(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return f"{host}{path}" if path else host

