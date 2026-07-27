#!/usr/bin/env bash
# ==============================================================================
# Database Backup Script for Kannans WhatsApp AI Agent (EC2 to Amazon S3)
# ==============================================================================
# This script reads database configurations from the application's .env file,
# creates a compressed backup (works for both SQLite and PostgreSQL), and
# uploads it to an S3 bucket.
#
# Prerequisite: Ensure the AWS CLI is installed and configured (`aws configure`).
#
# Schedule it in cron (run daily at 2:00 AM):
# 0 2 * * * /bin/bash /home/ubuntu/whatsapp/scripts/backup-to-s3.sh >> /var/log/db_backup.log 2>&1
# ==============================================================================

set -euo pipefail

# --- Configuration & Defaults ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
LOCAL_BACKUP_DIR="/var/backups/kannans"
RETENTION_DAYS=30

echo "=== Starting Database Backup: $(date) ==="

# 1. Load Environment Variables from .env
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    # Export vars from .env, ignoring comments and empty lines
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^\s*$' | xargs)
else
    echo "ERROR: .env file not found at $ENV_FILE!"
    exit 1
fi

# Ensure S3 Bucket variable is defined
if [ -z "${S3_BACKUP_BUCKET:-}" ]; then
    echo "ERROR: S3_BACKUP_BUCKET is not set in your environment or .env file."
    echo "Please add 'S3_BACKUP_BUCKET=your-bucket-name' to your .env file."
    exit 1
fi

# Ensure Database URL variable is defined
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set in .env file."
    exit 1
fi

# Make sure local backup directory exists
mkdir -p "$LOCAL_BACKUP_DIR"

# 2. Determine Database Type & Run Dump
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [[ "$DATABASE_URL" == sqlite* ]]; then
    echo "Detected SQLite database."
    
    # Extract path from URL (e.g. sqlite+aiosqlite:///./kannans.db -> ./kannans.db)
    # Remove sqlite+driver:/// prefix
    SQLITE_PATH=$(echo "$DATABASE_URL" | sed -E 's|^sqlite(\+[a-zA-Z0-9_]+)?:///||')
    
    # Resolve relative path if necessary
    if [[ ! "$SQLITE_PATH" = /* ]]; then
        SQLITE_PATH="$PROJECT_ROOT/$SQLITE_PATH"
    fi
    
    if [ ! -f "$SQLITE_PATH" ]; then
        echo "ERROR: SQLite database file not found at: $SQLITE_PATH"
        exit 1
    fi
    
    BACKUP_FILE="$LOCAL_BACKUP_DIR/kannans_sqlite_$TIMESTAMP.db.gz"
    echo "Backing up SQLite database from: $SQLITE_PATH"
    
    # Compress the SQLite database file
    gzip -c "$SQLITE_PATH" > "$BACKUP_FILE"
    
elif [[ "$DATABASE_URL" == postgres* ]]; then
    echo "Detected PostgreSQL database."
    
    # Clean up standard asyncpg drivers for pg_dump (e.g. postgresql+asyncpg:// -> postgresql://)
    PG_CONN_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//g' | sed 's/postgres+asyncpg:\/\//postgresql:\/\//g')
    
    BACKUP_FILE="$LOCAL_BACKUP_DIR/kannans_postgres_$TIMESTAMP.sql.gz"
    echo "Dumping PostgreSQL schema and data..."
    
    # Run pg_dump and pipe to gzip
    pg_dump "$PG_CONN_URL" | gzip > "$BACKUP_FILE"
    
else
    echo "ERROR: Unsupported database protocol in DATABASE_URL: $DATABASE_URL"
    exit 1
fi

echo "Local backup file created: $BACKUP_FILE ($(du -sh "$BACKUP_FILE" | cut -f1))"

# 3. Upload Backup to Amazon S3
S3_URI="s3://$S3_BACKUP_BUCKET/db-backups/$(basename "$BACKUP_FILE")"
echo "Uploading backup to Amazon S3: $S3_URI..."

if aws s3 cp "$BACKUP_FILE" "$S3_URI"; then
    echo "Upload succeeded!"
else
    echo "ERROR: AWS S3 upload failed! Please verify AWS CLI credentials and bucket permissions."
    exit 1
fi

# 4. Enforce Retention Policies (Clean up old backups)

# Local cleanup (delete files older than RETENTION_DAYS)
echo "Enforcing local retention policy (deleting local backups older than $RETENTION_DAYS days)..."
find "$LOCAL_BACKUP_DIR" -type f -name "kannans_*" -mtime +"$RETENTION_DAYS" -exec rm -f {} \; -print

# S3 cleanup (uses AWS CLI to list backups and deletes those older than RETENTION_DAYS)
echo "Enforcing S3 retention policy..."
# Get date threshold in seconds
THRESHOLD_DATE=$(date -d "$RETENTION_DAYS days ago" +%s)

# List all objects in the bucket path, format as: "Key LastModified"
aws s3api list-objects-v2 --bucket "$S3_BACKUP_BUCKET" --prefix "db-backups/" --query "Contents[?LastModified<=\`$(date -d "$RETENTION_DAYS days ago" --utc +%Y-%m-%dT%H:%M:%SZ)\`].[Key]" --output text | while read -r S3_KEY; do
    if [ -n "$S3_KEY" ] && [ "$S3_KEY" != "None" ]; then
        echo "Deleting old S3 backup: s3://$S3_BACKUP_BUCKET/$S3_KEY"
        aws s3 rm "s3://$S3_BACKUP_BUCKET/$S3_KEY"
    fi
done

echo "=== Backup Process Completed Successfully: $(date) ==="
