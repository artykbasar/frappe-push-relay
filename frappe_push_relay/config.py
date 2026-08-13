from __future__ import annotations

import json
from urllib.parse import urlparse

import frappe
from frappe import _

SETTINGS_DOCTYPE = "Push Relay Settings"


def get_settings():
    return frappe.get_single(SETTINGS_DOCTYPE)


def get_mode() -> str:
    settings = get_settings()
    return settings.mode or "Disabled"


def get_site_url() -> str:
    return (frappe.utils.get_url() or "").rstrip("/")


def normalize_site_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        frappe.throw(_("Invalid site URL"))
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        frappe.throw(_("Site URL must be a base URL without credentials, path, query, or fragment"))
    try:
        port_value = parsed.port
    except ValueError:
        frappe.throw(_("Invalid site URL port"))
    hostname = parsed.hostname.lower()
    if ":" in hostname:
        hostname = f"[{hostname}]"
    port = f":{port_value}" if port_value else ""
    return f"{parsed.scheme}://{hostname}{port}"


def validate_relay_url(url: str) -> str:
    normalized = normalize_site_url(url)
    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").lower()
    is_dev_local = bool(frappe.conf.developer_mode) and (
        hostname == "localhost" or hostname.endswith(".localhost") or hostname in {"127.0.0.1", "::1"}
    )
    if parsed.scheme != "https" and not is_dev_local:
        frappe.throw(_("Push relay URLs must use HTTPS outside localhost development"))
    return normalized


def firebase_web_config(settings=None) -> dict:
    settings = settings or get_settings()
    return {
        "apiKey": settings.firebase_api_key,
        "authDomain": settings.firebase_auth_domain,
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
        "messagingSenderId": settings.firebase_messaging_sender_id,
        "appId": settings.firebase_app_id,
        "measurementId": settings.firebase_measurement_id,
    }


def service_account_dict(settings=None) -> dict:
    settings = settings or get_settings()
    raw = settings.get_password("firebase_service_account_json", raise_exception=False)
    if not raw:
        frappe.throw(_("Firebase service account JSON is not configured"))
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        frappe.throw(_("Firebase service account JSON is invalid: {0}").format(exc))
    if not isinstance(value, dict) or not value.get("project_id"):
        frappe.throw(_("Firebase service account JSON is missing project_id"))
    return value
