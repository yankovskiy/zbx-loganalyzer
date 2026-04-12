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
RE_LLD_START = re.compile(r'processing discovery rule:(\d+)')
RE_LLD_END   = re.compile(r'End of lld_process_task\(\)')


def parse_line_dt(m):
    return datetime.strptime(m.group(2) + m.group(3)[:6], '%Y%m%d%H%M%S')


def parse_line_ts(m):
    """Return float seconds-since-midnight with millisecond precision."""
    t = m.group(3)          # "HHmmss.ms", e.g. "180642.906"
    hh, mm, ss = int(t[0:2]), int(t[2:4]), int(t[4:6])
    ms = float('0.' + t[7:]) if '.' in t else 0.0
    return hh * 3600 + mm * 60 + ss + ms


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


def parse_lld(lines, pid_filter=None, after=None, before=None):
    open_tasks = {}  # pid -> (start_ts, rule_id)
    stats = {}       # rule_id -> {'count': int, 'total': float, 'max': float}

    for line in lines:
        m = RE_LOG_LINE.match(line)
        if not m:
            continue

        pid = m.group(1)
        ms = RE_LLD_START.search(line)
        if ms:
            line_dt = parse_line_dt(m)
            if (not (pid_filter and pid != pid_filter)
                    and not (after  and line_dt < after)
                    and not (before and line_dt > before)):
                open_tasks[pid] = (parse_line_ts(m), ms.group(1))
        elif RE_LLD_END.search(line) and pid in open_tasks:
            start_ts, rule_id = open_tasks.pop(pid)
            duration = parse_line_ts(m) - start_ts
            if duration >= 0:
                if rule_id not in stats:
                    stats[rule_id] = {'count': 0, 'total': 0.0, 'max': 0.0}
                s = stats[rule_id]
                s['count'] += 1
                s['total'] += duration
                if duration > s['max']:
                    s['max'] = duration

    return stats


def render_lld(stats, top=10):
    rows = sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)
    if top > 0:
        rows = rows[:top]

    fmt = '{:<15} {:>6} {:>11} {:>9} {:>9}'
    sep = '-' * 55
    print(fmt.format('rule_id', 'count', 'total_sec', 'avg_sec', 'max_sec'))
    print(sep)
    for rule_id, s in rows:
        avg = s['total'] / s['count'] if s['count'] else 0.0
        print(fmt.format(rule_id, s['count'],
                         f"{s['total']:.3f}", f"{avg:.3f}", f"{s['max']:.3f}"))
    print(sep)
    shown = len(rows)
    total = len(stats)
    if top > 0 and total > shown:
        print(f"Total rules: {total}  (showing top {shown})")
    else:
        print(f"Total rules: {total}")


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
    parser.add_argument('--mode', required=True, choices=['profiling', 'lld'], help='Analysis mode')
    parser.add_argument('--top', type=int, default=10, metavar='N',
                        help='(lld mode) Show top N rules by total time (default: 10, 0 = all)')
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
        elif args.mode == 'lld':
            stats = parse_lld(f, pid_filter=args.pid, after=after_dt, before=before_dt)
            render_lld(stats, top=args.top)



if __name__ == '__main__':
    main()