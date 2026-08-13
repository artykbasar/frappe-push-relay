from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import frappe
from frappe import _


def require_system_manager():
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("System Manager permission required"), frappe.PermissionError)


def normalize_site_identity(value: str) -> str:
    """Normalize either a Frappe site hostname or a full site URL to hostname."""
    if not value:
        frappe.throw(_("Site name is required"))
    value = value.strip()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if not parsed.hostname:
        frappe.throw(_("Invalid site name"))
    return parsed.hostname.lower().rstrip(".")


def authenticated_relay_site():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)
    name = frappe.db.get_value("Push Relay Site", {"api_user": user, "enabled": 1, "status": "Active"}, "name")
    if not name:
        frappe.throw(_("This API credential is not registered as an active relay site"), frappe.PermissionError)

    relay_site = frappe.get_doc("Push Relay Site", name)
    settings = frappe.get_single("Push Relay Settings")
    if settings.mode != "Local":
        frappe.throw(_("This site is not operating as a local push relay"), frappe.PermissionError)

    current_host = normalize_site_identity(frappe.utils.get_url())
    client_host = normalize_site_identity(relay_site.site_name)
    if client_host != current_host and not settings.allow_other_sites_to_use_this_relay:
        frappe.throw(_("Relay hosting is disabled for other sites"), frappe.PermissionError)
    return relay_site


def assert_request_site(site_name: str):
    relay_site = authenticated_relay_site()
    if normalize_site_identity(relay_site.site_name) != normalize_site_identity(site_name):
        frappe.throw(_("The authenticated credential does not belong to this site"), frappe.PermissionError)
    return relay_site


def _is_non_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_callback_peer_ip(value: str, allow_localhost: bool = False) -> None:
    try:
        blocked = _is_non_public_ip(value)
    except ValueError:
        frappe.throw(_("Registration callback connected to an invalid address"))
    if blocked and not allow_localhost:
        frappe.throw(_("Registration callback connected to a non-public address"))


def validate_public_callback_url(url: str, allow_localhost: bool = False) -> str:
    parsed = urlparse(url)
    is_dev_localhost = bool(
        allow_localhost
        and parsed.hostname
        and (parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost"))
    )
    if (parsed.scheme != "https" and not (is_dev_localhost and parsed.scheme == "http")) or not parsed.hostname:
        frappe.throw(_("Registration callback must use HTTPS"))
    if parsed.username or parsed.password:
        frappe.throw(_("Credentials are not allowed in callback URLs"))
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        frappe.throw(_("Could not resolve registration callback host"))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ) and not is_dev_localhost:
            frappe.throw(_("Registration callback resolves to a non-public address"))
    return url
