"""Institute branding (white-label): logo and theme colour. Only used when the plan includes it."""

import re

from apps.subscriptions.features import Feature

# Colours that keep white text readable (WCAG AA) on buttons and stay readable as link text.
BRAND_COLORS = {
    "indigo": "#4f46e5",
    "blue": "#1d4ed8",
    "teal": "#0f766e",
    "green": "#15803d",
    "purple": "#7e22ce",
    "rose": "#be123c",
    "orange": "#c2410c",
    "slate": "#334155",
}
DEFAULT_COLOR = "indigo"
LOGO_MAX_CHARS = 200_000  # ~150 KB image; the app shrinks uploads to 256 px first
LOGO_PATTERN = re.compile(r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$")


def branding_allowed(tenant):
    subscription = getattr(tenant, "subscription", None)
    return bool(subscription and Feature.WHITE_LABEL in subscription.plan.features)


def effective_branding(tenant):
    """(logo, colour key, colour hex) to show for the institute: defaults when the plan lacks branding."""
    if not branding_allowed(tenant):
        return "", DEFAULT_COLOR, BRAND_COLORS[DEFAULT_COLOR]
    key = tenant.brand_color if tenant.brand_color in BRAND_COLORS else DEFAULT_COLOR
    return tenant.logo, key, BRAND_COLORS[key]
