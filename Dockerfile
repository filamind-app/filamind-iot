# filamind-iot — Odoo 19.0 Community + every filamind addon, ready
# to pair with a filamind-iotbox.
#
# Build:
#   docker build -t filamind-iot:latest .
#
# Run (with bundled docker-compose.yml — recommended):
#   docker compose up -d
#
# Run standalone (BYO Postgres):
#   docker run --rm -p 8069:8069 -p 8072:8072 \
#       -e DB_HOST=mypg -e DB_USER=odoo -e DB_PASSWORD=odoo \
#       filamind-iot:latest

FROM odoo:19.0

USER root

# Drop the entire monorepo's addons/ directory into a path Odoo
# scans on startup. odoo:19.0 already has /mnt/extra-addons in
# its addons_path env-var.
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/filamind/

# Render a default odoo.conf only if the user hasn't mounted one
COPY --chown=odoo:odoo docker/odoo.conf /etc/odoo/odoo.conf.template

# Pre-install every filamind addon at first boot via the
# entrypoint shim
COPY docker/entrypoint.sh /usr/local/bin/filamind-entrypoint
RUN chmod +x /usr/local/bin/filamind-entrypoint

EXPOSE 8069 8072

USER odoo

ENTRYPOINT ["/usr/local/bin/filamind-entrypoint"]
CMD ["odoo"]
