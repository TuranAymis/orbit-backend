#!/usr/bin/env bash
set -euo pipefail
umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backup_dir="${BACKUP_DIR:-./backups}"
shopt -s nullglob
backups=("$backup_dir"/orbit-*.dump "$backup_dir"/orbit-*.dump.gpg)
if [[ ${#backups[@]} -eq 0 ]]; then
  printf 'No backups found in %s\n' "$backup_dir" >&2
  exit 1
fi
newest="${backups[0]}"
for candidate in "${backups[@]:1}"; do
  if [[ "$candidate" -nt "$newest" ]]; then
    newest="$candidate"
  fi
done

container="orbit-restore-check-$$"
password="$(od -An -N24 -tx1 /dev/urandom | tr -d '[:space:]')"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker run -d --rm --name "$container" \
  -e POSTGRES_PASSWORD="$password" -e POSTGRES_DB=restore_check \
  -p 127.0.0.1::5432 postgres:16 >/dev/null

ready=0
for ((attempt = 0; attempt < 30; attempt++)); do
  if docker exec "$container" pg_isready -U postgres -d restore_check >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  printf 'Temporary PostgreSQL did not become ready\n' >&2
  exit 1
fi

port="$(docker port "$container" 5432/tcp)"
port="${port##*:}"
TARGET_DATABASE_URL="postgresql://postgres:${password}@127.0.0.1:${port}/restore_check" \
  FORCE=1 "$script_dir/db_restore.sh" "$newest"
printf 'Restore drill passed: %s\n' "${newest##*/}"
