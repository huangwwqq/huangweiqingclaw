# MCP Inspector 测试指南

## 快速测试

1. **启动测试环境**：
   ```bash
   # 设置测试环境变量
   export IMAGE_VIDEO_GENERATION_API_KEY="test-key-for-inspector"
   export IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL="cogview-4"
   export IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL="cogvideox-3"

   # 构建
   pnpm build

   # 启动 Inspector
   pnpm inspector
   ```

2. **预期行为**：
   - 浏览器自动打开 MCP Inspector 界面
   - 显示可用的工具：`generate_image`, `generate_video`, `query_video_result`, `wait_for_video`, `configure_models`
   - 可以查看服务器启动日志

3. **测试工具**：
   - 选择 `generate_image` 工具
   - 输入简单的提示词，如 "a cat sitting on a table"
   - 点击执行查看响应

4. **测试配置**：
   - 选择 `configure_models` 工具
   - 修改默认模型设置
   - 验证配置是否生效

## 故障排除

如果 Inspector 无法启动：
1. 确保已安装 `@modelcontextprotocol/inspector`
2. 检查 Node.js 版本 >= 18.0.0
3. 确保项目已正确构建
4. 检查环境变量是否正确设置