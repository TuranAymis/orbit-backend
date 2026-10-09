# PostgreSQL backup and restore

Run these commands from the repository root. Install PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`) compatible with the server. Set `DATABASE_URL` in the shell or the scheduler's secret store; the scripts accept both `postgresql://` and SQLAlchemy's `postgresql+psycopg://` scheme. Do not put credentials in command history or commit them.

## Daily backups

`scripts/db_backup.sh` creates a timestamped PostgreSQL custom-format dump (`pg_dump -Fc`) in `BACKUP_DIR`, which defaults to `./backups`. This directory is gitignored. Files have mode `600`, and the directory has mode `700`. The script reports only the file name and byte size. A failed dump or encryption leaves no published backup.

Schedule a daily job with a secret-injecting scheduler. For example, this crontab entry calls a wrapper that exports `DATABASE_URL` from your secret store and then runs the script:

```cron
0 2 * * * cd /path/to/orbit-backend && /path/to/secret-wrapper ./scripts/db_backup.sh >> /var/log/orbit-backup.log 2>&1
```

The wrapper is environment-specific; do not place the URL directly in the crontab. Monitor the job's exit status and backup age. Keep daily backups for 14 days (`BACKUP_RETENTION_DAYS=14` by default). For longer history, copy one backup per week to separate storage and retain eight weekly copies there. The script prunes only its own `orbit-*.dump` and `orbit-*.dump.gpg` files in `BACKUP_DIR`; it does not manage the weekly archive. Also enable the managed database provider's snapshots and point-in-time recovery when offered. Provider snapshots complement, rather than replace, independently restorable dumps.

Set `BACKUP_GPG_RECIPIENT` to a GPG recipient ID for public-key encryption. For symmetric encryption, set `BACKUP_GPG_RECIPIENT=symmetric` and supply `BACKUP_GPG_PASSPHRASE` securely through the scheduler. The resulting file ends in `.gpg`. Store recipient private keys or the symmetric passphrase separately from the backups, and test access during drills. Restrict backup storage and off-site copy access to the operators who restore databases; encrypt off-site copies and audit access. Avoid syncing plaintext dumps to shared storage.

## Restore

1. Identify the backup and target. Treat restore as destructive: `--clean --if-exists` drops matching objects in the target before recreating them. Stop application writes to the target during recovery.
2. Set `DATABASE_URL` to the source database URL and `TARGET_DATABASE_URL` to a **different** destination. The restore script refuses an identical URL, or a missing source URL, unless `FORCE=1` is deliberately supplied. Set the target URL through a secret store or shell environment, never in the command line or this document.
3. Run `./scripts/db_restore.sh ./backups/orbit-YYYYMMDDTHHMMSSZ-PID.dump` (or a `.dump.gpg` file). For recipient-encrypted backups, make the GPG private key available. For symmetric backups, supply `BACKUP_GPG_PASSPHRASE` through the secret store. `pg_restore` uses `--clean --if-exists --no-owner --exit-on-error` and the script prints `users` and `groups` row counts after a successful restore.
4. Verify application-level data and connectivity before directing traffic to the restored database. Keep the source and backup until recovery is confirmed.

## Recovery runbook

1. Declare the incident, record its start time, and stop writes. Determine whether a provider point-in-time restore or a dump is the best recovery point.
2. Select the latest known-good backup. Confirm its timestamp, encryption key access, and an isolated target database. Restore there first when possible.
3. Run the restore and inspect the row counts. Check representative users, groups, memberships, and application startup. Reconcile any writes after the backup timestamp.
4. Switch application traffic only after validation, then monitor errors and record the recovered time and data gap.

With a daily dump, the expected **RPO is up to 24 hours**, plus any scheduling or off-site copy delay. Provider point-in-time recovery may reduce it. Set an operational **RTO target of four hours** for a typical database, but measure it in restore drills: database size, download time, and verification can extend it. Escalate if the actual restore exceeds the target.

## Quarterly restore drill

Run `./scripts/db_restore_check.sh` from the repository root with `BACKUP_DIR` pointing at the backup set when needed. It selects the newest script-created dump, starts a temporary `postgres:16` Docker container bound to localhost, restores the dump, prints row counts, and removes the container on exit. Docker must be installed and able to pull or use the image. The script uses `FORCE=1` only for its throwaway target.

- Confirm the scheduled job has recent successful runs and the chosen backup is readable.
- Confirm the required GPG key or passphrase is available to the drill operator.
- Run the drill and record backup timestamp, restore duration, and `users`/`groups` counts.
- Spot-check representative application data and compare counts with the source or monitoring history.
- Confirm the temporary container was removed, record the measured RPO/RTO, and fix any failed step before the next quarter.
