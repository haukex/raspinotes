#!/usr/bin/env python3
"""Continually listens for UDP packets on a specific port and prints their
contents together with the sender's address."""
import socket
from contextlib import closing

with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
    sock.bind(('', 12340))
    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except KeyboardInterrupt:
            break
        print(f"From {addr[0]}: {data!r}")
