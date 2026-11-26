#!/usr/bin/env python3
"""Exit once a Claude Code session is quiet: its last user/assistant line is an end_turn reply
and neither the main transcript nor any subagent transcript changed for QUIET seconds.

Usage: python3 -I wait_quiet.py <path/to/<id>.jsonl> [pid] [quiet_seconds=300]
Run it with Bash run_in_background; it prints one line and exits. With pid, it also exits when
that process ends. A main thread at end_turn is not proof of done: background subagents keep
writing and wake it later, hence the quiet window over every transcript.
"""
import glob, json, os, sys, time

path = sys.argv[1]
pid = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
quiet = int(sys.argv[3]) if len(sys.argv) > 3 else 300


def last_turn():
    last = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for l in f:
            try:
                d = json.loads(l)
            except ValueError:
                continue
            if d.get('type') in ('user', 'assistant'):
                last = d
    return last


while True:
    if pid:
        try:
            os.kill(pid, 0)
        except OSError:
            print('process exited')
            break
    files = [path] + glob.glob(path[:-6] + '/subagents/*.jsonl')
    idle = min(time.time() - os.path.getmtime(p) for p in files)
    last = last_turn()
    if idle > quiet and last and last['type'] == 'assistant' and last['message'].get('stop_reason') == 'end_turn':
        print('quiet since', last.get('timestamp'))
        break
    time.sleep(20)
