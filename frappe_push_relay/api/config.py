import frappe
from frappe import _

from frappe_push_relay.config import firebase_web_config, get_settings
from frappe_push_relay.validation import project_name as validate_project_name


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_config(project_name=None):
    """Return public Firebase web configuration.

    Firebase web config and the VAPID public key are public client bootstrap
    values. Service-account credentials are never returned.
    """
    # HRMS and Frappe Suite fetch this public bootstrap endpoint directly
    # from the relay origin. Limit cross-origin access to this endpoint only;
    # authenticated token/topic/send APIs remain governed by normal site CORS.
    frappe.local.allow_cors = "*"
    project_name = validate_project_name(project_name)

    settings = get_settings()
    if settings.mode != "Local":
        frappe.throw(_("This site is not configured as a local push relay"))
    frappe.response["config"] = firebase_web_config(settings)
    frappe.response["vapid_public_key"] = settings.vapid_public_key
    frappe.response["project_name"] = project_name
    return None
