// No editor dependencies: exercise the grammar's build/parameter rules and the site's tokenizer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const grammar = JSON.parse(fs.readFileSync(path.join(root, 'editors/vscode/syntaxes/sloppy.tmLanguage.json'), 'utf8'));
const rule = grammar.repository.declaration.patterns.find(p => p.captures?.['1']?.name === 'keyword.other.build.sloppy');
const build = new RegExp(rule.match);
const yes = ['build:', '  build :  # options', '\tbuild:\t', 'build:\r'];
const no = ['build = 1', 'build: int', 'build: f64 = 1', 'w.build:', 'print(build)', 'rebuild:', 'x = "build:"', '# build:'];
for (const line of yes) assert(build.test(line), line);
for (const line of no) assert(!build.test(line), line);
for (const rule of grammar.repository.parameter.patterns) {
  const re = new RegExp(rule.match);
  assert(re.test(rule.match.startsWith('^') ? '  build: int' : '(build: int)'), rule.match);
}
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, 'tools/playground/highlight.js'), 'utf8'), context);
for (const line of yes) assert(context.sloppyHighlight(line).includes('<span class="k">build</span>'), line);
for (const line of no) assert(!context.sloppyHighlight(line).includes('<span class="k">build</span>'), line);
assert(!context.sloppyHighlight('"""\nbuild:\n"""').includes('<span class="k">build</span>'));
console.log('build highlighting: 27 checks passed');
