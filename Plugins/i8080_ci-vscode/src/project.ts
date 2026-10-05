// project.ts — определение корня проекта i8080-5_CI-AI-analysis.
// Приоритет:
//   1. Настройка i8080ci.projectRoot (если задана)
//   2. Автопоиск вверх от .asm-файла: папка, содержащая mcp_headless.py и profiles/
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

let cachedRoot: string | undefined;

/** Возвращает корень проекта или undefined. */
export function findProjectRoot(fileUri?: vscode.Uri): string | undefined {
  if (cachedRoot && fs.existsSync(cachedRoot)) {
    return cachedRoot;
  }

  const cfg = vscode.workspace.getConfiguration('i8080ci');
  const configured = cfg.get<string>('projectRoot', '');
  if (configured && configured.trim().length > 0) {
    const p = configured.trim();
    if (fs.existsSync(p)) {
      cachedRoot = p;
      return cachedRoot;
    }
  }

  // Автопоиск вверх от файла
  let dir: string | undefined;
  if (fileUri) {
    dir = path.dirname(fileUri.fsPath);
  } else {
    const ws = vscode.workspace.workspaceFolders?.[0];
    if (ws) {
      dir = ws.uri.fsPath;
    }
  }

  while (dir) {
    if (
      fs.existsSync(path.join(dir, 'mcp_headless.py')) &&
      fs.existsSync(path.join(dir, 'profiles'))
    ) {
      cachedRoot = dir;
      return cachedRoot;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      break;
    }
    dir = parent;
  }

  return undefined;
}

/** Сброс кэша. */
export function resetProjectRootCache(): void {
  cachedRoot = undefined;
}

/** Список доступных профилей (имена TOML без расширения) из profiles/. */
export function listProfiles(projectRoot: string): string[] {
  const profilesDir = path.join(projectRoot, 'profiles');
  try {
    return fs
      .readdirSync(profilesDir)
      .filter((f) => f.toLowerCase().endsWith('.toml'))
      .map((f) => f.replace(/\.toml$/i, ''))
      .sort();
  } catch {
    return [];
  }
}
