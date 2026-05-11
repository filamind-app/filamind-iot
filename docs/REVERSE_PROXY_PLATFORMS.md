# Reverse-proxy recipes for filamind-iot

`filamind-iot` exposes three transports the IoT Box can use to reach
your Odoo server, in this order of preference:

1. **WebSocket** (`/websocket`) — bi-directional, instant, low CPU on
   the box.
2. **Long-poll** (`/longpolling/poll`, `/iot/longpoll`) — single HTTP
   request that the server holds open for ~30 s.
3. **Short-poll** (`/iot/poll`) — boring HTTP GET that pulls pending
   commands every few seconds. Always works, never fast.

The box's `tools/transport.py` (filamind-iotbox patch 005) negotiates
down this list automatically. **Your job at the proxy layer is only
to make sure each transport reaches Odoo with its semantics intact** —
in particular, `/websocket` must complete a clean RFC 6455 handshake
(101 Switching Protocols, no `Connection: Keep-Alive`).

This document gives a working snippet for each common reverse proxy.
Pick the one that matches your hosting panel and apply it verbatim.

---

## nginx (vanilla, recommended)

```nginx
upstream odoo {
    server 127.0.0.1:8069;
}
upstream odoochat {
    server 127.0.0.1:8072;     # Odoo's gevent worker (websocket)
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl http2;
    server_name odoo.example.com;

    ssl_certificate     /etc/letsencrypt/live/odoo.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/odoo.example.com/privkey.pem;

    proxy_read_timeout    720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout    720s;
    proxy_buffering       off;

    proxy_set_header Host              $host;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP         $remote_addr;

    # WebSocket — must hit the gevent port, not the multi-worker one
    location /websocket {
        proxy_pass         http://odoochat;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_read_timeout 3600s;
    }

    # Everything else (incl. /longpolling/poll, /iot/poll, /iot/longpoll)
    location / {
        proxy_pass http://odoo;
    }

    gzip on;
    gzip_min_length 1100;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml application/json
               application/javascript application/xml application/xml+rss;
}
```

---

## Caddy (recommended fix for OpenLiteSpeed/CyberPanel)

```caddyfile
odoo.example.com {
    encode gzip

    # WebSocket → gevent
    @ws {
        path /websocket
        header Connection *Upgrade*
        header Upgrade    websocket
    }
    reverse_proxy @ws 127.0.0.1:8072

    # Everything else → main worker pool
    reverse_proxy 127.0.0.1:8069 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Real-IP         {remote}
        flush_interval -1                # disable buffering for long-poll
    }
}
```

Caddy auto-provisions Let's Encrypt and (unlike OpenLiteSpeed) emits a
clean `Connection: Upgrade` in its 101 response. **Use Caddy as a
sidecar** when your panel ships OpenLiteSpeed — see the OpenLiteSpeed
section for the layout.

---

## Apache 2.4 (mod_proxy + mod_proxy_wstunnel)

Enable the modules first:

```bash
a2enmod proxy proxy_http proxy_wstunnel headers rewrite
```

Then, in your VHost:

```apache
<VirtualHost *:443>
    ServerName odoo.example.com

    SSLEngine on
    SSLCertificateFile      /etc/letsencrypt/live/odoo.example.com/fullchain.pem
    SSLCertificateKeyFile   /etc/letsencrypt/live/odoo.example.com/privkey.pem

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"

    # WebSocket → gevent (must come BEFORE the catch-all)
    ProxyPass        /websocket  ws://127.0.0.1:8072/websocket
    ProxyPassReverse /websocket  ws://127.0.0.1:8072/websocket

    # Catch-all → main worker
    ProxyPass        /  http://127.0.0.1:8069/  retry=0 timeout=720
    ProxyPassReverse /  http://127.0.0.1:8069/
</VirtualHost>
```

`mod_proxy_wstunnel` is shipped with Apache 2.4 — no extra build needed.

---

## Traefik v2/v3

```yaml
http:
  routers:
    odoo-ws:
      rule: "Host(`odoo.example.com`) && Path(`/websocket`)"
      service: odoo-ws
      tls:
        certResolver: letsencrypt
    odoo:
      rule: "Host(`odoo.example.com`)"
      service: odoo
      tls:
        certResolver: letsencrypt

  services:
    odoo-ws:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8072"
    odoo:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8069"
```

Traefik handles `Upgrade` automatically — no extra middleware.

---

## HAProxy 2.x

```
frontend fe_https
    bind *:443 ssl crt /etc/haproxy/certs/odoo.pem
    option forwardfor
    http-request set-header X-Forwarded-Proto https

    acl is_websocket path_beg /websocket
    use_backend be_odoochat if is_websocket
    default_backend be_odoo

backend be_odoo
    timeout server 720s
    server odoo 127.0.0.1:8069 check

backend be_odoochat
    timeout server 3600s
    server odoochat 127.0.0.1:8072 check
```

HAProxy detects the `Upgrade` header at the layer-7 level and tunnels
the connection — no special directive needed.

---

## OpenLiteSpeed / CyberPanel — known broken, use Caddy sidecar

OpenLiteSpeed (and therefore CyberPanel, which is built on it) has a
WebSocket bug: it rewrites the upstream's RFC 6455 `101 Switching
Protocols` response to add `Connection: Keep-Alive` instead of
`Connection: Upgrade`. The browser/box then drops the connection.

**The fix is *not* to fight OpenLiteSpeed.** Run Caddy as a sidecar
on a different port, point CyberPanel's vhost at Caddy, and let
Caddy speak to Odoo:

```
[ browser/iot box ] ─── 443 ──► [ CyberPanel/OLS ] ─── 127.0.0.1:8443 ──► [ Caddy ] ─── 8069/8072 ──► [ Odoo ]
```

CyberPanel vhost (`vhConf.conf`):

```
context / {
    type proxy
    handler odoo_caddy
}

extProcessor odoo_caddy {
    type proxy
    address 127.0.0.1:8443
}
```

Caddy on `127.0.0.1:8443` then uses the standard Caddyfile from the
section above (drop the `tls` directive — TLS terminates at OLS).

---

## aaPanel (nginx mode)

aaPanel ships with the standard nginx, so the **vanilla nginx
recipe above works as-is**. Place the snippet in
`/www/server/panel/vhost/nginx/odoo.example.com.conf` and reload via
`systemctl reload nginx`.

If aaPanel is in **Apache mode**, use the Apache recipe instead.

---

## Plesk

Plesk uses nginx as a front-end to Apache by default, and exposes
"Additional nginx directives" in **Apache & nginx Settings**. Paste:

```nginx
location /websocket {
    proxy_pass         http://127.0.0.1:8072;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade    $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_read_timeout 3600s;
}

location / {
    proxy_pass http://127.0.0.1:8069;
}
```

into the field, save, and let Plesk regenerate the vhost.

---

## cPanel / WHM

cPanel runs Apache + EasyApache. Enable `mod_proxy_wstunnel`
via WHM → Software → EasyApache 4 → Apache Modules, then add
the Apache snippet (above) to the user's `userdata` include
file: `/etc/apache2/conf.d/userdata/std/2_4/<user>/<domain>/odoo.conf`.

Run `/scripts/ensure_vhost_includes --user=<user>` and
`apachectl graceful` to apply.

---

## IIS (Windows)

Install **URL Rewrite Module** + **Application Request Routing
(ARR)** + **WebSocket Protocol** features.

`web.config` for the site:

```xml
<configuration>
  <system.webServer>
    <webSocket enabled="true" />
    <rewrite>
      <rules>
        <rule name="ws" stopProcessing="true">
          <match url="^websocket(/.*)?$" />
          <action type="Rewrite" url="http://127.0.0.1:8072/websocket{R:1}" />
        </rule>
        <rule name="odoo" stopProcessing="true">
          <match url=".*" />
          <action type="Rewrite" url="http://127.0.0.1:8069/{R:0}" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

ARR's "Reverse Proxy" template auto-emits the `X-Forwarded-*`
headers — no extra work.

---

## Cloudflare in front (any origin)

Cloudflare Free **does** proxy WebSockets, but only if your origin
returns `Connection: Upgrade` cleanly. Once your origin is fixed
(per the recipes above), the IoT Box just talks to your hostname
and Cloudflare does the rest.

If Cloudflare is in **DNS-only / grey-cloud** mode, this whole
section is a no-op — traffic bypasses Cloudflare entirely.

---

## Bare systemd + nginx (no panel)

The cleanest setup. Drop the **vanilla nginx recipe** into
`/etc/nginx/sites-available/odoo`, symlink to `sites-enabled`,
`nginx -t && systemctl reload nginx`. That's it.

Pair with these two unit files for Odoo itself:

`/etc/systemd/system/odoo.service`:

```ini
[Unit]
Description=Odoo
After=network.target postgresql.service

[Service]
Type=simple
User=odoo
ExecStart=/opt/odoo/odoo-bin -c /etc/odoo/odoo.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`odoo.conf` must have `proxy_mode = True` and `gevent_port = 8072`
for WebSocket to work behind any of the proxies above.

---

## How to verify the proxy is correct

From any machine that can reach your Odoo URL:

```bash
# 1. WebSocket handshake — should return "101 Switching Protocols"
curl -i -N \
     -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
     -H "Sec-WebSocket-Version: 13" \
     https://odoo.example.com/websocket

# 2. Long-poll — should return JSON (or hang for ~30 s, then JSON)
curl -i https://odoo.example.com/longpolling/poll

# 3. Short-poll (filamind-iot endpoint) — should return JSON immediately
curl -i https://odoo.example.com/iot/poll
```

If `(1)` returns a 101 with `Connection: Upgrade` (NOT `Keep-Alive`),
the WebSocket layer is healthy and the IoT Box will use it. If only
`(2)` and `(3)` work, the box silently degrades to long-poll then
short-poll — slower but functional.

CI matrix tests these three transports against nginx, Caddy,
Apache, Traefik, and OpenLiteSpeed in Phase 11.
