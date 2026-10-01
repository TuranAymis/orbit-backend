# Web push

The first delivery target is browser Web Push with VAPID. Mobile push can implement the `PushSender` interface later. Configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, and `VAPID_SUBJECT`. `pywebpush` is optional: when it or VAPID configuration is absent, delivery is logged. Notification rows are stored regardless of push support; category preferences apply before creating them. Background dispatch catches delivery failures so event and group mutations can complete. Subscriptions are scoped to their owner and use HTTPS endpoints.
