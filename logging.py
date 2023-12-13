#!/usr/bin/python3
"""Simple Raspberry Pi Logging Script

**BETA** - needs some more real-world testing

This script logs some system information to a log file and can "commit" that
log file by appending it to the end of a different log file. This is intended
to be used when the Raspberry Pi's root partition is protected by the overlay
filesystem and the log needs to be saved to the writable data partition once in
a while.

Example crontab:

          0      * * * *     /path/to/logging.py -cd
          5-55/5 * * * *     /path/to/logging.py
"""
from datetime import datetime, timezone
from fcntl import flock, LOCK_EX
from typing import NamedTuple
from pathlib import Path
import urllib.request
import subprocess
import json
import csv
import os

CURRENT_LOG = Path('/home/pi/pi_log.csv')
COMMIT_LOG  = Path('/data/pi/pi_log.csv')
DATAPASS_URL = 'https://pass.telekom.de/api/service/generic/v1/status'
USE_CURL = True
LTE_STICK_IF = 'enx001e101f0000'

class LogEntry(NamedTuple):
    timestamp :datetime
    cpu_temp_c :float
    gpu_temp_c :float
    used_bytes :int|None = None
    total_bytes :int|None = None

def get_cpu_temp_c():
    with open('/sys/class/thermal/thermal_zone0/temp', encoding='ASCII') as fh:
        return float(fh.read().rstrip())/1000

def get_gpu_temp_c():
    rv = subprocess.run(['/usr/bin/vcgencmd','measure_temp'],
        check=True, capture_output=True, encoding='ASCII')
    if rv.stderr: raise subprocess.SubprocessError(f"stderr was not empty: {rv.stderr!r}")
    out = rv.stdout.rstrip()
    assert out.startswith('temp=') and out.endswith("'C")
    return float( out.removeprefix('temp=').removesuffix("'C") )

def get_datapass():
    if USE_CURL:
        # curl has the --interface option to specifically send request over the LTE stick
        rv = subprocess.run(['curl','--silent','--max-time','5','--fail','--fail-early','--show-error',
            '--interface',LTE_STICK_IF,DATAPASS_URL], check=True, capture_output=True, timeout=7)
        if rv.stderr: raise subprocess.SubprocessError(f"stderr was not empty: {rv.stderr!r}")
        data = json.loads(rv.stdout)
    else:
        with urllib.request.urlopen(DATAPASS_URL, timeout=5) as f:
            data = json.load(f)
    return data['usedVolume'], data['initialVolume']

def write_log(*, with_datapass :bool = False):
    datapass = get_datapass() if with_datapass else ()
    ent = LogEntry(datetime.now(timezone.utc), get_cpu_temp_c(), get_gpu_temp_c(), *datapass)
    with CURRENT_LOG.open('a', encoding='UTF-8', newline='') as fh:
        flock(fh, LOCK_EX)
        fh.seek(0, os.SEEK_END)
        csvwr = csv.DictWriter(fh, fieldnames=LogEntry._fields)
        if not os.stat(fh.fileno()).st_size:  # file is empty
            csvwr.writeheader()
        csvwr.writerow(ent._asdict())

def commit_log():
    with ( COMMIT_LOG.open('a', encoding='UTF-8') as ofh, CURRENT_LOG.open('r+', encoding='UTF-8') as ifh ):
        flock(ofh, LOCK_EX)
        ofh.seek(0, os.SEEK_END)
        flock(ifh, LOCK_EX)
        ifh.readline()  # discard CSV header
        for line in ifh:
            ofh.write(line)
        ofh.flush()
        ifh.truncate(0)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='RPi Logging Tool')
    parser.add_argument('-d', '--datapass', help="include datapass.de usage data", action="store_true")
    parser.add_argument('-c', '--commit', help="commit log file", action="store_true")
    args = parser.parse_args()
    write_log(with_datapass=args.datapass)
    if args.commit: commit_log()
    parser.exit(0)
