#!/usr/bin/env python3
"""Facts from one Claude Code session transcript, for judging how the config steered it.

Usage: python3 -I session_audit.py <session-id | path/to/<id>.jsonl> [--cwd-slug SLUG] [--json]

Reads <id>.jsonl plus <id>/subagents/*.jsonl (+ .meta.json). Prints:
  per agent: type, model, requests, tokens, cost in USD
  main thread: Flow lines, Skill calls, Agent calls (type, model override, description)
  hook blocks, permission denials, context-mode folds, tool errors, resumes
Notes it handles: usage deduped by requestId; '<synthetic>' entries skipped; Code Mode nested
calls (ids starting 'repl_') counted once; `claude -r` appends to the same .jsonl (a resume
shows as a 'SessionStart:resume' hook attachment); background subagents keep writing after the main end_turn.
Prices: per MTok, from the claude-api skill (2026-11). Update PRICES when they change.
"""
import glob, json, os, re, sys
from collections import Counter

PRICES = {  # input, output, cache read; cache write = input x 1.25 (5m) or x 2 (1h)
    'opus-5-5': (4.0, 20.0, 0.20), 'sonnet-5-5': (2.0, 10.0, 0.10),
    'haiku-5-5': (0.10, 0.50, 0.01), 'fable-5-2': (8.0, 40.0, 0.20),
}
PATTERNS = {
    'hook_block': r'BLOCKED:|PreToolUse:\w+ hook error',
    'denied': r'denied by the Claude Code auto mode classifier|denied by your permission settings|matches a deny rule',
    'hook_fail': r'the hook failed|the hook did not finish',
    'fold': r'ctx_search\(',
}


def find(arg, slug):
    if arg.endswith('.jsonl') and os.path.exists(arg):
        return arg
    pat = os.path.expanduser(f'~/.claude/projects/{slug or "*"}/{arg}*.jsonl')
    hits = [h for h in glob.glob(pat) if '/subagents/' not in h]
    if len(hits) != 1:
        sys.exit(f'need exactly one transcript for {arg}, found {hits}')
    return hits[0]


def lines(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        for l in f:
            try:
                yield json.loads(l)
            except ValueError:
                continue


def short(model):
    return (model or '?').replace('claude-', '')


def usage(path):
    req, models = {}, Counter()
    first = last = None
    for d in lines(path):
        ts = d.get('timestamp')
        if ts:
            first = first or ts
            last = ts
        if d.get('type') != 'assistant' or d['message'].get('model') == '<synthetic>':
            continue
        m = short(d['message'].get('model'))
        models[m] += 1
        req[d.get('requestId') or d.get('uuid')] = (m, d['message'].get('usage') or {})
    tot = Counter()
    cost = 0.0
    for m, u in req.values():
        p = PRICES.get(m)
        cw = u.get('cache_creation') or {}
        w1h = cw.get('ephemeral_1h_input_tokens', 0) or 0
        w5m = (u.get('cache_creation_input_tokens', 0) or 0) - w1h
        for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
            tot[k] += u.get(k, 0) or 0
        if p:
            cost += ((u.get('input_tokens', 0) or 0) * p[0] + (u.get('output_tokens', 0) or 0) * p[1]
                     + (u.get('cache_read_input_tokens', 0) or 0) * p[2] + w5m * p[0] * 1.25 + w1h * p[0] * 2) / 1e6
    return {'requests': len(req), 'models': dict(models), 'tokens': dict(tot), 'usd': round(cost, 2),
            'span': f'{(first or "")[11:16]}-{(last or "")[11:16]}'}


def main_thread(path):
    out = {'flow': [], 'skills': [], 'agents': [], 'events': Counter(), 'errors': [], 'resumes': 0, 'tools': Counter()}
    seen_tool, resumes = set(), set()
    for d in lines(path):
        t = d.get('type')
        att = d.get('attachment') or {}
        if att.get('hookName') == 'SessionStart:resume':
            resumes.add(att.get('toolUseID'))
        if t == 'assistant':
            for x in d['message'].get('content') or []:
                if x.get('type') == 'text':
                    for m in re.finditer(r'^Flow:.*$', x['text'], re.M):
                        out['flow'].append(m.group(0)[:160])
                if x.get('type') != 'tool_use' or x['id'] in seen_tool:
                    continue
                seen_tool.add(x['id'])
                out['tools'][x['name']] += 1
                inp = x.get('input') or {}
                if x['name'] == 'Skill':
                    out['skills'].append(inp.get('skill'))
                if x['name'] == 'Agent':
                    out['agents'].append((inp.get('subagent_type'), inp.get('model') or 'default', inp.get('description')))
        if t == 'user' and isinstance(d['message'].get('content'), list):
            for x in d['message']['content']:
                if x.get('type') != 'tool_result':
                    continue
                s = json.dumps(x.get('content'), ensure_ascii=False)
                for k, p in PATTERNS.items():
                    if re.search(p, s):
                        out['events'][k] += 1
                if x.get('is_error'):
                    out['errors'].append(s[:160])
    out['resumes'] = len(resumes)
    out['skills'] = list(dict.fromkeys(s for s in out['skills'] if s))
    return out


def main():
    args = sys.argv[1:]
    slug = args[args.index('--cwd-slug') + 1] if '--cwd-slug' in args else None
    path = find(args[0], slug)
    base = path[:-6]
    rows = [('main', '-', usage(path))]
    for sub in sorted(glob.glob(base + '/subagents/*.jsonl'), key=os.path.getmtime):
        meta = json.load(open(sub[:-6] + '.meta.json')) if os.path.exists(sub[:-6] + '.meta.json') else {}
        rows.append((meta.get('agentType', '?'), meta.get('description', '')[:40], usage(sub)))
    mt = main_thread(path)
    if '--json' in args:
        print(json.dumps({'agents': rows, 'main': mt}, default=list, ensure_ascii=False, indent=1))
        return
    print(f'# {os.path.basename(path)}  resumes: {mt["resumes"]}')
    print(f'{"agent":10} {"description":40} {"model":12} {"req":>4} {"cache_read":>10} {"cache_wr":>9} {"out":>7} {"usd":>7}  span')
    total = 0.0
    for a, desc, u in rows:
        tk = u['tokens']
        total += u['usd']
        print(f'{a:10} {desc:40} {"/".join(u["models"]):12} {u["requests"]:4} {tk.get("cache_read_input_tokens", 0):10} '
              f'{tk.get("cache_creation_input_tokens", 0):9} {tk.get("output_tokens", 0):7} {u["usd"]:7.2f}  {u["span"]}')
    print(f'total usd {total:.2f}')
    print('flow:', mt['flow'] or 'none')
    print('skills:', mt['skills'])
    print('agent calls:', mt['agents'])
    print('tool calls:', dict(mt['tools'].most_common()))
    print('events:', dict(mt['events']), ' tool errors:', len(mt['errors']))
    for e in mt['errors']:
        print('  err:', e)


if __name__ == '__main__':
    main()
