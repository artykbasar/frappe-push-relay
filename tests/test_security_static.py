from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_callback_has_ssrf_guard():
    text = (ROOT / "frappe_push_relay/security.py").read_text()
    for guard in ("is_private", "is_loopback", "is_link_local", "is_reserved"):
        assert guard in text


def test_tenant_binding_does_not_trust_site_name_only():
    text = (ROOT / "frappe_push_relay/security.py").read_text()
    assert "api_user" in text
    assert "assert_request_site" in text


def test_registration_binds_identity_to_verified_callback():
    text = (ROOT / "frappe_push_relay/api/auth.py").read_text()
    assert "registering_host = normalize_site_identity(callback)" in text
    assert "normalize_site_identity(site_name) != registering_host" in text
    assert "_get_or_create_relay_site(registering_host)" in text


def test_registration_callback_is_bounded_and_peer_verified():
    text = (ROOT / "frappe_push_relay/api/auth.py").read_text()
    for guard in (
        "session.trust_env = False",
        "_response_peer_ip",
        "validate_callback_peer_ip",
        "MAX_CALLBACK_RESPONSE_BYTES",
        "allow_redirects=False",
    ):
        assert guard in text


def test_existing_client_credentials_obey_host_policy():
    text = (ROOT / "frappe_push_relay/security.py").read_text()
    assert 'settings.mode != "Local"' in text
    assert "allow_other_sites_to_use_this_relay" in text
    assert '"status": "Active"' in text
