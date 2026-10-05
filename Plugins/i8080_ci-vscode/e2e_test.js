// E2E-тест плагина вне VS Code: python-поиск, ассемблер, MCP-клиент.
// Запуск: node e2e_test.js  (нужен Node.js и Python в PATH)
'use strict';
const path = require('path');
const fs = require('fs');
const os = require('os');

const PLUGIN = __dirname;
const PROJECT = path.resolve(__dirname, '..', '..'); // i8080-5_CI-AI-analysis

// Настройки "VS Code" для мока
global.__testConfig = {
  'i8080ci.projectRoot': PROJECT,
  'i8080ci.profile': 'full',
  'i8080ci.mcpPort': 8231,
  'i8080ci.mcpHost': '127.0.0.1',
  'i8080ci.outputBin': true,
  'i8080ci.outputMap': true,
  'i8080ci.showWarnings': true,
};

const vscode = require(path.join(PLUGIN, 'node_modules', 'vscode', 'index.js'));
const { findPython } = require(path.join(PLUGIN, 'out', 'python.js'));
const { findProjectRoot, listProfiles } = require(path.join(PLUGIN, 'out', 'project.js'));
const { assembleFile } = require(path.join(PLUGIN, 'out', 'assembler.js'));
const { McpClient } = require(path.join(PLUGIN, 'out', 'mcp.js'));

let passed = 0, failed = 0;
function check(name, cond, detail) {
  if (cond) { passed++; console.log(`  PASS  ${name}`); }
  else { failed++; console.log(`  FAIL  ${name}${detail ? ' — ' + detail : ''}`); }
}

(async () => {
  console.log('=== 1. Поиск Python ===');
  const py = await findPython();
  check('python найден', !!py, String(py));
  console.log('  python =', py);

  console.log('=== 2. Корень проекта и профили ===');
  const root = findProjectRoot();
  check('корень проекта найден', root === PROJECT, String(root));
  const profiles = listProfiles(root);
  check('профилей >= 12', profiles.length >= 12, String(profiles.length));
  console.log('  профили:', profiles.join(', '));

  console.log('=== 3. Ассемблер: успешная сборка ===');
  const goodFile = path.join(PROJECT, 'ASM_FOR_TEST', '8080PRE.asm');
  const uri = vscode.Uri.file(goodFile);
  const r1 = await assembleFile(uri, true, true, (m) => console.log('  [log]', m));
  check('сборка успешна', r1.success, r1.launchError || (r1.errors[0] || {}).message);
  check('бинарь не пуст', r1.binaryHex.length > 0);
  check('origin = 0x0100', r1.origin === 0x0100, '0x' + r1.origin.toString(16));
  check('.bin сохранён', r1.binPath && fs.existsSync(r1.binPath), String(r1.binPath));
  if (r1.binPath) {
    const binSize = fs.statSync(r1.binPath).size;
    check('размер .bin совпадает', binSize === r1.binaryHex.length / 2, `${binSize} vs ${r1.binaryHex.length / 2}`);
  }
  check('.map сохранён', r1.mapPath && fs.existsSync(r1.mapPath), String(r1.mapPath));
  check('CPU = i8080', r1.cpuType === 'i8080', r1.cpuType);

  console.log('=== 4. Ассемблер: файл с ошибкой ===');
  const tmpAsm = path.join(os.tmpdir(), 'i8080ci_bad_test.asm');
  fs.writeFileSync(tmpAsm, 'ORG 0100H\nSTART: MVI A, 05H\n        FOO A\n        HLT\n        END\n', 'utf-8');
  const r2 = await assembleFile(vscode.Uri.file(tmpAsm), false, false);
  check('сборка не успешна', !r2.success);
  check('ошибка найдена', r2.errors.length >= 1, JSON.stringify(r2.errors));
  if (r2.errors.length) {
    check('строка ошибки = 3', r2.errors[0].line === 3, String(r2.errors[0].line));
    // FOO без двоеточия ассемблер считает меткой (совместимость), мнемоникой идёт "A"
    check('текст ошибки про мнемонику', /Неизвестная мнемоника/.test(r2.errors[0].message), r2.errors[0].message);
  }
  fs.rmSync(tmpAsm, { force: true });

  console.log('=== 5. MCP: запуск headless-сервера и вызовы ===');
  const client = new McpClient((m) => console.log('  [mcp]', m));
  try {
    await client.start('full', '127.0.0.1', 8231, PROJECT);
    check('сервер запущен', client.isRunning);

    const st = await client.callToolText('emu_get_state');
    check('emu_get_state: есть A', /"A"\s*:/.test(st), st.slice(0, 80));

    const rs = await client.callToolText('emu_reset');
    check('emu_reset', /PC=0x0000/.test(rs), rs);

    const wm = await client.callToolText('write_mem', { addr: 0x0100, val: 0x55 });
    check('write_mem', /0x55/.test(wm), wm);
    const rm = await client.callToolText('read_mem', { addr: 0x0100 });
    check('read_mem = 85 (0x55)', /85/.test(rm), rm);

    // emu_disassemble дизассемблирует от addr-8; кладём MVI A,05H (3E 05) на 0x00F8
    await client.callTool('write_mem', { addr: 0x00F8, val: 0x3E });
    await client.callTool('write_mem', { addr: 0x00F9, val: 0x05 });
    const dis = await client.callToolText('emu_disassemble', { addr: 0x0100, length: 16 });
    check('emu_disassemble: MVI', /MVI/i.test(dis), dis.slice(0, 120));

    const bp1 = await client.callToolText('emu_add_breakpoint', { addr: 0x0100 });
    check('breakpoint добавлен', /0x0100/i.test(bp1), bp1);
    const bp2 = await client.callToolText('emu_list_breakpoints', {});
    check('breakpoint в списке', /0x0100/i.test(bp2), bp2);

    const status = await client.callToolText('get_status', {});
    check('get_status: mem_size > 0', /"mem_size"\s*:\s*[1-9]/.test(status), status.slice(0, 120));

    // HW-инструмент должен честно сказать, что устройства нет
    // (ошибка приходит как результат с isError=true, текст — в content)
    let hwErr = '', hwText = '';
    try { hwText = await client.callToolText('hold_bus', {}); } catch (e) { hwErr = e.message; }
    check('hold_bus: Device not connected', /not connected/i.test(hwErr + ' ' + hwText), (hwErr + ' | ' + hwText).slice(0, 120));
  } catch (e) {
    check('MCP-сценарий', false, String(e));
  } finally {
    await client.stop();
    check('сервер остановлен', !client.isRunning);
  }

  console.log(`\n=== ИТОГ: ${passed} passed, ${failed} failed ===`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('FATAL:', e); process.exit(2); });
