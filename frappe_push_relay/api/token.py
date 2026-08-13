import frappe
from frappe.utils import now_datetime

from frappe_push_relay.security import assert_request_site
from frappe_push_relay.services.rate_limit import check as rate_limit
from frappe_push_relay.validation import project_name as validate_project_name
from frappe_push_relay.validation import registration_hash, registration_id, user_id as validate_user_id


def _find_registration(relay_site, project_name, fcm_token):
    return frappe.db.exists("Push Device", {
        "relay_site": relay_site.name,
        "project_name": project_name,
        "token_hash": registration_hash(fcm_token),
    })


@frappe.whitelist(methods=["POST"])
def add(user_id, fcm_token, project_name, site_name, **kwargs):
    relay_site = assert_request_site(site_name)
    rate_limit(relay_site, "token")
    project_name = validate_project_name(project_name)
    user_id = validate_user_id(user_id)
    fcm_token = registration_id(fcm_token)
    name = _find_registration(relay_site, project_name, fcm_token)
    if name:
        doc = frappe.get_doc("Push Device", name)
        doc.user_id = user_id
        doc.token_hash = registration_hash(fcm_token)
        doc.enabled = 1
        doc.last_seen = now_datetime()
        doc.failure_count = 0
        doc.last_error_code = None
        doc.save(ignore_permissions=True)
    else:
        try:
            doc = frappe.get_doc({
                "doctype": "Push Device",
                "relay_site": relay_site.name,
                "project_name": project_name,
                "user_id": user_id,
                "fcm_token": fcm_token,
                "token_hash": registration_hash(fcm_token),
                "enabled": 1,
                "last_seen": now_datetime(),
            }).insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            name = _find_registration(relay_site, project_name, fcm_token)
            if not name:
                raise
            doc = frappe.get_doc("Push Device", name)
            doc.user_id = user_id
            doc.enabled = 1
            doc.last_seen = now_datetime()
            doc.failure_count = 0
            doc.last_error_code = None
            doc.save(ignore_permissions=True)
    relay_site.db_set("last_seen", now_datetime(), update_modified=False)
    return {"success": True, "message": "Token registered", "name": doc.name}


@frappe.whitelist(methods=["POST"])
def remove(user_id, fcm_token, project_name, site_name, **kwargs):
    relay_site = assert_request_site(site_name)
    rate_limit(relay_site, "token")
    project_name = validate_project_name(project_name)
    user_id = validate_user_id(user_id)
    fcm_token = registration_id(fcm_token)
    name = frappe.db.exists("Push Device", {
        "relay_site": relay_site.name,
        "project_name": project_name,
        "user_id": user_id,
        "token_hash": registration_hash(fcm_token),
    })
    if name:
        frappe.delete_doc("Push Device", name, ignore_permissions=True)
    return {"success": True, "message": "Token removed"}
