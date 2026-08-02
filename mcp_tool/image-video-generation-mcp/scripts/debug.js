#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 启动调试服务器
console.log('🔧 启动 MCP 调试服务器...');
console.log('📱 调试端口: 9229');
console.log('🌐 Chrome DevTools: chrome://inspect');
console.log('💡 或使用 VS Code 调试配置');
console.log('');

const debugProcess = spawn('node', [
  '--inspect',
  '--inspect-port=9229',
  join(__dirname, '../dist/index.js')
], {
  stdio: 'inherit',
  cwd: dirname(__dirname)
});

debugProcess.on('error', (error) => {
  console.error('❌ 调试启动失败:', error.message);
  process.exit(1);
});

debugProcess.on('close', (code) => {
  console.log(`🏁 调试进程退出，代码: ${code}`);
  process.exit(code);
});

// 处理进程信号
process.on('SIGINT', () => {
  console.log('\n🛑 正在停止调试服务器...');
  debugProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('\n🛑 正在停止调试服务器...');
  debugProcess.kill('SIGTERM');
});