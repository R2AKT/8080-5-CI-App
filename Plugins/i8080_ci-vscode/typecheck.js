// typecheck.js — полноценная проверка типов через TS-компилятор API.
const fs = require('fs');
const path = require('path');

const VSCODE_APP = 'C:\\Users\\Wiener\\AppData\\Local\\Programs\\Microsoft VS Code\\7debcd0e2a\\resources\\app';
const ts = require(path.join(VSCODE_APP, 'extensions', 'node_modules', 'typescript', 'lib', 'typescript.js'));
const vscodeDts = path.join(VSCODE_APP, 'out', 'vscode-dts', 'vscode.d.ts');

const pluginDir = __dirname;
const srcDir = path.join(pluginDir, 'src');
const tsFiles = fs.readdirSync(srcDir).filter((f) => f.endsWith('.ts')).map((f) => path.join(srcDir, f));
// Локальные декларации (vscode + node-globals)
const typesDir = path.join(pluginDir, 'types');
const dtsFiles = fs.existsSync(typesDir)
  ? fs.readdirSync(typesDir).filter((f) => f.endsWith('.d.ts')).map((f) => path.join(typesDir, f))
  : [];
const allFiles = tsFiles.concat(dtsFiles);

// Создаём декларацию для модуля 'vscode', указывающую на vscode.d.ts
if (!fs.existsSync(typesDir)) fs.mkdirSync(typesDir, { recursive: true });
const vscodeModDir = path.join(typesDir, 'vscode');
if (!fs.existsSync(vscodeModDir)) fs.mkdirSync(vscodeModDir, { recursive: true });
fs.writeFileSync(path.join(vscodeModDir, 'index.d.ts'),
  `/// <reference path="${vscodeDts.replace(/\\/g, '/')}" />\n`, 'utf-8');

const compilerOptions = {
  module: ts.ModuleKind.CommonJS,
  target: ts.ScriptTarget.ES2021,
  lib: ['lib.es2021.d.ts'],
  strict: true,
  esModuleInterop: true,
  skipLibCheck: true,
  noEmit: true,
  typeRoots: [typesDir],
  paths: { 'vscode': [path.join(typesDir, 'vscode', 'index.d.ts')] },
};

const program = ts.createProgram({
  rootNames: allFiles,
  options: compilerOptions,
});

const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length === 0) {
  console.log('TYPECHECK: OK — ошибок типов нет.');
} else {
  console.log(`TYPECHECK: ${diagnostics.length} ошибок/предупреждений:`);
  for (const d of diagnostics) {
    if (d.file) {
      const { line, character } = d.file.getLineAndCharacterOfPosition(d.start);
      console.log(`  ${d.file.fileName}:${line + 1}:${character + 1} - ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`);
    } else {
      console.log(`  ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`);
    }
  }
}
