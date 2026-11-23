"""Self-test for session_audit.py: python3 -I test_session_audit.py
Builds a tiny transcript (main + one subagent) in a temp dir and checks the context, cost-mix,
plugin, Code Mode and loaded-file facts the script reports."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'session_audit.py')
FOLD = 'ctx_search({queries:["x"], source:"s1"}) searches the whole output (5000 B).'


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
srows = [asst('s1', 'claude-sonnet-5-5', 'Bash', 'b1', cr=20000), result('b1', FOLD),
         asst('s2', 'claude-sonnet-5-5', 'Bash', 'b2', cr=21000)]
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
loaded = [f[0] for f in data['main'].get('loaded', [])]
check('loaded instruction files', '/u/.nvm/CLAUDE.md' in loaded and '/u/.claude/CLAUDE.md' in loaded, loaded)
hm = data['main'].get('hook_messages', {})
check('hook system messages', any('no CBM daemon' in k for k in hm), hm)

p = subprocess.run([sys.executable, '-I', SCRIPT, main], capture_output=True, text=True)
check('text run exits 0', p.returncode == 0, p.stderr)
check('text shows loaded files and fold follow-up', '/u/.nvm/CLAUDE.md' in p.stdout and 'folds' in p.stdout, p.stdout[-300:])
sys.exit(1 if fails else 0)
