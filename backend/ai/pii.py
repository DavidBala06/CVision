"""
PII helpers — mask/unmask candidate-identifying data for safer transport.

The HR dashboard does NOT need full email addresses on the candidate list page;
they only need them on the outreach view (after explicit human action).
Masking by default reduces the blast radius of a leaked snapshot or an
accidental browser-cache exposure.
"""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^([^@]+)@(.+)$")


def mask_email(email: str) -> str:
    """Return j***@domain.com style mask. Empty string for invalid input."""
    if not email or "@" not in email:
        return ""
    m = _EMAIL_RE.match(email.strip())
    if not m:
        return ""
    local, domain = m.group(1), m.group(2)
    if len(local) <= 1:
        masked_local = local + "***"
    else:
        masked_local = local[0] + "***"
    return f"{masked_local}@{domain}"


def mask_candidate_row(row: dict) -> dict:
    """Return a shallow copy of `row` with PII fields masked."""
    masked = dict(row)
    if masked.get("email"):
        masked["email"] = mask_email(masked["email"])
        masked["email_masked"] = True
    else:
        masked["email_masked"] = False
    return masked
