import frappe
from frappe import _

from frappe_push_relay.config import firebase_web_config, get_settings, get_site_url
from frappe_push_relay.providers.firebase import _firebase_app
from frappe_push_relay.security import require_system_manager


@frappe.whitelist()
def status():
    require_system_manager()
    settings = get_settings()
    return {
        "mode": settings.mode,
        "relay_host_enabled": bool(settings.allow_other_sites_to_use_this_relay),
        "relay_url": get_site_url() if settings.allow_other_sites_to_use_this_relay else None,
        "remote_relay_url": settings.remote_relay_url if settings.mode == "Remote" else None,
        "registered_sites": frappe.db.count("Push Relay Site", {"enabled": 1}),
        "devices": frappe.db.count("Push Device", {"enabled": 1}),
    }


@frappe.whitelist(methods=["POST"])
def test_firebase():
    require_system_manager()
    settings = get_settings()
    if settings.mode != "Local":
        frappe.throw(_("Firebase is only configured in Local mode"))
    from google.auth.transport.requests import Request

    app = _firebase_app()
    credential = app.credential.get_credential()
    credential.refresh(Request())
    return {"success": True, "project_id": app.project_id, "config": firebase_web_config(settings)}
