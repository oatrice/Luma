import hashlib
import re


MAX_DIRNAME_BYTES = 255
DEFAULT_FEATURE_SLUG = "feature"


def sanitize_slug(name: str) -> str:
    """Convert free-form titles into a filesystem-safe slug."""
    sanitized = re.sub(r"[^\w\s-]", "", name).strip().lower()
    sanitized = re.sub(r"[-\s]+", "-", sanitized).strip("-")
    return sanitized or DEFAULT_FEATURE_SLUG


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
    slug = sanitize_slug(title)
    full_name = f"{prefix}{slug}"

    if len(full_name.encode("utf-8")) <= MAX_DIRNAME_BYTES:
        return full_name

    digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]
    suffix = f"-{digest}"
    available_slug_bytes = MAX_DIRNAME_BYTES - len(prefix.encode("utf-8")) - len(suffix.encode("utf-8"))

    truncated_slug = _truncate_to_bytes(slug, available_slug_bytes).rstrip("-_")
    if not truncated_slug:
        truncated_slug = DEFAULT_FEATURE_SLUG

    return f"{prefix}{truncated_slug}{suffix}"
