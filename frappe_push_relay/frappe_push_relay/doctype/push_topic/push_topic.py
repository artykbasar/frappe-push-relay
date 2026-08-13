import frappe
from frappe.model.document import Document


class PushTopic(Document):
    pass


def on_doctype_update():
    frappe.db.add_unique(
        "Push Topic",
        ["relay_site", "project_name", "topic"],
        constraint_name="uniq_push_topic",
    )
