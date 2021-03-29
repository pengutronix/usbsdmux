#! /usr/bin/env python3

# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (C) 2017 Pengutronix, Chris Fiege <entwicklung@pengutronix.de>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from .usbsdmux import UsbSdMux
import argparse
import sys, errno
import json
import socket
import os

def list_mode():
    muxes = UsbSdMux.enumerate()

    header = {
        'path': 'Path',
        'manufacturer' : 'Manufacturer',
        'product' : 'Product',
        'version' : 'Version',
        'serial' : 'Serial'
    }

    for mux in [header] + muxes:
        print('{:10} | {:21} | {:17} | {:7} | {:12}'.format(
            mux['path'], mux['manufacturer'], mux['product'],
            mux['version'], mux['serial']
        ))

def direct_mode(sg, mode, validate_usb=True):
    ctl = UsbSdMux(sg, validate_usb)

    if mode.lower() == "off":
        ctl.mode_disconnect()
    elif mode.lower() == "dut" or mode.lower() == "client":
        ctl.mode_DUT()
    elif mode.lower() == "host":
        ctl.mode_host()

def client_mode(sg, mode, socket_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        sock.connect(socket_path)
    except FileNotFoundError:
        print("Socket path %s does not exist. Exiting." % socket_path, file=sys.stderr)
        exit(1)
    except socket.error as ex:
        print("Failed opening socket %s : %s. Exiting." % (socket_path, ex), file=sys.stderr)
        exit(1)
    payload = dict()
    payload["mode"] = mode
    payload["sg"] = sg
    sock.send(json.dumps(payload).encode())
    answer = json.loads(sock.recv(4096).decode())
    sock.close()
    if 'text' in answer:
        print(answer['text'])
    if not 'error' in answer or answer['error']:
        exit(1)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("sg", metavar="<SG>/list", help="/dev/sg* device to use. Or \"list\" to show available devices")
    parser.add_argument(
        "mode",
        help="mode to switch to",
        choices=["dut", "host", "off", "client"],
        type=str.lower,
        nargs='?')
    parser.add_argument(
        "-d",
        "--direct",
        help="Forces to run in direct mode.",
        action="store_true",
        default=False)
    parser.add_argument(
        "-c",
        "--client",
        help="Force to run in client mode with socket /tmp/sdmux.sock",
        action="store_true",
        default=False)
    parser.add_argument(
        "-f",
        "--force",
        help=argparse.SUPPRESS,
        action="store_true",
        default=False)
    parser.add_argument(
        "-s",
        "--socket",
        help="Overrides the default socket for client mode.",
        default="/tmp/sdmux.sock")

    args = parser.parse_args()

    if args.sg == 'list':
        list_mode()
        exit(0)

    if args.mode not in ("dut", "host", "off", "client"):
        print("Mode must be either dut, host, off or client. Exiting", file=sys.stderr)
        exit(1)

    if args.client is True and args.direct is True:
        print("Can not run in direct and client mode at the same time. Exiting.", file=sys.stderr)
        exit(1)

    if args.client is True:
        client_mode(args.sg, args.mode, args.socket)
    elif args.direct is True:
        direct_mode(args.sg, args.mode, not args.force)
    else:
        if os.getresuid()[0] == 0:
            direct_mode(args.sg, args.mode, not args.force)
        else:
            client_mode(args.sg, args.mode, args.socket)

if __name__ == "__main__":
    main()
