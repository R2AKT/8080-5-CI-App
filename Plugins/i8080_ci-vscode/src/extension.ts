// extension.ts — точка входа расширения i8080-ci-vscode.
import * as vscode from 'vscode';
import { assembleFile, AssembleResult } from './assembler';
import { setDiagnostics, clearDiagnostics, clearAllDiagnostics } from './diagnostics';
import { McpClient, McpError } from './mcp';
import { findProjectRoot, listProfiles } from './project';
import { resetPythonCache } from './python';
import { resetProjectRootCache } from './project';
import { I8080HoverProvider } from './hover';
import { I8080CodeLensProvider, CodeLensData } from './codelens';
import { ErrorLens } from './errorlens';

let outputChannel: vscode.OutputChannel;
let mcp: McpClient;
let statusBarItem: vscode.StatusBarItem;
let codeLensData: CodeLensData;
let codeLensProvider: I8080CodeLensProvider;
let errorLens: ErrorLens;
let emulatorRunningContext = 'i8080ci.emulatorRunning';

export function activate(context: vscode.ExtensionContext): void {
  outputChannel = vscode.window.createOutputChannel('i8080-5 CI');
  context.subscriptions.push(outputChannel);

  mcp = new McpClient((msg) => outputChannel.appendLine(msg));

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.text = '$(cpu) i8080-5 CI';
  statusBarItem.tooltip = 'i8080-5 CI: статус эмулятора';
  statusBarItem.command = 'i8080ci.emuGetState';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // --- Phase 2: Hover, Code Lens, Error Lens ---
  codeLensData = new CodeLensData();
  codeLensProvider = new I8080CodeLensProvider(codeLensData);
  errorLens = new ErrorLens();

  const asmSelector: vscode.DocumentSelector = { language: 'i8080-asm', scheme: 'file' };

  context.subscriptions.push(
    vscode.languages.registerHoverProvider(asmSelector, new I8080HoverProvider(context)),
    vscode.languages.registerCodeLensProvider(asmSelector, codeLensProvider),
  );

  const isAsmFile = (uri: vscode.Uri): boolean => {
    const ext = uri.fsPath.toLowerCase();
    return ext.endsWith('.asm') || ext.endsWith('.mac') || ext.endsWith('.inc') || ext.endsWith('.s');
  };

  // --- Команды: сборка ---
  context.subscriptions.push(
    vscode.commands.registerCommand('i8080ci.assemble', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || !isAsmFile(editor.document.uri)) {
        vscode.window.showWarningMessage('i8080-5 CI: откройте .asm-файл.');
        return;
      }
      await doAssemble(editor.document.uri);
    }),

    vscode.commands.registerCommand('i8080ci.assembleAndEmulate', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || !isAsmFile(editor.document.uri)) {
        vscode.window.showWarningMessage('i8080-5 CI: откройте .asm-файл.');
        return;
      }
      const result = await doAssemble(editor.document.uri);
      if (result && result.success) {
        await loadAndRunInEmulator(result);
      }
    }),

    // --- Команды: профиль ---
    vscode.commands.registerCommand('i8080ci.selectProfile', async () => {
      const root = findProjectRoot();
      if (!root) {
        vscode.window.showErrorMessage('i8080-5 CI: корень проекта не найден.');
        return;
      }
      const profiles = listProfiles(root);
      if (profiles.length === 0) {
        vscode.window.showErrorMessage('i8080-5 CI: нет профилей в profiles/.');
        return;
      }
      const cfg = vscode.workspace.getConfiguration('i8080ci');
      const current = cfg.get<string>('profile', 'full');
      const chosen = await vscode.window.showQuickPick(
        profiles.map((p) => ({ label: p, description: p === current ? '✓ текущий' : '' })),
        { placeHolder: 'Выберите профиль системы', matchOnDescription: true }
      );
      if (chosen) {
        await cfg.update('profile', chosen.label, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`i8080-5 CI: профиль = ${chosen.label}`);
      }
    }),

    // --- Команды: эмулятор ---
    vscode.commands.registerCommand('i8080ci.emuStart', async () => {
      await ensureEmulatorStarted();
    }),

    vscode.commands.registerCommand('i8080ci.emuStop', async () => {
      await mcp.stop();
      updateStatusBar('stopped');
      vscode.window.showInformationMessage('i8080-5 CI: эмулятор остановлен.');
    }),

    vscode.commands.registerCommand('i8080ci.emuReset', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_reset');
        showEmuResult('Reset', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuRun', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_run', { max_instructions: 100000 });
        showEmuResult('Run', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuStepInto', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_step_into');
        showEmuResult('Step Into', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuStepOver', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_step_over');
        showEmuResult('Step Over', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuStopRun', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_stop');
        showEmuResult('Stop', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuGetState', async () => {
      await withEmulator(async () => {
        const text = await mcp.callToolText('emu_get_state');
        showEmuResult('State', text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.emuDisassemble', async () => {
      await withEmulator(async () => {
        const stateText = await mcp.callToolText('emu_get_state');
        let pc = 0x0100;
        try {
          const state = JSON.parse(stateText);
          pc = state.PC ?? 0x0100;
        } catch { /* ignore */ }
        const text = await mcp.callToolText('emu_disassemble', { addr: pc, length: 256 });
        showEmuResult(`Disassemble @ 0x${pc.toString(16).toUpperCase()}`, text);
      });
    }),

    vscode.commands.registerCommand('i8080ci.showOutput', () => {
      outputChannel.show();
    })
  );

  // --- Task Integration (Ctrl+Shift+B) ---
  context.subscriptions.push(
    vscode.tasks.registerTaskProvider('i8080ci-assemble', new I8080TaskProvider())
  );

  // --- Авто-сборка при сохранении ---
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const cfg = vscode.workspace.getConfiguration('i8080ci');
      if (!cfg.get<boolean>('autoAssemble', false)) return;
      if (!isAsmFile(doc.uri)) return;
      await doAssemble(doc.uri);
    })
  );

  // --- Очистка при деактивации ---
  context.subscriptions.push({
    dispose: async () => {
      await mcp.stop();
      clearAllDiagnostics();
      errorLens.dispose();
    }
  });

  outputChannel.appendLine('i8080-5 CI: расширение активировано.');
}

export function deactivate(): void {
  // mcp.stop() вызывается в dispose
}

// =============================================================
// Вспомогательные функции
// =============================================================

async function doAssemble(uri: vscode.Uri): Promise<AssembleResult | undefined> {
  const cfg = vscode.workspace.getConfiguration('i8080ci');
  const outputBin = cfg.get<boolean>('outputBin', true);
  const outputMap = cfg.get<boolean>('outputMap', true);
  const showWarnings = cfg.get<boolean>('showWarnings', true);
  const showErrorLens = cfg.get<boolean>('errorLens', true);

  outputChannel.appendLine(`\n=== Сборка: ${uri.fsPath} ===`);
  const result = await assembleFile(uri, outputBin, outputMap, (m) => outputChannel.appendLine(m));

  if (result.launchError) {
    vscode.window.showErrorMessage(`i8080-5 CI: ${result.launchError}`);
    outputChannel.appendLine(`ОШИБКА: ${result.launchError}`);
    return result;
  }

  setDiagnostics(uri, result, showWarnings);

  // Phase 2: Error Lens (inline)
  if (showErrorLens) {
    errorLens.update(result.errors, result.warnings, showWarnings);
  } else {
    errorLens.clear();
  }

  // Phase 2: Code Lens (адреса + метки)
  if (result.success) {
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.uri.fsPath === uri.fsPath) {
      codeLensData.populate(result.listing, result.symbols, editor.document);
      codeLensProvider.notifyChanged();
    }
  } else {
    codeLensData.clear();
    codeLensProvider.notifyChanged();
  }

  if (result.success) {
    const size = result.binaryHex.length / 2;
    vscode.window.showInformationMessage(
      `i8080-5 CI: сборка OK — ${size} байт, origin=0x${result.origin.toString(16).toUpperCase()}, CPU=${result.cpuType}`
    );
    outputChannel.appendLine(`OK: ${size} байт, origin=0x${result.origin.toString(16).toUpperCase()}, end=0x${result.endAddress.toString(16).toUpperCase()}, CPU=${result.cpuType}`);
  } else {
    const nErr = result.errors.length;
    const nWarn = result.warnings.length;
    vscode.window.showErrorMessage(
      `i8080-5 CI: ошибки сборки — ${nErr} (предупреждений: ${nWarn}). См. Problems.`
    );
    outputChannel.appendLine(`ОШИБКИ: ${nErr}, предупреждений: ${nWarn}`);
    for (const e of result.errors) {
      outputChannel.appendLine(`  ${e.line}:${e.col} ${e.message}`);
    }
  }

  return result;
}

async function ensureEmulatorStarted(): Promise<boolean> {
  if (mcp.isRunning) {
    return true;
  }
  const cfg = vscode.workspace.getConfiguration('i8080ci');
  const profile = cfg.get<string>('profile', 'full');
  const host = cfg.get<string>('mcpHost', '127.0.0.1');
  const port = cfg.get<number>('mcpPort', 8000);
  const root = findProjectRoot();
  if (!root) {
    vscode.window.showErrorMessage('i8080-5 CI: корень проекта не найден. Задайте i8080ci.projectRoot.');
    return false;
  }
  try {
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: 'i8080-5 CI: запуск эмулятора…' },
      async () => {
        await mcp.start(profile, host, port, root);
      }
    );
    updateStatusBar('running', profile);
    return true;
  } catch (e) {
    const msg = e instanceof McpError ? e.message : String(e);
    vscode.window.showErrorMessage(`i8080-5 CI: не удалось запустить эмулятор: ${msg}`);
    outputChannel.appendLine(`ОШИБКА запуска: ${msg}`);
    return false;
  }
}

async function withEmulator(fn: () => Promise<void>): Promise<void> {
  const ok = await ensureEmulatorStarted();
  if (!ok) return;
  try {
    await fn();
  } catch (e) {
    const msg = e instanceof McpError ? e.message : String(e);
    vscode.window.showErrorMessage(`i8080-5 CI: ${msg}`);
    outputChannel.appendLine(`ОШИБКА: ${msg}`);
  }
}

async function loadAndRunInEmulator(result: AssembleResult): Promise<void> {
  const ok = await ensureEmulatorStarted();
  if (!ok) return;
  try {
    // Reset
    await mcp.callTool('emu_reset');

    // Загружаем бинарь через write_block (один вызов вместо N)
    const bytes: number[] = [];
    const hex = result.binaryHex;
    for (let i = 0; i < hex.length; i += 2) {
      bytes.push(parseInt(hex.substring(i, i + 2), 16));
    }
    const origin = result.origin;
    await mcp.callTool('write_block', { addr: origin, data: bytes });

    // Устанавливаем PC на origin
    await mcp.callTool('emu_set_reg', { reg: 'PC', val: origin });
    updateStatusBar('loaded', undefined, origin);

    // Авто-запуск
    const cfg = vscode.workspace.getConfiguration('i8080ci');
    const autoRun = cfg.get<boolean>('autoRun', true);
    if (autoRun) {
      const text = await mcp.callToolText('emu_run', { max_instructions: 100000 });
      showEmuResult('Run', text);
      updateStatusBar('running');
      vscode.window.showInformationMessage(
        `i8080-5 CI: ${bytes.length} байт @ 0x${origin.toString(16).toUpperCase()} — запущено.`
      );
    } else {
      vscode.window.showInformationMessage(
        `i8080-5 CI: ${bytes.length} байт @ 0x${origin.toString(16).toUpperCase()}. Готово к запуску (F5).`
      );
    }
    outputChannel.appendLine(`Загружено ${bytes.length} байт @ 0x${origin.toString(16).toUpperCase()}${autoRun ? ', запущено' : ''}`);
  } catch (e) {
    const msg = e instanceof McpError ? e.message : String(e);
    vscode.window.showErrorMessage(`i8080-5 CI: ошибка загрузки в эмулятор: ${msg}`);
    outputChannel.appendLine(`ОШИБКА загрузки: ${msg}`);
  }
}

function showEmuResult(title: string, text: string): void {
  outputChannel.appendLine(`\n=== ${title} ===\n${text}`);
  outputChannel.show();
}

function updateStatusBar(state: 'stopped' | 'running' | 'loaded', profile?: string, pc?: number): void {
  const cfg = vscode.workspace.getConfiguration('i8080ci');
  const prof = profile ?? cfg.get<string>('profile', 'full');
  switch (state) {
    case 'stopped':
      statusBarItem.text = '$(debug-disconnect) i8080: stopped';
      statusBarItem.tooltip = 'i8080-5 CI: эмулятор остановлен';
      break;
    case 'running':
      statusBarItem.text = '$(debug-start) i8080: running';
      statusBarItem.tooltip = `i8080-5 CI: эмулятор работает (профиль ${prof})`;
      break;
    case 'loaded':
      statusBarItem.text = pc !== undefined
        ? `$(symbol-array) i8080: @0x${pc.toString(16).toUpperCase()}`
        : '$(symbol-array) i8080: loaded';
      statusBarItem.tooltip = `i8080-5 CI: образ загружен (профиль ${prof})`;
      break;
  }
  vscode.commands.executeCommand('setContext', emulatorRunningContext, state !== 'stopped');
}

// =============================================================
// Task Provider (Ctrl+Shift+B)
// =============================================================

class I8080TaskProvider implements vscode.TaskProvider {
  provideTasks(): vscode.Task[] {
    // Возвращаем один task для активного .asm файла
    const editor = vscode.window.activeTextEditor;
    if (!editor) return [];
    const uri = editor.document.uri;
    const ext = uri.fsPath.toLowerCase();
    if (!ext.endsWith('.asm') && !ext.endsWith('.s') && !ext.endsWith('.mac')) return [];

    const task = new vscode.Task(
      { type: 'i8080ci-assemble', file: uri.fsPath },
      vscode.TaskScope.Workspace,
      'Assemble i8080',
      'i8080ci-assemble',
      new vscode.ShellExecution('echo i8080ci-assemble-task'),
      []
    );
    task.presentationOptions = { reveal: vscode.TaskRevealKind.Always, panel: vscode.TaskPanelKind.Shared };
    return [task];
  }

  resolveTask(task: vscode.Task): vscode.Task | undefined {
    return task;
  }
}
