"""Password rules. Each institute picks a policy; platform super admins use PLATFORM_PASSWORD_POLICY."""

import re

from django.conf import settings
from django.contrib.auth.password_validation import CommonPasswordValidator, UserAttributeSimilarityValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from rest_framework import serializers


class PasswordPolicy(models.TextChoices):
    EASY = "easy", "Easy — at least 4 characters"
    STANDARD = "standard", "Standard — at least 8 characters, not a common password"
    STRONG = "strong", "Strong — at least 8 characters with letters and numbers, not a common password"


MIN_LENGTH = {PasswordPolicy.EASY: 4, PasswordPolicy.STANDARD: 8, PasswordPolicy.STRONG: 8}


def policy_for(tenant):
    return tenant.password_policy if tenant is not None else settings.PLATFORM_PASSWORD_POLICY


def password_errors(password, policy, user=None):
    """Return a list of messages explaining why ``password`` breaks ``policy`` (empty if it is fine)."""
    errors = []
    min_length = MIN_LENGTH[policy]
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters.")
    if policy in (PasswordPolicy.STANDARD, PasswordPolicy.STRONG):
        try:
            CommonPasswordValidator().validate(password)
        except DjangoValidationError:
            errors.append("This password is too common.")
    if policy == PasswordPolicy.STRONG:
        if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
            errors.append("Password must contain both letters and numbers.")
        if user is not None:
            try:
                UserAttributeSimilarityValidator().validate(password, user)
            except DjangoValidationError:
                errors.append("Password is too similar to the username or name.")
    return errors


def check_password(password, policy, field_name="password", user=None):
    """Raise a DRF validation error on ``field_name`` if the password breaks the policy."""
    errors = password_errors(password, policy, user)
    if errors:
        raise serializers.ValidationError({field_name: errors})
