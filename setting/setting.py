import json
import os
import logging
import sys
from logging.handlers import RotatingFileHandler  # 导入轮转处理器

# 根目录
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT_PATH)
# 日志输出路径
log_path = os.path.join(ROOT_PATH, 'logs').replace('\\', '/')
# 日志文件夹不存在路径就自己建立
if not os.path.exists(log_path):
    os.makedirs(log_path)
# logger 配置
logger = logging.getLogger('huangweiqingclaw')
logger.setLevel(level=logging.INFO)
# --- 修改部分开始 ---
# 参数说明：
# filename: 日志文件路径
# maxBytes: 每个文件的最大字节数 (3 * 1024 * 1024 = 3MB)
# backupCount: 保留的备份文件数量 (设为 1，加上当前正在写的 1 个，总共最多 2 个)
handler = RotatingFileHandler(
    os.path.join(log_path, 'huangweiqingclaw.log'),
    maxBytes=3 * 1024 * 1024,
    backupCount=1,
    encoding='utf-8'
)
# --- 修改部分结束 ---
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logger.addHandler(console)
logger.propagate = False
# 智能体配置
skills_path = os.path.join(ROOT_PATH, 'skills').replace('\\', '/')
# 技能文件夹不存在路径就自己建立
if not os.path.exists(skills_path):
    os.makedirs(skills_path)

# 文件下载默认保存路径
download_file_dir_path = os.path.join(ROOT_PATH, 'download').replace('\\', '/')
if not os.path.exists(download_file_dir_path):
    os.makedirs(download_file_dir_path)

task_assignment_prompt = """
# 任务计划分配提示词
你是专业任务规划与分配助手，擅长拆解目标、合理分工、明确权责、规划时间、把控进度，输出清晰、可落地、无歧义。
请根据我提供的项目/目标、参与人员、时间周期、资源限制，完成：
1. 将目标拆解为可执行子任务
2. 按人员能力/特长合理分配任务
3. 明确每项任务的完成标准、交付物、截止时间，标注依赖关系、风险点与跟进节点

要求：
不冗余、不空话，任务可量化、可验收
分工公平合理，避免重叠或遗漏
支持加急、优先级排序、里程碑规划
输出结构化、简洁直观
"""  # 任务分配提示词(后续用于多智能体协同)

department_work_number = 20  # 部门单次协同最多执行的任务步数(防死循环)
department_max_workers = 5  # 单个任务最多并发的员工数
department_max_retry = 1  # 单个任务验收不通过后的最大重试次数
department_digest_limit = 6000  # 跨任务上下文摘要的最大长度

department_leader_prompt = """
你是「{department_name}」的部门主管。
部门目标:{department_goal}
你的职责边界:
1. 把用户任务拆解成有序的可执行子任务，并派给最合适的岗位
2. 验收员工交付物，不通过则给出明确的整改意见
3. 员工反复失败时，你才亲自兜底执行
4. 最后把所有任务成果汇总成给用户的最终交付
你不替员工抢活干，也不编造员工没有产出的结果。
"""  # 部门主管人设

department_employee_prompt = """
你是「{department_name}」的「{role_name}」(工号:{worker_id})。
岗位职责:{duty}
你被授权使用的技能:{skill_desc}

协作纪律:
1. 只做主管当前分配给你的这一个子任务，不要越权去做别人的任务，也不要擅自扩大范围
2. 任务带「你的分工」说明时，严格只完成分给你的那一份数量或范围，不多做也不少做，剩下的部分由同事并行完成，你多做就是重复劳动
3. 优先使用你被授权的技能与工具真实执行，严禁凭空编造数据、链接或结论
4. 交付物要结构化、可直接被下一个岗位使用，写清楚关键数据、产物路径和执行结论
5. 任务失败或数据缺失时，如实说明失败原因和已完成到哪一步，不要用假数据掩盖
"""  # 部门员工人设模板

task_review_prompt = """
你是部门主管，正在验收员工交付的子任务成果。
判定标准:
1. 交付物是否满足任务描述与验收标准
2. 有总量要求时，实际净数量是否达标；分片之间是否出现重复内容导致虚高，重复的不计入总量
3. 是否存在明显编造、答非所问、或只说做了却没有实际结果的情况
4. 数据缺失但已如实说明且属于客观不可得，可以判定通过

严格只输出如下JSON，不要输出任何解释、markdown标记或多余文字:
{"passed": true 或 false, "reason": "验收结论理由", "suggestion": "未通过时给员工的整改意见，通过则为空字符串"}
"""  # 任务验收提示词

task_merge_prompt = """
你是部门主管，同一个子任务被拆成多个分片交给多名同岗位员工并行执行，现在需要你把他们的交付物合并成一份。
要求:
1. 按数量分片的任务，把各分片结果按顺序拼成完整的一份，核对总量是否达标，既不能丢数据也不能重复计数
2. 分片之间出现重复内容时只保留一份，并说明重复了多少条、实际净总量是多少
3. 不同员工结论冲突时，标注冲突点并给出你判断更可信的一方
4. 明确标注哪些员工执行失败、失败原因，以及因此缺了多少份额
5. 直接输出合并后的交付内容，不要输出寒暄和过程描述
"""  # 多员工分片产出归并提示词

department_summary_prompt = """
你是部门主管，所有子任务已执行完毕，请汇总成给用户的最终交付。
要求:
1. 直接回答用户最初的诉求，把分散的任务成果整合成完整答案
2. 保留关键数据、产物路径与可验证的结论
3. 如实说明未完成或失败的部分，以及建议的后续动作
4. 结构清晰、不说废话、不复述任务调度过程
"""  # 部门最终交付汇总提示词

max_react_step = 200  # 最大react步数
memory_limit = 3  # 最多获取3条记忆
memory_time = 3 * 60 * 60  # 最多记住前3个小时的记忆
file_list_max_length = 3  # 最多传入3个文件url
threshold = 80000  # 压缩最大长度

# huangweiqingclaw mysql连接设置
huangweiqingclaw_mysql_config = {
    'host':'127.0.0.1',
    'port':3306,
    'user': 'root',
    'passwd': '141418hwq',
    'db': 'huangweiqingclaw',
    'charset': 'utf8mb4'
}

# redis连接
redis_config = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 0,
    'password': None,
}

# milvus连接
milvus_config = {
    'uri':"http://localhost:19520",
}
# minio连接
minio_config = {
    'endpoint': '127.0.0.1:9100',
    'access_key': 'minioadmin',
    'secret_key': 'minioadmin',
    'secure': False
}
# 转向量设置
embedding_config = {
    "api_key": "***",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "text-embedding-v4",
    "dim":1024
}



# mcp工具配置
mcp_tool_path = os.path.join(ROOT_PATH, 'mcp_tool').replace('\\', '/')
# mcp工具文件夹不存在路径就自己建立
if not os.path.exists(mcp_tool_path):
    os.makedirs(mcp_tool_path)
mcp_tool_config = {
    "mcpServers": {
        "image-video-generation-mcp": {
            "command": "node",
            "args": [
                os.path.join(mcp_tool_path,'image-video-generation-mcp/dist/index.js')
            ],
            "env": {
                "IMAGE_VIDEO_GENERATION_API_KEY": "***"
            }
        }
    }
}  # mcp工具配置

# redis配置
REDISHOST = '127.0.0.1'
REDISPORT = 6379
REDISDB = 1
REDISPASSWORD = ''