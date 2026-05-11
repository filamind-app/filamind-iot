#!/usr/bin/env python3
"""mock_adam_scale.py — pretend to be an Adam Equipment AGN-protocol
scale on a virtual serial port.

Lets you exercise the filamind_pos_iot_adam_scale data path + the
on-box filamind_adam_driver without owning real hardware. The
filamind_adam_driver opens a serial.Serial; this mock provides the
other end of that serial connection via a Linux pty pair.

Usage:
    python3 mock_adam_scale.py --weight 1.234 --unit kg

The script prints the slave pty path on stdout, e.g.:
    /dev/pts/7
Configure that path as the scale's serial device on the box, then
the AGN driver's Z / T / P commands will be answered by this
process.

AGN protocol cheatsheet:
    Send:   Z\r            response: (none)
    Send:   T\r            response: (none)
    Send:   P\r            response: "  +1.234 kg\r\n"
"""
import argparse
import os
import pty
import select
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weight', type=float, default=1.234)
    ap.add_argument('--unit', default='kg', choices=['g', 'kg', 'lb', 'oz'])
    ap.add_argument('--zero-on-z', action='store_true',
                    help="pretend `Z` resets weight to 0")
    args = ap.parse_args()

    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)
    print(slave_path, flush=True)

    weight = args.weight
    unit = args.unit
    tare_offset = 0.0

    while True:
        r, _, _ = select.select([master_fd], [], [], 1.0)
        if not r:
            continue
        try:
            chunk = os.read(master_fd, 64)
        except OSError:
            break
        if not chunk:
            break
        cmd = chunk.decode('latin-1', errors='ignore').strip()
        sys.stderr.write(f'[mock_adam] received {cmd!r}\n')
        if cmd.upper().startswith('Z'):
            if args.zero_on_z:
                weight = 0.0
            sys.stderr.write('[mock_adam] zero acknowledged (no reply)\n')
        elif cmd.upper().startswith('T'):
            tare_offset = weight
            sys.stderr.write(f'[mock_adam] tare = {tare_offset}\n')
        elif cmd.upper().startswith('P'):
            value = weight - tare_offset
            sign = '+' if value >= 0 else '-'
            reply = f'  {sign}{abs(value):.3f} {unit}\r\n'.encode('ascii')
            os.write(master_fd, reply)
            sys.stderr.write(f'[mock_adam] sent {reply!r}\n')
        else:
            sys.stderr.write(f'[mock_adam] ignoring unknown {cmd!r}\n')


if __name__ == '__main__':
    main()
