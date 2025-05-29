#!/bin/bash
set -e
echo "Running init_db.sh..."

DATABASE="${DB_NAME}"
USERNAME="${DB_USER}"

echo "Checking if database '$DATABASE' exists..."

# Kiểm tra lệnh này có lỗi không
if ! psql -U "$USERNAME" -lqt | cut -d \| -f 1 | grep -qw "$DATABASE"; then
  echo "Database '$DATABASE' does not exist. Creating it..."
  psql -U "postgres" -c "CREATE DATABASE $DATABASE OWNER $USERNAME;"
  echo "Database '$DATABASE' created."
else
  echo "Database '$DATABASE' already exists."
fi

echo "init_db.sh completed successfully"
