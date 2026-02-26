#!/usr/bin/env python3
"""
zbx_loganalyzer.py - Zabbix log analyzer
Usage: python3 zbx_loganalyzer.py --help
"""

import re
import argparse
import sys
from datetime import datetime

DEFAULT_LOG_PATH = '/var/log/zabbix/zabbix_server.log'

# PID:YYYYMMDD:HHmmss.ms
RE_LOG_LINE = re.compile(r'^\s*(\d+):(\d{8}):(\d{6}\.\d+)\s+')
RE_PROFILING = re.compile(r'=== Profiling statistics')


def parse_line_dt(m):
    return datetime.strptime(m.group(2) + m.group(3)[:6], '%Y%m%d%H%M%S')


def parse_profiling(lines, pid_filter=None, after=None, before=None):
    blocks = []
    current_lines = None

    for line in lines:
        m = RE_LOG_LINE.match(line)

        if not m:
            if current_lines is not None:
                current_lines.append(line.rstrip())
            continue

        # Любая строка с PID завершает текущий блок
        if current_lines is not None:
            blocks.append(current_lines)
            current_lines = None

        pid = m.group(1)
        line_dt = parse_line_dt(m)
        if (RE_PROFILING.search(line)
                and not (pid_filter and pid != pid_filter)
                and not (after  and line_dt < after)
                and not (before and line_dt > before)):
            current_lines = [line.rstrip()]

    if current_lines is not None:
        blocks.append(current_lines)

    return blocks


def render_text(blocks):
    sep = '-' * 60
    for block in blocks:
        print(sep)
        for line in block:
            print(line)
    print(sep)
    print(f"Total blocks: {len(blocks)}")


def main():
    parser = argparse.ArgumentParser(description='Zabbix log analyzer')
    parser.add_argument('--log', default=DEFAULT_LOG_PATH, help=f'Path to zabbix log file (default: {DEFAULT_LOG_PATH})')
    parser.add_argument('--mode', required=True, choices=['profiling'], help='Analysis mode')
    parser.add_argument('--pid', default=None, help='Filter by PID')
    parser.add_argument('--after',  default=None, metavar='DATETIME', help='Show blocks after this time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--before', default=None, metavar='DATETIME', help='Show blocks before this time (YYYY-MM-DD HH:MM:SS)')
    args = parser.parse_args()

    FMT = '%Y-%m-%d %H:%M:%S'
    try:
        after_dt  = datetime.strptime(args.after,  FMT) if args.after  else None
        before_dt = datetime.strptime(args.before, FMT) if args.before else None
    except ValueError as e:
        print(f"Error: invalid datetime format: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        f = open(args.log, 'r', errors='replace')
    except FileNotFoundError:
        print(f"Error: file not found: {args.log}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: permission denied: {args.log}", file=sys.stderr)
        sys.exit(1)

    with f:
        if args.mode == 'profiling':
            blocks = parse_profiling(f, pid_filter=args.pid, after=after_dt, before=before_dt)
        render_text(blocks)



if __name__ == '__main__':
    main()