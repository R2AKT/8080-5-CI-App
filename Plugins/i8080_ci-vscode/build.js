// build.js — компиляция TypeScript плагина через бандл-TypeScript из VS Code.
// Не требует npm install (использует transpileModule, без type-resolution).
const fs = require('fs');
const path = require('path');

const VSCODE_APP = 'C:\\Users\\Wiener\\AppData\\Local\\Programs\\Microsoft VS Code\\7debcd0e2a\\resources\\app';
const ts = require(path.join(VSCODE_APP, 'extensions', 'node_modules', 'typescript', 'lib', 'typescript.js'));

const pluginDir = __dirname;
const srcDir = path.join(pluginDir, 'src');
const outDir = path.join(pluginDir, 'out');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const tsFiles = fs.readdirSync(srcDir).filter((f) => f.endsWith('.ts'));
console.log('TypeScript version:', ts.version);
console.log('Файлы:', tsFiles.join(', '));

let allDiagnostics = [];
const compilerOptions = {
  module: ts.ModuleKind.CommonJS,
  target: ts.ScriptTarget.ES2021,
  lib: ['lib.es2021.d.ts'],
  strict: true,
  esModuleInterop: true,
  skipLibCheck: true,
  sourceMap: true,
};

for (const file of tsFiles) {
  const full = path.join(srcDir, file);
  const source = fs.readFileSync(full, 'utf-8');
  const result = ts.transpileModule(source, {
    compilerOptions,
    reportDiagnostics: true,
    fileName: file,
  });

  const outName = file.replace(/\.ts$/, '.js');
  fs.writeFileSync(path.join(outDir, outName), result.outputText, 'utf-8');
  if (result.sourceMapText) {
    fs.writeFileSync(path.join(outDir, outName + '.map'), result.sourceMapText, 'utf-8');
  }
  console.log('  скомпилировано:', outName, `(${result.outputText.length} байт)`);

  if (result.diagnostics && result.diagnostics.length > 0) {
    for (const d of result.diagnostics) {
      const msg = ts.flattenDiagnosticMessageText(d.messageText, '\n');
      allDiagnostics.push(`${file}: ${msg}`);
    }
  }
}

if (allDiagnostics.length > 0) {
  console.log('\n=== ПРЕДУПРЕЖДЕНИЯ/ОШИБКИ ===');
  allDiagnostics.forEach((d) => console.log('  ', d));
} else {
  console.log('\nКомпиляция завершена без ошибок.');
}

console.log('\nСодержимое out/:');
fs.readdirSync(outDir).forEach((f) => console.log('  ', f));
