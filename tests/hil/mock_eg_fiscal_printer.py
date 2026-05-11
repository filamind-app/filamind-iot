#!/usr/bin/env python3
"""mock_eg_fiscal_printer.py — pretend to be an Egyptian Tax Authority
hardware fiscal printer (Sunmi V2 / Aures Yuno) on a virtual serial
port.

Lets you exercise the filamind_l10n_eg_iot data path + the on-box
filamind_eg_fiscal_driver without owning real hardware.

Usage:
    python3 mock_eg_fiscal_printer.py --uuid-prefix MOCK-EG

The script prints the slave pty path on stdout, e.g. /dev/pts/7.
Configure that path as the printer's serial device on the box.

Implements the four ESC/POS command shapes the driver speaks:
    ESC i      begin fiscal section (acknowledged silently)
    ESC I      end fiscal section + sign (assigns next UUID + QR)
    ESC ? u    query last UUID
    ESC ? q    query last QR payload

Other bytes are accepted as receipt body (printed to stderr).
"""
import argparse
import os
import pty
import select
import sys
import time

ESC = 0x1b
GS  = 0x1d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--uuid-prefix', default='MOCK-EG')
    ap.add_argument('--qr-prefix', default='ETAQR-')
    args = ap.parse_args()

    master_fd, slave_fd = pty.openpty()
    print(os.ttyname(slave_fd), flush=True)
    sys.stderr.write('[mock_eg_fiscal] waiting for ESC commands\n')

    last_uuid = ''
    last_qr = ''
    counter = 0
    in_fiscal = False
    fiscal_buf = b''

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
        i = 0
        while i < len(chunk):
            b = chunk[i]
            if b == ESC and i + 1 < len(chunk):
                cmd = chunk[i + 1]
                if cmd == ord('i'):
                    in_fiscal = True
                    fiscal_buf = b''
                    sys.stderr.write('[mock_eg_fiscal] BEGIN fiscal\n')
                    i += 2
                    continue
                if cmd == ord('I'):
                    counter += 1
                    last_uuid = f'{args.uuid_prefix}-{counter:06d}'
                    last_qr = (f'{args.qr_prefix}'
                               f'{int(time.time())}-{counter}')
                    in_fiscal = False
                    sys.stderr.write(
                        f'[mock_eg_fiscal] END fiscal '
                        f'uuid={last_uuid} qr={last_qr}\n')
                    sys.stderr.write(
                        f'[mock_eg_fiscal] body was {len(fiscal_buf)} '
                        f'bytes: {fiscal_buf[:80]!r}\n')
                    i += 2
                    continue
                if cmd == ord('?') and i + 2 < len(chunk):
                    sub = chunk[i + 2]
                    if sub == ord('u'):
                        os.write(master_fd,
                                 (last_uuid + '\n').encode('ascii'))
                        sys.stderr.write(
                            f'[mock_eg_fiscal] query u → {last_uuid}\n')
                        i += 3
                        continue
                    if sub == ord('q'):
                        os.write(master_fd,
                                 (last_qr + '\n').encode('ascii'))
                        sys.stderr.write(
                            f'[mock_eg_fiscal] query q → {last_qr}\n')
                        i += 3
                        continue
                # Unknown ESC sequence — swallow 2 bytes
                i += 2
                continue
            if in_fiscal:
                fiscal_buf += bytes([b])
            i += 1


if __name__ == '__main__':
    main()
