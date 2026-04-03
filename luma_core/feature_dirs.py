import hashlib
import re


MAX_DIRNAME_BYTES = 255
MAX_FEATURE_SLUG_BYTES = 64
MAX_FEATURE_SLUG_TOKENS = 8
DEFAULT_FEATURE_SLUG = "feature"
THAI_TRANSLITERATION_MAP = {
    "ก": "k",
    "ข": "kh",
    "ฃ": "kh",
    "ค": "kh",
    "ฅ": "kh",
    "ฆ": "kh",
    "ง": "ng",
    "จ": "ch",
    "ฉ": "ch",
    "ช": "ch",
    "ซ": "s",
    "ฌ": "ch",
    "ญ": "y",
    "ฎ": "d",
    "ฏ": "t",
    "ฐ": "th",
    "ฑ": "th",
    "ฒ": "th",
    "ณ": "n",
    "ด": "d",
    "ต": "t",
    "ถ": "th",
    "ท": "th",
    "ธ": "th",
    "น": "n",
    "บ": "b",
    "ป": "p",
    "ผ": "ph",
    "ฝ": "f",
    "พ": "ph",
    "ฟ": "f",
    "ภ": "ph",
    "ม": "m",
    "ย": "y",
    "ร": "r",
    "ล": "l",
    "ว": "w",
    "ศ": "s",
    "ษ": "s",
    "ส": "s",
    "ห": "h",
    "ฬ": "l",
    "อ": "o",
    "ฮ": "h",
    "ะ": "a",
    "ั": "a",
    "า": "a",
    "ำ": "am",
    "ิ": "i",
    "ี": "i",
    "ึ": "ue",
    "ื": "ue",
    "ุ": "u",
    "ู": "u",
    "เ": "e",
    "แ": "ae",
    "โ": "o",
    "ใ": "ai",
    "ไ": "ai",
    "ๅ": "a",
    "ๆ": "",
    "็": "",
    "่": "",
    "้": "",
    "๊": "",
    "๋": "",
    "์": "",
    "ํ": "m",
    "ฯ": "",
    "฿": "baht",
}
SLUG_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def _transliterate_thai(text: str) -> str:
    result = []
    for char in text:
        if char in THAI_TRANSLITERATION_MAP:
            result.append(THAI_TRANSLITERATION_MAP[char])
        elif "\u0E00" <= char <= "\u0E7F":
            result.append(" ")
        else:
            result.append(char)
    return "".join(result)


def _normalize_slug(name: str) -> str:
    transliterated = _transliterate_thai(name).replace("&", " and ")
    ascii_text = transliterated.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9\s-]", " ", ascii_text)
    ascii_text = re.sub(r"[-\s]+", "-", ascii_text).strip("-")
    return ascii_text


def _compact_slug(slug: str) -> str:
    tokens = [token for token in slug.split("-") if token]
    compact_tokens = []

    for token in tokens:
        if token in SLUG_STOPWORDS and compact_tokens:
            continue
        compact_tokens.append(token)
        if len(compact_tokens) >= MAX_FEATURE_SLUG_TOKENS:
            break

    compacted = "-".join(compact_tokens) if compact_tokens else DEFAULT_FEATURE_SLUG
    compacted = _truncate_to_bytes(compacted, MAX_FEATURE_SLUG_BYTES).rstrip("-_")
    return compacted or DEFAULT_FEATURE_SLUG


def _with_hash_suffix(slug: str, digest: str, max_bytes: int) -> str:
    suffix = f"-{digest}"
    available_slug_bytes = max_bytes - len(suffix.encode("utf-8"))
    truncated_slug = _truncate_to_bytes(slug, available_slug_bytes).rstrip("-_")
    if not truncated_slug:
        truncated_slug = DEFAULT_FEATURE_SLUG
    return f"{truncated_slug}{suffix}"


def sanitize_slug(name: str) -> str:
    """Convert free-form titles into a filesystem-safe slug."""
    normalized = _normalize_slug(name)
    return _compact_slug(normalized)


def _truncate_to_bytes(value: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""

    result = []
    size = 0

    for char in value:
        char_size = len(char.encode("utf-8"))
        if size + char_size > max_bytes:
            break
        result.append(char)
        size += char_size

    return "".join(result)


def build_feature_dirname(index: int, issue_number: str, title: str) -> str:
    """Build a docs/features directory name that stays within filesystem limits."""
    prefix = f"{index}_issue-{issue_number}_"
    normalized_slug = _normalize_slug(title) or DEFAULT_FEATURE_SLUG
    compact_slug = _compact_slug(normalized_slug)
    digest = hashlib.sha1(normalized_slug.encode("utf-8")).hexdigest()[:8]

    if compact_slug != normalized_slug:
        compact_slug = _with_hash_suffix(compact_slug, digest, MAX_FEATURE_SLUG_BYTES)

    dirname = f"{prefix}{compact_slug}"
    if len(dirname.encode("utf-8")) <= MAX_DIRNAME_BYTES:
        return dirname

    available_slug_bytes = MAX_DIRNAME_BYTES - len(prefix.encode("utf-8"))
    return f"{prefix}{_with_hash_suffix(compact_slug, digest, available_slug_bytes)}"
