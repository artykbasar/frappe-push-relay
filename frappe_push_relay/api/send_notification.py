import frappe
from frappe import _

from frappe_push_relay.security import assert_request_site
from frappe_push_relay.services.delivery import enqueue_topic, enqueue_user
from frappe_push_relay.services.rate_limit import check as rate_limit
from frappe_push_relay.validation import data_payload, project_name as validate_project_name
from frappe_push_relay.validation import topic_name as validate_topic_name
from frappe_push_relay.validation import user_id as validate_user_id


def _validate_message(title, body):
    title = str(title or "")[:250]
    body = str(body or "")
    if len(body) > 1000:
        frappe.throw(_("Notification body cannot exceed 1000 characters"))
    return title, body


@frappe.whitelist(methods=["POST"])
def user(user_id, title, body, project_name, site_name, data=None, **kwargs):
    site = assert_request_site(site_name)
    rate_limit(site, "send")
    project_name = validate_project_name(project_name)
    user_id = validate_user_id(user_id)
    data = data_payload(data)
    title, body = _validate_message(title, body)
    log = enqueue_user(site.name, project_name, user_id, title, body, data)
    return {"success": True, "message": "Notification queued", "delivery_log": log.name}


@frappe.whitelist(methods=["POST"])
def topic(topic_name, title, body, project_name, site_name, data=None, **kwargs):
    site = assert_request_site(site_name)
    rate_limit(site, "send")
    project_name = validate_project_name(project_name)
    topic_name = validate_topic_name(topic_name)
    data = data_payload(data)
    title, body = _validate_message(title, body)
    log = enqueue_topic(site.name, project_name, topic_name, title, body, data)
    return {"success": True, "message": "Notification queued", "delivery_log": log.name}
