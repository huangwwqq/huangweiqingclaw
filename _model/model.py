from pydantic import BaseModel, Field
from typing import Optional, Dict, Any,List,Literal
from dataclasses import dataclass, field
import copy



default_headers = {
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
}

@dataclass
class SkillDescriptor:
    """技能描述对象。

    字段说明:
    - slug: 技能唯一标识，优先取 `_meta.json` 中的 slug，没有则退回目录名
    - name: 技能展示名称，通常来自 `SKILL.md` frontmatter 的 name
    - description: 技能简要说明，通常来自 `SKILL.md` frontmatter 的 description
    - body: 技能正文内容，为目录下 markdown 说明文件合并后的完整文本
    - folder: 技能目录的绝对路径
    - files: 当前技能关联的 markdown 文件绝对路径列表
    - extensions: 技能声明支持的文件扩展名列表，例如 `.pdf`、`.docx`
    - aliases: 技能别名列表，用于兼容 slug、目录名、展示名等多种匹配方式
    - version: 技能版本号，优先取 `_meta.json` 中的 version
    """

    slug: str
    name: str
    description: str
    body: str
    folder: str
    files: List[str]
    extensions: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    version: str = ""
    scripts: str = ""

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

class RedisExecuteModel(BaseModel):
    """Redis 执行命令的参数校验模型"""
    command: str = Field(description="需要执行的完整 Redis 命令，如 'SET key value'、'GET key'、'HGETALL hash'、'KEYS *' 等")
    redis_config: Dict[str, Any] = Field(description="Redis 连接配置，包含 host、port、password、db 等")
    db: Optional[int] = Field(default=None, description="可选，指定要切换操作的 Redis 数据库编号，不填则使用配置默认库")

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





class DocumentExtractSchema(BaseModel):
    path: str = Field(description="要提取内容的本地文件路径，支持 pdf/docx/xlsx/pptx")
    pages: str = Field(default="all", description="仅 pdf 生效。页码选择器：all、单页如 3、范围如 2-5")


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


class SelfAwareness(BaseModel):
    """
    自我认知表
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
    """
    userid: str = Field(default='', description='用户ID，唯一索引')
    name: str = Field(default='', description='用户昵称')
    age: str = Field(default='', description='年龄')
    birthday: str = Field(default='', description='生日')
    education: str = Field(default='', description='学历')
    school: str = Field(default='', description='毕业院校')
    company: str = Field(default='', description='当前任职公司')
    position: str = Field(default='', description='职位')
    occupation: str = Field(default='', description='职业')
    dialogue_style: str = Field(default='', description='与AI的对话风格')
    ai_name: str = Field(default='', description='智能体的名字')
    other: str = Field(default='', description='其他补充说明')




# milvus 和 minio 相关

class MinioInsertSchema(BaseModel):
    bucket_name: str = Field(description="MinIO 桶名称")
    object_name: str = Field(description="MinIO 对象名称/保存路径")
    file_path: str = Field(description="要上传的本地文件绝对路径")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置，包含 endpoint、access_key、secret_key、secure 等")

class MinioUpdateSchema(BaseModel):
    bucket_name: str = Field(description="MinIO 桶名称")
    object_name: str = Field(description="MinIO 对象名称/保存路径")
    file_path: str = Field(description="要上传的本地文件绝对路径")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置")

class MinioSearchSchema(BaseModel):
    bucket_name: str = Field(description="MinIO 桶名称")
    object_name: str = Field(description="MinIO 对象名称/保存路径")
    save_path: str = Field(default="", description="下载保存的本地文件路径，为空则只查询文件是否存在及状态")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置")

class MinioDeleteSchema(BaseModel):
    bucket_name: str = Field(description="MinIO 桶名称")
    object_name: str = Field(description="MinIO 对象名称/保存路径")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置")


class MilvusInsertSchema(BaseModel):
    collection_name: str = Field(description="Milvus 集合名称")
    text: str = Field(description="文本内容或文件描述，将转换为向量存储")
    file_path: str = Field(default="", description="本地文件路径（如果有文件传入则必填，将传到 minio）")
    bucket_name: str = Field(default="default-bucket", description="MinIO 桶名称（如果有文件传入）")
    object_name: str = Field(default="", description="MinIO 对象名称（如果有文件传入）")
    db_name: str = Field(default="default", description="Milvus 数据库名，默认为 default")
    custom_milvus_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 Milvus 连接配置，包含 uri、token 等")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置")

class MilvusUpdateSchema(BaseModel):
    collection_name: str = Field(description="Milvus 集合名称")
    id: int = Field(description="要修改的数据主键 ID")
    text: str = Field(description="文本内容或文件描述，将转换为向量存储")
    file_path: str = Field(default="", description="本地文件路径（如果有文件传入则必填，将传到 minio）")
    bucket_name: str = Field(default="default-bucket", description="MinIO 桶名称（如果有文件传入）")
    object_name: str = Field(default="", description="MinIO 对象名称（如果有文件传入）")
    db_name: str = Field(default="default", description="Milvus 数据库名，默认为 default")
    custom_milvus_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 Milvus 连接配置")
    custom_minio_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 MinIO 连接配置")

class MilvusSearchSchema(BaseModel):
    collection_name: str = Field(description="Milvus 集合名称")
    text: str = Field(description="要查询的文本内容，将转换为向量进行相似度搜索")
    limit: int = Field(default=10, description="返回的相似结果数量")
    db_name: str = Field(default="default", description="Milvus 数据库名，默认为 default")
    custom_milvus_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 Milvus 连接配置")

class MilvusDeleteSchema(BaseModel):
    collection_name: str = Field(description="Milvus 集合名称")
    id: int = Field(description="要删除的数据主键 ID")
    db_name: str = Field(default="default", description="Milvus 数据库名，默认为 default")
    custom_milvus_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 Milvus 连接配置")

class UploadToKnowledgeBaseSchema(BaseModel):
    collection_name: str = Field(description="Milvus 集合（知识库）名称")
    file_path: str = Field(description="要上传和处理的本地文件绝对路径（支持 txt, md, docx, pdf, xlsx, pptx 等）")
    db_name: str = Field(default="default", description="Milvus 数据库名，默认为 default")
    split_pattern: str = Field(default=r"\n\n", description="文本分割的正则表达式规则，默认为双换行符")
    chunk_size: int = Field(default=2000, description="每个文本块的最大字符数，默认为 2000")
    custom_milvus_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义 Milvus 连接配置")


class UrlDownloadSchema(BaseModel):
    url: str = Field(description="要下载的文件 URL 地址")
    save_path: str = Field(default="", description="保存路径。可为完整文件路径(如 D:/img/photo.jpg)或目录(如 D:/img/)。为空则默认保存到项目根目录，文件名自动生成")


class WorkResponse(BaseModel):
    user_id: str = Field(default='', description='用户ID')
    message_id: str = Field(default='', description='会话ID')
    ai_summary_msg: dict = Field(default_factory=dict, description='AI总结消息')
    message_list: list = Field(default_factory=list, description='消息列表')
    error_code: int = Field(default=0, description='错误码 0-正常 1-未建立自我认知 2-异常')
    error_msg: str = Field(default='', description='错误信息')


# AI部门多智能体协同相关

class DepartmentMemberConfig(BaseModel):
    """部门岗位编制配置，不同部门只需替换这一份配置即可"""
    role_name: str = Field(default='', description='岗位名称，如 内容采集专员')
    duty: str = Field(default='', description='岗位职责描述，主管据此分派任务')
    skill_folders: Optional[List[str]] = Field(default=None, description='该岗位插入的技能目录列表，对应 skills 目录下的文件夹名')
    system_prompt: str = Field(default='', description='岗位专属提示词，会拼接在通用员工人设之后')
    headcount: int = Field(default=1, description='同岗位编制人数，同一任务最多可由这么多人并发执行')
    model_manufacturer: str = Field(default='', description='模型厂商，不填则继承部门默认模型配置')
    model_name: str = Field(default='', description='模型名称，不填则继承部门默认模型配置')
    base_url: str = Field(default='', description='模型请求地址，不填则继承部门默认模型配置')
    api_key: str = Field(default='', description='模型api_key，不填则继承部门默认模型配置')
    temperature: Optional[float] = Field(default=None, description='温度参数，不填则继承部门默认模型配置')


class DepartmentTask(BaseModel):
    """主管拆解出来的单个子任务"""
    task_id: str = Field(default='', description='任务编号')
    title: str = Field(default='', description='任务标题')
    description: str = Field(default='', description='任务详细描述')
    assignee_roles: List[str] = Field(default_factory=list, description='承接该任务的岗位名称列表')
    parallel_count: int = Field(default=1, description='该任务希望几名同岗位员工一起执行')
    workload_total: int = Field(default=0, description='任务的可量化总量，如采集5篇笔记就是5，无法量化则为0')
    workload_unit: str = Field(default='', description='任务量的单位，如 篇笔记、个商品、条评论')
    split_mode: str = Field(
        default='none',
        description='并行拆分方式 quantity-按数量平分给多人 dimension-按维度拆分 none-不可拆分只能一人执行'
    )
    split_items: List[str] = Field(default_factory=list, description='按维度拆分时每一份的具体内容，如不同关键词')
    acceptance_criteria: str = Field(default='', description='任务验收标准')
    expected_output: str = Field(default='', description='期望交付物')
    retry_count: int = Field(default=0, description='已重试次数')
    extra_note: str = Field(default='', description='重试时主管给出的整改意见')


class TaskExecuteResult(BaseModel):
    """单个员工执行单个任务的结果"""
    task_id: str = Field(default='', description='任务编号')
    role_name: str = Field(default='', description='岗位名称')
    worker_id: str = Field(default='', description='员工编号')
    shard_desc: str = Field(default='', description='该员工承担的分片说明，如 第1片:第1到第3篇')
    output: str = Field(default='', description='员工产出内容')
    error_code: int = Field(default=0, description='错误码 0-正常 非0-异常')
    error_msg: str = Field(default='', description='错误信息')


class TaskReviewResult(BaseModel):
    """主管对任务产出的验收结论"""
    passed: bool = Field(default=False, description='是否通过验收')
    reason: str = Field(default='', description='验收结论理由')
    suggestion: str = Field(default='', description='未通过时的整改意见')


class DepartmentResponse(BaseModel):
    user_id: str = Field(default='', description='用户ID')
    message_id: str = Field(default='', description='会话ID')
    department_name: str = Field(default='', description='部门名称')
    task_list: list = Field(default_factory=list, description='主管拆解出的任务列表')
    task_record_list: list = Field(default_factory=list, description='每个任务的执行与验收记录')
    final_answer: str = Field(default='', description='部门最终交付内容')
    error_code: int = Field(
        default=0,
        description='错误码 0-正常 1-参数或自我认知缺失 2-规划失败 3-任务失败且主管兜底失败 4-达到最大步数仍未完成'
    )
    error_msg: str = Field(default='', description='错误信息')


