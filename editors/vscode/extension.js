// The Sloppy extension: a language client for `sloppy lsp` (written out here instead of depending on
// vscode-languageclient: the protocol subset it needs is small), and commands to run files.

const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

let client = null;
let output = null;
let diagnostics = null;
let restarts = 0;
let restartTimer = null;
let deactivated = false;

// ---- the server connection (JSON-RPC with Content-Length framing) ----

class Connection {
    constructor(command, onNotification, onExit) {
        this.nextId = 1;
        this.pending = new Map();
        this.buffer = Buffer.alloc(0);
        this.onNotification = onNotification;
        this.onExit = onExit;
        this.closed = false;
        this.ready = false;         // (initialized: documents can be sent)
        // (in the first workspace folder: new unsaved files' imports are relative to it)
        const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0].uri.scheme === 'file' ? vscode.workspace.workspaceFolders[0].uri.fsPath : undefined;
        this.proc = cp.spawn(command, ['lsp'], { stdio: ['pipe', 'pipe', 'pipe'], cwd: folder });
        this.proc.stdout.on('data', (chunk) => this.receive(chunk));
        this.proc.stderr.on('data', (chunk) => output.append(chunk.toString()));
        this.proc.stdin.on('error', (err) => output.appendLine(`sloppy lsp: ${err.message}`));
        this.proc.on('error', (err) => {
            output.appendLine(`sloppy: cannot start '${command} lsp': ${err.message}`);
            vscode.window.showErrorMessage(`Sloppy: cannot start the language server (${command}). Set sloppy.path to the sloppy compiler.`);
            this.close(null, null, false);
        });
        this.proc.on('exit', (code, signal) => this.close(code, signal, true));
    }

    // (once, however it ended: a failed start has no exit)
    close(code, signal, ran) {
        if (this.closed) return;
        this.closed = true;
        for (const [, p] of this.pending) p.resolve(null);
        this.pending.clear();
        this.onExit(code, signal, ran);
    }

    receive(chunk) {
        this.buffer = Buffer.concat([this.buffer, chunk]);
        for (;;) {
            const end = this.buffer.indexOf('\r\n\r\n');
            if (end < 0) return;
            const header = this.buffer.slice(0, end).toString('ascii');
            const m = /content-length:\s*(\d+)/i.exec(header);
            const n = m ? parseInt(m[1], 10) : 0;
            if (this.buffer.length < end + 4 + n) return;
            const body = this.buffer.slice(end + 4, end + 4 + n).toString('utf8');
            this.buffer = this.buffer.slice(end + 4 + n);
            let msg;
            try { msg = JSON.parse(body); } catch (e) { continue; }
            if (msg.id !== undefined && msg.method === undefined) {
                const p = this.pending.get(msg.id);
                if (!p) continue;
                this.pending.delete(msg.id);
                if (msg.error) p.reject(new Error(msg.error.message));
                else p.resolve(msg.result);
            } else if (msg.method) {
                this.onNotification(msg.method, msg.params);
            }
        }
    }

    send(msg) {
        if (this.closed || !this.proc.stdin.writable) return;
        const body = Buffer.from(JSON.stringify(msg), 'utf8');
        this.proc.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
        this.proc.stdin.write(body);
    }

    request(method, params, token) {
        if (this.closed) return Promise.resolve(null);
        const id = this.nextId++;
        return new Promise((resolve, reject) => {
            let sub = null;
            const done = (f) => (v) => { if (sub) sub.dispose(); f(v); };
            this.pending.set(id, { resolve: done(resolve), reject: done(reject) });
            this.send({ jsonrpc: '2.0', id, method, params });
            if (token) sub = token.onCancellationRequested(() => {
                if (this.pending.has(id)) this.send({ jsonrpc: '2.0', method: '$/cancelRequest', params: { id } });
            });
        });
    }

    notify(method, params) { this.send({ jsonrpc: '2.0', method, params }); }

    stop() {
        const proc = this.proc;
        this.request('shutdown', null).then(() => this.notify('exit', null), () => {});
        setTimeout(() => proc.kill(), 1000);
    }
}

// ---- conversions between the protocol and VS Code ----

const toPosition = (p) => new vscode.Position(p.line, p.character);
const toRange = (r) => new vscode.Range(toPosition(r.start), toPosition(r.end));
const toLocation = (l) => new vscode.Location(vscode.Uri.parse(l.uri), toRange(l.range));
const fromPosition = (p) => ({ line: p.line, character: p.character });
const textDocument = (doc) => ({ uri: doc.uri.toString() });
const at = (doc, pos) => ({ textDocument: textDocument(doc), position: fromPosition(pos) });

function toSymbol(s) {
    // (LSP symbol kinds start at 1, VS Code's at 0)
    const sym = new vscode.DocumentSymbol(s.name, s.detail || '', s.kind - 1, toRange(s.range), toRange(s.selectionRange));
    sym.children = (s.children || []).map(toSymbol);
    return sym;
}

const toFolder = (f) => ({ uri: f.uri.toString(), name: f.name });

function toSymbolInformation(s) {
    return new vscode.SymbolInformation(s.name, s.kind - 1, s.containerName || '', toLocation(s.location));
}

function toWorkspaceEdit(we) {
    const edit = new vscode.WorkspaceEdit();
    for (const uri of Object.keys(we.changes || {})) {
        for (const e of we.changes[uri]) edit.replace(vscode.Uri.parse(uri), toRange(e.range), e.newText);
    }
    return edit;
}

// (fired when the server has checked something again: names' kinds and the type hints may have changed)
const resultsChanged = new vscode.EventEmitter();

// semantic tokens: the server's legend (its capabilities say the same)
const semanticLegend = new vscode.SemanticTokensLegend(
    ['namespace', 'type', 'struct', 'enum', 'parameter', 'variable', 'property', 'enumMember', 'function'],
    ['declaration', 'readonly', 'defaultLibrary']);

function onNotification(method, params) {
    if (method === 'textDocument/publishDiagnostics') {
        // (not for an older version of an open document)
        const doc = vscode.workspace.textDocuments.find((d) => d.uri.toString() === params.uri);
        if (doc && typeof params.version === 'number' && params.version < doc.version) return;
        resultsChanged.fire();
        const ds = params.diagnostics.map((d) => {
            const diag = new vscode.Diagnostic(toRange(d.range), d.message, (d.severity || 1) - 1);
            diag.source = d.source || 'sloppy';
            return diag;
        });
        diagnostics.set(vscode.Uri.parse(params.uri), ds);
    }
}

// ---- which sloppy ----

const os = require('os');
const https = require('https');
const zlib = require('zlib');
const crypto = require('crypto');

const RELEASES = 'https://github.com/david-andrew/sloppy-lang/releases/latest/download/';
const windows = process.platform === 'win32';
const EXE = windows ? 'sloppy.exe' : 'sloppy';
const installDir = () => process.env.SLOPPY_INSTALL ||
    (windows ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'sloppy') : path.join(os.homedir(), '.sloppy'));

const isExe = (p) => { try { fs.accessSync(p, fs.constants.X_OK); return fs.statSync(p).isFile(); } catch (e) { return false; } };

// the sloppy compiler to use, or null: the setting, the Sloppy repository's own (working on Sloppy), the
// PATH, or where the install script (and this extension) put it
function findSloppy() {
    const configured = vscode.workspace.getConfiguration('sloppy').get('path');
    if (configured) return configured;
    for (const folder of vscode.workspace.workspaceFolders || []) {
        const p = path.join(folder.uri.fsPath, 'bin', EXE);
        if (isExe(p) && fs.existsSync(path.join(folder.uri.fsPath, 'lib', 'core', 'rt.jo'))) return p;
    }
    for (const dir of (process.env.PATH || '').split(path.delimiter)) {
        if (dir && isExe(path.join(dir, EXE))) return path.join(dir, EXE);
    }
    const installed = path.join(installDir(), 'bin', EXE);
    return isExe(installed) ? installed : null;
}

function sloppyCommand() { return findSloppy() || 'sloppy'; }

// ---- installing sloppy (as tools/install.sh does: the latest release, into ~/.sloppy) ----

function download(url, redirects = 5) {
    return new Promise((resolve, reject) => {
        https.get(url, { headers: { 'User-Agent': 'sloppy-vscode' } }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirects > 0) {
                res.resume();
                resolve(download(new URL(res.headers.location, url).toString(), redirects - 1));
                return;
            }
            if (res.statusCode !== 200) { res.resume(); reject(new Error(`${url}: HTTP ${res.statusCode}`)); return; }
            const chunks = [];
            res.on('data', (c) => chunks.push(c));
            res.on('end', () => resolve(Buffer.concat(chunks)));
            res.on('error', reject);
        }).on('error', reject);
    });
}

// the files of a .tar (name -> {data, mode}); ustar, with pax headers for long names
function untar(buf) {
    const files = [];
    let off = 0, paxPath = null;
    const str = (a, b) => buf.toString('utf8', a, b).replace(/\0.*$/s, '');
    while (off + 512 <= buf.length) {
        if (buf[off] === 0) break;
        let name = str(off, off + 100);
        const mode = parseInt(str(off + 100, off + 108).trim() || '644', 8);
        const size = parseInt(str(off + 124, off + 136).trim() || '0', 8);
        const type = String.fromCharCode(buf[off + 156] || 48);
        const prefix = str(off + 345, off + 500);
        if (prefix) name = prefix + '/' + name;
        const data = buf.subarray(off + 512, off + 512 + size);
        off += 512 + Math.ceil(size / 512) * 512;
        if (type === 'x') {
            const m = /\d+ path=([^\n]*)\n/.exec(data.toString('utf8'));
            paxPath = m ? m[1] : null;
            continue;
        }
        if (type === 'g') continue;
        if (paxPath) { name = paxPath; paxPath = null; }
        if (type === '0' || type === '\0') files.push({ name, mode, data });
    }
    return files;
}

// (Windows: tools/install.ps1 does it, in PowerShell)
function installSloppyWindows() {
    return vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'Installing Sloppy' }, () => new Promise((resolve) => {
        const ps = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
        const p = cp.spawn(ps, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', 'irm https://sloppy-lang.org/install.ps1 | iex'], { windowsHide: true });
        let log = '';
        p.stdout.on('data', (d) => { log += d; });
        p.stderr.on('data', (d) => { log += d; });
        p.on('error', (e) => { vscode.window.showErrorMessage(`Could not install Sloppy: ${e.message}`); resolve(false); });
        p.on('exit', (code) => {
            output.appendLine(log);
            if (code === 0 && isExe(path.join(installDir(), 'bin', EXE))) {
                vscode.window.showInformationMessage(`Sloppy was installed to ${path.join(installDir(), 'bin')} (and added to your PATH for new terminals).`);
                resolve(true);
            } else {
                vscode.window.showErrorMessage('Could not install Sloppy (see the Sloppy output). In PowerShell: irm https://sloppy-lang.org/install.ps1 | iex');
                resolve(false);
            }
        });
    }));
}

// the release's archive for this system (as tools/install.sh picks it), or null
function releaseAsset() {
    if (process.platform === 'linux' && process.arch === 'x64') return 'sloppy-linux-x86_64.tar.gz';
    if (process.platform === 'linux' && process.arch === 'arm64') return 'sloppy-linux-arm64.tar.gz';
    if (process.platform === 'darwin' && process.arch === 'arm64') return 'sloppy-macos-arm64.tar.gz';
    return null;
}

async function installSloppy() {
    if (windows && process.arch === 'x64') return installSloppyWindows();
    const asset = releaseAsset();
    if (!asset) {
        vscode.window.showErrorMessage('Sloppy runs on Linux (x86-64, arm64), macOS (Apple silicon) and Windows (x86-64). (Its programs run in any browser: try the playground.)');
        return false;
    }
    try {
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'Installing Sloppy' }, async (progress) => {
            progress.report({ message: 'downloading the latest release\u2026' });
            const tgz = await download(RELEASES + asset);
            const sum = (await download(RELEASES + asset + '.sha256')).toString().split(/\s+/)[0];
            if (crypto.createHash('sha256').update(tgz).digest('hex') !== sum) throw new Error('the download is damaged (checksum)');
            progress.report({ message: 'unpacking\u2026' });
            const files = untar(zlib.gunzipSync(tgz));
            const dest = installDir();
            const tmp = dest + '.new';
            fs.rmSync(tmp, { recursive: true, force: true });
            for (const f of files) {
                const rel = f.name.split('/').slice(1).join('/');          // (without sloppy-<version>/)
                if (!rel || rel.split('/').includes('..')) continue;
                const p = path.join(tmp, rel);
                fs.mkdirSync(path.dirname(p), { recursive: true });
                fs.writeFileSync(p, f.data, { mode: f.mode & 0o777 });
            }
            if (!isExe(path.join(tmp, 'bin', 'sloppy'))) throw new Error('the release does not hold bin/sloppy');
            fs.rmSync(dest + '.old', { recursive: true, force: true });
            if (fs.existsSync(dest)) fs.renameSync(dest, dest + '.old');
            fs.renameSync(tmp, dest);
            fs.rmSync(dest + '.old', { recursive: true, force: true });
        });
    } catch (e) {
        vscode.window.showErrorMessage(`Could not install Sloppy: ${e.message}`);
        return false;
    }
    const bin = path.join(installDir(), 'bin');
    vscode.window.showInformationMessage(`Sloppy was installed to ${bin.replace(os.homedir(), '~')}. For terminals, add it to your PATH (or run the install script, which does): curl -fsSL https://sloppy-lang.org/install | bash`);
    return true;
}

// no sloppy: offer to install it
async function offerInstall() {
    const choice = await vscode.window.showInformationMessage(
        'Sloppy is not installed: the language server and the run commands need the sloppy compiler.',
        'Install Sloppy', 'Set sloppy.path', 'Not now');
    if (choice === 'Install Sloppy') {
        if (await installSloppy()) vscode.commands.executeCommand('sloppy.restartServer');
    } else if (choice === 'Set sloppy.path') {
        vscode.commands.executeCommand('workbench.action.openSettings', 'sloppy.path');
    }
}

// ---- starting, stopping ----

// (new unsaved files too: they are checked like files, their imports relative to the first workspace folder)
function isSloppy(doc) { return doc.languageId === 'sloppy' && (doc.uri.scheme === 'file' || doc.uri.scheme === 'untitled'); }

function start() {
    clearTimeout(restartTimer);
    restartTimer = null;
    if (deactivated || client) return;
    if (!findSloppy()) {
        offerInstall();
        return;
    }
    const conn = new Connection(sloppyCommand(), (method, params) => {
        if (client === conn) onNotification(method, params);
    }, (code, signal, ran) => {
        if (client !== conn) return;
        client = null;
        if (ran) output.appendLine(`sloppy lsp exited (${signal || code})`);
        if (ran && restarts < 5 && !deactivated) {
            restarts++;
            restartTimer = setTimeout(start, 500 * restarts);
        }
    });
    client = conn;
    conn.request('initialize', {
        processId: process.pid,
        rootUri: vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.toString() : null,
        workspaceFolders: (vscode.workspace.workspaceFolders || []).map(toFolder),
        capabilities: {},
    }).then((r) => {
        if (client !== conn || !r) return;
        conn.notify('initialized', {});
        conn.ready = true;
        for (const doc of vscode.workspace.textDocuments) open(doc);
        resultsChanged.fire();
    }, (err) => output.appendLine(`initialize failed: ${err.message}`));
}

// the server, when it is ready for documents
function ready() { return client && client.ready ? client : null; }

function open(doc) {
    if (!ready() || !isSloppy(doc)) return;
    client.notify('textDocument/didOpen', {
        textDocument: { uri: doc.uri.toString(), languageId: 'sloppy', version: doc.version, text: doc.getText() },
    });
}

// a request, or null when there is no server (or it failed)
async function ask(method, params, token) {
    if (!ready()) return null;
    try {
        return await client.request(method, params, token);
    } catch (e) {
        return null;
    }
}

// ---- running ----

function runInTerminal(args) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'sloppy') return;
    const doc = editor.document;
    if (!findSloppy()) {
        offerInstall();
        return;
    }
    doc.save().then((saved) => {
        // (a new file is saved as another document: the active one)
        if (!saved) return;
        const file = doc.isUntitled ? vscode.window.activeTextEditor && vscode.window.activeTextEditor.document : doc;
        if (!file || file.uri.scheme !== 'file') return;
        let term = vscode.window.terminals.find((t) => t.name === 'Sloppy');
        if (!term) term = vscode.window.createTerminal('Sloppy');
        term.show(true);
        const words = [sloppyCommand(), ...args, file.uri.fsPath];
        const shell = (vscode.env.shell || '').toLowerCase();
        if (/cmd(\.exe)?$/.test(shell)) {
            term.sendText(words.map((s) => `"${s}"`).join(' '));
        } else if (/pwsh|powershell/.test(shell) || (windows && !/(ba|z|fi)?sh(\.exe)?$/.test(shell))) {
            // (PowerShell: '' inside quotes, and & to run a quoted command)
            term.sendText('& ' + words.map((s) => `'${s.replace(/'/g, "''")}'`).join(' '));
        } else {
            term.sendText(words.map((s) => `'${s.replace(/'/g, `'\\''`)}'`).join(' '));
        }
    });
}

// sloppy new: a project to start from, in a new folder, opened
async function newProject() {
    if (!findSloppy()) {
        offerInstall();
        return;
    }
    const kinds = [
        { label: 'game', description: 'the smallest game: a window, update and draw' },
        { label: 'arcade', description: 'a 2D arcade game: a title menu, a score, a best score kept, sounds' },
        { label: '3d', description: 'a first-person 3D game: mouse look, walking, jumping, shooting' },
        { label: 'program', description: 'a program for the terminal, with a test' },
    ];
    const kind = await vscode.window.showQuickPick(kinds, { title: 'New Sloppy project', placeHolder: 'What to start from' });
    if (!kind) return;
    const name = await vscode.window.showInputBox({
        title: 'New Sloppy project', prompt: 'Its name (the folder, and its main file)', value: kind.label === 'program' ? 'my_program' : 'my_game',
        validateInput: (v) => (/^[A-Za-z_][A-Za-z0-9_-]*$/.test(v) ? null : 'letters, digits, _ and -'),
    });
    if (!name) return;
    const where = await vscode.window.showOpenDialog({ canSelectFolders: true, canSelectFiles: false, openLabel: 'Make it here', title: `Where to make the folder ${name}` });
    if (!where || where.length === 0) return;
    const dir = path.join(where[0].fsPath, name);
    cp.execFile(sloppyCommand(), ['new', dir, kind.label], (err, stdout, stderr) => {
        if (err) {
            vscode.window.showErrorMessage(`sloppy new: ${(stderr || err.message).trim()}`);
            return;
        }
        // (the folder opened: in this window, or a new one when a folder is open here)
        vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(dir), { forceNewWindow: !!vscode.workspace.workspaceFolders });
    });
}

// ---- the extension ----

function activate(context) {
    output = vscode.window.createOutputChannel('Sloppy');
    diagnostics = vscode.languages.createDiagnosticCollection('sloppy');
    context.subscriptions.push(output, diagnostics, resultsChanged);
    const selector = [{ language: 'sloppy', scheme: 'file' }, { language: 'sloppy', scheme: 'untitled' }];
    // (files changed on disk, not in an editor: the programs using them are checked again)
    const watcher = vscode.workspace.createFileSystemWatcher('**/*.jo');
    const changed = (type) => (uri) => {
        if (!ready() || vscode.workspace.textDocuments.some((d) => d.uri.toString() === uri.toString())) return;
        client.notify('workspace/didChangeWatchedFiles', { changes: [{ uri: uri.toString(), type }] });
    };
    const L = vscode.languages;

    context.subscriptions.push(
        watcher,
        watcher.onDidCreate(changed(1)),
        watcher.onDidChange(changed(2)),
        watcher.onDidDelete(changed(3)),
        vscode.workspace.onDidOpenTextDocument(open),
        vscode.workspace.onDidChangeTextDocument((e) => {
            if (!ready() || !isSloppy(e.document) || e.contentChanges.length === 0) return;
            client.notify('textDocument/didChange', {
                textDocument: { uri: e.document.uri.toString(), version: e.document.version },
                contentChanges: [{ text: e.document.getText() }],
            });
        }),
        vscode.workspace.onDidSaveTextDocument((doc) => {
            if (ready() && isSloppy(doc)) client.notify('textDocument/didSave', { textDocument: textDocument(doc) });
        }),
        vscode.workspace.onDidCloseTextDocument((doc) => {
            if (isSloppy(doc)) diagnostics.delete(doc.uri);
            if (!ready() || !isSloppy(doc)) return;
            client.notify('textDocument/didClose', { textDocument: textDocument(doc) });
        }),

        L.registerHoverProvider(selector, {
            async provideHover(doc, pos, token) {
                const r = await ask('textDocument/hover', at(doc, pos), token);
                if (!r || !r.contents) return null;
                const md = new vscode.MarkdownString(r.contents.value);
                return new vscode.Hover(md);
            },
        }),
        L.registerDefinitionProvider(selector, {
            async provideDefinition(doc, pos, token) {
                const r = await ask('textDocument/definition', at(doc, pos), token);
                if (!r) return null;
                return Array.isArray(r) ? r.map(toLocation) : toLocation(r);
            },
        }),
        L.registerReferenceProvider(selector, {
            async provideReferences(doc, pos, ctx, token) {
                const r = await ask('textDocument/references', { ...at(doc, pos), context: { includeDeclaration: ctx.includeDeclaration } }, token);
                return (r || []).map(toLocation);
            },
        }),
        L.registerDocumentHighlightProvider(selector, {
            async provideDocumentHighlights(doc, pos, token) {
                const r = await ask('textDocument/documentHighlight', at(doc, pos), token);
                return (r || []).map((h) => new vscode.DocumentHighlight(toRange(h.range)));
            },
        }),
        L.registerRenameProvider(selector, {
            async prepareRename(doc, pos, token) {
                if (!client) throw new Error('the Sloppy language server is not running');
                const r = await client.request('textDocument/prepareRename', at(doc, pos), token);
                return toRange(r);
            },
            async provideRenameEdits(doc, pos, newName, token) {
                if (!client) return null;
                const r = await client.request('textDocument/rename', { ...at(doc, pos), newName }, token);
                return r ? toWorkspaceEdit(r) : null;
            },
        }),
        L.registerCompletionItemProvider(selector, {
            async provideCompletionItems(doc, pos, token) {
                const r = await ask('textDocument/completion', at(doc, pos), token);
                if (!r) return null;
                const items = (r.items || r).map((c) => {
                    // (LSP completion kinds start at 1, VS Code's at 0)
                    const item = new vscode.CompletionItem(c.label, (c.kind || 1) - 1);
                    item.detail = c.detail;
                    item.sortText = c.sortText;
                    return item;
                });
                return new vscode.CompletionList(items, !!r.isIncomplete);
            },
        }, '.'),
        L.registerSignatureHelpProvider(selector, {
            async provideSignatureHelp(doc, pos, token) {
                const r = await ask('textDocument/signatureHelp', at(doc, pos), token);
                if (!r || !r.signatures || r.signatures.length === 0) return null;
                const help = new vscode.SignatureHelp();
                help.signatures = r.signatures.map((s) => {
                    const info = new vscode.SignatureInformation(s.label, s.documentation ? new vscode.MarkdownString(s.documentation) : undefined);
                    info.parameters = (s.parameters || []).map((p) => new vscode.ParameterInformation(p.label));
                    return info;
                });
                help.activeSignature = r.activeSignature || 0;
                help.activeParameter = r.activeParameter || 0;
                return help;
            },
        }, { triggerCharacters: ['(', ','], retriggerCharacters: [','] }),
        L.registerInlayHintsProvider(selector, {
            onDidChangeInlayHints: resultsChanged.event,
            async provideInlayHints(doc, range, token) {
                const r = await ask('textDocument/inlayHint', { textDocument: textDocument(doc), range: { start: fromPosition(range.start), end: fromPosition(range.end) } }, token);
                return (r || []).map((h) => {
                    const hint = new vscode.InlayHint(toPosition(h.position), h.label, vscode.InlayHintKind.Type);
                    hint.paddingLeft = !!h.paddingLeft;
                    return hint;
                });
            },
        }),
        L.registerDocumentSemanticTokensProvider(selector, {
            onDidChangeSemanticTokens: resultsChanged.event,
            async provideDocumentSemanticTokens(doc, token) {
                const r = await ask('textDocument/semanticTokens/full', { textDocument: textDocument(doc) }, token);
                return r && r.data ? new vscode.SemanticTokens(new Uint32Array(r.data)) : null;
            },
        }, semanticLegend),
        L.registerDocumentSymbolProvider(selector, {
            async provideDocumentSymbols(doc, token) {
                const r = await ask('textDocument/documentSymbol', { textDocument: textDocument(doc) }, token);
                return (r || []).map(toSymbol);
            },
        }),
        L.registerDocumentFormattingEditProvider(selector, {
            async provideDocumentFormattingEdits(doc, options, token) {
                const r = await ask('textDocument/formatting', { textDocument: textDocument(doc), options: { tabSize: options.tabSize, insertSpaces: options.insertSpaces } }, token);
                return (r || []).map((e) => vscode.TextEdit.replace(toRange(e.range), e.newText));
            },
        }),
        L.registerWorkspaceSymbolProvider({
            async provideWorkspaceSymbols(query, token) {
                const r = await ask('workspace/symbol', { query }, token);
                return (r || []).map(toSymbolInformation);
            },
        }),
        vscode.workspace.onDidChangeWorkspaceFolders((e) => {
            if (ready()) client.notify('workspace/didChangeWorkspaceFolders', { event: { added: e.added.map(toFolder), removed: e.removed.map(toFolder) } });
        }),

        vscode.commands.registerCommand('sloppy.run', () => runInTerminal([])),
        vscode.commands.registerCommand('sloppy.runWeb', () => runInTerminal(['--web'])),
        vscode.commands.registerCommand('sloppy.test', () => runInTerminal(['test'])),
        vscode.commands.registerCommand('sloppy.newProject', newProject),
        vscode.commands.registerCommand('sloppy.install', async () => {
            if (await installSloppy()) vscode.commands.executeCommand('sloppy.restartServer');
        }),
        vscode.commands.registerCommand('sloppy.restartServer', () => {
            restarts = 0;
            const old = client;
            client = null;
            if (old) old.stop();
            diagnostics.clear();
            start();
        }),
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('sloppy.path')) vscode.commands.executeCommand('sloppy.restartServer');
        }),
    );
    start();
}

function deactivate() {
    deactivated = true;
    clearTimeout(restartTimer);
    if (client) client.stop();
    client = null;
}

module.exports = { activate, deactivate };
