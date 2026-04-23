# HuangweiqingClaw

**HuangweiqingClaw** 是一个基于 **OpenClaw** 架构深度演进、完全**个人自研**的多模态 AI Agent 核心控制引擎。

我写这个项目的初衷，是为了解决目前市面上开源 Agent 框架（如原生 LangChain Agent）在长文本截断、动态技能加载上不够灵活的问题。它不仅是一个简单的“调包”脚本，而是一个拥有底层操作系统控制权、数据库访问权、网络调度权以及长短期记忆能力的全自动化智能体编排系统。通过赋予大模型（LLM）执行本地 CLI 命令、读写文件、操作 MySQL 数据库、发起 HTTP 请求的能力，实现用自然语言直接驱动复杂的本地自动化服务。

---

## ✨ 核心特性

- 🧠 **多厂商大模型无缝接入**
  底层基于 `LangChainLLMFactory` 工厂模式构建，完美兼容 LangChain 生态。支持一键切换 `DeepSeek`、`OpenAI`、`Gemini`、`Ollama`(本地模型) 等，彻底解耦业务逻辑与模型基座。
  
- 📜 **独创 Agentic Skills 动态技能加载机制**
  摒弃传统的 Python 硬编码工具函数，我首创了基于 Markdown 文档的动态技能说明书。Agent 可通过自主阅读 `skills/` 目录下的 Markdown 文档，像人类开发者一样学习第三方 API 接口协议并动态发起 HTTP 调度。极大降低了新业务的接入成本。
  
- 📦 **自研上下文治理与降维算法**
  针对真实业务场景中 Agent 执行复杂任务时常见的 **Token 爆炸/溢出** 痛点，我自研了以下机制：
  - **动态文本压缩降维算法**：利用大模型二次摘要过长的历史记录或报错信息，避免挤占主流程的 Token。
  - **分页切块读取机制**：读取超大文件或抓取超长 DOM 节点时，自动进行分块（Chunking）拦截，保障程序长期运行不崩溃。

- 💾 **高可用工具链与 Long-term Memory**
  - **跨平台 CLI 执行器**：支持自动识别 Windows/Linux 编码（UTF-8/GBK），内置防死循环超时保护机制。
  - **数据库与网络请求**：内置读写分离的 MySQL 执行器和健壮的 Requests 请求工具。
  - **持久化记忆流**：基于 MySQL `TbAgentMessage` 表存储对话，通过异步后台 `summary_prompt` 自动生成“核心记忆快照”，实现长短期记忆的无缝流转。

---

## 🛠️ 项目架构

```text
huangweiqingclaw/
├── _model/           # 提示词模型与系统内置 prompt (如自我认知、技能说明书组装)
├── claw/             
│   ├── claw.py       # Agent 核心调度引擎，负责状态图流转流式输出及上下文压缩
│   └── llm_client.py # 大模型工厂模式封装，提供统一的 BaseChatModel
├── common/           # 通用工具类与 MySQL 数据库连接池封装
├── curd/             # 数据库操作层 (Agent 记忆流读写)
├── logs/             # 系统运行日志
├── memory/           # 持久化存储与记忆管理
├── setting/          # 全局配置文件 (数据库、超时配置等)
├── skills/           # 核心：动态技能 Markdown 目录
│   └── whatsapp/     # WhatsApp API 接口文档 (供大模型自主学习阅读)
└── tool/             # 硬编码底层工具链 (CLI执行、SQL执行、HTTP请求、文件读写)
```

---

## 🚀 快速开始

### 1. 环境准备

- Python 3.10+
- 推荐使用虚拟环境：
  ```bash
  python -m venv venv
  source venv/bin/activate  # Linux/Mac
  venv\Scripts\activate     # Windows
  ```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库与环境变量

请确保在 `setting/setting.py` 中正确配置了你的 MySQL 数据库连接参数（`huangweiqingclaw_mysql_config`），以保障长期记忆功能的正常工作。

### 4. 运行 Agent

在 `claw/claw.py` 中配置你所使用的模型厂商和 API Key：

```python
from claw.claw import HuangwqClaw

# 实例化 Agent 引擎
claw = HuangwqClaw(
    model_manufacturer='deepseek',
    model_name='deepseek-chat',
    base_url='https://api.deepseek.com',
    api_key='your_api_key_here'
)

# 启动任务
response = claw.work(
    user_id='huangweiqing',
    user_input='你给whatsapp号码:************... 发送一条文本信息, 内容是:我是一条群发消息'
)
print(response)
```

---

## 📞 关于 WhatsApp 自动化服务 (特别声明)

本项目 `skills/whatsapp/whatsapp_api.md` 中描述的 **WhatsApp API 服务** 并非本项目自带，而是 **我本人另外独立开发并运行在本地 `127.0.0.1:8000` 端口的另一个微服务项目**。

> **设计初衷**：
> 这里之所以不将 WhatsApp 的 Python 代码揉进主仓库，是为了验证本项目的 **Agentic Skills (动态技能)** 能力。
> Agent 根本不需要知道底层的 WhatsApp 代码是怎么写的，它只需要像人类开发者一样，阅读这份 `whatsapp_api.md` 接口文档，就能理解如何扫码登录、如何鉴权、如何发送消息，并利用内置的 `request_tool` 主动对该微服务发起 HTTP 请求。

如果你想要测试 WhatsApp 技能，请确保你已经在本地启动了配套的 WhatsApp FastAPI 服务。

---

## 🛡️ 常见问题 (FAQ)

**Q: 为什么 Agent 会返回 `[已压缩]: xxxx`？**
A: 这是我手写的上下文降维机制触发了。当命令行工具或文件读取返回的内容超过设定阈值时，引擎会自动开辟一条独立调用，利用 LLM 对冗长内容进行摘要，防止主流程上下文 Token 溢出。

**Q: 为什么 CLI 执行器会报错超时？**
A: `execute_cli_tool` 内置了 120 秒的硬超时保护机制。如果 Agent 执行了需要人类交互（如 `python script.py` 遇到 `input()`）的命令，为防止进程僵死，会主动切断并返回报错让 Agent 自我纠错。
