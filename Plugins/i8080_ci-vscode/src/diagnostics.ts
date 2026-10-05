// diagnostics.ts — отображение ошибок/предупреждений ассемблера в VS Code.
import * as vscode from 'vscode';
import { AssembleResult, AsmErrorInfo } from './assembler';

const DIAGNOSTIC_COLLECTION_NAME = 'i8080-asm';

let collection: vscode.DiagnosticCollection | undefined;

export function getDiagnosticsCollection(): vscode.DiagnosticCollection {
  if (!collection) {
    collection = vscode.languages.createDiagnosticCollection(DIAGNOSTIC_COLLECTION_NAME);
  }
  return collection;
}

function toDiagnostic(e: AsmErrorInfo, uri: vscode.Uri): vscode.Diagnostic | undefined {
  // line/col из ассемблера — 1-based; VS Code — 0-based
  const line = Math.max(0, (e.line ?? 1) - 1);
  const col = Math.max(0, (e.col ?? 1) - 1);
  const range = new vscode.Range(line, col, line, col + 1);
  const severity = e.severity === 'warning'
    ? vscode.DiagnosticSeverity.Warning
    : vscode.DiagnosticSeverity.Error;
  const diag = new vscode.Diagnostic(range, e.message, severity);
  diag.source = 'i8080-5 CI';
  if (e.source) {
    diag.code = e.source;
  }
  return diag;
}

/** Устанавливает diagnostics для файла по результату сборки. */
export function setDiagnostics(uri: vscode.Uri, result: AssembleResult, showWarnings: boolean): void {
  const col = getDiagnosticsCollection();
  const diags: vscode.Diagnostic[] = [];

  for (const e of result.errors) {
    const d = toDiagnostic(e, uri);
    if (d) diags.push(d);
  }
  if (showWarnings) {
    for (const w of result.warnings) {
      const d = toDiagnostic(w, uri);
      if (d) diags.push(d);
    }
  }

  col.set(uri, diags);
}

/** Очищает diagnostics для файла. */
export function clearDiagnostics(uri: vscode.Uri): void {
  getDiagnosticsCollection().delete(uri);
}

/** Очищает все diagnostics расширения. */
export function clearAllDiagnostics(): void {
  getDiagnosticsCollection().clear();
}
