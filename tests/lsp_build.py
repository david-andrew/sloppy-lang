#!/usr/bin/env python3
"""Contextual build: completion kinds, semantic tokens, rename and document symbols.
Run after tools/lsptest.py: TMPDIR=... python3 tests/lsp_build.py.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
checks = 0
p = subprocess.Popen([str(root / 'bin/sloppy'), 'lsp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     env=dict(os.environ, SLOPPY_LIB=str(root / 'lib')))
seq = 0


def send(method, params, request=False):
    global seq
    msg = dict(jsonrpc='2.0', method=method, params=params)
    if request:
        seq += 1
        msg['id'] = seq
    b = json.dumps(msg).encode()
    p.stdin.write(b'Content-Length: %d\r\n\r\n' % len(b) + b)
    p.stdin.flush()
    if not request:
        return
    while True:
        headers = {}
        while True:
            line = p.stdout.readline()
            assert line, 'LSP stopped'
            if line == b'\r\n':
                break
            k, v = line.decode().split(':', 1)
            headers[k.lower()] = v.strip()
        msg = json.loads(p.stdout.read(int(headers['content-length'])))
        if msg.get('id') == seq:
            assert 'error' not in msg, msg
            return msg['result']


def check(ok):
    global checks
    assert ok
    checks += 1


with tempfile.TemporaryDirectory(prefix='build-lsp-') as scratch:
    try:
        caps = send('initialize', dict(capabilities={}, rootUri=Path(scratch).as_uri()), True)['capabilities']
        send('initialized', {})
        uri = (Path(scratch) / 'build.jo').as_uri()
        version = 0

        def text(src):
            global version
            version += 1
            if version == 1:
                send('textDocument/didOpen', dict(textDocument=dict(uri=uri, languageId='sloppy', version=version, text=src)))
            else:
                send('textDocument/didChange', dict(textDocument=dict(uri=uri, version=version), contentChanges=[dict(text=src)]))

        def at(src, off):
            prefix = src[:off]
            return dict(textDocument=dict(uri=uri), position=dict(line=prefix.count('\n'), character=off-prefix.rfind('\n')-1))

        def complete(src):
            off = src.index('|')
            src = src.replace('|', '')
            text(src)
            return {x['label']: x['kind'] for x in send('textDocument/completion', at(src, off), True)['items']}

        check('build' not in complete('x = bu|\n'))
        check(complete('bu|\n').get('build') == 14)
        check('build' not in complete('bu|: int = 1\n'))
        check(complete('build = 1\nx = bu|\n').get('build') == 6)
        check(complete('struct Hall:\n    build: int\nh = Hall()\nprint(h.bu|)\n').get('build') == 5)
        src = 'struct Hall:\n    build: int\nbuild = 1\nh = Hall(build = build)\nprint(h.build)\n'
        text(src)
        data = send('textDocument/semanticTokens/full', dict(textDocument=dict(uri=uri)), True)['data']
        line = col = 0
        tokens = []
        lines = src.splitlines()
        types = caps['semanticTokensProvider']['legend']['tokenTypes']
        for i in range(0, len(data), 5):
            dl, dc, size, kind, mods = data[i:i+5]
            line += dl
            col = dc if dl else col+dc
            if lines[line][col:col+size] == 'build':
                tokens.append(types[kind])
        check(tokens.count('property') == 3 and tokens.count('variable') == 2)
        src = 'foo = 1\nprint(foo)\n'
        text(src)
        params = at(src, 0)
        params['newName'] = 'build'
        edits = send('textDocument/rename', params, True)['changes'][uri]
        check(len(edits) == 2 and all(e['newText'] == 'build' for e in edits))
        src = 'build: int = 1\nprint(build)\n'
        text(src)
        symbols = send('textDocument/documentSymbol', dict(textDocument=dict(uri=uri)), True)
        check(any(x['name'] == 'build' for x in symbols))
        send('shutdown', {}, True)
        send('exit', {})
        p.wait(timeout=5)
    finally:
        if p.poll() is None:
            p.terminate()
            p.wait(timeout=5)
print(f'build LSP: {checks} passed, 0 failed')
