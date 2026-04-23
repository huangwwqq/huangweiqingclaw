from pydantic import BaseModel, Field
from typing import Optional, Dict, Any,List,Literal
import copy

default_headers = {
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
}

class RequestsModel(BaseModel):
    """HTTP 请求参数校验模型"""
    method: str = Field(description="请求方式 GET/POST/PUT/DELETE 等")
    url: str = Field(description="需要请求的目标 URL")
    params: Optional[Dict[str, Any]] = Field(default=None, description="URL 中的查询参数")
    headers: Optional[Dict[str, Any]] = Field(default=copy.deepcopy(default_headers), description="请求头字典")
    data: Optional[Dict[str, Any]] = Field(default=None,description="POST 请求的表单请求体")
    cookies: Optional[Dict[str, Any]] = Field(default=None, description="请求携带的 Cookie")
    files: Optional[Dict[str, Any]] = Field(default=None, description="上传文件")
    auth: Optional[Any] = Field(default=None, description="身份认证")
    timeout: Optional[int] = Field(default=None, description="请求超时时间（秒）")
    allow_redirects: bool = Field(default=True, description="是否允许重定向")
    proxies: Optional[Dict[str, str]] = Field(default=None, description="代理配置")
    stream: Optional[bool] = Field(default=None, description="是否流式响应")
    verify: Optional[bool] = Field(default=None, description="是否验证 SSL 证书")
    cert: Optional[Any] = Field(default=None, description="SSL 证书路径")

class MySQLExecuteModel(BaseModel):
    """MySQL 执行 SQL 的参数校验模型"""
    sql: str = Field(description="需要执行的完整 SQL 语句，支持 SELECT / INSERT / UPDATE / DELETE 等")
    mysql_config: Dict[str, Any] = Field(description="MySQL 连接配置，包含 host、port、user、password、database 等")
    database: Optional[str] = Field(default=None, description="可选，指定要切换操作的数据库名，不填则使用配置默认库")

class ExecuteCliSchema(BaseModel):
    command: str = Field(description="完整的命令行执行语句，例如 'python skills/wechat-auto-send-1.0.0/xxx.py arg1 arg2'")
    cwd: Optional[str] = Field(default=None, description="执行命令的工作目录，默认为项目根目录")


class FileOperationModel(BaseModel):
    mode: Literal[
        "r", "rb", "r+", "rb+",
        "w", "wb", "w+", "wb+",
        "a", "ab", "a+", "ab+"
    ] = Field(
        default="r",
        description=(
            "文件操作模式详述：\n"
            "--- 读取模式 ---\n"
            "- 'r': 只读（默认）。文件必须存在。\n"
            "- 'r+': 读写。文件必须存在，指针在开头。\n"
            "--- 写入模式 ---\n"
            "- 'w': 只写。若文件存在则【清空】，不存在则创建。\n"
            "- 'w+': 读写。若文件存在则【清空】，不存在则创建。\n"
            "--- 追加模式 ---\n"
            "- 'a': 追加写入。指针在文件末尾，不存在则创建。\n"
            "- 'a+': 读取并追加。指针在文件末尾，不存在则创建。\n"
            "--- 二进制后缀 ---\n"
            "- 加 'b' (如 'wb', 'ab') 用于处理非文本文件（如图片、字节流）。"
        )
    )

    path: str = Field(
        description="文件的绝对路径或相对路径"
    )

    content: str = Field(
        default="",
        description="待写入/追加的内容。仅在模式包含 w 或 a 时使用。"
    )


# mysql 关于huangweiqingclaw的配置

class ModelConfig(BaseModel):
    """
    模型配置表
    mysql表创建语句
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
    """
    model_manufacturer:str = ''  # 模型厂商
    model_name:str = ''  # 模型名称
    base_url:str = ''  # 模型的api
    api_key:str = ''  # 模型的api_key


class AgentMessage(BaseModel):
    """
    模型对话表
    CREATE TABLE `agent_message` (
      `id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
      `user_id` varchar(255) NOT NULL DEFAULT '' COMMENT '用户id',
      `message_id` varchar(255) NOT NULL DEFAULT '' COMMENT '会话id',
      `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '角色,有5种角色:system(系统),agent(智能体),Tool(工具),user(用户),summary(总结)',
      `message` text NOT NULL COMMENT '对话',
      `file_url_list` json NOT NULL COMMENT '文件url列表',
      `is_delete` int NOT NULL DEFAULT '0' COMMENT '是否删除,默认为0,1为软删除(用于删除违反法律法规的对话,保留证据,日后举报)',
      `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
      `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
      PRIMARY KEY (`id`),
      KEY `nro_message_id` (`message_id`),
      KEY `nro_create_time` (`create_time`),
      KEY `nro_user_id` (`user_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='智能体对话列表';
    """
    user_id:str = ''
    message_id:str = ''
    role:str = ''
    message:str = ''
    file_url_list:Optional[List[str]] = None







