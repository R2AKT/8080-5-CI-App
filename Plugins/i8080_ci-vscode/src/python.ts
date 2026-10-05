// python.ts — обнаружение Python-интерпретатора.
// Приоритет:
//   1. Настройка i8080ci.pythonPath (если задана)
//   2. 'where python' (Windows) / 'which python' (POSIX)
//   3. 'py -3' (Windows launcher)
//   4. 'python3' / 'python' из PATH
import * as vscode from 'vscode';
import * as cp from 'child_process';

let cachedPython: string | undefined;

function run(cmd: string, args: string[], timeoutMs = 4000): Promise<string> {
  return new Promise((resolve) => {
    try {
      const child = cp.spawn(cmd, args, {
        shell: process.platform === 'win32',
        windowsHide: true,
      });
      let out = '';
      let err = '';
      const timer = setTimeout(() => {
        try { child.kill(); } catch { /* ignore */ }
      }, timeoutMs);
      child.stdout?.on('data', (d) => { out += d.toString(); });
      child.stderr?.on('data', (d) => { err += d.toString(); });
      child.on('close', () => {
        clearTimeout(timer);
        resolve(out.trim() || err.trim());
      });
      child.on('error', () => {
        clearTimeout(timer);
        resolve('');
      });
    } catch {
      resolve('');
    }
  });
}

/** Возвращает путь к Python или undefined, если не найден. */
export async function findPython(context?: vscode.ExtensionContext): Promise<string | undefined> {
  if (cachedPython) {
    return cachedPython;
  }

  const cfg = vscode.workspace.getConfiguration('i8080ci');
  const configured = cfg.get<string>('pythonPath', '');
  if (configured && configured.trim().length > 0) {
    cachedPython = configured.trim();
    return cachedPython;
  }

  const isWin = process.platform === 'win32';

  // 1) where python / which python
  const whereCmd = isWin ? 'where' : 'which';
  const whereOut = await run(whereCmd, ['python']);
  const firstLine = whereOut.split(/\r?\n/)[0]?.trim();
  if (firstLine && firstLine.length > 0 && looksLikePath(firstLine)) {
    cachedPython = firstLine;
    return cachedPython;
  }

  // 2) py -3 (Windows launcher)
  if (isWin) {
    const pyOut = await run('py', ['-3', '-c', 'import sys; print(sys.executable)']);
    const pyLine = pyOut.split(/\r?\n/)[0]?.trim();
    if (pyLine && looksLikePath(pyLine)) {
      cachedPython = pyLine;
      return cachedPython;
    }
  }

  // 3) python3 / python из PATH
  const candidates = isWin ? ['python', 'python3'] : ['python3', 'python'];
  for (const c of candidates) {
    const out = await run(c, ['-c', 'import sys; print(sys.executable)']);
    const line = out.split(/\r?\n/)[0]?.trim();
    if (line && looksLikePath(line)) {
      cachedPython = line;
      return cachedPython;
    }
  }

  return undefined;
}

function looksLikePath(s: string): boolean {
  // Путь к исполняемому файлу (с расширением или абсолютный)
  return /(^|[\\/])python\d*\.?(exe)?$/.test(s) || s.includes('/') || s.includes('\\');
}

/** Сброс кэша (для команды "Reload Python"). */
export function resetPythonCache(): void {
  cachedPython = undefined;
}
