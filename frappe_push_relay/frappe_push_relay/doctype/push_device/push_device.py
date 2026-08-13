import frappe
from frappe.model.document import Document

from frappe_push_relay.validation import registration_hash


class PushDevice(Document):
    def validate(self):
        self.token_hash = registration_hash(self.fcm_token)


def on_doctype_update():
    # Backfill hashes before adding the constraint. If an older installation
    # contains duplicate registrations, keep the most recently modified row.
    seen = set()
    rows = frappe.get_all(
        "Push Device",
        fields=["name", "relay_site", "project_name", "fcm_token"],
        order_by="modified desc",
    )
    for row in rows:
        token_hash = registration_hash(row.fcm_token)
        key = (row.relay_site, row.project_name, token_hash)
        if key in seen:
            frappe.delete_doc("Push Device", row.name, ignore_permissions=True, force=True)
            continue
        seen.add(key)
        frappe.db.set_value("Push Device", row.name, "token_hash", token_hash, update_modified=False)

    frappe.db.add_unique(
        "Push Device",
        ["relay_site", "project_name", "token_hash"],
        constraint_name="uniq_push_device_registration",
    )
    frappe.db.add_index(
        "Push Device",
        ["relay_site", "project_name", "user_id", "enabled"],
        "idx_push_device_delivery",
    )
