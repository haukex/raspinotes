#!/usr/bin/python3
# pylint: disable=missing-function-docstring
"""Serial-to-Bluetooth Bridge.

See
<https://github.com/haukex/raspinotes/blob/main/bt-serial/BluetoothSerial.md>
for details.

Copyright (c) 2025 Hauke Dämpfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <https://www.igb-berlin.de/>

This project is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This project is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this project. If not, see <https://www.gnu.org/licenses/>.
"""
from contextlib import contextmanager
from textwrap import dedent
from typing import Any
from uuid import UUID
import subprocess
import argparse
import os.path
import select
import socket
import time
import io
import serial
import bluetooth  # type: ignore[import-untyped]
import inotify.adapters  # type: ignore[import-untyped]

# spell: ignore RFCOMM dsrdtr rtscts xonxoff baudrate bytesize
# spell: ignore FIVEBITS SIXBITS SEVENBITS EIGHTBITS stopbits inotify
# spell: ignore bluetoothctl btmgmt hciconfig pairable piscan sdptool


def main() -> None:
    parser = argparse.ArgumentParser(
        'bt_serial_bridge', description='Serial-to-Bluetooth Bridge')
    parser.add_argument('-r', '--baud', help="baud rate (default: 4800)",
                        type=int, default=4800)
    parser.add_argument('-b', '--bits', help="bits per byte (default: 8)",
                        choices=['5', '6', '7', '8'], default='8')
    parser.add_argument('-p', '--parity', help="parity (default: none)",
                        choices=['none', 'even', 'odd', 'mark', 'space'],
                        default='none')
    parser.add_argument('-s', '--stop-bits', help="stop bits (default: 1)",
                        choices=['1', '1.5', '2'], default='1')
    parser.add_argument('-f', '--flow-control',
                        help="flow control (default: none)",
                        choices=['none', 'xonxoff', 'rtscts', 'dsrdtr'],
                        default='none')
    parser.add_argument('-u', '--bt-uuid', help="Bluetooth UUID", type=UUID,
                        default='94f39d29-7d6d-437d-973b-fba39e49d4ee')
    parser.add_argument('-i', '--init-bt', help="Initialize Bluetooth",
                        action='store_true')
    parser.add_argument('-d', '--debug', help="Enable debugging output",
                        action='store_true')
    parser.add_argument('port')
    args = parser.parse_args()

    # Build arguments for Serial constructor
    ser_args: dict[str, int | str | float] = {
        "timeout": 0, "port": args.port, "baudrate": args.baud}
    match args.bits:
        case '5': ser_args['bytesize'] = serial.FIVEBITS
        case '6': ser_args['bytesize'] = serial.SIXBITS
        case '7': ser_args['bytesize'] = serial.SEVENBITS
        case _: ser_args['bytesize'] = serial.EIGHTBITS
    match args.parity:
        case 'even': ser_args['parity'] = serial.PARITY_EVEN
        case 'odd': ser_args['parity'] = serial.PARITY_ODD
        case 'mark': ser_args['parity'] = serial.PARITY_MARK
        case 'space': ser_args['parity'] = serial.PARITY_SPACE
        case _: ser_args['parity'] = serial.PARITY_NONE
    match args.stop_bits:
        case '1.5': ser_args['stopbits'] = serial.STOPBITS_ONE_POINT_FIVE
        case '2': ser_args['stopbits'] = serial.STOPBITS_TWO
        case _: ser_args['stopbits'] = serial.STOPBITS_ONE
    # In theory it's possible to have multiple kinds of flow control enabled
    # at the same time, but really unlikely.
    match args.flow_control:
        case 'xonxoff': ser_args['xonxoff'] = True
        case 'rtscts': ser_args['rtscts'] = True
        case 'dsrdtr': ser_args['dsrdtr'] = True

    if args.init_bt:
        init_bt(debug=args.debug)
    try:
        main_loop(
            ser_args=ser_args, bt_uuid=str(args.bt_uuid), debug=args.debug)
    except KeyboardInterrupt:
        if args.debug:
            print("Caught KeyboardInterrupt")

    parser.exit(0)


def init_bt(*, debug: bool):
    def cmd(args: list[str], *, stdin: str | None = None):
        if debug:
            print('+ '+' '.join(args)+('' if stdin is None else ' <<EOF'))
            if stdin is not None:
                print(stdin)
                print('EOF')
        subprocess.run(
            args, check=True,
            input=None if stdin is None else stdin.encode('UTF-8'))
    # NOTE some of these commands may duplicate settings and not every command
    # may be necessary, but since it doesn't seem to hurt it's fine for now.
    cmd(['/usr/bin/sdptool', 'add', 'SP'])
    cmd(['/usr/bin/hciconfig', 'hci0', 'piscan'])
    cmd(['/usr/bin/bluetoothctl'], stdin=dedent("""\
        power on
        discoverable on
        agent NoInputNoOutput
        default-agent
        agent off
        pairable on
        """))
    # 0x03 is NoInputNoOutput as per:
    # https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/mgmt.rst
    # stdin='' appears to be required due to a bug in btmgmt's STDIN handling?
    cmd(['/usr/bin/btmgmt', 'io-cap', '3'], stdin='')


MAX_INTERVAL_NS: int = 1000000000


def main_loop(*, ser_args: dict[str, Any], bt_uuid: str, debug: bool):
    notify = inotify.adapters.Inotify()
    notify.add_watch(os.path.dirname(ser_args['port']))
    last_check_ns: int = time.monotonic_ns() - MAX_INTERVAL_NS - 1
    while True:
        now_ns = time.monotonic_ns()
        if (sleep_ns := MAX_INTERVAL_NS - (now_ns - last_check_ns)) > 0:
            if debug:
                print(f"Rate limiting sleeping {sleep_ns/1e9:.6f}s")
            time.sleep(sleep_ns/1e9)
        last_check_ns = now_ns
        try:
            ser = serial.Serial(**ser_args)  # type: ignore[arg-type]
        except OSError as ex:
            if debug:
                print(f"Ignoring {ex!r}")
            # wait for an inotify event, which may be the port appearing
            if not os.path.exists(ser_args['port']):
                next(notify.event_gen(yield_nones=False))
        else:
            try:
                with ser, bluetooth_ctx(uuid=bt_uuid, debug=debug) as bt:
                    bridge_ports(ser=ser, bt=bt, debug=debug)
            except OSError as ex:  # from bluetooth_ctx
                if debug:
                    print(f"Ignoring {ex!r}")


@contextmanager
def bluetooth_ctx(*, uuid: str, debug: bool):
    # https://github.com/pybluez/pybluez/blob/master/examples/simple/rfcomm-client.py
    server_sock: socket.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # pyright: ignore [reportAssignmentType]  # noqa: E501  # pylint: disable=line-too-long
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    bluetooth.advertise_service(
        server_sock, "SerialBridge", service_id=uuid,
        service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
        profiles=[bluetooth.SERIAL_PORT_PROFILE],
        description="Serial-to-Bluetooth Bridge")

    if debug:
        print(
            'Waiting for RFCOMM connection on port'
            f"{server_sock.getsockname()}...")
    bt_sock, client_info = server_sock.accept()
    print(f"Accepted connection from {client_info}")

    try:
        yield bt_sock
    finally:
        bt_sock.close()
        bluetooth.stop_advertising(server_sock)
        server_sock.close()


def bridge_ports(*, ser: serial.Serial, bt: socket.socket, debug: bool):
    keep_running = True
    while keep_running:
        try:
            readable, _, _ = select.select((ser, bt), [], [], 0.1)
            for source in readable:
                if source is bt:
                    data = bt.recv(io.DEFAULT_BUFFER_SIZE)
                    if debug:
                        print(f"BT -> Serial: {data!r}")
                    if data:
                        ser.write(data)
                    else:
                        print('Stopping b/c of empty Bluetooth data')
                        keep_running = False
                        break
                elif source is ser:
                    data = ser.read(ser.in_waiting)
                    if debug:
                        print(f"Serial -> BT: {data!r}")
                    if data:
                        bt.send(data)
                    elif not ser.is_open:
                        print('Stopping b/c of Serial disconnect')
                        keep_running = False
                        break
        except OSError as ex:
            # bluetooth.BluetoothError isa IOError == OSError
            # and SerialException isa IOError == OSError
            print(f"Stopping due to {ex!r}")
            keep_running = False


if __name__ == '__main__':
    main()
