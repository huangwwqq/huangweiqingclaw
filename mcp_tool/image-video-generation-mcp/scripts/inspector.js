#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('🔍 启动 MCP Inspector...');
console.log('📱 Inspector 将在浏览器中打开');
console.log('🔧 确保已设置环境变量:');
console.log('   - IMAGE_VIDEO_GENERATION_API_KEY');
console.log('   - IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL (可选)');
console.log('   - IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL (可选)');
console.log('');

// 启动 MCP Inspector，连接到我们的服务器
const inspectorProcess = spawn('npx', [
  '@modelcontextprotocol/inspector',
  'node',
  join(__dirname, '../dist/index.js')
], {
  stdio: 'inherit',
  cwd: dirname(__dirname),
  env: {
    ...process.env,
    NODE_ENV: 'development'
  }
});

inspectorProcess.on('error', (error) => {
  console.error('❌ Inspector 启动失败:', error.message);
  console.log('💡 请确保已安装 @modelcontextprotocol/inspector');
  process.exit(1);
});

inspectorProcess.on('close', (code) => {
  console.log(`🏁 Inspector 退出，代码: ${code}`);
  process.exit(code);
});

// 处理进程信号
process.on('SIGINT', () => {
  console.log('\n🛑 正在停止 Inspector...');
  inspectorProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('\n🛑 正在停止 Inspector...');
  inspectorProcess.kill('SIGTERM');
});