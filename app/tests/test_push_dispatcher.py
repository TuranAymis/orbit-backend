from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services import push_dispatcher
from app.services.push_dispatcher import (
    GONE_STATUS_CODES,
    LoggingPushSender,
    NotificationDispatcher,
    WebPushSender,
    default_sender,
    is_gone,
)


class GoneError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"status {status_code}")
        self.response = SimpleNamespace(status_code=status_code)


def make_db(subscriptions):
    db = MagicMock()
    db.get.return_value = None  # no preference row -> notifications enabled
    db.scalars.return_value.all.return_value = subscriptions
    return db


def make_subscription():
    return SimpleNamespace(id=uuid4(), endpoint="https://push.example/x", p256dh="p", auth="a")


def dispatch(db, sender):
    NotificationDispatcher(sender).dispatch(
        db, user_ids=[uuid4()], category="events", title="Hi", message="There"
    )


def test_unconfigured_deployment_falls_back_to_logging(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VAPID_PRIVATE_KEY", None)
    monkeypatch.setattr("app.core.config.settings.VAPID_SUBJECT", None)
    assert isinstance(default_sender(), LoggingPushSender)


def test_configured_deployment_uses_web_push(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.VAPID_PRIVATE_KEY", "private")
    monkeypatch.setattr("app.core.config.settings.VAPID_SUBJECT", "mailto:ops@example.com")
    assert isinstance(default_sender(), WebPushSender)


def test_web_push_sender_passes_payload_claims_and_ttl():
    with patch("pywebpush.webpush") as webpush:
        sender = WebPushSender("private-key", "mailto:ops@example.com")
        subscription = make_subscription()
        sender.send(subscription, {"title": "t"})
    webpush.assert_called_once()
    kwargs = webpush.call_args.kwargs
    assert kwargs["subscription_info"] == {
        "endpoint": subscription.endpoint,
        "keys": {"p256dh": "p", "auth": "a"},
    }
    assert kwargs["vapid_private_key"] == "private-key"
    assert kwargs["vapid_claims"] == {"sub": "mailto:ops@example.com"}
    assert kwargs["ttl"] == push_dispatcher.PUSH_TTL_SECONDS
    assert '"title": "t"' in kwargs["data"]


def test_revoked_subscription_is_removed():
    subscription = make_subscription()
    db = make_db([subscription])
    sender = MagicMock()
    sender.send.side_effect = GoneError(410)
    dispatch(db, sender)
    db.delete.assert_called_once_with(subscription)


def test_other_failures_never_propagate_and_keep_the_subscription():
    subscription = make_subscription()
    db = make_db([subscription])
    sender = MagicMock()
    sender.send.side_effect = RuntimeError("push service down")
    dispatch(db, sender)  # must not raise
    db.delete.assert_not_called()
    assert db.add.called  # the in-app notification row was still created


def test_delete_failure_is_contained():
    db = make_db([make_subscription()])
    db.delete.side_effect = RuntimeError("db gone")
    sender = MagicMock()
    sender.send.side_effect = GoneError(404)
    dispatch(db, sender)  # must not raise
    db.rollback.assert_called()


def test_is_gone_recognises_expired_statuses_only():
    assert GONE_STATUS_CODES == {404, 410}
    assert is_gone(GoneError(404)) and is_gone(GoneError(410))
    assert not is_gone(GoneError(500))
    assert not is_gone(RuntimeError("no response"))
