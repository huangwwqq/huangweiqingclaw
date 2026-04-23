---
name: "whatsapp-api"
description: "用于操作本地 WhatsApp FastAPI 服务，支持二维码登录、联系人、个人信息、历史记录与消息发送；当用户想使用或排查此 session 型 API 时调用。"
---

# WhatsApp API 技能

当用户想操作当前工作区里的本地 WhatsApp 自动化 API 时，使用这个技能。它适用于二维码登录、检查账号状态、读取联系人、读取消息历史、发送文本、发送文件，以及排查 WhatsApp 会话不可用等问题。

## 适用范围

这个技能面向当前工作区中实现的本地 FastAPI 服务。

- 服务地址：`http://127.0.0.1:8000`
- API 风格：基于 `session_id` 的会话型接口
- 鉴权方式：没有 token 鉴权；是否可用取决于 WhatsApp 登录状态
- 主要代码来源：
  - `whatsapp_python/main.py`
  - `whatsapp_python/client_manager.py`
  - `API_DOCS.md`

## 什么时候调用

当用户提出以下需求时，应调用这个技能：

- 获取或查看 WhatsApp 二维码
- 登录某个 WhatsApp 会话
- 检查某个 WhatsApp 账号是否已连接
- 获取当前登录账号信息
- 拉取联系人
- 拉取内存中的消息历史
- 给某个 WhatsApp 号码发送文本
- 发送图片、视频、音频或文档
- 排查二维码、登录、联系人、历史记录或发送消息失败的问题

不要把这个技能用于无关的浏览器自动化、无关的 REST API，或绕过本地 API 直接抓取 WhatsApp Web。

## 服务模型

这个服务通过 `session_id` 隔离多个 WhatsApp 会话。

- 无需登录即可访问的接口：
  - `GET /`
  - `GET /{session_id}/qr`
  - `GET /{session_id}/qr-view`
- 必须登录后才能访问的接口：
  - `GET /{session_id}/contacts`
  - `POST /{session_id}/messages/send`
  - `GET /{session_id}/history`
  - `GET /{session_id}/me`

标准成功响应：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

标准未登录响应：

```json
{
  "code": -1,
  "msg": "未登录,请重新登录",
  "data": null
}
```

## 核心流程

除非用户明确要求别的方式，否则按下面顺序执行：

1. 先确认或选择一个 `session_id`。
2. 如果是新会话或未知会话，调用 `GET /{session_id}/qr`，或者直接打开 `GET /{session_id}/qr-view`。
3. 等待出现以下状态之一：
   - `qr_generated`
   - `connected`
   - `waiting`
4. 登录完成后，用 `GET /{session_id}/me` 进行确认。
5. 只有确认已登录后，再调用联系人、历史记录或发送消息接口。

如果用户说“拿不到二维码”，按下面顺序排查：

1. 先调用 `GET /{session_id}/qr`。
2. 如果一直返回 `waiting`，就检查服务日志。
3. 看是否有连接错误或依赖错误，例如客户端库版本过旧。
4. 检查 `whatsapp_python/sessions/` 下是否存在旧的会话数据库文件。

## 接口说明

### 1. 获取二维码状态

`GET /{session_id}/qr`

作用：
- 如果需要，会自动初始化会话
- 返回二维码生成状态

可能的返回结果：

- 已生成二维码：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "qr_code": "base64_encoded_qr_string",
    "status": "qr_generated"
  }
}
```

- 已经连接：

```json
{
  "code": 0,
  "msg": "Already connected",
  "data": {
    "status": "connected"
  }
}
```

- 仍在等待：

```json
{
  "code": 0,
  "msg": "Waiting for QR code generation",
  "data": {
    "status": "waiting"
  }
}
```

### 2. 浏览器查看二维码

`GET /{session_id}/qr-view`

作用：
- 以 HTML 页面形式渲染二维码
- 每 5 秒自动刷新一次

当用户想直接在浏览器里看到可扫码页面时，用这个接口。

### 3. 获取当前账号信息

`GET /{session_id}/me`

用这个接口确认是否已登录，以及当前激活的是哪个 WhatsApp 账号。

典型返回字段：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "jid": "1234567890@s.whatsapp.net",
    "phone": "1234567890",
    "name": "1234567890",
    "lid": "123456789@lid",
    "platform": "android"
  }
}
```

### 4. 获取联系人

`GET /{session_id}/contacts`

登录成功后，用这个接口获取已同步的联系人列表。

单个联系人典型结构：

```json
{
  "jid": "1234567890@s.whatsapp.net",
  "name": "张三"
}
```

### 5. 发送消息

`POST /{session_id}/messages/send`

请求类型：

```text
multipart/form-data
```

表单字段：

- `phone`：必填
- `message`：可选
- `file`：可选

规则：

- `message` 和 `file` 至少要传一个
- 如果 `message` 和 `file` 同时存在，`message` 会作为文件的 caption
- 文件类型按 MIME 自动推断
- 不支持或无法识别的文件类型会按文档消息发送

典型成功返回字段：

```json
{
  "code": 0,
  "msg": "sent",
  "data": {
    "id": "3EB0...",
    "sender_jid": "me@s.whatsapp.net",
    "sender_lid": "me@lid",
    "receiver_jid": "target@s.whatsapp.net",
    "receiver_lid": "target@lid",
    "content": "hello",
    "file_url": "",
    "timestamp": 1678900000000
  }
}
```

### 6. 获取历史消息

`GET /{session_id}/history`

可选查询参数：

- `phone`

说明：

- 不传 `phone` 时，返回当前运行进程中的内存消息历史
- 传了 `phone` 时，会按目标联系人过滤
- 这不是一个持久化数据库历史接口

### 7. 首页

`GET /`

这个接口只适合作为轻量入口页，或手工访问时的起点。

## 常见使用方式

### 登录流程

1. 选择一个 `session_id`。
2. 打开 `/{session_id}/qr-view`，或轮询 `/{session_id}/qr`。
3. 等待状态变成 `qr_generated`。
4. 提示用户扫码。
5. 继续轮询，直到状态变成 `connected`。
6. 用 `/{session_id}/me` 确认登录成功。

### 发送文本

1. 用 `/{session_id}/me` 确认已登录。
2. 调用 `POST /{session_id}/messages/send`，传 `phone` 和 `message`。
3. 把发送结果返回给用户。

### 发送文件

1. 用 `/{session_id}/me` 确认已登录。
2. 调用 `POST /{session_id}/messages/send`，传 `phone` 和 `file`。
3. 如有需要，再附带 `message` 作为 caption。
4. 如果接口返回了 `file_url` 和消息元数据，一并告诉用户。

### 排障流程

如果调用失败，按下面顺序检查：

1. FastAPI 服务是否运行在 `8000` 端口？
2. 请求里使用的 `session_id` 是否正确？
3. `/{session_id}/qr` 返回的是 `waiting`、`qr_generated` 还是 `connected`？
4. `/{session_id}/me` 是否返回 `code = -1`？
5. `whatsapp_python/sessions/` 下是否存在会话数据库文件？
6. 日志中是否有依赖错误或上游协议错误，例如客户端版本问题？

## 使用注意事项

- 这套代码同时使用运行时内存状态和本地会话数据库文件。
- 即使当前进程没有连接成功，本地仍然可能存在会话数据库文件。
- 消息历史来自运行时事件和发送记录补记，因此服务重启后不一定保留。
- `whatsapp_python/models.py` 里的 Pydantic 模型并不是当前发送消息接口的真实输入契约；实际接口使用的是 `multipart/form-data`。
- 如果 README 示例与代码不一致，以真实代码实现为准。

## 示例请求

获取二维码状态：

```bash
curl http://127.0.0.1:8000/demo-session/qr
```

获取当前账号信息：

```bash
curl http://127.0.0.1:8000/demo-session/me
```

获取联系人：

```bash
curl http://127.0.0.1:8000/demo-session/contacts
```

发送文本消息：

```bash
curl -X POST http://127.0.0.1:8000/demo-session/messages/send \
  -F "phone=1234567890" \
  -F "message=Hello from API"
```

发送带 caption 的文件：

```bash
curl -X POST http://127.0.0.1:8000/demo-session/messages/send \
  -F "phone=1234567890" \
  -F "message=Here is the file" \
  -F "file=@C:/path/to/file.pdf"
```

获取历史消息：

```bash
curl "http://127.0.0.1:8000/demo-session/history?phone=1234567890"
```

## 响应输出建议

使用这个技能时，应尽量做到：

- 明确说明当前 session 是否已登录
- 明确指出当前调用的是哪个接口
- 清楚区分 `waiting`、`qr_generated` 和 `connected`
- 在需要登录前置条件时主动提醒
- 排障时给出可能的根因
- 优先给出具体下一步，而不是泛泛而谈的 API 总结
