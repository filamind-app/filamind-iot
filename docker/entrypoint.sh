#!/bin/bash
# filamind-iot entrypoint — render odoo.conf from env, then exec odoo.
#
# On first boot of a fresh DB, also pre-installs filamind_iot_full
# so the user doesn't have to click "Install" 14 times in the
# Apps screen. Set FILAMIND_AUTO_INSTALL=0 to disable.
set -euo pipefail

CONF=/etc/odoo/odoo.conf
TEMPLATE=/etc/odoo/odoo.conf.template

# Render env vars into the template
if [[ -r "$TEMPLATE" && ! -e "$CONF" ]]; then
    envsubst < "$TEMPLATE" > "$CONF" 2>/dev/null \
        || cp "$TEMPLATE" "$CONF"
fi

# Wait for Postgres
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
for i in $(seq 1 30); do
    if (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) 2>/dev/null; then
        break
    fi
    echo "[filamind] waiting for postgres at ${DB_HOST}:${DB_PORT} ($i/30)..."
    sleep 1
done

# First-boot install (idempotent — Odoo no-ops if already installed)
DB_NAME="${DB_NAME:-filamind}"
AUTO_INSTALL="${FILAMIND_AUTO_INSTALL:-1}"
if [[ "$AUTO_INSTALL" == "1" ]]; then
    echo "[filamind] auto-installing filamind_iot_full into ${DB_NAME}"
    odoo -c "$CONF" \
        -d "$DB_NAME" \
        -i filamind_iot_full \
        --stop-after-init \
        --without-demo=True \
        || echo "[filamind] auto-install returned non-zero (probably already installed) — continuing"
fi

# Hand off to Odoo
exec "$@" -c "$CONF"
