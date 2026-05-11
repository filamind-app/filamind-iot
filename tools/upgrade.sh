#!/bin/bash
# filamind-iot upgrade helper.
#
# One-step deploy: download the v<X.Y.Z> release zip, back up the
# currently installed addons, replace them, run Odoo's `-u` to apply
# any DB schema migrations, and restart the Odoo container.
#
# Designed for the common deltafabs/dockerized setup:
#   * Odoo runs in a docker container named `odoo-web`
#   * addons are mounted from the host into /mnt/extra-addons
#   * Postgres runs in a sibling container `odoo-db`
#
# Customise the env vars at the top if your layout differs.
#
# Usage:
#   sudo ./tools/upgrade.sh 1.1.0
#   sudo VERSION=1.1.0 ADDONS_HOST=/path/to/custom_addons ./tools/upgrade.sh
#
# Hard-codes nothing destructive — runs with `set -e`, makes a
# timestamped backup of every filamind_* dir BEFORE replacing.
# Roll back: see the printed instructions at the end.

set -euo pipefail

# ── Config (override via env) ───────────────────────────────────────
VERSION="${1:-${VERSION:-}}"
ADDONS_HOST="${ADDONS_HOST:-/home/deltafabs.com/public_html/custom_addons}"
BACKUP_ROOT="${BACKUP_ROOT:-${ADDONS_HOST}/../filamind-upgrade-backups}"
ODOO_CONTAINER="${ODOO_CONTAINER:-odoo-web}"
DB_HOST="${DB_HOST:-odoo-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-}"          # if blank, autodetect
GH_REPO="${GH_REPO:-filamind-app/filamind-iot}"

ALL_ADDONS=(
    filamind_iot filamind_pos_iot filamind_stock_iot
    filamind_mrp_iot filamind_quality_iot filamind_kitchen_display
    filamind_self_order_iot filamind_event_iot filamind_l10n_eg_iot
    filamind_l10n_eu_iot_scale_cert filamind_pos_iot_six
    filamind_pos_iot_worldline filamind_pos_iot_adam_scale
    filamind_iot_full
)

log()   { printf '\033[1;34m▶\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m⚠\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

[[ -n "${VERSION}" ]] || fail "usage: $0 <version>  (e.g. $0 1.1.0)"
[[ -d "${ADDONS_HOST}" ]] || fail "addons dir not found: ${ADDONS_HOST}"
command -v docker >/dev/null || fail "docker not on PATH"
command -v curl   >/dev/null || fail "curl not on PATH"
command -v unzip  >/dev/null || fail "unzip not on PATH"
docker ps --filter "name=^${ODOO_CONTAINER}$" --format '{{.Names}}' \
    | grep -q "^${ODOO_CONTAINER}$" \
    || fail "container ${ODOO_CONTAINER} not running"

# ── Step 1: timestamped backup ──────────────────────────────────────
STAMP="v${VERSION}-$(date +%Y%m%d-%H%M%S)"
BACKUP="${BACKUP_ROOT}/${STAMP}"
mkdir -p "${BACKUP}"

log "Backup currently-installed filamind_* dirs -> ${BACKUP}"
backed_up=0
for d in "${ALL_ADDONS[@]}"; do
    if [[ -d "${ADDONS_HOST}/${d}" && ! -L "${ADDONS_HOST}/${d}" ]]; then
        cp -a "${ADDONS_HOST}/${d}" "${BACKUP}/"
        ok "  backed up ${d}"
        backed_up=$((backed_up + 1))
    fi
done
log "  ${backed_up} addons backed up"

# ── Step 2: download + verify zip ───────────────────────────────────
log "Download v${VERSION} addons zip + sha256"
ZIP_DIR="$(mktemp -d)"
trap 'rm -rf "${ZIP_DIR}"' EXIT
cd "${ZIP_DIR}"
curl -fsSLO "https://github.com/${GH_REPO}/releases/download/v${VERSION}/filamind-iot-v${VERSION}.zip"
curl -fsSLO "https://github.com/${GH_REPO}/releases/download/v${VERSION}/filamind-iot-v${VERSION}.zip.sha256"
sha256sum -c "filamind-iot-v${VERSION}.zip.sha256" \
    || fail "SHA-256 mismatch on downloaded zip"
ok "Downloaded + verified"

# ── Step 3: unzip + chown ───────────────────────────────────────────
log "Unzip into ${ADDONS_HOST}"
unzip -q -o "filamind-iot-v${VERSION}.zip" -d "${ADDONS_HOST}/"

# Match ownership of an existing addon (safer than root)
REF_OWNER=""
for ref in oca-queue muk_web_theme base_account_budget; do
    if [[ -d "${ADDONS_HOST}/${ref}" ]]; then
        REF_OWNER="$(stat -c '%U:%G' "${ADDONS_HOST}/${ref}")"
        break
    fi
done
if [[ -n "${REF_OWNER}" ]]; then
    # IMPORTANT: glob is filamind_* (with underscore). filamind* would
    # also match the unrelated 3D-printer `filamind/` directory.
    chown -R "${REF_OWNER}" "${ADDONS_HOST}"/filamind_*
    ok "  chown ${REF_OWNER}"
fi

# ── Step 4: detect DB if not explicitly set ─────────────────────────
if [[ -z "${DB_NAME}" ]]; then
    log "Auto-detect DB with filamind_iot installed"
    DB_NAME=$(docker exec "${ODOO_CONTAINER}" python3 -c "
import os, psycopg2
conn = psycopg2.connect(
    host=os.environ.get('PGHOST','${DB_HOST}'),
    port=int(os.environ.get('PGPORT','${DB_PORT}')),
    user=os.environ.get('PGUSER','${DB_USER}'),
    password=os.environ.get('PGPASSWORD','${DB_PASSWORD}'),
    dbname='postgres',
)
cur = conn.cursor()
cur.execute(\"SELECT datname FROM pg_database WHERE datistemplate = false\")
candidates = []
for (db,) in cur.fetchall():
    try:
        c2 = psycopg2.connect(host=os.environ.get('PGHOST','${DB_HOST}'),
            port=int(os.environ.get('PGPORT','${DB_PORT}')),
            user=os.environ.get('PGUSER','${DB_USER}'),
            password=os.environ.get('PGPASSWORD','${DB_PASSWORD}'),
            dbname=db)
        cu = c2.cursor()
        cu.execute(\"SELECT 1 FROM ir_module_module WHERE name='filamind_iot' AND state='installed'\")
        if cu.fetchone():
            candidates.append(db)
        c2.close()
    except Exception:
        pass
conn.close()
print(','.join(candidates))
" 2>/dev/null || true)
    [[ -n "${DB_NAME}" ]] || fail "Could not auto-detect a DB with filamind_iot installed. Set DB_NAME explicitly."
    log "  found: ${DB_NAME}"
fi

# ── Step 5: run Odoo -u against each detected DB ────────────────────
INSTALLED_LIST=""
for d in "${ALL_ADDONS[@]}"; do
    [[ -d "${ADDONS_HOST}/${d}" ]] && INSTALLED_LIST="${INSTALLED_LIST}${d},"
done
INSTALLED_LIST="${INSTALLED_LIST%,}"

IFS=',' read -ra DBS <<< "${DB_NAME}"
for db in "${DBS[@]}"; do
    log "Run Odoo upgrade on DB '${db}'"
    docker exec "${ODOO_CONTAINER}" odoo \
        -c /etc/odoo/odoo.conf \
        --db_host="${DB_HOST}" --db_port="${DB_PORT}" \
        --db_user="${DB_USER}" --db_password="${DB_PASSWORD}" \
        -d "${db}" \
        -u "${INSTALLED_LIST}" \
        --stop-after-init --no-http --workers=0 \
        2>&1 | grep -E '(ERROR|CRITICAL|Loading module|Modules loaded|Registry loaded)' \
        | tail -50
    ok "  ${db} upgraded"
done

# ── Step 6: restart container so workers pick up new code ───────────
log "Restart ${ODOO_CONTAINER}"
docker restart "${ODOO_CONTAINER}" >/dev/null
sleep 4
docker ps --filter "name=^${ODOO_CONTAINER}$" --format '{{.Names}} {{.Status}}'

# ── Done ────────────────────────────────────────────────────────────
echo
ok "Upgrade complete."
log "Backup: ${BACKUP}"
log "Roll back if needed:"
log "  rm -rf ${ADDONS_HOST}/filamind_*"
log "  cp -a ${BACKUP}/* ${ADDONS_HOST}/"
log "  docker restart ${ODOO_CONTAINER}"
