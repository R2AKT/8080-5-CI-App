// mcp.ts — клиент headless MCP-сервера i8080-5 CI.
// Запускает `python mcp_headless.py --profile X --port Y`, подключается по SSE
// и вызывает инструменты (JSON-RPC 2.0 поверх SSE). Без внешних зависимостей.
import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as http from 'http';
import { findPython } from './python';
import { findProjectRoot } from './project';

interface JsonRpcResponse {
  jsonrpc: string;
  id?: number;
  result?: any;
  error?: { code: number; message: string; data?: any };
}

type PendingResolver = (value: JsonRpcResponse) => void;
type PendingRejector = (err: Error) => void;

export class McpError extends Error {
  constructor(message: string, public data?: any) {
    super(message);
  }
}

/**
 * Минимальный MCP-клиент (SSE transport).
 * Один экземпляр, без параллельных сессий.
 */
export class McpClient {
  private pythonProc: cp.ChildProcess | undefined;
  private sseReq: http.ClientRequest | undefined;
  private sseRes: http.IncomingMessage | undefined;
  private baseUrl = '';
  private messagesUrl = '';
  private nextId = 1;
  private pending = new Map<number, { resolve: PendingResolver; reject: PendingRejector }>();
  private sseBuffer = '';
  private connected = false;
  private log: (msg: string) => void;

  constructor(log: (msg: string) => void) {
    this.log = log;
  }

  get isRunning(): boolean {
    return this.connected;
  }

  /** Запускает headless-сервер и подключается. */
  async start(profile: string, host: string, port: number, projectRoot: string): Promise<void> {
    if (this.connected) {
      return;
    }

    const python = await findPython();
    if (!python) {
      throw new McpError('Python не найден. Установите Python 3.10+ или задайте i8080ci.pythonPath.');
    }

    const serverScript = `${projectRoot}/mcp_headless.py`;
    this.baseUrl = `http://${host}:${port}`;

    // 1) Запускаем сервер
    this.log(`Запуск headless MCP: ${python} ${serverScript} --profile ${profile} --port ${port}`);
    this.pythonProc = cp.spawn(python, [serverScript, '--profile', profile, '--host', host, '--port', String(port)], {
      cwd: projectRoot,
      windowsHide: true,
      env: { ...process.env, QT_QPA_PLATFORM: 'offscreen', PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    });
    this.pythonProc.stdout?.on('data', (d) => {
      const s = d.toString();
      // Логируем только ключевые строки сервера
      if (s.includes('Готов к подключению') || s.includes('MCP Server started') || s.includes('ERROR')) {
        this.log(s.trim());
      }
    });
    this.pythonProc.stderr?.on('data', (d) => {
      const s = d.toString().trim();
      if (s) this.log(`[server] ${s}`);
    });
    this.pythonProc.on('exit', (code) => {
      this.log(`Headless-сервер завершился (code=${code}).`);
      this.cleanupConnection();
    });

    // 2) Ждём, пока порт станет доступен, и подключаемся по SSE
    await this.waitForPort(host, port, 15000);
    await this.connectSse();
    this.connected = true;

    // 3) Инициализация MCP-сессии
    await this.request('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'i8080-ci-vscode', version: '0.1.0' },
    });
    // Уведомление об инициализации (без id)
    this.notify('notifications/initialized', {});

    this.log(`MCP-сессия установлена: ${this.baseUrl}/sse`);
  }

  /** Останавливает сервер и закрывает соединение. */
  async stop(): Promise<void> {
    this.cleanupConnection();
    if (this.pythonProc) {
      const proc = this.pythonProc;
      this.pythonProc = undefined;
      try {
        proc.kill('SIGTERM');
        // Даем время на штатное завершение, затем SIGKILL
        await new Promise<void>((resolve) => {
          const t = setTimeout(() => {
            try { proc.kill('SIGKILL'); } catch { /* ignore */ }
            resolve();
          }, 3000);
          proc.on('exit', () => { clearTimeout(t); resolve(); });
        });
      } catch { /* ignore */ }
    }
    this.log('Headless MCP-сервер остановлен.');
  }

  // ---------------------------------------------------------
  // Публичные вызовы инструментов
  // ---------------------------------------------------------
  async callTool(name: string, args: Record<string, any> = {}): Promise<any> {
    const res = await this.request('tools/call', { name, arguments: args });
    if (res.error) {
      throw new McpError(res.error.message, res.error.data);
    }
    return res.result;
  }

  /** Возвращает текст первого content-элемента результата инструмента. */
  async callToolText(name: string, args: Record<string, any> = {}): Promise<string> {
    const result = await this.callTool(name, args);
    if (result && Array.isArray(result.content) && result.content.length > 0) {
      const c = result.content[0];
      if (typeof c.text === 'string') return c.text;
    }
    if (result && result.structuredContent !== undefined) {
      return JSON.stringify(result.structuredContent, null, 2);
    }
    return JSON.stringify(result ?? null, null, 2);
  }

  // ---------------------------------------------------------
  // Внутреннее: SSE + JSON-RPC
  // ---------------------------------------------------------
  private waitForPort(host: string, port: number, timeoutMs: number): Promise<void> {
    const start = Date.now();
    return new Promise((resolve, reject) => {
      const tryConnect = () => {
        if (Date.now() - start > timeoutMs) {
          reject(new McpError(`Порт ${port} не стал доступен за ${timeoutMs} мс`));
          return;
        }
        const sock = new (require('net').Socket)();
        sock.once('connect', () => { sock.destroy(); resolve(); });
        sock.once('error', () => { sock.destroy(); setTimeout(tryConnect, 300); });
        sock.connect(port, host);
      };
      tryConnect();
    });
  }

  private connectSse(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.sseReq = http.get(`${this.baseUrl}/sse`, (res) => {
        this.sseRes = res;
        if (res.statusCode !== 200) {
          reject(new McpError(`SSE HTTP ${res.statusCode}`));
          return;
        }
        this.sseBuffer = '';
        res.setEncoding('utf-8');
        res.on('data', (chunk) => this.onSseData(chunk, resolve));
        res.on('end', () => {
          this.cleanupConnection();
        });
        res.on('error', (e) => reject(new McpError(`SSE error: ${e.message}`)));
      });
      this.sseReq.on('error', (e) => reject(new McpError(`SSE connect error: ${e.message}`)));
    });
  }

  private onSseData(chunk: string, resolveEndpoint: () => void): void {
    // Сервер (sse-starlette) шлёт окончания строк \r\n — нормализуем к \n
    this.sseBuffer += chunk.replace(/\r\n/g, '\n');
    // SSE-события разделены пустой строкой
    let idx: number;
    while ((idx = this.sseBuffer.indexOf('\n\n')) !== -1) {
      const rawEvent = this.sseBuffer.slice(0, idx);
      this.sseBuffer = this.sseBuffer.slice(idx + 2);
      this.processSseEvent(rawEvent, resolveEndpoint);
    }
  }

  private processSseEvent(rawEvent: string, resolveEndpoint: () => void): void {
    let event = 'message';
    const dataLines: string[] = [];
    for (const line of rawEvent.split('\n')) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length === 0) return;
    const data = dataLines.join('\n');

    if (event === 'endpoint') {
      // data — относительный URL для POST (например /messages/?session_id=...)
      this.messagesUrl = data.startsWith('http') ? data : `${this.baseUrl}${data}`;
      this.log(`SSE endpoint: ${this.messagesUrl}`);
      resolveEndpoint();
    } else if (event === 'message') {
      try {
        const msg: JsonRpcResponse = JSON.parse(data);
        if (msg.id !== undefined && this.pending.has(msg.id)) {
          const p = this.pending.get(msg.id)!;
          this.pending.delete(msg.id);
          p.resolve(msg);
        }
      } catch (e) {
        this.log(`Некорректный JSON-RPC: ${String(e)}`);
      }
    }
  }

  private request(method: string, params: any): Promise<JsonRpcResponse> {
    if (!this.connected || !this.messagesUrl) {
      return Promise.reject(new McpError('MCP-сессия не установлена'));
    }
    const id = this.nextId++;
    const body = JSON.stringify({ jsonrpc: '2.0', id, method, params });
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      // Таймаут на ответ
      const timer = setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new McpError(`Таймаут запроса ${method} (id=${id})`));
        }
      }, 30000);
      this.postJson(body).catch((e) => {
        clearTimeout(timer);
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(e);
        }
      });
    });
  }

  private notify(method: string, params: any): void {
    if (!this.connected || !this.messagesUrl) return;
    const body = JSON.stringify({ jsonrpc: '2.0', method, params });
    this.postJson(body).catch(() => { /* уведомления не критичны */ });
  }

  private postJson(body: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = new URL(this.messagesUrl);
      const req = http.request({
        hostname: url.hostname,
        port: Number(url.port) || 80,
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': String(Buffer.byteLength(body)),
        },
      }, (res) => {
        // Сервер отвечает 202 Accepted; тело не читаем
        res.resume();
        res.on('end', () => resolve());
      });
      req.on('error', (e) => reject(new McpError(`POST error: ${e.message}`)));
      req.write(body);
      req.end();
    });
  }

  private cleanupConnection(): void {
    this.connected = false;
    for (const [, p] of this.pending) {
      p.reject(new McpError('Соединение закрыто'));
    }
    this.pending.clear();
    try { this.sseReq?.destroy(); } catch { /* ignore */ }
    try { this.sseRes?.destroy(); } catch { /* ignore */ }
    this.sseReq = undefined;
    this.sseRes = undefined;
    this.messagesUrl = '';
  }
}
