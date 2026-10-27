import re

from django.core.exceptions import ValidationError

RESERVED_CODES = {"admin", "api", "app", "platform", "www", "static", "login", "register", "billing", "support"}
CODE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,28}[a-z0-9])$")


def normalize_code(value):
    return (value or "").strip().lower()


def validate_institute_code(value):
    if not CODE_PATTERN.match(value):
        raise ValidationError(
            "Use 3–30 lowercase letters, numbers or dashes, starting and ending with a letter or number."
        )
    if value in RESERVED_CODES:
        raise ValidationError("This code is reserved. Please choose another.")
