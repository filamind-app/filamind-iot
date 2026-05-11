{
    'name': 'Filamind IoT Proxy — Admin',
    'version': '19.0.0.1.0',
    'category': 'Productivity/IoT',
    'summary': 'Operator UI for filamind-iot-proxy (REST client + admin views)',
    'description': """
Filamind IoT Proxy Admin
========================
Thin Odoo addon that lets an operator manage a self-hosted
filamind-iot-proxy (https://github.com/filamind-app/filamind-iot-proxy)
without leaving the Odoo backend.

What it does
------------
* Stores proxy URL + bearer token in a single config record.
* Mirrors the proxy's tenants, boxes, and audit log into local
  read-only models, refreshable on demand.
* Buttons to create/edit/delete tenants, unpair boxes, and finalize
  pairing codes — all delegated to the proxy's REST API.

What it does NOT do
-------------------
* Hold any pairing or cert state locally — the proxy remains the source
  of truth. Local rows are caches, dropped on every refresh.
* Replace ``filamind_iot`` (the direct customer-side IoT addon).
  Both can coexist; this one only manages the proxy.
    """,
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot-proxy',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'views/proxy_config_views.xml',
        'views/proxy_tenant_views.xml',
        'views/proxy_box_views.xml',
        'views/proxy_audit_views.xml',
        'wizard/tenant_create_wizard_views.xml',
        'wizard/finalize_pairing_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
