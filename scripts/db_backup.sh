#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${DATABASE_URL:?DATABASE_URL is required}"
backup_dir="${BACKUP_DIR:-./backups}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
if [[ ! "$retention_days" =~ ^[0-9]+$ ]]; then
  printf 'BACKUP_RETENTION_DAYS must be a non-negative integer\n' >&2
  exit 1
fi

database_url="$DATABASE_URL"
if [[ "$database_url" == postgresql+psycopg://* ]]; then
  database_url="postgresql://${database_url#postgresql+psycopg://}"
fi
mkdir -p -- "$backup_dir"
chmod 700 "$backup_dir"
working_file="$(mktemp "$backup_dir/.orbit-backup.XXXXXXXX")"
encrypted_file=""
cleanup() {
  rm -f -- "$working_file"
  if [[ -n "$encrypted_file" ]]; then
    rm -f -- "$encrypted_file"
  fi
}
trap cleanup EXIT

pg_dump -Fc --dbname="$database_url" --file="$working_file"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
filename="orbit-${stamp}-$$.dump"
if [[ -n "${BACKUP_GPG_RECIPIENT:-}" ]]; then
  encrypted_file="$(mktemp "$backup_dir/.orbit-encrypted.XXXXXXXX")"
  if [[ "$BACKUP_GPG_RECIPIENT" == "symmetric" ]]; then
    : "${BACKUP_GPG_PASSPHRASE:?BACKUP_GPG_PASSPHRASE is required for symmetric encryption}"
    gpg --batch --quiet --yes --pinentry-mode loopback --passphrase-fd 3 \
      --symmetric --output "$encrypted_file" "$working_file" \
      3<<< "$BACKUP_GPG_PASSPHRASE"
  else
    gpg --batch --quiet --yes --trust-model always --encrypt \
      --recipient "$BACKUP_GPG_RECIPIENT" --output "$encrypted_file" "$working_file"
  fi
  rm -f -- "$working_file"
  working_file="$encrypted_file"
  encrypted_file=""
  filename="${filename}.gpg"
fi

chmod 600 "$working_file"
mv -- "$working_file" "$backup_dir/$filename"
working_file=""
find "$backup_dir" -maxdepth 1 -type f \
  \( -name 'orbit-*.dump' -o -name 'orbit-*.dump.gpg' \) \
  -mmin "+$((retention_days * 1440))" -delete
size="$(wc -c < "$backup_dir/$filename" | tr -d '[:space:]')"
printf '%s %s bytes\n' "$filename" "$size"
