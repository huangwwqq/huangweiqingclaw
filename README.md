# 🦅 HuangweiqingClaw

**HuangweiqingClaw** 是一个多模态 AI Agent 编排引擎，基于 LangChain/LangGraph 构建，赋予大模型操作系统级执行能力、数据库访问能力、网络调度能力，以及可生长的长期记忆和动态技能加载机制。

不只是一个"套壳聊天机器人"——它真正让 LLM 作为调度中枢，驱动本地 CLI、HTTP 请求、MySQL/Milvus/MinIO 数据库、Playwright 浏览器、MCP 协议工具等一系列底层能力协同工作。

---

## ✨ 核心能力

### 🧠 多厂商模型无缝接入

通过 `LangChainLLMFactory` 工厂模式统一封装，一套代码兼容 DeepSeek、OpenAI、Gemini、Ollama（本地模型）等主流平台。切换模型只需改参数，业务逻辑零改动。

### 📜 Agentic Skills —— 动态技能文档加载

这是本项目最特别的设计：Agent 的能力不是写死在 Python 代码里的，而是通过阅读 `skills/` 目录下的 Markdown 技能文档**动态学习**的。

每个技能文档就是一份"API 使用说明书"，Agent 像人类开发者一样阅读文档，然后用内置的 HTTP 工具主动调用对应的服务。接新产品、换业务，只需新写一份 Markdown，不必动一行 Python 代码。

同时借鉴了 `Kocoro` 的技能组织思路：

- `system prompt` 默认只注入技能目录摘要，避免把全部技能全文硬塞进上下文
- 每轮会根据当前任务和附件类型动态挑选最相关的技能正文注入
- 额外提供 `use_skill_tool`，允许 Agent 在执行过程中显式拉取某个技能的完整说明

当前内置技能：

| 技能 | 说明 |
|------|------|
| `whatsapp` | WhatsApp 多账号消息收发（配合独立微服务使用） |
| `knowledge_operation` | Milvus 知识库的增删改查与文档入库策略 |
| `web_search` | Playwright 驱动的联网搜索 |
| `image-video-generation` | 智谱 BigModel 图像/视频生成（MCP 协议） |
| `file_operation` | 文件读写约束，防止 Agent 误读二进制文件污染上下文 |

### 📚 可生长的 RAG 知识库

深度集成 **Milvus** 向量数据库与 **MinIO** 对象存储，提供从文档入库到语义检索的完整链路：

- **一键入库** — 支持 PDF、Docx、Markdown、TXT、XLSX、PPTX 的自动解析、分块（可配正则+块大小）、向量化嵌入并批量存入 Milvus
- **语义检索** — 自然语言查询，自动向量化后搜索最相关内容
- **完整 CRUD** — AGent 可自主对知识库执行增删改查，知识库是"活着"的

### 📦 上下文治理：Token 防溢出机制

复杂任务中，超长的工具返回结果和历史消息容易挤爆上下文窗口。本项目的处理方式：

- **初步截断** — 超过阈值（默认 80,000 字符）时保留前 1/4 和后 1/4，中间省略
- **LLM 二次压缩** — 截断后仍过长时，异步调用 LLM 对内容做摘要提炼
- **分块读取** — 文件操作和终端输出均支持分块返回，避免单次读取炸掉上下文
- **附件分流** — 文档附件提取文本片段，图片附件只保留尺寸/格式等元信息，避免把二进制污染上下文

### 💾 长短期记忆系统

基于 MySQL 持久化存储对话记录，后台自动生成"核心记忆快照"：

- 每次对话结束后，异步调用 LLM 对操作过程做摘要
- 下一次对话时，提取最近 N 条摘要作为历史背景注入 system prompt
- 实现跨会话的记忆连续性，同时避免无限制膨胀

### 🔧 全栈工具链

内置 15 个可调用工具（含 MCP 动态加载）：

| 类别 | 工具 | 说明 |
|------|------|------|
| 数据库 | `execute_mysql_sql` | MySQL 读写执行，自动识别 SELECT/DDL |
| 网络 | `request_tool` | HTTP 请求，自动处理 JSON 压缩与 HTML 清洗 |
| 系统 | `execute_cli_tool` | 命令行执行，跨平台编码识别，120s 超时保护 |
| 技能 | `use_skill_tool` | 按需加载某个技能的完整正文，避免全量技能常驻上下文 |
| 文件 | `file_operation_tool` | 文件读写追加，支持分块读取，禁止读取二进制 |
| 文档 | `pdf_to_text_tool` / `docx_to_text_tool` / `xlsx_to_text_tool` / `pptx_to_text_tool` | 专门提取文档文本，避免误用普通文件读取 |
| 搜索 | `web_search_tool` | Playwright 无头浏览器搜索，百度优先，智能反爬处理 |
| 存储 | MinIO 全套 | 对象存储的增删改查 |
| 向量库 | Milvus 全套 | 向量数据的增删改查 + 文件批量入库 |
| 下载 | `url_download_tool` | URL 文件下载，自动识别类型 |
| MCP | 动态加载 | 通过 MCP 协议接入外部工具（如智谱图像生成） |

---

## 🏗️ 项目结构

```text
huangweiqingclaw/
├── claw/                    # Agent 核心引擎
│   ├── claw.py              # 主调度器：状态流、上下文压缩、记忆管理、流式输出
│   └── llm_client.py        # LLM 工厂：DeepSeek / OpenAI / Gemini / Ollama
├── tool/                    
│   └── tool.py              # 工具集：CLI / HTTP / MySQL / Milvus / MinIO / Playwright
├── common/                  # 基础设施层
│   ├── common.py            # 技能扫描、自我认知、文本向量化、PDF/Docx 解析、分块
│   ├── db_mysql.py          # MySQL 连接池封装（DBUtils）
│   ├── db_milvus.py         # Milvus 连接池封装（Queue-based）
│   ├── db_minio.py          # MinIO 连接池封装（Queue-based）
│   └── mcp_compatible.py    # MCP 协议兼容层（stdio / SSE / Streamable HTTP）
├── _model/
│   └── model.py             # Pydantic 参数校验模型（全部工具 schema + 数据表定义）
├── curd/huangweiqingclaw/   # 数据访问层
│   ├── tb_agent_message.py  # 对话记录 CRUD
│   └── tb_model_config.py   # 模型配置 CRUD
├── setting/
│   └── setting.py           # 全局配置中心（数据库、LLM、日志、MCP、阈值等）
├── skills/                  # Agentic Skills 技能文档目录
│   ├── whatsapp/
│   ├── knowledge_operation/
│   ├── web_search/
│   ├── image-video-generation/
│   └── file_operation/
├── mcp_tool/                # MCP 子项目
│   └── image-video-generation-mcp/  # TypeScript MCP 服务（智谱 BigModel 图像/视频）
├── memory/
│   └── user.md              # 用户身份与对话风格记忆
└── requirements.txt         # Python 依赖
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+（使用 MCP 工具时需要）
- MySQL 8.0+（必要，用于对话记忆与用户认知存储）
- Milvus（可选，用于知识库向量检索）
- MinIO（可选，用于对象存储）

```bash
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 前置准备 —— 数据库初始化

#### 3.1 MySQL（必要）

项目依赖 MySQL 存储对话记录、用户自我认知和模型配置。请先创建数据库并建立以下 3 张表：

##### ① 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS `huangweiqingclaw`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;
```

##### ② 建表：model_config（模型配置表）

存储 LLM 厂商、模型名称、API Key 等配置信息。

```sql
CREATE TABLE `model_config` (
  `id` int NOT NULL COMMENT '主键',
  `model_manufacturer` varchar(255) NOT NULL DEFAULT '' COMMENT '模型厂商',
  `model_name` varchar(255) NOT NULL DEFAULT '' COMMENT '模型名称',
  `base_url` varchar(255) NOT NULL DEFAULT '' COMMENT '模型的请求API',
  `api_key` varchar(255) NOT NULL DEFAULT '' COMMENT 'apikey',
  `is_delete` int NOT NULL DEFAULT '0' COMMENT '默认为0不删除,1为已删除',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_key` (`model_manufacturer`,`model_name`),
  KEY `nro_model_name` (`model_name`),
  KEY `update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

##### ③ 建表：agent_message（对话记录表）

存储用户与 Agent 的每一轮对话，支持 5 种角色（system / agent / Tool / user / summary）。

```sql
CREATE TABLE `agent_message` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` varchar(255) NOT NULL DEFAULT '' COMMENT '用户id',
  `message_id` varchar(255) NOT NULL DEFAULT '' COMMENT '会话id',
  `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '角色,有5种角色:system(系统),agent(智能体),Tool(工具),user(用户),summary(总结)',
  `message` text NOT NULL COMMENT '对话',
  `file_url_list` json NOT NULL COMMENT '文件url列表',
  `is_delete` int NOT NULL DEFAULT '0' COMMENT '是否删除,默认为0,1为软删除',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `nro_message_id` (`message_id`),
  KEY `nro_create_time` (`create_time`),
  KEY `nro_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='智能体对话列表';
```

##### ④ 建表：self_awareness（用户自我认知表）

存储用户画像数据：昵称、年龄、学历、职业、对话风格偏好等，userid 唯一索引。

```sql
CREATE TABLE `self_awareness` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `userid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '用户ID，唯一索引',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '用户昵称，普通索引',
  `age` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '年龄',
  `birthday` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '生日',
  `education` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '学历',
  `school` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '毕业院校',
  `company` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '当前任职公司',
  `position` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '职位',
  `occupation` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '职业',
  `dialogue_style` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '与AI的对话风格',
  `ai_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT 'AI的名称',
  `other` text COMMENT '其他说明',
  `is_delete` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除 0-不删除 1-删除',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_userid` (`userid`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户自我认知表';
```

##### ⑤ 初始化用户认知（可选但推荐）

首次使用前，建议插入一条用户认知记录，让 Agent 了解你的基本信息和对话偏好：

```sql
INSERT INTO `self_awareness` (`userid`, `name`, `dialogue_style`, `ai_name`, `other`)
VALUES ('your_user_id', '你的昵称', '简洁、专业', '你的AI助手名', '其他补充说明');
```

> 以上建表语句也以 Pydantic Model docstring 的形式内嵌在 [_model/model.py](file:///d:/work_place/huangweiqingclaw/_model/model.py) 中，方便查阅对照。

#### 3.2 Milvus（可选，用于知识库）

如果你需要使用知识库（RAG）功能，请启动 Milvus 向量数据库（推荐使用 Docker 或 Milvus Lite）：

```bash
# Docker 方式启动 Milvus Standalone
docker run -d --name milvus-standalone \
  -p 19530:19530 -p 9091:9091 \
  milvusdb/milvus:latest
```

#### 3.3 MinIO（可选，用于文件存储）

如果需要对文件进行对象存储管理，请启动 MinIO：

```bash
# Docker 方式启动 MinIO
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### 4. 配置

编辑 `setting/setting.py`，按需配置各个服务的连接信息：

```python
# MySQL（必要，用于记忆存储）
huangweiqingclaw_mysql_config = {
    'host': '127.0.0.1', 'port': 3306,
    'user': 'root', 'passwd': 'your_password',
    'db': 'huangweiqingclaw', 'charset': 'utf8mb4'
}

# Milvus（用于知识库，可选）
milvus_config = {'uri': "http://localhost:19530"}

# MinIO（用于文件存储，可选）
minio_config = {
    'endpoint': '127.0.0.1:9000',
    'access_key': 'minioadmin', 'secret_key': 'minioadmin',
    'secure': False
}

# 嵌入模型（用于知识库向量化，可选）
embedding_config = {
    "api_key": "your_key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "text-embedding-v4",
    "dim": 1024
}
```

### 5. 启动

```python
from claw.claw import HuangwqClaw

claw = HuangwqClaw(
    model_manufacturer='deepseek',
    model_name='deepseek-chat',
    base_url='https://api.deepseek.com',
    api_key='your_api_key'
)

response = claw.work(
    user_id='huangweiqing',
    user_input='帮我把 外贸手册.pdf 上传到 trade 库的 foreign_trade_knowledge 集合中',
    file_url_path_list=['https://example.com/files/外贸手册.pdf']
)
```

---

## 🤖 关于 WhatsApp 技能

`skills/whatsapp/whatsapp_api.md` 描述的 WhatsApp API 是一个**独立运行的微服务**（FastAPI，端口 8000），不包含在本仓库代码中。Agent 通过阅读这份接口文档，用 `request_tool` 主动调用该服务实现扫码登录、发送消息等功能——这正是 Agentic Skills 设计理念的典型体现：Agent 不需要知道底层实现，只读文档就能干活。

---

## 📋 常见问题

**Q: 命令行工具执行超时？**
A: `execute_cli_tool` 内置 120 秒硬超时。如果命令需要交互输入（如 `input()`），会超时返回让 Agent 自行纠错。

**Q: 为什么 Agent 返回 `[已压缩]: xxx`？**
A: 上下文压缩机制被触发了——超长的工具返回或历史记录被 LLM 二次摘要压缩，防止主流程 Token 溢出。

**Q: Agent 为什么不会读图片/PDF 文件？**
A: `file_operation_tool` 内置了二进制文件拦截逻辑，同时 `skills/file_operation/` 技能文档也会提醒 Agent 避免此操作。

---

## 💬 联系我

对 Agent 架构、动态技能加载、RAG 知识库等方向感兴趣，或有合作需求，欢迎微信交流：

<div align="center">
  <img src="wechat_qrcode.jpg" alt="半岛铁盒-广东江门" width="300" />
  <p><strong>半岛铁盒 (广东 江门)</strong></p>
  <p><em>扫二维码，添加我为朋友。</em></p>
</div>
