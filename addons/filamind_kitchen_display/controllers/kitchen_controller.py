"""Public KDS HTTP routes.

The tablet bookmarks `/filamind_kitchen/<id>?access_token=<tok>` and
gets a self-contained HTML page (with a tiny vanilla-JS poller until
the OWL frontend lands in v0.2.0).
"""
import json

from odoo import http
from odoo.http import request, Response


def _check_access(display_id, access_token):
    display = request.env['filamind.kitchen.display'].sudo().browse(
        int(display_id)).exists()
    if not display:
        return None
    if not access_token or display.access_token != access_token:
        return None
    return display


class FilamindKitchenController(http.Controller):

    @http.route('/filamind_kitchen/<int:display_id>',
                type='http', auth='public', methods=['GET'])
    def display_page(self, display_id, access_token=None, **kwargs):
        display = _check_access(display_id, access_token)
        if not display:
            return Response('forbidden', status=403)
        return Response(_render_minimal_page(display),
                         mimetype='text/html')

    @http.route('/filamind_kitchen/<int:display_id>/orders',
                type='http', auth='public', methods=['GET'])
    def display_orders_json(self, display_id, access_token=None, **kwargs):
        display = _check_access(display_id, access_token)
        if not display:
            return Response('forbidden', status=403)
        Order = request.env['filamind.kitchen.order'].sudo()
        rows = Order.search(
            [('display_id', '=', display.id)], order='create_date asc')
        out = {
            'display': {'id': display.id, 'name': display.name},
            'stages': [{'id': s.id, 'name': s.name, 'sequence': s.sequence,
                        'color': s.color, 'is_final': s.is_final}
                       for s in display.stage_ids.sorted('sequence')],
            'orders': [{
                'id': o.id,
                'pos_order': o.pos_order_id.name or '',
                'table': o.table_number,
                'stage_id': o.stage_id.id,
                'fired_date': o.fired_date and o.fired_date.isoformat(),
                'completion_seconds': o.completion_seconds,
                'customer_note': o.customer_note or '',
                'lines': [{'product': line.product_id.display_name,
                           'qty': line.qty, 'note': line.note or ''}
                          for line in o.line_ids],
            } for o in rows],
        }
        return Response(json.dumps(out), mimetype='application/json')

    @http.route('/filamind_kitchen/transition',
                type='http', auth='public', methods=['POST'], csrf=False)
    def transition_order(self, **post):
        try:
            payload = request.httprequest.get_json(silent=True) or post
            display_id = int(payload.get('display_id') or 0)
            order_id = int(payload.get('order_id') or 0)
            target_stage_id = int(payload.get('target_stage_id') or 0)
            access_token = payload.get('access_token')
            display = _check_access(display_id, access_token)
            if not display:
                return Response(json.dumps({'error': 'forbidden'}),
                                 status=403, mimetype='application/json')
            order = request.env['filamind.kitchen.order'].sudo().browse(
                order_id).exists()
            if not order or order.display_id != display:
                return Response(json.dumps({'error': 'not_found'}),
                                 status=404, mimetype='application/json')
            order.transition(target_stage_id)
            return Response(json.dumps({'status': 'ok'}),
                             mimetype='application/json')
        except Exception as exc:
            return Response(json.dumps({'error': str(exc)[:200]}),
                             status=500, mimetype='application/json')


def _render_minimal_page(display):
    """Tiny vanilla-JS page that polls /orders every 5 s. Replaced by
    a proper OWL component in filamind_kitchen_display v0.2.0."""
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{display.name}</title>
<link rel="stylesheet" href="/filamind_kitchen_display/static/src/css/kitchen.css"/>
</head><body>
<header><h1>{display.name}</h1>
<span id="updated">--:--:--</span></header>
<main id="board"><p>Loading…</p></main>
<script>
const TOKEN = new URLSearchParams(location.search).get("access_token");
const DID   = {display.id};
async function refresh() {{
  try {{
    const r = await fetch(`/filamind_kitchen/${{DID}}/orders?access_token=${{TOKEN}}`);
    if (!r.ok) {{ document.getElementById("board").innerHTML = "<p>access denied</p>"; return; }}
    const data = await r.json();
    document.getElementById("updated").textContent = new Date().toLocaleTimeString();
    const cols = data.stages.map(s => {{
      const orders = data.orders.filter(o => o.stage_id === s.id);
      const cards  = orders.map(o => `
        <article class="card stage-${{s.is_final ? "final" : "active"}}">
          <header><strong>${{o.pos_order}}</strong>${{o.table ? ` · T${{o.table}}` : ""}}</header>
          <ul>${{o.lines.map(l => `<li>${{l.qty}}× ${{l.product}}${{l.note ? ` <em>${{l.note}}</em>` : ""}}</li>`).join("")}}</ul>
          ${{o.customer_note ? `<p class="note">${{o.customer_note}}</p>` : ""}}
          <footer>${{data.stages.map(t => t.id !== s.id ? `<button onclick="trans(${{o.id}}, ${{t.id}})">→ ${{t.name}}</button>` : "").join("")}}</footer>
        </article>`).join("");
      return `<section class="col color-${{s.color}}"><h2>${{s.name}} (${{orders.length}})</h2>${{cards}}</section>`;
    }}).join("");
    document.getElementById("board").innerHTML = cols;
  }} catch(e) {{ console.warn(e); }}
}}
async function trans(orderId, stageId) {{
  await fetch("/filamind_kitchen/transition", {{
    method: "POST", headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{display_id: DID, order_id: orderId,
                          target_stage_id: stageId, access_token: TOKEN}}),
  }});
  refresh();
}}
refresh(); setInterval(refresh, 5000);
</script>
</body></html>'''
