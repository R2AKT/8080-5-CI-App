// node-globals.d.ts — минимальные декларации Node.js API, используемых плагином.
// Замена @types/node (который не скачивается из-за сети). Покрывает ровно то,
// что используется в src/*.ts.
declare module 'child_process' {
  export interface SpawnOptions {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
    shell?: boolean;
    windowsHide?: boolean;
  }
  export interface ChildProcess {
    stdout: NodeJS.ReadableStream | null;
    stderr: NodeJS.ReadableStream | null;
    kill(signal?: string): boolean;
    on(event: 'close', listener: (code: number | null) => void): this;
    on(event: 'error', listener: (err: Error) => void): this;
    on(event: string, listener: (...args: any[]) => void): this;
  }
  export function spawn(command: string, args?: string[], options?: SpawnOptions): ChildProcess;
}

declare module 'fs' {
  export function mkdtempSync(prefix: string): string;
  export function writeFileSync(path: string, data: string | Buffer, options?: string | { encoding?: string }): void;
  export function readFileSync(path: string, options?: string | { encoding?: string }): string;
  export function rmSync(path: string, options?: { recursive?: boolean; force?: boolean }): void;
  export function existsSync(path: string): boolean;
  export function readdirSync(path: string): string[];
  export function mkdirSync(path: string, options?: { recursive?: boolean }): void;
}

declare module 'os' {
  export function tmpdir(): string;
}

declare module 'path' {
  export function dirname(p: string): string;
  export function join(...segments: string[]): string;
  export function isAbsolute(p: string): boolean;
  export function basename(p: string, ext?: string): string;
  export function extname(p: string): string;
}

declare module 'http' {
  export interface ClientRequest {
    on(event: 'error', listener: (err: Error) => void): this;
    write(data: string): void;
    end(): void;
    destroy(): void;
  }
  export interface IncomingMessage {
    statusCode?: number;
    setEncoding(encoding: string): this;
    on(event: 'data', listener: (chunk: string) => void): this;
    on(event: 'end', listener: () => void): this;
    on(event: 'error', listener: (err: Error) => void): this;
    resume(): void;
    destroy(): void;
  }
  export interface RequestOptions {
    hostname?: string;
    port?: number;
    path?: string;
    method?: string;
    headers?: Record<string, string>;
  }
  export function get(url: string, callback?: (res: IncomingMessage) => void): ClientRequest;
  export function request(options: RequestOptions, callback?: (res: IncomingMessage) => void): ClientRequest;
}

declare module 'net' {
  export class Socket {
    constructor();
    connect(port: number, host: string): this;
    once(event: 'connect', listener: () => void): this;
    once(event: 'error', listener: (err: Error) => void): this;
    destroy(): this;
  }
}

declare namespace NodeJS {
  export interface ProcessEnv {
    [key: string]: string | undefined;
  }
  export interface ReadableStream {
    on(event: 'data', listener: (chunk: any) => void): this;
  }
}

interface Timer {
  // маркер
}
declare function setTimeout(callback: (...args: any[]) => void, ms?: number, ...args: any[]): Timer;
declare function clearTimeout(timer: Timer | undefined): void;

declare class Buffer {
  static from(data: string | any[], encoding?: string): Buffer;
  static byteLength(str: string): number;
}

declare class URL {
  constructor(input: string);
  hostname: string;
  port: string;
  pathname: string;
  search: string;
}

declare function require(id: string): any;

declare const process: {
  platform: string;
  env: NodeJS.ProcessEnv;
};
