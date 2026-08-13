from __future__ import annotations

import hashlib
import json

import frappe

from frappe_push_relay.config import service_account_dict
from frappe_push_relay.providers.base import PushProvider, SendResult


def _firebase_app():
    import firebase_admin
    from firebase_admin import credentials

    info = service_account_dict()
    identity = ":".join(str(info.get(key) or "") for key in ("project_id", "client_email", "private_key_id"))
    fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    name = f"frappe-push-relay-{frappe.local.site}-{fingerprint}"
    try:
        return firebase_admin.get_app(name)
    except ValueError:
        cred = credentials.Certificate(info)
        return firebase_admin.initialize_app(cred, name=name)


class FirebaseProvider(PushProvider):
    def send_token(self, token: str, title: str, body: str, data: dict | None = None) -> SendResult:
        from firebase_admin import exceptions as fb_exceptions
        from firebase_admin import messaging

        clean_data = {str(k): _stringify(v) for k, v in (data or {}).items() if v is not None}
        message = messaging.Message(
            notification=messaging.Notification(title=title or "", body=body or ""),
            data=clean_data,
            token=token,
        )
        try:
            message_id = messaging.send(message, app=_firebase_app())
            return SendResult(success=True, provider_message_id=message_id)
        except messaging.UnregisteredError as exc:
            return SendResult(False, error_code="unregistered", error_message=str(exc), permanent_token_failure=True)
        except messaging.SenderIdMismatchError as exc:
            return SendResult(False, error_code="sender-id-mismatch", error_message=str(exc), permanent_token_failure=True)
        except fb_exceptions.FirebaseError as exc:
            code = getattr(exc, "code", None) or exc.__class__.__name__
            return SendResult(False, error_code=str(code), error_message=str(exc))
        except Exception as exc:  # provider boundary: log but do not leak secrets
            frappe.log_error(title="Frappe Push Relay Firebase error", message=frappe.get_traceback())
            return SendResult(False, error_code=exc.__class__.__name__, error_message=str(exc))


def _stringify(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value).lower() if isinstance(value, bool) else str(value)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
