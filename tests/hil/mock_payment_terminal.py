#!/usr/bin/env python3
"""mock_payment_terminal.py — pretend to be a Six TIM or Worldline
CTEP payment terminal on a virtual serial port (and optionally over
HTTPS for TIM Cloud / cless_evo).

Lets you exercise the filamind_pos_iot_six and filamind_pos_iot_worldline
data paths + the on-box vendor drivers without owning real terminals.

Usage:
    # Serial mode (default — for TIM Direct / CTEP)
    python3 mock_payment_terminal.py --vendor six \\
        --result approved --auth 012345 --brand Visa --last4 4242

    # Stdout: the slave pty path, e.g. /dev/pts/7
    # Configure as the terminal's serial device on the box.

    # HTTP mode (for TIM Cloud / cless_evo)
    python3 mock_payment_terminal.py --vendor worldline --http :9870 \\
        --result declined --message "Insufficient funds"

    # Stdout: "listening on http://0.0.0.0:9870"

The mock answers any "pay" frame with the configured response.
Both TIM and CTEP framings are tolerated — we just look for the
amount + return the canned response. This is enough to validate
the round trip; real protocol verification needs real hardware.
"""
import argparse
import http.server
import json
import os
import pty
import select
import socketserver
import sys
import time


def serial_mode(args):
    master_fd, slave_fd = pty.openpty()
    print(os.ttyname(slave_fd), flush=True)
    sys.stderr.write(f'[mock_{args.vendor}] serial mode, waiting for frames\n')
    while True:
        r, _, _ = select.select([master_fd], [], [], 1.0)
        if not r:
            continue
        try:
            chunk = os.read(master_fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        sys.stderr.write(f'[mock_{args.vendor}] received {len(chunk)} bytes: '
                         f'{chunk[:80]!r}\n')
        # Pretend to take 1.5s to process the card
        time.sleep(1.5)
        reply = build_reply_frame(args, chunk)
        os.write(master_fd, reply)
        sys.stderr.write(f'[mock_{args.vendor}] sent reply ({len(reply)} '
                         f'bytes)\n')


def build_reply_frame(args, request_chunk):
    """Build a vendor-specific reply frame. Real terminals encode
    the response in TIM (LRC-checksummed) or CTEP (length-prefixed
    ISO 8583); for now we emit a JSON envelope that the on-box
    driver can decode in its TODO-stubbed branches."""
    payload = {
        'status': args.result,            # approved | declined | error
        'authorization_code': args.auth,
        'card_brand': args.brand,
        'card_last4': args.last4,
        'emv_aid': args.emv_aid,
        'emv_tvr': args.emv_tvr,
        'emv_tsi': args.emv_tsi,
        'signature_required': args.signature,
        'message': args.message,
        'transaction_id': f'mock-{args.vendor}-{int(time.time() * 1000)}',
    }
    body = json.dumps(payload).encode('utf-8')
    # Vendor-prefix so the driver knows what it parsed.
    return b'FILAMIND_MOCK\n' + body + b'\n'


def http_mode(args):
    pid = args.vendor
    canned = {
        'status': args.result,
        'authorization_code': args.auth,
        'card_brand': args.brand,
        'card_last4': args.last4,
        'emv_aid': args.emv_aid,
        'emv_tvr': args.emv_tvr,
        'emv_tsi': args.emv_tsi,
        'signature_required': args.signature,
        'message': args.message,
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (stdlib name)
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length else b''
            sys.stderr.write(f'[mock_{pid} http] {self.path} '
                             f'received {len(body)} bytes\n')
            time.sleep(1.5)
            payload = dict(canned)
            payload['transaction_id'] = (
                f'mock-{pid}-{int(time.time() * 1000)}')
            data = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *a):
            sys.stderr.write(f'[mock_{pid} http] {fmt % a}\n')

    host, _, port = args.http.lstrip(':').rpartition(':')
    if not port:
        port = host
        host = '0.0.0.0'
    port = int(port)
    print(f'listening on http://{host or "0.0.0.0"}:{port}', flush=True)
    with socketserver.TCPServer((host or '0.0.0.0', port), Handler) as srv:
        srv.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vendor', choices=['six', 'worldline'],
                    required=True)
    ap.add_argument('--http', default=None,
                    help='Listen on HTTP instead of serial, e.g. :9870')
    ap.add_argument('--result', choices=['approved', 'declined', 'error'],
                    default='approved')
    ap.add_argument('--auth', default='012345')
    ap.add_argument('--brand', default='Visa')
    ap.add_argument('--last4', default='4242')
    ap.add_argument('--emv-aid', default='A0000000031010')
    ap.add_argument('--emv-tvr', default='8080040000')
    ap.add_argument('--emv-tsi', default='F800')
    ap.add_argument('--signature', action='store_true')
    ap.add_argument('--message', default='')
    args = ap.parse_args()

    if args.http:
        http_mode(args)
    else:
        serial_mode(args)


if __name__ == '__main__':
    main()
