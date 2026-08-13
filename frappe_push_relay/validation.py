from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _

MAX_PROJECT_NAME = 140
MAX_USER_ID = 140
MAX_TOPIC_NAME = 140
MAX_REGISTRATION_ID = 4096
MAX_DATA_BYTES = 2048


def bounded_text(value, label, max_length):
    value = str(value or "").strip()
    if not value:
        frappe.throw(_("{0} is required").format(label))
    if len(value) > max_length:
        frappe.throw(_("{0} is too long").format(label))
    if any(ord(char) < 32 for char in value):
        frappe.throw(_("{0} contains invalid control characters").format(label))
    return value


def project_name(value):
    return bounded_text(value, _("Project name"), MAX_PROJECT_NAME)


def user_id(value):
    return bounded_text(value, _("User ID"), MAX_USER_ID)


def topic_name(value):
    return bounded_text(value, _("Topic name"), MAX_TOPIC_NAME)


def registration_id(value):
    return bounded_text(value, _("FCM registration identifier"), MAX_REGISTRATION_ID)


def registration_hash(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def data_payload(value):
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            frappe.throw(_("Notification data must be valid JSON"))
    if not isinstance(value, dict):
        frappe.throw(_("Notification data must be a JSON object"))
    normalized = {str(key): item for key, item in value.items()}
    encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_DATA_BYTES:
        frappe.throw(_("Notification data payload is too large"))
    return normalized
