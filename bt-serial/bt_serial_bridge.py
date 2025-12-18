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
import threading
import argparse
import os.path
import select
import socket
import queue
import time
import enum
import io
import serial            # https://github.com/pyserial/pyserial
import bluetooth         # https://github.com/pybluez/pybluez
import inotify.adapters  # https://github.com/dsoprea/PyInotify

# spell: ignore RFCOMM dsrdtr rtscts xonxoff baudrate bytesize actpwr
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
    # UUID should be random, *except* xxxxxxxx-0000-1000-8000-00805f9b34fb
    parser.add_argument('-u', '--bt-uuid', help="Bluetooth UUID", type=UUID,
                        required=True)
    parser.add_argument('-i', '--init-bt', help="Initialize Bluetooth",
                        action='store_true')
    parser.add_argument('-d', '--debug', help="Enable debugging output",
                        action='store_true')
    parser.add_argument('ports', metavar='PORT', help="port(s) to watch",
                        nargs="+")
    args = parser.parse_args()

    # Build arguments for Serial constructor
    ser_args: dict[str, int | str | float] = {
        "timeout": 0, "baudrate": args.baud}
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
        case _: pass  # make linter happy

    if args.init_bt:
        init_bt(debug=args.debug)

    try:
        main_loop(ports=args.ports, ser_args=ser_args,
                  bt_uuid=str(args.bt_uuid), debug=args.debug)
    except KeyboardInterrupt:
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


LED_PATH = '/sys/class/leds/ACT'


class LedState(enum.Enum):
    """LED States."""
    NO_SERIAL = enum.auto()
    WAITING_BLUE = enum.auto()
    CONNECTED = enum.auto()
    #: For internal use only, for stopping the LED thread.
    STOP = enum.auto()


class LedControlThread(threading.Thread):
    """Thread that blinks the LED."""

    def __init__(self, q: queue.Queue[LedState]):
        self._q = q
        super().__init__()

    def run(self):
        with open(os.path.join(LED_PATH, 'max_brightness'), 'rb') as fh:
            on_st = str(int(fh.read())).encode('ASCII')
        off_st = b'1' if on_st == b'0' else b'0'
        _cur_on: bool = False  # only for use in toggle() below

        with open(os.path.join(LED_PATH, 'trigger'), 'wb') as fh:
            fh.write(b'none\n')

        def toggle(force: bool | None = None):
            nonlocal _cur_on
            if force is not None:
                _cur_on = force
            else:
                _cur_on = not _cur_on
            with open(os.path.join(LED_PATH, 'brightness'), 'wb') as fh:
                fh.write((on_st if _cur_on else off_st) + b'\n')
        toggle()

        state: LedState = LedState.NO_SERIAL
        while state != LedState.STOP:
            try:
                state = self._q.get_nowait()
            except queue.Empty:
                pass
            if state == LedState.NO_SERIAL:  # Blink rapidly
                time.sleep(0.1)
                toggle()
            elif state == LedState.WAITING_BLUE:  # Solid on
                toggle(True)
                time.sleep(0.5)  # rate limit this loop (!)
            elif state == LedState.CONNECTED:  # Blink slowly
                time.sleep(0.5)
                toggle()

        with open(os.path.join(LED_PATH, 'trigger'), 'wb') as fh:
            fh.write(b'actpwr\n')  # this appears to be the default


@contextmanager
def led_control():
    q: queue.Queue[LedState] = queue.Queue()
    thr = LedControlThread(q)
    thr.start()
    try:
        yield q
    finally:
        q.put(LedState.STOP)
        thr.join(3)


MAX_INTERVAL_NS: int = 1000000000  # 1s


def main_loop(  # pylint: disable=too-many-branches
        *, ports: list[str], ser_args: dict[str, Any], bt_uuid: str,
        debug: bool):
    notify = inotify.adapters.Inotify()
    watch = sorted(set(map(os.path.dirname, ports)))
    for p in watch:
        notify.add_watch(p)
    with led_control() as blinker:
        blinker.put(LedState.NO_SERIAL)
        last_check_ns: int = time.monotonic_ns() - MAX_INTERVAL_NS - 1
        while True:
            # rate limit this loop
            now_ns = time.monotonic_ns()
            if (sleep_ns := MAX_INTERVAL_NS - (now_ns - last_check_ns)) > 0:
                if debug:
                    print(f"Rate limiting sleeping {sleep_ns/1e9:.6f}s")
                time.sleep(sleep_ns/1e9)
            last_check_ns = now_ns
            # check which port exists
            the_port: str | None = None
            for p in ports:
                if os.path.exists(p):
                    the_port = p
                    break
            else:  # no ports exist, so wait for inotify event
                if debug:
                    print(f"No ports, watching {watch} for changes")
                blinker.put(LedState.NO_SERIAL)
                next(notify.event_gen(yield_nones=False))
                continue
            # try opening the port
            try:
                ser = serial.Serial(port=the_port, **ser_args)
            except OSError as ex:
                if debug:
                    print(f"Ignoring {ex!r}")
            else:
                print(f"Opened {the_port}, will now serve via Bluetooth")
                blinker.put(LedState.WAITING_BLUE)
                try:
                    with ser, bluetooth_ctx(uuid=bt_uuid, debug=debug) as bt:
                        blinker.put(LedState.CONNECTED)
                        bridge_ports(ser=ser, bt=bt, debug=debug)
                except OSError as ex:  # from bluetooth_ctx (not bridge_ports)
                    if debug:
                        print(f"Ignoring {ex!r}")
                finally:
                    blinker.put(LedState.WAITING_BLUE)


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
