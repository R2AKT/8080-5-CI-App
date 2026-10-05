// codelens.ts — Code Lens: над строкой показываем адрес + имя метки из listing.
import * as vscode from 'vscode';
import { ListingEntry } from './assembler';

/**
 * Хранилище данных для Code Lens.
 * Заполняется после успешной сборки.
 */
export class CodeLensData {
  /** line (0-based) → { addr, label } */
  private lineMap: Map<number, { addr: number; label: string }> = new Map();
  private version = 0;

  /** Заполнить из listing + symbols. */
  populate(listing: ListingEntry[], symbols: Record<string, number>, document: vscode.TextDocument): void {
    this.lineMap.clear();

    // Строим mapping: source_line_text → addr (из listing)
    // Listing содержит source-строки без номера, поэтому сопоставляем по тексту
    const lines = document.getText().split(/\r?\n/);
    const lineToAddr = new Map<number, number>();

    // Простое сопоставление: ищем source-строки из listing в документе
    for (const entry of listing) {
      const src = entry.source.trim();
      if (!src) continue;
      // Ищем строку в документе (первое совпадение)
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim() === src) {
          lineToAddr.set(i, entry.addr);
          break;
        }
      }
    }

    // Определяем метки: строки, начинающиеся с имени + ":" или "::"
    const labelRe = /^([A-Za-z_@][A-Za-z0-9_@]*)\s*::?\s*(.*)/;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const m = line.match(labelRe);
      if (m) {
        const label = m[1];
        const addr = lineToAddr.get(i);
        if (addr !== undefined) {
          this.lineMap.set(i, { addr, label });
        } else if (symbols[label] !== undefined) {
          this.lineMap.set(i, { addr: symbols[label], label });
        }
      }
    }

    // Также показываем адрес для строк без меток (каждую строку кода)
    for (const [lineNum, addr] of lineToAddr) {
      if (!this.lineMap.has(lineNum)) {
        this.lineMap.set(lineNum, { addr, label: '' });
      }
    }

    this.version++;
  }

  getVersion(): number {
    return this.version;
  }

  getLensForLine(line: number): { addr: number; label: string } | undefined {
    return this.lineMap.get(line);
  }

  clear(): void {
    this.lineMap.clear();
    this.version++;
  }
}

export class I8080CodeLensProvider implements vscode.CodeLensProvider {
  private data: CodeLensData;
  private _onChange: vscode.EventEmitter<void>;
  onDidChangeCodeLenses: vscode.Event<void>;

  constructor(data: CodeLensData) {
    this.data = data;
    this._onChange = new vscode.EventEmitter<void>();
    this.onDidChangeCodeLenses = this._onChange.event;
  }

  notifyChanged(): void {
    this._onChange.fire();
  }

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const lenses: vscode.CodeLens[] = [];
    const maxLine = document.lineCount;

    for (let i = 0; i < maxLine; i++) {
      const info = this.data.getLensForLine(i);
      if (!info) continue;

      const addrStr = `0x${info.addr.toString(16).toUpperCase().padStart(4, '0')}`;
      const label = info.label ? ` ${info.label}` : '';
      const title = `${addrStr}${label}`;

      const range = new vscode.Range(i, 0, i, 0);
      const lens = new vscode.CodeLens(range, {
        title,
        tooltip: `Адрес: ${addrStr}${info.label ? `, метка: ${info.label}` : ''}`,
        command: 'i8080ci.emuGetState',
      });
      lenses.push(lens);
    }

    return lenses;
  }
}
