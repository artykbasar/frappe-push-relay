import frappe
from frappe import _
from frappe.installer import update_site_config
from frappe.model.document import Document

from frappe_push_relay.config import service_account_dict, validate_relay_url


class PushRelaySettings(Document):
    def validate(self):
        if self.mode == "Local":
            required = [
                ("firebase_project_id", "Firebase Project ID"),
                ("firebase_api_key", "Firebase API Key"),
                ("firebase_messaging_sender_id", "Messaging Sender ID"),
                ("firebase_app_id", "Firebase App ID"),
                ("vapid_public_key", "VAPID Public Key"),
            ]
            missing = [label for field, label in required if not self.get(field)]
            if not self.get_password("firebase_service_account_json", raise_exception=False):
                missing.append("Firebase Service Account JSON")
            if missing:
                frappe.throw(_("Missing Firebase configuration: {0}").format(", ".join(missing)))

            service_account = service_account_dict(self)
            if service_account.get("project_id") != self.firebase_project_id:
                frappe.throw(_("Firebase Service Account project_id must match Firebase Project ID"))

        elif self.mode == "Remote":
            self.remote_relay_url = validate_relay_url(self.remote_relay_url)
            if not self.remote_relay_url:
                frappe.throw(_("Remote Relay URL is required in Remote mode"))

        if self.allow_other_sites_to_use_this_relay and self.mode != "Local":
            frappe.throw(_("Relay hosting can only be enabled in Local mode"))

    def on_update(self):
        self._sync_frappe_push_settings()

    def _sync_frappe_push_settings(self):
        current_url = frappe.conf.get("push_relay_server_url")
        desired_url = self._desired_relay_url()

        if desired_url:
            update_site_config("push_relay_server_url", desired_url, validate=False)
            frappe.conf.push_relay_server_url = desired_url
        else:
            update_site_config("push_relay_server_url", "None", validate=False)
            frappe.conf.pop("push_relay_server_url", None)

        core = frappe.get_single("Push Notification Settings")
        enabled = self.mode in {"Local", "Remote"}
        if self.mode != "Remote" or current_url != desired_url:
            core.api_key = None
            core.api_secret = None
        core.enable_push_notification_relay = 1 if enabled else 0
        core.save(ignore_permissions=True)

    def _desired_relay_url(self):
        if self.mode == "Remote":
            return self.remote_relay_url
        if self.mode == "Local":
            # When saved from Desk, get_url() includes the dev port from the request.
            return validate_relay_url(frappe.utils.get_url())
        return None
