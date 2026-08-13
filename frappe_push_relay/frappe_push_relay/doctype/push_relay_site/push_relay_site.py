from frappe.model.document import Document
from frappe_push_relay.security import normalize_site_identity


class PushRelaySite(Document):
    def validate(self):
        self.site_name = normalize_site_identity(self.site_name)
