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

memory_path = os.path.join(ROOT_PATH, 'memory').replace('\\', '/')
# 自我意识文件夹不存在路径就自己建立
if not os.path.exists(memory_path):
    os.makedirs(memory_path)

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
max_react_step = 20  # 最大react步数
memory_limit = 3  # 最多获取3条记忆
memory_time = 3 * 60 * 60  # 最多记住前3个小时的记忆
file_list_max_length = 3  # 最多传入3个文件url
threshold = 30000  # 压缩最大长度

# huangweiqingclaw mysql连接设置
huangweiqingclaw_mysql_config = {
    'host':'127.0.0.1',
    'port':3306,
    'user': 'root',
    'passwd': '141418hwq',
    'db': 'huangweiqingclaw',
    'charset': 'utf8mb4'
}

