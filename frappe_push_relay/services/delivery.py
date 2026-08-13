from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from frappe_push_relay.providers import get_provider
from frappe_push_relay.validation import data_payload


def parse_data(data):
    return data_payload(data)


def create_log(relay_site, project_name, target_type, target):
    return frappe.get_doc({
        "doctype": "Push Delivery Log",
        "relay_site": relay_site,
        "project_name": project_name,
        "target_type": target_type,
        "target": target,
        "status": "Queued",
    }).insert(ignore_permissions=True)


def enqueue_user(relay_site, project_name, user_id, title, body, data=None):
    log = create_log(relay_site, project_name, "User", user_id)
    frappe.enqueue(
        "frappe_push_relay.services.delivery.deliver_user",
        queue="short",
        enqueue_after_commit=True,
        log_name=log.name,
        relay_site=relay_site,
        project_name=project_name,
        user_id=user_id,
        title=title,
        body=body,
        data=parse_data(data),
    )
    return log


def enqueue_topic(relay_site, project_name, topic_name, title, body, data=None):
    log = create_log(relay_site, project_name, "Topic", topic_name)
    frappe.enqueue(
        "frappe_push_relay.services.delivery.deliver_topic",
        queue="short",
        enqueue_after_commit=True,
        log_name=log.name,
        relay_site=relay_site,
        project_name=project_name,
        topic_name=topic_name,
        title=title,
        body=body,
        data=parse_data(data),
    )
    return log


def deliver_user(log_name, relay_site, project_name, user_id, title, body, data=None):
    tokens = frappe.get_all(
        "Push Device",
        filters={"relay_site": relay_site, "project_name": project_name, "user_id": user_id, "enabled": 1},
        fields=["name", "fcm_token"],
    )
    _deliver(log_name, tokens, title, body, data)


def deliver_topic(log_name, relay_site, project_name, topic_name, title, body, data=None):
    users = frappe.get_all(
        "Push Topic Subscription",
        filters={"relay_site": relay_site, "project_name": project_name, "topic": topic_name},
        pluck="user_id",
    )
    if not users:
        _finish_empty(log_name)
        return
    tokens = frappe.get_all(
        "Push Device",
        filters={"relay_site": relay_site, "project_name": project_name, "user_id": ["in", list(set(users))], "enabled": 1},
        fields=["name", "fcm_token"],
    )
    _deliver(log_name, tokens, title, body, data)


def _finish_empty(log_name):
    frappe.db.set_value("Push Delivery Log", log_name, {
        "status": "Completed",
        "recipient_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "completed_on": now_datetime(),
    })


def _deliver(log_name, tokens, title, body, data):
    provider = get_provider()
    frappe.db.set_value("Push Delivery Log", log_name, "status", "Sending")
    success = 0
    failure = 0
    last_error = None

    for token_row in tokens:
        result = provider.send_token(token_row.fcm_token, title, body, data or {})
        if result.success:
            success += 1
            frappe.db.set_value("Push Device", token_row.name, {"failure_count": 0, "last_error_code": None})
        else:
            failure += 1
            last_error = result.error_code
            current = frappe.db.get_value("Push Device", token_row.name, "failure_count") or 0
            values = {"failure_count": current + 1, "last_error_code": result.error_code}
            if result.permanent_token_failure:
                values["enabled"] = 0
            frappe.db.set_value("Push Device", token_row.name, values)

    if failure == 0:
        status = "Completed"
    elif success:
        status = "Partial Failure"
    else:
        status = "Failed"

    frappe.db.set_value("Push Delivery Log", log_name, {
        "status": status,
        "recipient_count": len(tokens),
        "success_count": success,
        "failure_count": failure,
        "error_code": last_error,
        "completed_on": now_datetime(),
    })
