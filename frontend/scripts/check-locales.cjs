// Validate translation coverage and placeholders without executing catalog code.
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const vi = JSON.parse(read('src/vi.json'));
const zh = {};
const problems = [];
const source = ts.createSourceFile('zh-CN.ts', read('src/zh-CN.ts'), ts.ScriptTarget.Latest, true);
function collect(node) {
  if (ts.isPropertyAssignment(node)) {
    const key = node.name.text;
    if (!ts.isStringLiteralLike(node.initializer)) problems.push(`zh-CN: non-text translation for ${key}`);
    else {
      if (Object.hasOwn(zh, key)) problems.push(`zh-CN: duplicate key ${key}`);
      zh[key] = node.initializer.text;
    }
  }
  ts.forEachChild(node, collect);
}
collect(source);
const placeholders = text => [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort().join(',');
for (const [language, catalog] of [['vi', vi], ['zh-CN', zh]]) {
  for (const [key, value] of Object.entries(catalog)) {
    if (typeof value !== 'string' || !value.trim()) problems.push(`${language}: empty translation for ${key}`);
    else if (placeholders(key) !== placeholders(value)) problems.push(`${language}: placeholder mismatch for ${key}`);
  }
}
const required = new Set(['Channel Name', 'Channel ID', 'Channel URL', 'Search Keyword', 'Created Date',
  'Channel Age (Days)', 'Subscribers', 'Total Views', 'Total Videos', 'Latest Video', 'Country',
  'Email', 'Facebook', 'Other Contacts', 'Hidden', 'Not disclosed']);
const files = ['src/i18n.tsx', 'src/App.tsx', ...fs.readdirSync(path.join(root, 'src/components'))
  .filter(file => file.endsWith('.tsx')).map(file => `src/components/${file}`)];
for (const file of files) {
  const tree = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  function visit(node) {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 't'
        && node.arguments[0] && ts.isStringLiteralLike(node.arguments[0]) && node.arguments[0].text) {
      required.add(node.arguments[0].text);
    }
    ts.forEachChild(node, visit);
  }
  visit(tree);
}
for (const key of required) {
  for (const [language, catalog] of [['vi', vi], ['zh-CN', zh]]) {
    if (!Object.hasOwn(catalog, key)) problems.push(`${language}: missing ${key}`);
  }
}
if (problems.length) {
  process.stderr.write(problems.join('\n') + '\n');
  process.exitCode = 1;
} else {
  process.stdout.write(`Locale validation passed: ${required.size} required keys; Vietnamese and Simplified Chinese placeholders match.\n`);
}
