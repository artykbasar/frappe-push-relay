from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime


def prune_delivery_logs():
    settings = frappe.get_single("Push Relay Settings")
    days = int(settings.delivery_log_retention_days or 30)
    cutoff = add_days(now_datetime(), -days)
    frappe.db.delete("Push Delivery Log", {"creation": ["<", cutoff]})


def prune_disabled_devices():
    settings = frappe.get_single("Push Relay Settings")
    days = int(settings.disabled_device_retention_days or 30)
    cutoff = add_days(now_datetime(), -days)
    frappe.db.delete("Push Device", {"enabled": 0, "modified": ["<", cutoff]})
