# MCP Image Video Generation Server

一个免费生成图像和视频的 MCP (Model Context Protocol) 服务器，支持 BigModel AI 平台的 CogView 和 CogVideoX 模型。

## 功能

- 🎨 **图像生成**: 使用 CogView 模型（cogview-4, cogview-4-250304, cogview-3-flash）生成高质量图像，默认使用 cogview-3-flash 免费模型
- 🚀 **批量图像生成**: **[新功能]** 支持一次性生成1-100张图像，具备并行处理和灵活批次管理能力
- 🎬 **视频生成**: 使用 CogVideoX 模型（cogvideox-3, cogvideox-2, cogvideox-flash）生成视频，默认使用 cogvideox-flash 模型
- ⚙️ **配置管理**: 支持环境变量配置和动态设置更新
- 🔄 **异步处理**: 支持视频生成任务状态查询和自动等待完成
- 🛡️ **错误处理**: 内置重试机制和详细错误信息
- 📝 **TypeScript**: 完整的类型安全支持
- 🔧 **调试支持**: 内置 MCP Inspector 和 VS Code 调试配置
- 🎯 **无水印**: 默认生成无水印内容（可以在 bigmodel.cn 安全管理中去掉水印）

## 安装

```bash
pnpm add -g image-video-generation-mcp
```

## API Key 申请

在使用本服务器之前，您需要在 BigModel.cn 平台申请 API Key。

### 申请步骤

1. **访问 BigModel 开放平台**

   - 打开浏览器访问：[https://www.bigmodel.cn/claude-code?ic=QHPPFCALMK](https://bigmodel.cn/)
   - 点击右上角"登录"或"注册"

2. **注册/登录账号**

   - 使用手机号或邮箱注册账号
   - 完成实名认证（根据平台要求）
   - 登录到开发者控制台

3. **获取 API Key**
   - 点击右上角头像，找到 API Key 后点击进入
   - 添加新的 API Key（注意保密）

### 费用说明

- **免费额度**: 新用户通常会获得一定的免费调用额度
- **计费方式**: 按实际调用次数和资源使用量计费
- **余额查询**: 在控制台可以查看余额和使用情况
- **充值方式**: 支持多种在线充值方式

### 模型定价

| 模型类型 | 模型名称        | 费用类型    | 推荐场景             |
| -------- | --------------- | ----------- | -------------------- |
| 图像生成 | cogview-3-flash | 免费/低成本 | 快速原型、日常使用   |
| 图像生成 | cogview-4       | 付费        | 高质量图像、专业用途 |
| 视频生成 | cogvideox-flash | 免费        | 快速视频生成         |
| 视频生成 | cogvideox-3     | 付费        | 标准质量视频         |

> 💡 **建议**: 开发和测试阶段建议使用免费模型（cogview-3-flash），生产环境根据需求选择付费模型。

### API Key 使用注意事项

- 🔒 **保密**: API Key 相当于密码，请勿在代码仓库中公开
- ✅ **权限**: 确保 API Key 有权限访问所需的模型服务
- 🔄 **轮换**: 定期更换 API Key 以提高安全性
- 📊 **监控**: 定期检查 API 使用量和费用情况

## 配置

设置环境变量：

```bash
export IMAGE_VIDEO_GENERATION_API_KEY="your_api_key_here"
export IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL="cogview-3-flash"
export IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL="cogvideox-flash"
```

或创建配置文件 `.image-video-generation-config.json`：

```json
{
  "apiKey": "your_api_key_here",
  "defaultImageModel": "cogview-3-flash",
  "defaultVideoModel": "cogvideox-flash",
  "timeout": 30000,
  "maxRetries": 3
}
```

## 使用方法

### 作为 MCP 服务器使用

在你的 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "image-video-generation": {
      "command": "npx",
      "args": ["-y", "image-video-generation-mcp@latest"],
      "env": {
        "IMAGE_VIDEO_GENERATION_API_KEY": "your_api_key"
      },
      "type": "stdio"
    }
  }
}
```

> **重要说明**: MCP 服务器通过 stdio 进行通信，所以直接运行 `npx image-video-generation-mcp@latest` 会看起来像是"卡住"或"无法运行"，这是正常现象。服务器正在等待来自 MCP 客户端的输入。

> **注意**: 模型配置是可选的，如果不设置环境变量，将使用默认模型：
>
> - 默认图像模型: `cogview-3-flash`
> - 默认视频模型: `cogvideox-flash`

### 环境变量说明

| 环境变量                                     | 必需 | 默认值            | 说明             |
| -------------------------------------------- | ---- | ----------------- | ---------------- |
| `IMAGE_VIDEO_GENERATION_API_KEY`             | ✅   | -                 | API 密钥         |
| `IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL` | ❌   | `cogview-3-flash` | 默认图像生成模型 |
| `IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL` | ❌   | `cogvideox-flash` | 默认视频生成模型 |

### 支持的工具

#### 1. generate_image

生成单张图像，支持以下参数：

- `prompt` (必需): 图像描述文本
- `model`: 模型选择 (`cogview-4`, `cogview-4-250304`, `cogview-3-flash`)
- `quality`: 图像质量 (`standard`, `hd`)
- `size`: 图像尺寸 (例如 `1024x1024`)
- `watermark_enabled`: 是否添加水印
- `user_id`: 用户追踪 ID

#### 2. batch_generate_images 🆕

**[新功能]** 批量生成多张图像，支持1-100个提示词，具备并行处理能力。

**基础参数：**
- `prompts` (必需): 提示词数组，最多100个
- `model`: 模型选择 (`cogview-4`, `cogview-4-250304`, `cogview-3-flash`)
- `quality`: 图像质量 (`standard`, `hd`)
- `size`: 图像尺寸 (例如 `1024x1024`)
- `watermark_enabled`: 是否添加水印
- `user_id`: 用户追踪 ID

**批次管理参数：**
- `batch_size`: 每批处理的提示词数量 (1-20，默认4)
- `parallel`: 是否并行处理 (默认true)
- `max_concurrent`: 最大并发数 (1-10，默认3)
- `delay_between_batches`: 批次间延迟(毫秒，0-10000，默认1000)

**使用示例：**
```json
{
  "prompts": ["小猫玩耍", "城市夜景", "程序员工作"],
  "model": "cogview-3-flash",
  "batch_size": 3,
  "parallel": true,
  "max_concurrent": 2
}
```

📖 **详细使用指南**: [BATCH_GENERATION_GUIDE.md](./BATCH_GENERATION_GUIDE.md)

#### 3. generate_video

生成视频，支持以下参数：

- `prompt` (必需): 视频描述文本 (最大 512 字符)
- `model`: 模型选择 (`cogvideox-3`, `cogvideox-2`, `cogvideox-flash`)
- `quality`: 输出质量模式 (`speed`, `quality`)
- `size`: 视频分辨率 (例如 `1920x1080`)
- `fps`: 帧率 (30, 60)
- `duration`: 视频时长 (5, 10 秒)
- `with_audio`: 是否启用 AI 生成音频
- `watermark_enabled`: 是否控制水印

#### 4. query_video_result

查询异步视频生成任务结果：

- `task_id` (必需): 视频生成任务返回的 ID

#### 5. wait_for_video

等待视频生成完成并返回结果：

- `task_id` (必需): 任务 ID
- `max_wait_time`: 最大等待时间 (默认 300000 毫秒)
- `poll_interval`: 轮询间隔 (默认 5000 毫秒)

#### 6. configure_models

配置默认模型和设置：

- `default_image_model`: 默认图像生成模型
- `default_video_model`: 默认视频生成模型
- `timeout`: 请求超时时间
- `max_retries`: 最大重试次数

## 默认模型

- **图像生成**: `cogview-3-flash` (免费模型，快速生成)
- **视频生成**: `cogvideox-flash` (快速视频生成)

## 开发

```bash
# 克隆项目
git clone https://github.com/156554395/image-video-generation-mcp.git
cd image-video-generation-mcp

# 安装依赖
pnpm install

# 开发模式
pnpm dev

# 运行测试
pnpm test

# 构建
pnpm build
```

## 发布

### 发布到 npm

```bash
# 登录 npm（如果尚未登录）
npm login

# 发布新版本
pnpm release

# 或者手动发布
pnpm build
pnpm test
npm publish
```

### 发布脚本说明

- `prepublishOnly`: 发布前自动构建和测试
- `prepack`: 打包前自动构建
- `release`: 完整的发布流程（构建 → 测试 → 发布）

### 发布文件说明

通过 `package.json` 中的 `files` 字段和 `.npmignore` 文件，发布包将只包含：

**包含的文件：**

- `dist/` - 构建后的 JavaScript 和 TypeScript 声明文件
- `README.md` - 项目文档
- `LICENSE` - 许可证文件

**排除的文件：**

- `src/` - 源代码目录
- `scripts/` - 开发脚本
- 测试文件和调试文件
- 配置文件和开发工具文件

### 版本管理

```bash
# 更新补丁版本 (1.0.0 -> 1.0.1)
npm version patch

# 更新次版本 (1.0.0 -> 1.1.0)
npm version minor

# 更新主版本 (1.0.0 -> 2.0.0)
npm version major

# 预发布版本 (1.0.0 -> 1.0.1-beta.0)
npm version prerelease --preid=beta
```

## 调试

### 使用 VS Code 调试

1. **使用 VS Code 调试配置**：

   - 打开 VS Code
   - 按 `F5` 或点击调试面板
   - 选择 "Debug MCP Server" 配置
   - 设置断点并开始调试

2. **调试配置选项**：
   - `Debug MCP Server`: 普通调试模式
   - `Debug MCP Server (Break at Start)`: 启动时暂停
   - `Debug Tests`: 调试测试代码

### 使用命令行调试

1. **启动调试服务器**：

   ```bash
   # 构建项目
   pnpm build

   # 启动调试（在第一行断点）
   pnpm debug:break

   # 或者启动调试（不在第一行断点）
   pnpm debug
   ```

2. **使用 Chrome DevTools**：

   - 打开 Chrome 浏览器
   - 访问 `chrome://inspect`
   - 点击 "Open dedicated DevTools for Node"
   - 在 DevTools 中查看和控制调试

3. **使用 Node Inspector**：

   ```bash
   # 使用 inspector
   node --inspect --inspect-port=9229 dist/index.js

   # 使用 inspector-brk（启动时暂停）
   node --inspect-brk --inspect-port=9229 dist/index.js
   ```

### 调试环境变量

```bash
# 设置调试环境变量
export NODE_ENV=development
export DEBUG=mcp:*
```

### 使用 MCP Inspector (推荐)

1. **启动 MCP Inspector**：

   ```bash
   # 构建项目
   pnpm build

   # 使用 MCP Inspector（推荐方式）
   pnpm inspector

   # 或者直接使用 npx
   pnpm inspector:direct
   ```

2. **MCP Inspector 功能**：

   - 🎯 **可视化调试**: 直观的 Web 界面调试 MCP 服务器
   - 🛠️ **工具测试**: 直接在浏览器中测试所有 MCP 工具
   - 📝 **实时日志**: 查看服务器日志和调试信息
   - 🔧 **参数编辑**: 动态修改请求参数进行测试
   - 📊 **响应预览**: 查看工具执行的详细响应

3. **Inspector 使用方法**：
   - 运行 `pnpm inspector` 命令
   - 浏览器会自动打开 Inspector 界面
   - 在左侧选择要测试的工具
   - 填写参数并点击"Execute"执行
   - 在右侧查看执行结果和日志

### 调试技巧

- **断点调试**: 在源代码中设置断点，调试器会在这些点暂停执行
- **控制台输出**: 使用 `console.log()` 输出调试信息
- **变量监视**: 在调试器中监视变量值的变化
- **调用堆栈**: 查看函数调用链，了解程序执行流程
- **热重载**: 使用 `pnpm dev` 进行开发，自动重新编译
- **MCP Inspector**: 最佳调试方式，提供完整的可视化和交互功能

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

### 开发指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 贡献者

感谢所有为这个项目做出贡献的开发者！

## 故障排除

### MCP 连接问题

如果遇到 MCP 连接不上的问题，请检查以下几点：

1. **API Key 配置**：确保已正确设置 `IMAGE_VIDEO_GENERATION_API_KEY` 环境变量
   ```bash
   # 测试 API Key 是否正确配置
   IMAGE_VIDEO_GENERATION_API_KEY=your_api_key npx image-video-generation-mcp@latest
   ```

2. **网络连接**：确保能访问 `https://open.bigmodel.cn/api`

3. **版本问题**：使用最新版本
   ```bash
   # 清除 npm 缓存并使用最新版本
   npm cache clean --force
   npx -y image-video-generation-mcp@latest
   ```

4. **配置文件格式**：确保 MCP 配置文件格式正确
   ```json
   {
     "mcpServers": {
       "image-video-generation": {
         "command": "npx",
         "args": ["-y", "image-video-generation-mcp@latest"],
         "env": {
           "IMAGE_VIDEO_GENERATION_API_KEY": "your_actual_api_key_here"
         },
         "type": "stdio"
       }
     }
   }
   ```

5. **错误日志**：如果仍有问题，请查看 MCP 客户端的错误日志

### 常见错误

- **"API Key is required"**：需要设置 `IMAGE_VIDEO_GENERATION_API_KEY` 环境变量
- **"command not found"**：npm 缓存问题，尝试清除缓存或等待几分钟
- **连接超时**：检查网络连接和防火墙设置

## 支持

如有问题，请提交 [GitHub Issues](https://github.com/156554395/image-video-generation-mcp/issues)。

## 相关链接

- [BigModel API 文档](https://docs.bigmodel.cn/)
- [MCP 协议](https://modelcontextprotocol.io/)
