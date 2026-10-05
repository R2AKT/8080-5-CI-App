// assembler.ts — вызов Python-ассемблера i8080/8085 из VS Code.
// Ассемблер — stateless: читаем .asm, собираем, получаем JSON-результат.
import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { findPython } from './python';
import { findProjectRoot } from './project';

export interface AsmErrorInfo {
  line: number;
  col: number;
  message: string;
  severity: string; // "error" | "warning"
  source: string;
}

/** Одна строка listing: адрес + исходный текст. */
export interface ListingEntry {
  addr: number;
  source: string;
}

export interface AssembleResult {
  success: boolean;
  origin: number;
  endAddress: number;
  binaryHex: string;
  cpuType: string;
  errors: AsmErrorInfo[];
  warnings: AsmErrorInfo[];
  symbols: Record<string, number>;
  mapText: string;
  /** Listing: [(addr, source_line)] — для Code Lens. */
  listing: ListingEntry[];
  /** Абсолютный путь к сгенерированному .bin (если сохранён). */
  binPath?: string;
  /** Абсолютный путь к сгенерированному .map (если сохранён). */
  mapPath?: string;
  /** Текст ошибки запуска (если Python не запустился). */
  launchError?: string;
}

// Python-хелпер: собирает файл и печатает JSON в stdout.
const PYTHON_HELPER = `
import json, sys, os

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "launchError": "no file arg"}))
        return
    asm_file = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    sys.path.insert(0, project_root)
    try:
        from assemble8080 import Assembler
    except Exception as e:
        print(json.dumps({"success": False, "launchError": f"import failed: {e}"}))
        return
    try:
        with open(asm_file, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        print(json.dumps({"success": False, "launchError": f"read failed: {e}"}))
        return
    asm = Assembler()
    r = asm.assemble(src, asm_file)
    def errinfo(e):
        return {
            "line": getattr(e, "line", 0),
            "col": getattr(e, "col", 0),
            "message": getattr(e, "message", str(e)),
            "severity": getattr(e, "severity", "error"),
            "source": getattr(e, "source", ""),
        }
    # Listing: [(addr, bytes, source)] -> [{addr, source}]
    listing = []
    for item in (getattr(r, "listing", None) or []):
        if len(item) >= 3:
            listing.append({"addr": int(item[0]), "source": item[2]})
    out = {
        "success": bool(r.success),
        "origin": int(r.origin),
        "end_address": int(getattr(r, "end_address", 0)),
        "binary_hex": (r.binary.hex() if r.binary else ""),
        "cpu_type": getattr(asm, "cpu_type", "i8080"),
        "errors": [errinfo(e) for e in (r.errors or [])],
        "warnings": [errinfo(w) for w in (r.warnings or [])],
        "symbols": {k: int(v) for k, v in (r.symbols or {}).items()},
        "map_text": getattr(r, "map_text", "") or "",
        "listing": listing,
    }
    print(json.dumps(out, ensure_ascii=False))

main()
`;

function runPython(python: string, args: string[], cwd: string, timeoutMs = 30000): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const child = cp.spawn(python, args, {
      cwd,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    });
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      try { child.kill(); } catch { /* ignore */ }
    }, timeoutMs);
    child.stdout?.on('data', (d) => { stdout += d.toString(); });
    child.stderr?.on('data', (d) => { stderr += d.toString(); });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ code: code ?? -1, stdout, stderr });
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: String(err) });
    });
  });
}

/**
 * Ассемблирует .asm-файл.
 */
export async function assembleFile(
  fileUri: vscode.Uri,
  outputBin: boolean,
  outputMap: boolean,
  log?: (msg: string) => void
): Promise<AssembleResult> {
  const fail = (launchError: string): AssembleResult => ({
    success: false, origin: 0, endAddress: 0, binaryHex: '', cpuType: 'i8080',
    errors: [], warnings: [], symbols: {}, mapText: '', listing: [], launchError,
  });

  const python = await findPython();
  if (!python) {
    return fail('Python не найден. Установите Python 3.10+ или задайте i8080ci.pythonPath.');
  }

  const projectRoot = findProjectRoot(fileUri);
  if (!projectRoot) {
    return fail('Корень проекта не найден (нет mcp_headless.py + profiles/). Задайте i8080ci.projectRoot.');
  }

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'i8080ci-'));
  const helperPath = path.join(tmpDir, '_assemble_helper.py');
  try {
    fs.writeFileSync(helperPath, PYTHON_HELPER, 'utf-8');
    const res = await runPython(python, [helperPath, fileUri.fsPath, projectRoot], projectRoot);

    if (res.code !== 0 && !res.stdout.trim()) {
      return fail(`Python завершился с кодом ${res.code}: ${res.stderr.slice(0, 500)}`);
    }

    const lines = res.stdout.split(/\r?\n/).filter((l) => l.trim().length > 0);
    const jsonLine = lines[lines.length - 1];
    if (!jsonLine) {
      return fail(`Пустой вывод Python. stderr: ${res.stderr.slice(0, 500)}`);
    }

    let parsed: any;
    try {
      parsed = JSON.parse(jsonLine);
    } catch (e) {
      return fail(`Некорректный JSON от ассемблера: ${String(e)}. Raw: ${jsonLine.slice(0, 300)}`);
    }

    if (parsed.launchError) {
      return fail(parsed.launchError);
    }

    const result: AssembleResult = {
      success: !!parsed.success,
      origin: parsed.origin ?? 0,
      endAddress: parsed.end_address ?? 0,
      binaryHex: parsed.binary_hex ?? '',
      cpuType: parsed.cpu_type ?? 'i8080',
      errors: (parsed.errors ?? []).map((e: any) => ({
        line: e.line ?? 0, col: e.col ?? 0, message: e.message ?? '',
        severity: e.severity ?? 'error', source: e.source ?? '',
      })),
      warnings: (parsed.warnings ?? []).map((e: any) => ({
        line: e.line ?? 0, col: e.col ?? 0, message: e.message ?? '',
        severity: e.severity ?? 'warning', source: e.source ?? '',
      })),
      symbols: parsed.symbols ?? {},
      mapText: parsed.map_text ?? '',
      listing: (parsed.listing ?? []).map((l: any) => ({
        addr: l.addr ?? 0, source: l.source ?? '',
      })),
    };

    const base = fileUri.fsPath.replace(/\.[^.]+$/, '');
    if (result.success && result.binaryHex.length > 0) {
      if (outputBin) {
        const binPath = base + '.bin';
        fs.writeFileSync(binPath, Buffer.from(result.binaryHex, 'hex'));
        result.binPath = binPath;
        log?.(`.bin: ${binPath} (${result.binaryHex.length / 2} байт)`);
      }
      if (outputMap && result.mapText) {
        const mapPath = base + '.map';
        fs.writeFileSync(mapPath, result.mapText, 'utf-8');
        result.mapPath = mapPath;
        log?.(`.map: ${mapPath}`);
      }
    }

    return result;
  } finally {
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
  }
}
