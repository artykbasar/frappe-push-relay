from __future__ import annotations

import frappe
from frappe import _


def check(site_doc, bucket: str = "push"):
    limit = int(site_doc.rate_limit_per_hour or 0)
    if limit <= 0:
        return
    key = f"push-relay:{bucket}:{site_doc.name}:{frappe.utils.now_datetime().strftime('%Y%m%d%H')}"
    current = frappe.cache.incr(key)
    if current == 1:
        frappe.cache.expire(key, 3700)
    if current > limit:
        frappe.throw(_("Push relay rate limit exceeded"), frappe.RateLimitExceededError)
