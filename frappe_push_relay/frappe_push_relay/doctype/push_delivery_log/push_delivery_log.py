import frappe
from frappe.model.document import Document


class PushDeliveryLog(Document):
    pass


def on_doctype_update():
    frappe.db.add_index(
        "Push Delivery Log",
        ["relay_site", "project_name", "status", "creation"],
        "idx_push_delivery_status",
    )
