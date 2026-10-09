# Production security checklist

- Set `ENVIRONMENT=production`, `DEBUG=false`, a unique `JWT_SECRET_KEY` of at least 32 characters, explicit `BACKEND_CORS_ORIGINS` (use HTTPS origins), and a non-console `EMAIL_SENDER_MODE` with its delivery settings.
- Startup rejects the default or short JWT key, debug mode, empty or wildcard CORS origins, HTTP localhost/127.0.0.1 origins, and console email delivery in production. HTTP responses receive security headers; HSTS is sent only in production.
- Failed login attempts are limited per email to 10 in 15 minutes by default. Registration, verification, and resend requests retain their existing limits. Tune `AUTH_LOGIN_RATE_LIMIT_WINDOW_MINUTES` and `AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS` if needed.
- Rotate secrets through the deployment secret manager, terminate HTTPS at the proxy, and audit dependencies on a regular schedule.
