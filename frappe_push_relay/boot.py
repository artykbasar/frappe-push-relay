import frappe


def boot_session(bootinfo):
    """Expose the configured push relay URL to Desk clients."""
    bootinfo.push_relay_server_url = frappe.conf.get("push_relay_server_url") or ""
