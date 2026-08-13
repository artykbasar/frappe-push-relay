app_name = "frappe_push_relay"
app_title = "Frappe Push Relay"
app_publisher = "Frappe Push Relay contributors"
app_description = "Self-hosted push notification relay for Frappe"
app_email = ""
app_license = "MIT"

required_apps = []

# We intentionally keep the scheduler light. Push delivery itself is queued.
scheduler_events = {
    "daily": [
        "frappe_push_relay.services.cleanup.prune_delivery_logs",
        "frappe_push_relay.services.cleanup.prune_disabled_devices",
    ]
}

before_uninstall = "frappe_push_relay.install.before_uninstall"
boot_session = "frappe_push_relay.boot.boot_session"

# Frappe's PushNotification client always calls the notification_relay.api.* contract.
# This app is installed as frappe_push_relay, so alias those HTTP method names to
# our implementation. This does not replace frappe.push_notification methods/classes.
override_whitelisted_methods = {
    "notification_relay.api.get_config": "frappe_push_relay.api.config.get_config",
    "notification_relay.api.auth.get_credential": "frappe_push_relay.api.auth.get_credential",
    "notification_relay.api.token.add": "frappe_push_relay.api.token.add",
    "notification_relay.api.token.remove": "frappe_push_relay.api.token.remove",
    "notification_relay.api.topic.add": "frappe_push_relay.api.topic.add",
    "notification_relay.api.topic.remove": "frappe_push_relay.api.topic.remove",
    "notification_relay.api.topic.subscribe": "frappe_push_relay.api.topic.subscribe",
    "notification_relay.api.topic.unsubscribe": "frappe_push_relay.api.topic.unsubscribe",
    "notification_relay.api.send_notification.user": "frappe_push_relay.api.send_notification.user",
    "notification_relay.api.send_notification.topic": "frappe_push_relay.api.send_notification.topic",
}
