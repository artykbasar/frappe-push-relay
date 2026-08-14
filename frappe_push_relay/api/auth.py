from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password, set_encrypted_password

from frappe_push_relay.config import get_settings
from frappe_push_relay.security import normalize_site_identity, validate_callback_peer_ip, validate_public_callback_url


CALLBACK_PATH = "/api/method/frappe.push_notification.auth_webhook"
MAX_CALLBACK_RESPONSE_BYTES = 4096


def _callback_url(endpoint, protocol, port, webhook_route):
    route = urlparse(str(webhook_route or ""))
    if route.scheme or route.netloc or route.path != CALLBACK_PATH:
        frappe.throw(_("Invalid relay registration callback route"))

    if str(endpoint).startswith(("http://", "https://")):
        base = endpoint.rstrip("/")
    else:
        scheme = protocol or "https"
        port_part = f":{port}" if port and str(port) not in {"80", "443"} else ""
        base = f"{scheme}://{endpoint}{port_part}"
    return urljoin(base + "/", str(webhook_route).lstrip("/"))


def _registration_rate_limit(registering_host):
    request_ip = str(getattr(frappe.local, "request_ip", "unknown") or "unknown")
    hour = now_datetime().strftime("%Y%m%d%H")
    for scope, value, limit in (("ip", request_ip, 60), ("site", registering_host, 20)):
        key = f"push-relay:registration:{scope}:{value}:{hour}"
        current = frappe.cache.incr(key)
        if current == 1:
            frappe.cache.expire(key, 3700)
        if current > limit:
            frappe.throw(_("Too many relay registration attempts"), frappe.RateLimitExceededError)


def _response_peer_ip(response):
    candidates = []
    connection = getattr(response.raw, "_connection", None) or getattr(response.raw, "connection", None)
    if connection is not None:
        candidates.append(getattr(connection, "sock", None))

    for chain in (("_fp", "fp", "raw", "_sock"), ("_original_response", "fp", "raw", "_sock")):
        obj = response.raw
        try:
            for attr in chain:
                obj = getattr(obj, attr)
            candidates.append(obj)
        except AttributeError:
            continue

    for sock in candidates:
        if sock is None:
            continue
        try:
            return sock.getpeername()[0]
        except OSError:
            continue
    return None


def _get_or_create_relay_site(site_name):
    site_name = normalize_site_identity(site_name)
    name = frappe.db.exists("Push Relay Site", {"site_name": site_name})
    if name:
        return frappe.get_doc("Push Relay Site", name)

    try:
        return frappe.get_doc({
            "doctype": "Push Relay Site",
            "site_name": site_name,
            "status": "Pending",
            "enabled": 0,
        }).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # A simultaneous first registration may have created the same unique site.
        name = frappe.db.exists("Push Relay Site", {"site_name": site_name})
        if not name:
            raise
        return frappe.get_doc("Push Relay Site", name)


def _lock_relay_site(site_doc):
    frappe.db.sql(
        "SELECT name FROM `tabPush Relay Site` WHERE name = %s FOR UPDATE",
        site_doc.name,
    )
    site_doc.reload()
    return site_doc


def _existing_api_credentials(user_name):
    api_key = frappe.db.get_value("User", user_name, "api_key")
    api_secret = get_decrypted_password("User", user_name, "api_secret", raise_exception=False)
    if api_key and api_secret:
        return api_key, api_secret
    return None


def _write_api_credentials(user_name):
    api_key = frappe.db.get_value("User", user_name, "api_key") or frappe.generate_hash(length=24)
    api_secret = frappe.generate_hash(length=32)

    # Do not save a User document here. User insert hooks/background work can change
    # its modified timestamp while a relay registration is in flight. API auth only
    # needs User.api_key plus the encrypted api_secret in __Auth.
    frappe.db.set_value(
        "User",
        user_name,
        {"api_key": api_key, "api_secret": "********"},
        update_modified=False,
    )
    set_encrypted_password("User", user_name, api_secret, "api_secret")
    return api_key, api_secret


def _create_api_user(site_doc):
    if site_doc.api_user and frappe.db.exists("User", site_doc.api_user):
        if credentials := _existing_api_credentials(site_doc.api_user):
            return credentials
        user_name = site_doc.api_user
    else:
        suffix = frappe.generate_hash(length=12).lower()
        email = f"push-relay-{suffix}@relay.local"
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": "Push Relay",
            "last_name": site_doc.site_name[:80],
            "enabled": 1,
            "send_welcome_email": 0,
            "user_type": "System User",
        })
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
        user_name = user.name
        frappe.db.set_value("Push Relay Site", site_doc.name, "api_user", user_name, update_modified=False)
        site_doc.api_user = user_name

    return _write_api_credentials(user_name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def get_credential(endpoint, protocol="https", port=None, token=None, webhook_route=None, site_name=None, **kwargs):
    settings = get_settings()
    if not token or not webhook_route or len(str(token)) > 256:
        frappe.throw(_("A valid registration token and webhook route are required"))

    callback = validate_public_callback_url(
        _callback_url(endpoint, protocol, port, webhook_route),
        allow_localhost=bool(frappe.conf.developer_mode),
    )
    registering_host = normalize_site_identity(callback)
    if normalize_site_identity(endpoint) != registering_host:
        frappe.throw(_("Registration endpoint must match the callback host"), frappe.PermissionError)
    if site_name and normalize_site_identity(site_name) != registering_host:
        frappe.throw(_("Site name must match the verified callback host"), frappe.PermissionError)

    current_host = normalize_site_identity(frappe.utils.get_url())
    is_self = current_host == registering_host
    if settings.mode != "Local" or (not is_self and not settings.allow_other_sites_to_use_this_relay):
        frappe.throw(_("This site is not accepting relay clients"), frappe.PermissionError)
    _registration_rate_limit(registering_host)
    allow_local_peer = bool(frappe.conf.developer_mode) and (
        registering_host == "localhost" or registering_host.endswith(".localhost")
    )
    session = requests.Session()
    session.trust_env = False
    try:
        with session.get(callback, timeout=(3.05, 10), allow_redirects=False, stream=True) as response:
            peer_ip = _response_peer_ip(response)
            if not peer_ip:
                frappe.throw(_("Could not verify registration callback peer address"))
            validate_callback_peer_ip(peer_ip, allow_localhost=allow_local_peer)
            response.raise_for_status()
            raw = response.raw.read(MAX_CALLBACK_RESPONSE_BYTES + 1, decode_content=True)
            encoding = response.encoding or "utf-8"
            content_type = response.headers.get("content-type", "")
    finally:
        session.close()

    if len(raw) > MAX_CALLBACK_RESPONSE_BYTES:
        frappe.throw(_("Relay registration callback response was too large"))
    text = raw.decode(encoding, errors="replace")
    if "json" in content_type:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            frappe.throw(_("Relay registration callback returned invalid JSON"))
    else:
        payload = text

    returned_token = payload.get("message") if isinstance(payload, dict) else payload
    if str(returned_token).strip().strip('"') != str(token):
        frappe.throw(_("Relay registration callback token did not match"), frappe.AuthenticationError)

    site_doc = _lock_relay_site(_get_or_create_relay_site(registering_host))
    if not is_self and site_doc.status in {"Rejected", "Disabled"}:
        frappe.throw(_("This relay site has been rejected or disabled"), frappe.PermissionError)

    if settings.registration_policy == "Approval Required" and not is_self and site_doc.status != "Active":
        site_doc.status = "Pending"
        site_doc.enabled = 0
        site_doc.save(ignore_permissions=True)
        return {"success": False, "pending_approval": True, "message": _("Relay registration is pending approval")}

    site_doc.status = "Active"
    site_doc.enabled = 1
    site_doc.approved_on = site_doc.approved_on or now_datetime()
    site_doc.save(ignore_permissions=True)
    api_key, api_secret = _create_api_user(site_doc)
    return {"success": True, "credentials": {"api_key": api_key, "api_secret": api_secret}}


@frappe.whitelist(methods=["POST"])
def approve_site(site):
    frappe.only_for("System Manager")
    doc = frappe.get_doc("Push Relay Site", site)
    doc.status = "Active"
    doc.enabled = 1
    doc.approved_on = now_datetime()
    doc.save(ignore_permissions=True)
    # The client receives credentials only after it repeats the verified callback handshake.
    return {"success": True, "site": doc.site_name, "message": _("Relay site approved")}
