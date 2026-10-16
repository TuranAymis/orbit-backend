# Web push

The first delivery target is browser Web Push with VAPID. Mobile push can implement the `PushSender` interface later. Configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, and `VAPID_SUBJECT`. Delivery uses `pywebpush` (in `requirements.txt`); when the VAPID configuration is absent, delivery is only logged. Notification rows are stored regardless of push support; category preferences apply before creating them. Background dispatch catches delivery failures so event and group mutations can complete. Subscriptions are scoped to their owner and use HTTPS endpoints.

## Setup

1. `python scripts/generate_vapid_keys.py` prints a key pair. Copy the values into your secret store or the untracked `.env` (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT=mailto:...`). The private key must never be committed. Names only are listed in `.env.example`.
2. The web client reads the public key from `GET /notifications/push/config` when subscribing.
3. Subscriptions that the push service reports as gone (HTTP 404/410) are deleted automatically; any other delivery failure is logged and never blocks the main request.
