# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Model Context Protocol (MCP) 的图像和视频生成服务器，使用 BigModel AI 平台的 CogView 和 CogVideoX 模型。项目使用 TypeScript 开发，通过 npm 包管理器 pnpm 进行依赖管理。

## 开发命令

### 构建和开发
```bash
# 安装依赖
pnpm install

# 开发模式（监听文件变化自动编译）
pnpm dev

# 构建
pnpm build

# 启动服务器
pnpm start

# 运行测试
pnpm test

# 代码检查
pnpm lint
```

### 调试命令
```bash
# 启动调试模式
pnpm debug

# 启动调试并在开始时暂停
pnpm debug:break

# 启动 MCP Inspector（推荐）
pnpm inspector

# 直接使用 MCP Inspector
pnpm inspector:direct
```

### 发布命令
```bash
# 完整发布流程（构建→测试→发布）
pnpm release

# 发布前准备
pnpm prepublishOnly
pnpm prepack
```

## 项目架构

### 核心模块

- **src/index.ts**: MCP 服务器主入口，定义了5个核心工具
  - `generate_image`: 图像生成工具
  - `generate_video`: 视频生成工具
  - `query_video_result`: 查询视频生成结果
  - `wait_for_video`: 等待视频生成完成
  - `configure_models`: 配置默认模型和设置

- **src/config.ts**: 配置管理模块
  - `Config` 类：管理 API 密钥、默认模型、超时等配置
  - 接口定义：`ImageVideoGenerationConfig`、`ImageGenerationParams`、`VideoGenerationParams` 等
  - 支持环境变量和配置文件两种配置方式

- **src/image-video-generation-client.ts**: API 客户端模块
  - `ImageVideoGenerationClient` 类：封装 BigModel API 调用
  - 实现重试机制、错误处理、异步视频状态查询
  - 支持图像生成、视频生成、结果查询三个主要功能

- **src/errors.ts**: 错误处理模块
  - 定义了 `ValidationError`、`ApiError`、`NetworkError` 等自定义错误类型

### 配置管理

项目支持两种配置方式：

1. **环境变量配置**：
   - `IMAGE_VIDEO_GENERATION_API_KEY`: API 密钥（必需）
   - `IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL`: 默认图像模型（可选，默认 cogview-3-flash）
   - `IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL`: 默认视频模型（可选，默认 cogvideox-flash）

2. **配置文件**：`.image-video-generation-config.json`

### 默认模型配置

- **图像生成**: `cogview-3-flash`（免费模型，快速生成）
- **视频生成**: `cogvideox-flash`（免费模型，快速视频生成）

## 调试

### 推荐调试方式：MCP Inspector

MCP Inspector 是最佳调试工具，提供可视化界面：

```bash
# 设置环境变量
export IMAGE_VIDEO_GENERATION_API_KEY="your_api_key"
export IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL="cogview-3-flash"

# 启动 Inspector
pnpm inspector
```

Inspector 功能：
- 🎯 可视化调试界面
- 🛠️ 工具测试和参数编辑
- 📝 实时日志查看
- 📊 响应结果预览

### VS Code 调试配置

项目包含 3 个调试配置：
- `Debug MCP Server`: 普通调试模式
- `Debug MCP Server (Break at Start)`: 启动时暂停调试
- `Debug Tests`: 调试测试代码

### 命令行调试

```bash
# 构建
pnpm build

# 启动调试（第一行断点）
pnpm debug:break

# 或使用 Chrome DevTools 访问 chrome://inspect
```

## 代码风格

- 使用 ES 模块 (import/export) 语法
- 优先使用解构导入
- TypeScript 严格模式
- ESLint 代码检查

## 测试

```bash
# 运行所有测试
pnpm test

# 单个测试文件调试
node --inspect-brk --inspect-port=9230 node_modules/.bin/jest --runInBand <test-file>
```

## 重要提醒

1. **API 密钥**: 开发前必须设置 `IMAGE_VIDEO_GENERATION_API_KEY` 环境变量
2. **构建优先**: 调试前先运行 `pnpm build` 构建 TypeScript 代码
3. **模型选择**: 图像生成和视频生成都默认使用免费模型
4. **异步处理**: 视频生成是异步的，需要使用 `query_video_result` 或 `wait_for_video` 工具获取结果
5. **错误处理**: 客户端内置重试机制，最多重试 3 次

## 发布注意事项

- 发布包只包含 `dist/` 目录、README.md 和 LICENSE 文件
- 源代码、测试文件、配置文件等不会包含在发布包中
- 使用 `pnpm release` 命令进行完整发布流程