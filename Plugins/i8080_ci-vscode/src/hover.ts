// hover.ts — Hover-провайдер: наведение на мнемонику → opcode + описание + размер.
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface OpcodeInfo {
  mnemonic: string;
  operand: string;
  size: number;
  undoc: string;
}

/** Краткие описания мнемоник (RU). */
const DESC: Record<string, string> = {
  'NOP': 'Нет операции',
  'HLT': 'Остановка CPU',
  'DI': 'Запрет прерываний',
  'EI': 'Разрешить прерывания',
  'RET': 'Возврат из подпрограммы',
  'RZ': 'Возврат если Z=1',
  'RNZ': 'Возврат если Z=0',
  'RC': 'Возврат если CY=1',
  'RNC': 'Возврат если CY=0',
  'RPE': 'Возврат если PE=1',
  'RPO': 'Возврат если PE=0',
  'RM': 'Возврат если S=1',
  'RP': 'Возврат если S=0',
  'JMP': 'Безусловный переход',
  'JZ': 'Переход если Z=1',
  'JNZ': 'Переход если Z=0',
  'JC': 'Переход если CY=1',
  'JNC': 'Переход если CY=0',
  'JPE': 'Переход если PE=1',
  'JPO': 'Переход если PE=0',
  'JM': 'Переход если S=1',
  'JP': 'Переход если S=0',
  'CALL': 'Вызов подпрограммы',
  'CZ': 'Вызов если Z=1',
  'CNZ': 'Вызов если Z=0',
  'CC': 'Вызов если CY=1',
  'CNC': 'Вызов если CY=0',
  'CPE': 'Вызов если PE=1',
  'CPO': 'Вызов если PE=0',
  'CM': 'Вызов если S=1',
  'CP': 'Вызов если S=0',
  'RST': 'Сброс (вызов фиксированного адреса)',
  'MVI': 'Загрузка константы в регистр',
  'LXI': 'Загрузка константы в регистровую пару',
  'MOV': 'Копирование регистра',
  'INR': 'Инкремент регистра',
  'DCR': 'Декремент регистра',
  'INX': 'Инкремент регистровой пары',
  'DCX': 'Декремент регистровой пары',
  'ADD': 'Сложение регистра с A',
  'ADC': 'Сложение с переносом',
  'SUB': 'Вычитание регистра из A',
  'SBB': 'Вычитание с заёмом',
  'ANA': 'И (AND) с A',
  'XRA': 'ИСКЛ. ИЛИ (XOR) с A',
  'ORA': 'ИЛИ (OR) с A',
  'CMP': 'Сравнение с A',
  'ADI': 'Сложение константы с A',
  'ACI': 'Сложение константы с переносом',
  'SUI': 'Вычитание константы из A',
  'SBI': 'Вычитание константы с заёмом',
  'ANI': 'И (AND) константы с A',
  'XRI': 'ИСКЛ. ИЛИ константы с A',
  'ORI': 'ИЛИ константы с A',
  'CPI': 'Сравнение константы с A',
  'DAA': 'Десятичная корректировка A',
  'CMA': 'Дополнение A (NOT)',
  'CMC': 'Инверсия флага CY',
  'STC': 'Установка флага CY',
  'RLC': 'Циклический сдвиг A влево через CY',
  'RRC': 'Циклический сдвиг A вправо через CY',
  'RAL': 'Сдвиг A влево (CY участвует)',
  'RAR': 'Сдвиг A вправо (CY участвует)',
  'DAD': 'Сложение регистровой пары с HL',
  'LDA': 'Загрузка A из памяти',
  'STA': 'Запись A в память',
  'LHLD': 'Загрузка HL из памяти (16 бит)',
  'SHLD': 'Запись HL в память (16 бит)',
  'LDAX': 'Загрузка A из памяти (адрес в BC/DE)',
  'STAX': 'Запись A в память (адрес в BC/DE)',
  'IN': 'Чтение из порта ввода-вывода',
  'OUT': 'Запись в порт ввода-вывода',
  'PUSH': 'Запись регистровой пары на стек',
  'POP': 'Чтение регистровой пары из стека',
  'XCHG': 'Обмен HL ↔ DE',
  'XTHL': 'Обмен HL ↔ [SP]',
  'SPHL': 'SP ← HL',
  'PCHL': 'PC ← HL',
  'SIM': '8085: установка маски прерываний',
  'RIM': '8085: чтение маски прерываний',
  'DSUB': '8085: вычитание B из A (без флагов)',
  'ARHL': '8085: деление HL на 2',
  'SHLX': '8085: сдвиг [M] влево',
  'LHLX': '8085: загрузка HL из [M] со сдвигом',
};

let opcodeTable8080: Record<string, OpcodeInfo> = {};
let opcodeTable8085: Record<string, OpcodeInfo> = {};
let loaded = false;

function loadTables(context: vscode.ExtensionContext): void {
  if (loaded) return;
  const dir = context.extensionUri.fsPath;
  try {
    const t8080 = fs.readFileSync(path.join(dir, 'data', 'opcodes_8080.json'), 'utf-8');
    opcodeTable8080 = JSON.parse(t8080);
  } catch { /* ignore */ }
  try {
    const t8085 = fs.readFileSync(path.join(dir, 'data', 'opcodes_8085.json'), 'utf-8');
    opcodeTable8085 = JSON.parse(t8085);
  } catch { /* ignore */ }
  loaded = true;
}

/** Обратный поиск: мнемоника → список опкодов. */
function findOpcodes(mnemonic: string, cpuType: string): { op: string; info: OpcodeInfo }[] {
  const table = cpuType === '8085' ? opcodeTable8085 : opcodeTable8080;
  const results: { op: string; info: OpcodeInfo }[] = [];
  for (const [op, info] of Object.entries(table)) {
    if (info.mnemonic.toUpperCase() === mnemonic.toUpperCase()) {
      results.push({ op, info });
    }
  }
  return results;
}

export class I8080HoverProvider implements vscode.HoverProvider {
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    loadTables(context);
  }

  provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | undefined {
    // Получаем слово под курсором
    const wordRange = document.getWordRangeAtPosition(position, /[A-Za-z][A-Za-z0-9]*/);
    if (!wordRange) return undefined;
    const word = document.getText(wordRange).toUpperCase();

    // Проверяем, является ли это мнемоникой
    const cpuType = this.getCpuType(document);
    const opcodes = findOpcodes(word, cpuType);
    if (opcodes.length === 0) return undefined;

    // Формируем markdown
    const desc = DESC[word] || '';
    let md = `**${word}**`;
    if (desc) md += ` — ${desc}\n\n`;

    // Показываем до 4 опкодов
    const shown = opcodes.slice(0, 4);
    for (const { op, info } of shown) {
      const undoc = info.undoc ? ` *(недокументировано)*` : '';
      md += `\`0x${op}\` — ${info.mnemonic}${info.operand ? ' ' + info.operand : ''} [${info.size} байт]${undoc}\n`;
    }
    if (opcodes.length > 4) {
      md += `\n_…и ещё ${opcodes.length - 4}_\n`;
    }

    return new vscode.Hover(md, wordRange);
  }

  private getCpuType(document: vscode.TextDocument): string {
    // Ищем директиву CPU в файле
    const text = document.getText();
    const match = text.match(/(?:CPU|\.8085|\.8080)\s*(808[05])?/i);
    if (match) {
      if (match[0].toUpperCase().includes('8085')) return '8085';
      if (match[0].toUpperCase().includes('8080')) return '8080';
      if (match[1]) return match[1];
    }
    return '8080';
  }
}
