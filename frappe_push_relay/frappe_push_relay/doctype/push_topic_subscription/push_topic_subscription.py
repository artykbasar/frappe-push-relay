import frappe
from frappe.model.document import Document


class PushTopicSubscription(Document):
    pass


def on_doctype_update():
    frappe.db.add_unique(
        "Push Topic Subscription",
        ["relay_site", "project_name", "topic", "user_id"],
        constraint_name="uniq_push_topic_subscription",
    )
    frappe.db.add_index(
        "Push Topic Subscription",
        ["relay_site", "project_name", "topic"],
        "idx_push_topic_members",
    )
