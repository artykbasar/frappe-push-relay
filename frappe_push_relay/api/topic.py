import frappe

from frappe_push_relay.security import assert_request_site
from frappe_push_relay.services.rate_limit import check as rate_limit
from frappe_push_relay.validation import project_name as validate_project_name
from frappe_push_relay.validation import topic_name as validate_topic_name
from frappe_push_relay.validation import user_id as validate_user_id


def _topic_filters(site, project_name, topic_name):
    return {"relay_site": site.name, "project_name": project_name, "topic": topic_name}


def _validated(site_name, project_name, topic_name):
    site = assert_request_site(site_name)
    rate_limit(site, "topic")
    return site, validate_project_name(project_name), validate_topic_name(topic_name)


def _ensure_topic(site, project_name, topic_name):
    filters = _topic_filters(site, project_name, topic_name)
    if not frappe.db.exists("Push Topic", filters):
        try:
            frappe.get_doc({"doctype": "Push Topic", **filters}).insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
    return filters


@frappe.whitelist(methods=["POST"])
def add(topic_name, project_name, site_name, **kwargs):
    site, project_name, topic_name = _validated(site_name, project_name, topic_name)
    _ensure_topic(site, project_name, topic_name)
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def remove(topic_name, project_name, site_name, **kwargs):
    site, project_name, topic_name = _validated(site_name, project_name, topic_name)
    filters = _topic_filters(site, project_name, topic_name)
    for name in frappe.get_all("Push Topic Subscription", filters=filters, pluck="name"):
        frappe.delete_doc("Push Topic Subscription", name, ignore_permissions=True)
    name = frappe.db.exists("Push Topic", filters)
    if name:
        frappe.delete_doc("Push Topic", name, ignore_permissions=True)
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def subscribe(topic_name, user_id, project_name, site_name, **kwargs):
    site, project_name, topic_name = _validated(site_name, project_name, topic_name)
    user_id = validate_user_id(user_id)
    filters = _ensure_topic(site, project_name, topic_name)
    subscription = {**filters, "user_id": user_id}
    if not frappe.db.exists("Push Topic Subscription", subscription):
        try:
            frappe.get_doc({"doctype": "Push Topic Subscription", **subscription}).insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def unsubscribe(topic_name, user_id, project_name, site_name, **kwargs):
    site, project_name, topic_name = _validated(site_name, project_name, topic_name)
    user_id = validate_user_id(user_id)
    filters = {**_topic_filters(site, project_name, topic_name), "user_id": user_id}
    for name in frappe.get_all("Push Topic Subscription", filters=filters, pluck="name"):
        frappe.delete_doc("Push Topic Subscription", name, ignore_permissions=True)
    return {"success": True}
