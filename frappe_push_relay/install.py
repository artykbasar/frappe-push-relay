import frappe
from frappe.installer import update_site_config


def before_uninstall():
    """Remove integration state that lives outside this app's DocTypes."""
    update_site_config("push_relay_server_url", "None", validate=False)
    if hasattr(frappe.local, "conf"):
        frappe.conf.pop("push_relay_server_url", None)

    if frappe.db.exists("DocType", "Push Notification Settings"):
        core = frappe.get_single("Push Notification Settings")
        core.enable_push_notification_relay = 0
        core.api_key = None
        core.api_secret = None
        core.save(ignore_permissions=True)

    api_users = set(
        frappe.get_all("Push Relay Site", filters={"api_user": ["is", "set"]}, pluck="api_user")
    )
    for site in frappe.get_all("Push Relay Site", filters={"api_user": ["is", "set"]}, pluck="name"):
        frappe.db.set_value("Push Relay Site", site, "api_user", None, update_modified=False)

    for user in api_users:
        if user and user not in {"Administrator", "Guest"} and frappe.db.exists("User", user):
            frappe.delete_doc("User", user, ignore_permissions=True, force=True)
