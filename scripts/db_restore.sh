#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -ne 1 || ! -f "$1" ]]; then
  printf 'Usage: %s BACKUP_FILE\n' "$0" >&2
  exit 1
fi
: "${TARGET_DATABASE_URL:?TARGET_DATABASE_URL is required}"
target_url="$TARGET_DATABASE_URL"
if [[ "$target_url" == postgresql+psycopg://* ]]; then
  target_url="postgresql://${target_url#postgresql+psycopg://}"
fi
source_url="${DATABASE_URL:-}"
if [[ "$source_url" == postgresql+psycopg://* ]]; then
  source_url="postgresql://${source_url#postgresql+psycopg://}"
fi
# Identify a database by host:port/name so localhost and 127.0.0.1 count as the same server.
db_identity() {
  local rest="${1#*@}"
  rest="${rest%%\?*}"
  rest="${rest/#localhost/127.0.0.1}"
  rest="${rest/#\[::1\]/127.0.0.1}"
  if [[ "$rest" != *:*/* ]]; then
    rest="${rest/\//:5432/}"
  fi
  printf '%s' "$rest"
}
if [[ "${FORCE:-0}" != "1" ]]; then
  if [[ -z "$source_url" || "$(db_identity "$target_url")" == "$(db_identity "$source_url")" ]]; then
    printf 'Set DATABASE_URL to a different source database, or set FORCE=1 for an intentional restore.\n' >&2
    exit 1
  fi
fi

dump_file="$1"
decrypted_file=""
cleanup() {
  if [[ -n "$decrypted_file" ]]; then
    rm -f -- "$decrypted_file"
  fi
}
trap cleanup EXIT
if [[ "$dump_file" == *.gpg ]]; then
  decrypted_file="$(mktemp "${TMPDIR:-/tmp}/orbit-restore.XXXXXXXX")"
  if [[ -n "${BACKUP_GPG_PASSPHRASE:-}" ]]; then
    gpg --batch --quiet --pinentry-mode loopback --passphrase-fd 3 \
      --decrypt --output "$decrypted_file" "$dump_file" \
      3<<< "$BACKUP_GPG_PASSPHRASE"
  else
    gpg --batch --quiet --decrypt --output "$decrypted_file" "$dump_file"
  fi
  dump_file="$decrypted_file"
fi

pg_restore --clean --if-exists --no-owner --exit-on-error \
  --dbname="$target_url" "$dump_file"
psql -X -v ON_ERROR_STOP=1 -At --dbname="$target_url" \
  -c "SELECT 'users=' || (SELECT count(*) FROM users) || ' groups=' || (SELECT count(*) FROM groups);"
