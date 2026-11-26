#!/usr/bin/env python3
"""Facts from one Claude Code session transcript, for judging how the config steered it.

Usage: python3 -I session_audit.py <session-id | path/to/<id>.jsonl> [--cwd-slug SLUG] [--json]

Reads <id>.jsonl plus <id>/subagents/*.jsonl (+ .meta.json). Prints:
  per agent: type, model, requests, tokens, cost in USD and its mix, first-request and peak
    context (tokens sent), REPL calls, Poll-only requests, context-mode / CBM calls, folds received
  main thread: Flow lines, Skill calls, Agent calls (type, model override, description),
    instruction files loaded (CLAUDE.md, memory) with size, hook system messages
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
UNPRICED = set()  # advisor models already warned about
PATTERNS = {
    'hook_block': r'BLOCKED:|PreToolUse:\w+ hook error',
    'denied': r'denied by the Claude Code auto mode classifier|denied by your permission settings|matches a deny rule',
    'hook_fail': r'the hook failed|the hook did not finish',
    'fold': r'ctx_search\(',
}
FOLD = re.compile(r'searches the whole output|ctx_search\(\{queries')
PLUGINS = {'mcp__plugin_context-mode_': 'context-mode', 'mcp__codebase-memory-mcp__': 'cbm'}


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
    req, models, tools, plug, seen = {}, Counter(), {}, Counter(), set()
    folds = repl = 0
    first = last = None
    for d in lines(path):
        ts = d.get('timestamp')
        if ts:
            first = first or ts
            last = ts
        msg = d.get('message') or {}
        if d.get('type') == 'user' and isinstance(msg.get('content'), list):
            folds += sum(1 for x in msg['content'] if x.get('type') == 'tool_result'
                         and FOLD.search(json.dumps(x.get('content'), ensure_ascii=False)))
        if d.get('type') != 'assistant' or msg.get('model') == '<synthetic>':
            continue
        m = short(msg.get('model'))
        models[m] += 1
        k = d.get('requestId') or d.get('uuid')
        req[k] = (m, msg.get('usage') or {})
        for x in msg.get('content') or []:
            if x.get('type') != 'tool_use' or x['id'] in seen:
                continue
            seen.add(x['id'])
            tools.setdefault(k, set()).add(x['name'])
            repl += x['name'] == 'REPL'
            for pre, label in PLUGINS.items():
                plug[label] += x['name'].startswith(pre)
    tot, parts = Counter(), Counter()
    sizes = []
    for m, u in req.values():
        sizes.append(sum(u.get(k, 0) or 0 for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')))
        p = PRICES.get(m)
        cw = u.get('cache_creation') or {}
        w1h = cw.get('ephemeral_1h_input_tokens', 0) or 0
        w5m = (u.get('cache_creation_input_tokens', 0) or 0) - w1h
        for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
            tot[k] += u.get(k, 0) or 0
        if p:
            parts['input'] += (u.get('input_tokens', 0) or 0) * p[0] / 1e6
            parts['output'] += (u.get('output_tokens', 0) or 0) * p[1] / 1e6
            parts['cache_read'] += (u.get('cache_read_input_tokens', 0) or 0) * p[2] / 1e6
            parts['cache_write'] += (w5m * 1.25 + w1h * 2) * p[0] / 1e6
        # An advisor call bills at its own model and is absent from the top-level usage: in 360 of 360 records (2026-11),
        # the top-level usage equals the sum of the `message` iterations, so adding `advisor_message` ones counts nothing twice.
        for it in u.get('iterations') or []:
            if it.get('type') != 'advisor_message':
                continue
            am = short(it.get('model'))
            models[am] += 1
            for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
                tot[k] += it.get(k, 0) or 0
            ap = PRICES.get(am)
            if not ap:
                if am not in UNPRICED:
                    UNPRICED.add(am)
                    print(f'warning: no price for advisor model {it.get("model")}; its cost is left out', file=sys.stderr)
            else:
                a1h = (it.get('cache_creation') or {}).get('ephemeral_1h_input_tokens', 0) or 0
                a5m = (it.get('cache_creation_input_tokens', 0) or 0) - a1h
                parts['advisor'] += ((it.get('input_tokens', 0) or 0) * ap[0] + (it.get('output_tokens', 0) or 0) * ap[1]
                                     + (it.get('cache_read_input_tokens', 0) or 0) * ap[2] + (a5m * 1.25 + a1h * 2) * ap[0]) / 1e6
    return {'requests': len(req), 'models': dict(models), 'tokens': dict(tot), 'usd': round(sum(parts.values()), 2),
            'usd_parts': {k: round(v, 4) for k, v in parts.items()}, 'advisor_usd': round(parts['advisor'], 2),
            'ctx0': sizes[0] if sizes else 0, 'peak': max(sizes, default=0), 'repl': repl, 'folds': folds,
            'poll_only': sum(1 for s in tools.values() if s == {'Poll'}), 'plugin_calls': {k: v for k, v in plug.items() if v},
            'span': f'{(first or "")[11:16]}-{(last or "")[11:16]}'}


def main_thread(path):
    out = {'flow': [], 'skills': [], 'agents': [], 'events': Counter(), 'errors': [], 'resumes': 0, 'tools': Counter(),
           'hook_messages': Counter()}
    seen_tool, resumes, loaded = set(), set(), {}
    for d in lines(path):
        t = d.get('type')
        att = d.get('attachment') or {}
        if att.get('hookName') == 'SessionStart:resume':
            resumes.add(att.get('toolUseID'))
        for f in att.get('files') or [] if att.get('type') == 'instructions' else []:
            loaded[f.get('path')] = (f.get('type'), len(f.get('content') or ''))
        if att.get('type') == 'nested_memory':
            c = att.get('content') or {}
            loaded[att.get('path')] = (c.get('type'), len(c.get('content') or ''))
        if att.get('type') == 'hook_system_message':
            out['hook_messages'][str(att.get('content'))[:120]] += 1
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
    out['loaded'] = [(p, ty, n) for p, (ty, n) in loaded.items()]
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
    total, parts = 0.0, Counter()
    for a, desc, u in rows:
        tk = u['tokens']
        total += u['usd']
        parts.update(u['usd_parts'])
        print(f'{a:10} {desc:40} {"/".join(u["models"]):12} {u["requests"]:4} {tk.get("cache_read_input_tokens", 0):10} '
              f'{tk.get("cache_creation_input_tokens", 0):9} {tk.get("output_tokens", 0):7} {u["usd"]:7.2f}  {u["span"]}')
    print(f'total usd {total:.2f}  mix: ' + ', '.join(f'{k} {v / (total or 1):.0%}' for k, v in parts.most_common()))
    print(f'\n{"agent":10} {"ctx0_k":>6} {"peak_k":>6} {"repl":>4} {"poll_only":>9} {"ctx_mode":>8} {"cbm":>4} {"folds":>5}')
    for a, _, u in rows:
        pc = u['plugin_calls']
        print(f'{a:10} {u["ctx0"] // 1000:6} {u["peak"] // 1000:6} {u["repl"]:4} {u["poll_only"]:9} '
              f'{pc.get("context-mode", 0):8} {pc.get("cbm", 0):4} {u["folds"]:5}')
    print('\nloaded:')
    for p, ty, n in mt['loaded']:
        print(f'  {ty or "?":8} {n:7} chars  {p}')
    print('hook messages:', dict(mt['hook_messages']) or 'none')
    print('flow:', mt['flow'] or 'none')
    print('skills:', mt['skills'])
    print('agent calls:', mt['agents'])
    print('tool calls:', dict(mt['tools'].most_common()))
    print('events:', dict(mt['events']), ' tool errors:', len(mt['errors']))
    for e in mt['errors']:
        print('  err:', e)


if __name__ == '__main__':
    main()
