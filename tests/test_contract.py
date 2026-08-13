"""Static contract tests that do not require a running Frappe site."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compatibility_namespace_exists():
    required = [
        "notification_relay/api/auth.py",
        "notification_relay/api/token.py",
        "notification_relay/api/topic.py",
        "notification_relay/api/send_notification.py",
    ]
    for path in required:
        assert (ROOT / path).exists(), path


def test_frappe_expected_method_names_are_exported():
    assert "get_credential" in (ROOT / "notification_relay/api/auth.py").read_text()
    assert "add, remove" in (ROOT / "notification_relay/api/token.py").read_text()
    topic = (ROOT / "notification_relay/api/topic.py").read_text()
    for name in ("add", "remove", "subscribe", "unsubscribe"):
        assert name in topic
    send = (ROOT / "notification_relay/api/send_notification.py").read_text()
    assert "topic" in send and "user" in send


def test_desk_boot_exposes_push_relay_url():
    hooks = (ROOT / "frappe_push_relay/hooks.py").read_text()
    boot = (ROOT / "frappe_push_relay/boot.py").read_text()
    assert "boot_session" in hooks
    assert "push_relay_server_url" in boot


def test_public_config_is_cross_origin_bootstrap_only():
    config_api = (ROOT / "frappe_push_relay/api/config.py").read_text()
    assert 'methods=["GET"]' in config_api
    assert 'frappe.local.allow_cors = "*"' in config_api

    token_api = (ROOT / "frappe_push_relay/api/token.py").read_text()
    send_api = (ROOT / "frappe_push_relay/api/send_notification.py").read_text()
    assert "allow_cors" not in token_api
    assert "allow_cors" not in send_api


def test_storage_constraints_and_no_redundant_topic_enabled_field():
    device = (ROOT / "frappe_push_relay/frappe_push_relay/doctype/push_device/push_device.py").read_text()
    topic = (ROOT / "frappe_push_relay/frappe_push_relay/doctype/push_topic/push_topic.py").read_text()
    subscription = (
        ROOT / "frappe_push_relay/frappe_push_relay/doctype/push_topic_subscription/push_topic_subscription.py"
    ).read_text()
    topic_json = (ROOT / "frappe_push_relay/frappe_push_relay/doctype/push_topic/push_topic.json").read_text()

    assert "uniq_push_device_registration" in device
    assert "uniq_push_topic" in topic
    assert "uniq_push_topic_subscription" in subscription
    assert '"fieldname":"enabled"' not in topic_json


def test_install_lifecycle_does_not_leave_core_relay_configuration():
    hooks = (ROOT / "frappe_push_relay/hooks.py").read_text()
    install = (ROOT / "frappe_push_relay/install.py").read_text()
    settings_json = (
        ROOT / "frappe_push_relay/frappe_push_relay/doctype/push_relay_settings/push_relay_settings.json"
    ).read_text()
    assert "before_uninstall" in hooks
    assert 'update_site_config("push_relay_server_url", "None"' in install
    assert '"default":"Disabled"' in settings_json
    assert "Push Relay Client" not in hooks + install
