"""Self-test for session_audit.py: python3 -I test_session_audit.py
Builds a tiny transcript (main + one subagent) in a temp dir and checks the context, cost-mix,
plugin, Code Mode and loaded-file facts the script reports."""
import json, os, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")  # the checks print ✓; a cp1252 console on Windows cannot

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'session_audit.py')
FOLD = 'ctx_search({queries:["x"], source:"s1"}) searches the whole ' 'output (5000 B).'  # split: write-fold-guard refuses the whole phrase


def asst(req, model, tool, tid, cr=0, cw=0, inp=0, out=0):
    return {'type': 'assistant', 'requestId': req, 'timestamp': '2026-11-23T10:00:00Z',
            'message': {'model': model, 'usage': {'input_tokens': inp, 'output_tokens': out,
                        'cache_read_input_tokens': cr, 'cache_creation_input_tokens': cw},
                        'content': [{'type': 'tool_use', 'id': tid, 'name': tool, 'input': {}}]}}


def result(tid, text):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': tid, 'content': text}]}}


def att(a):
    return {'type': 'attachment', 'attachment': a}


d = tempfile.mkdtemp()
main = os.path.join(d, 'abc.jsonl')
os.makedirs(os.path.join(d, 'abc', 'subagents'))
sub = os.path.join(d, 'abc', 'subagents', 'agent-1.jsonl')
rows = [
    att({'type': 'instructions', 'files': [{'path': '/u/.claude/CLAUDE.md', 'type': 'User', 'content': 'x' * 100},
                                           {'path': '/u/.nvm/CLAUDE.md', 'type': 'Project', 'content': 'y' * 50}]}),
    att({'type': 'hook_system_message', 'hookName': 'SessionStart:startup',
         'content': 'codebase-memory-mcp: no CBM daemon is running, so graph augmentation is skipped.'}),
    asst('r1', 'claude-opus-5-5', 'REPL', 't1', cr=30000, cw=7000, inp=10, out=100),
    result('t1', FOLD),
    asst('r2', 'claude-opus-5-5', 'Poll', 't2', cr=40000, inp=5, out=10),
    asst('r3', 'claude-opus-5-5', 'mcp__plugin_context-mode_context-mode__ctx_search', 't3', cr=50000),
    asst('r4', 'claude-opus-5-5', 'mcp__codebase-memory-mcp__search_graph', 't4', cr=45000),
]
open(main, 'w').write('\n'.join(json.dumps(r) for r in rows) + '\n')
advised = asst('s3', 'claude-sonnet-5-5', 'Bash', 'b3', cr=22000)
advised['message']['usage']['iterations'] = [  # an advisor call: billed at its own model, absent from the top-level usage
    {'type': 'message', 'cache_read_input_tokens': 22000},
    {'type': 'advisor_message', 'model': 'claude-opus-5-5', 'input_tokens': 1_000_000, 'output_tokens': 0},
    {'type': 'advisor_message', 'model': 'claude-unknown-9', 'input_tokens': 5}, {'type': 'advisor_message', 'model': 'claude-unknown-9'}]
srows = [asst('s1', 'claude-sonnet-5-5', 'Bash', 'b1', cr=20000), result('b1', FOLD),
         asst('s2', 'claude-sonnet-5-5', 'Bash', 'b2', cr=21000), advised]
open(sub, 'w').write('\n'.join(json.dumps(r) for r in srows) + '\n')
json.dump({'agentType': 'worker', 'description': 'fix it'}, open(sub[:-6] + '.meta.json', 'w'))

fails = 0
def check(name, ok, detail=''):
    global fails
    fails += not ok
    print(('ok   ' if ok else 'FAIL ') + name, str(detail)[:120])

p = subprocess.run([sys.executable, '-I', SCRIPT, main, '--json'], capture_output=True, text=True)
check('json run exits 0', p.returncode == 0, p.stderr)
data = json.loads(p.stdout) if p.returncode == 0 else {'agents': [[0, 0, {}], [0, 0, {}]], 'main': {}}
m, s = data['agents'][0][2], data['agents'][1][2]
check('main first-request context', m.get('ctx0') == 37010, m.get('ctx0'))
check('main peak context', m.get('peak') == 50000, m.get('peak'))
check('main poll-only requests', m.get('poll_only') == 1, m.get('poll_only'))
check('main REPL calls', m.get('repl') == 1, m.get('repl'))
check('main plugin calls', m.get('plugin_calls') == {'context-mode': 1, 'cbm': 1}, m.get('plugin_calls'))
check('main folds', m.get('folds') == 1, m.get('folds'))
parts = m.get('usd_parts') or {}
check('cost parts add up', parts and abs(sum(parts.values()) - m.get('usd', -1)) < 0.011, parts)
check('subagent folds, no plugin calls', s.get('folds') == 1 and s.get('plugin_calls') == {}, (s.get('folds'), s.get('plugin_calls')))
check('subagent first-request context', s.get('ctx0') == 20000, s.get('ctx0'))
check('advisor calls priced at their own model', s.get('advisor_usd') == 4.0, s.get('advisor_usd'))
check('advisor tokens and model are counted', s.get('tokens', {}).get('input_tokens') == 1_000_005 and s.get('models', {}).get('opus-5-5') == 1, (s.get('tokens'), s.get('models')))
check('an unpriced advisor model is reported once', p.stderr.count('claude-unknown-9') == 1, p.stderr[-300:])
check('advisor cost counts in the agent total', abs(s.get('usd', 0) - 4.01) < 0.001, s.get('usd'))
loaded = [f[0] for f in data['main'].get('loaded', [])]
check('loaded instruction files', '/u/.nvm/CLAUDE.md' in loaded and '/u/.claude/CLAUDE.md' in loaded, loaded)
hm = data['main'].get('hook_messages', {})
check('hook system messages', any('no CBM daemon' in k for k in hm), hm)

p = subprocess.run([sys.executable, '-I', SCRIPT, main], capture_output=True, text=True)
check('text run exits 0', p.returncode == 0, p.stderr)
check('text shows loaded files and fold follow-up', '/u/.nvm/CLAUDE.md' in p.stdout and 'folds' in p.stdout, p.stdout[-300:])

# A second transcript: two prompts, a Flow line, a skill before the first write, one real hook block (shown twice, as
# Code Mode does) beside hook source that only quotes the word, a cold cache write after a long gap, and an Exit list.
BLOCK = "Permission denied for Bash: PreToolUse:Bash hook error: [~/.claude/hooks/bash-ban-shell-writes]: BLOCKED: 'echo > f' writes a file from Bash."


def at(row, ts):
    row['timestamp'] = '2026-11-23T' + ts + 'Z'
    return row


def says(req, text, ts, model='claude-fable-5-2', **kw):
    row = at(asst(req, model, 'Read', 'x' + req, **kw), ts)
    row['message']['content'] = [{'type': 'text', 'text': text}]
    return row


def calls(req, tool, inp, ts, **kw):
    row = at(asst(req, 'claude-fable-5-2', tool, 'x' + req, **kw), ts)
    row['message']['content'][0]['input'] = inp
    return row


def prompt(text, ts):
    return at({'type': 'user', 'origin': {'kind': 'human'}, 'message': {'content': text}}, ts)  # a typed prompt carries this origin


def failed(tid, text):
    row = result(tid, text)
    row['message']['content'][0]['is_error'] = True
    return row


two = os.path.join(d, 'two.jsonl')
os.makedirs(os.path.join(d, 'two', 'subagents'))
rows = [
    prompt('do the thing', '10:00:00'),
    says('q1', 'Flow: Code flow (`tdd`)', '10:00:05', cr=1000),
    calls('q2', 'Skill', {'skill': 'tdd'}, '10:00:10', cr=1000),
    calls('q3', 'Write', {'file_path': '/repo/a.py'}, '10:00:20', cr=1000),
    calls('q4', 'Bash', {'command': 'echo > f'}, '10:00:30', cr=1000), failed('xq4', BLOCK),
    calls('q5', 'REPL', {}, '10:00:40', cr=1000), result('xq5', '- "Bash", refused: "' + BLOCK.replace('>', '&gt;') + '\n"'),  # Code Mode escapes it
    calls('q6', 'Read', {'file_path': '/repo/hook'}, '10:00:50', cr=1000), result('xq6', 'print("BLOCKED: %s writes a file")\nBLOCK = "' + BLOCK.replace('echo', 'cat') + '"'),  # hook source, and a test file that quotes a block
    says('q7', 'Done.\n\n## Exit\n\n- ✓ gate green: `bin/check` exit 0', '10:01:00', cr=1000),
    prompt('commit', '11:30:00'),
    calls('q8', 'Write', {'file_path': '/repo/b.py'}, '11:30:05', cw=150000),
    {**prompt('<task-notification>\n<task-id>b1</task-id>', '11:30:07'), 'origin': {'kind': 'task-notification'}},  # not a prompt
    {**prompt('<local-command-stdout>Set model</local-command-stdout>', '11:30:08'), 'origin': None},  # nor is this
    calls('q9', 'Read', {'file_path': '/repo/b.py'}, '11:30:10', cr=450000),
    says('q10', 'Checks so far:\n- ✓ pushed', '11:30:20'),
    says('q11', '## Exiting early is not a list. No list in the last reply.', '11:30:30'),
]
open(two, 'w').write('\n'.join(json.dumps(r) for r in rows) + '\n')
review = '## Review\n\nNo P0 found.\n- P0-only re-check ran: none\n- HIGH-level summary\n\n**P1. One** a\n- **Finding P1: two**\n**1. HIGH: three**\n**Finding: MEDIUM, four.**'
sub2 = os.path.join(d, 'two', 'subagents', 'agent-1.jsonl')
open(sub2, 'w').write(json.dumps(says('v1', review, '10:00:45', model='claude-opus-5-5', cr=19000)) + '\n')
json.dump({'agentType': 'reviewer', 'description': 'review it'}, open(sub2[:-6] + '.meta.json', 'w'))

p = subprocess.run([sys.executable, '-I', SCRIPT, two, '--json'], capture_output=True, text=True, encoding='utf-8')  # the output holds ✓: Windows would decode it as cp1252
check('second transcript: json run exits 0', p.returncode == 0, p.stderr)
data = json.loads(p.stdout) if p.returncode == 0 else {'agents': [[0, 0, {}], [0, 0, {}]], 'main': {}}
t = data['main'].get('turns') or []
t = t if len(t) == 2 else [{}, {}]
check('one turn per prompt', len(data['main'].get('turns') or []) == 2, data['main'].get('turns'))
check('Flow line before the first tool call, per turn', t[0].get('flow_first') is True and t[1].get('flow_first') is False, (t[0].get('flow_first'), t[1].get('flow_first')))
check('skill called before the first write', t[0].get('skills_before_write') == ['tdd'] and t[0].get('writes') == 1 and t[1].get('skills_before_write') == [], t)
check('turn cost: a cold write plus a read', abs(t[1].get('usd', 0) - 1.59) < 0.005, t[1].get('usd'))
check('a turn keeps its Exit list', '✓ gate green' in (t[0].get('exit') or '') and not t[1].get('exit'), (t[0].get('exit'), t[1].get('exit')))
m = data['agents'][0][2]
bands = m.get('bands') or {}
check('requests and cost per context band', bands.get('400-600k', [0])[0] == 1 and bands.get('<200k', [0])[0] == 10, bands)
check('turn costs add up to the agent cost', abs(sum(x.get('usd', 0) for x in t) - m.get('usd', -1)) < 0.011, (t[0].get('usd'), t[1].get('usd'), m.get('usd')))
cold = m.get('cold') or [{}]
check('cold cache write with the gap before it', len(cold) == 1 and cold[0].get('tokens') == 150000 and cold[0].get('gap_min') == 89, cold)
blocks = data['main'].get('blocks') or []
check('one real hook block, counted once', len(blocks) == 1 and 'echo > f' in blocks[0] and data['main'].get('events', {}).get('hook_block') == 1, (blocks, data['main'].get('events')))
check('severity counts from a subagent final message', data['agents'][1][2].get('sev') == {'P1': 2, 'HIGH': 1, 'MEDIUM': 1}, data['agents'][1][2].get('sev'))

p = subprocess.run([sys.executable, '-I', SCRIPT, two, '--turns', '--exits'], capture_output=True, text=True, encoding='utf-8')
check('--turns prints a row per prompt', p.returncode == 0 and '1.59' in p.stdout and 'commit' in p.stdout, p.stdout[-400:] + p.stderr[-200:])
check('--exits prints the Exit lists', '✓ gate green' in p.stdout, p.stdout[-300:])
p = subprocess.run([sys.executable, '-I', SCRIPT, two], capture_output=True, text=True, encoding='utf-8')
check('default text: distinct hook blocks, bands, no Exit lists', 'hook blocks: 1' in p.stdout and '400-600k' in p.stdout and '✓ gate green' not in p.stdout, p.stdout[-400:])
sys.exit(1 if fails else 0)
