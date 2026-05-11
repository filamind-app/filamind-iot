"""Tiny stand-in for an Odoo server. Implements the three transports
filamind-iot uses so we can exercise reverse-proxy configs without
having to bring up a real Odoo + Postgres stack in CI.

Bind ports:
  8069  — main HTTP (longpoll + shortpoll)
  8072  — gevent worker (websocket)

Endpoints:
  GET  /websocket          — 101 Switching Protocols (RFC 6455)
  GET  /longpolling/poll   — 200 application/json, holds 2s then replies
  GET  /iot/longpoll       — alias of the above
  GET  /iot/poll           — 200 application/json, immediate
  GET  /                   — 200 text/plain ("ok") for healthchecks
"""
import asyncio
import base64
import hashlib
import json
import time

WS_MAGIC = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def _ws_accept(key: str) -> str:
    sha = hashlib.sha1((key + WS_MAGIC).encode()).digest()
    return base64.b64encode(sha).decode()


async def _read_request(reader):
    """Parse a minimal HTTP request — returns (method, path, headers).

    Returns None on empty / malformed inputs (e.g. orchestrator
    health-check probes that just open a TCP socket and close it)."""
    try:
        line = await reader.readline()
    except Exception:
        return None
    if not line:
        return None
    parts = line.decode('latin-1').rstrip('\r\n').split(' ', 2)
    if len(parts) < 2:
        return None
    method, path = parts[0], parts[1]
    headers = {}
    while True:
        try:
            h = await reader.readline()
        except Exception:
            break
        if h in (b'\r\n', b''):
            break
        k, _, v = h.decode('latin-1').rstrip('\r\n').partition(':')
        headers[k.strip().lower()] = v.strip()
    return method, path, headers


async def _send_json(writer, body, status='200 OK'):
    data = json.dumps(body).encode()
    out = (
        f'HTTP/1.1 {status}\r\n'
        f'Content-Type: application/json\r\n'
        f'Content-Length: {len(data)}\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    ).encode() + data
    writer.write(out)
    await writer.drain()


async def _send_text(writer, body, status='200 OK', ctype='text/plain'):
    data = body.encode() if isinstance(body, str) else body
    out = (
        f'HTTP/1.1 {status}\r\n'
        f'Content-Type: {ctype}\r\n'
        f'Content-Length: {len(data)}\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    ).encode() + data
    writer.write(out)
    await writer.drain()


async def _handle_main(reader, writer):
    """Port 8069 — HTTP transports."""
    try:
        req = await _read_request(reader)
        if not req:
            return
        method, path, _h = req
        path = path.split('?', 1)[0]
        if path in ('/longpolling/poll', '/iot/longpoll'):
            await asyncio.sleep(2)
            await _send_json(writer, {
                'result': [{'channel': 'iot.bus', 'message': 'ok',
                             't': time.time()}]
            })
        elif path == '/iot/poll':
            await _send_json(writer, {
                'commands': [], 't': time.time()
            })
        elif path == '/':
            await _send_text(writer, 'ok')
        else:
            await _send_text(writer, 'not found', status='404 Not Found')
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _handle_ws(reader, writer):
    """Port 8072 — WebSocket handshake. Replies 101 with a clean
    Connection: Upgrade and immediately closes the data channel —
    we only care about whether the proxy preserves the 101 headers."""
    try:
        req = await _read_request(reader)
        if not req:
            return
        method, path, headers = req
        if path != '/websocket' or headers.get('upgrade', '').lower() \
                != 'websocket':
            await _send_text(writer, 'expected websocket',
                              status='400 Bad Request')
            return
        key = headers.get('sec-websocket-key', '')
        accept = _ws_accept(key)
        out = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n'
            '\r\n'
        ).encode()
        writer.write(out)
        await writer.drain()
        # Hold the socket open briefly so the proxy doesn't think the
        # upstream died mid-handshake.
        await asyncio.sleep(1)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    s8069 = await asyncio.start_server(_handle_main, '0.0.0.0', 8069)
    s8072 = await asyncio.start_server(_handle_ws, '0.0.0.0', 8072)
    print('backend listening: 8069 (http), 8072 (ws)', flush=True)
    async with s8069, s8072:
        await asyncio.gather(s8069.serve_forever(), s8072.serve_forever())


if __name__ == '__main__':
    asyncio.run(main())
