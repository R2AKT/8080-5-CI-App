// errorlens.ts — inline-ошибки ассемблера в конце строки (decorations).
import * as vscode from 'vscode';
import { AsmErrorInfo } from './assembler';

/**
 * Показывает ошибки/предупреждения ассемблера как inline-текст в конце строки.
 * Использует TextEditorDecorations (не зависит от сторонних расширений).
 */
export class ErrorLens {
  private decorationType: vscode.TextEditorDecorationType;
  private warningType: vscode.TextEditorDecorationType;
  private editor: vscode.TextEditor | undefined;

  constructor() {
    this.decorationType = vscode.window.createTextEditorDecorationType({
      after: {
        color: '#f44747',
        fontStyle: 'italic',
      },
      isWholeLine: false,
    });
    this.warningType = vscode.window.createTextEditorDecorationType({
      after: {
        color: '#cca700',
        fontStyle: 'italic',
      },
      isWholeLine: false,
    });
  }

  /** Обновить decorations для активного редактора. */
  update(errors: AsmErrorInfo[], warnings: AsmErrorInfo[], showWarnings: boolean): void {
    this.editor = vscode.window.activeTextEditor;
    if (!this.editor) return;

    const errorDecos: vscode.DecorationOptions[] = [];
    const warnDecos: vscode.DecorationOptions[] = [];

    for (const e of errors) {
      const line = Math.max(0, e.line - 1); // 1-based → 0-based
      const range = new vscode.Range(line, this.editor.document.lineAt(line).text.length, line, this.editor.document.lineAt(line).text.length);
      errorDecos.push({
        range,
        hoverMessage: e.message,
        renderOptions: {
          after: {
            contentText: ` ⚡ ${e.message}`,
            color: '#f44747',
            fontStyle: 'italic',
          },
        },
      });
    }

    if (showWarnings) {
      for (const w of warnings) {
        const line = Math.max(0, w.line - 1);
        const range = new vscode.Range(line, this.editor.document.lineAt(line).text.length, line, this.editor.document.lineAt(line).text.length);
        warnDecos.push({
          range,
          hoverMessage: w.message,
          renderOptions: {
            after: {
              contentText: ` ⚠ ${w.message}`,
              color: '#cca700',
              fontStyle: 'italic',
            },
          },
        });
      }
    }

    this.editor.setDecorations(this.decorationType, errorDecos);
    this.editor.setDecorations(this.warningType, warnDecos);
  }

  /** Очистить все decorations. */
  clear(): void {
    if (this.editor) {
      this.editor.setDecorations(this.decorationType, []);
      this.editor.setDecorations(this.warningType, []);
    }
  }

  dispose(): void {
    this.decorationType.dispose();
    this.warningType.dispose();
  }
}
