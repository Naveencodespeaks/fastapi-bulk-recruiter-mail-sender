import re
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email


SEPARATOR_PATTERN = re.compile(r"[\s,;]+")


@dataclass(frozen=True)
class ParsedRecipients:
    valid: list[str]
    invalid: list[str]
    duplicate_count: int
    total_tokens: int


def _clean_token(token: str) -> str:
    return token.strip().strip("<>()[]{}'\"")


def parse_and_validate_recipients(raw: str) -> ParsedRecipients:
    tokens = [_clean_token(token) for token in SEPARATOR_PATTERN.split(raw.strip())]
    tokens = [token for token in tokens if token]

    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    duplicate_count = 0

    for token in tokens:
        try:
            result = validate_email(token, check_deliverability=False)
            normalized = result.normalized
        except EmailNotValidError:
            invalid.append(token)
            continue

        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            duplicate_count += 1
            continue

        seen.add(dedupe_key)
        valid.append(normalized)

    return ParsedRecipients(
        valid=valid,
        invalid=invalid,
        duplicate_count=duplicate_count,
        total_tokens=len(tokens),
    )
