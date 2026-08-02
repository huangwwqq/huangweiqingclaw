import sys
sys.path.append('../')
from common.db_mysql import *
from setting.setting import *

class TbAgentMessage:

    def __init__(self,connect_data:dict):
        pool = PoolMysql(**connect_data)
        self.db = DBPoolMysql(pool)
        self.table_name = 'agent_message'
        self._init_table()

    def _init_table(self):
        # 先判断表是否存在，如果存在则直接跳过
        check_sql = f"SHOW TABLES LIKE '{self.table_name}'"
        if self.db.read(sql=check_sql):
            return

        sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` ( 
          `id` int NOT NULL AUTO_INCREMENT COMMENT '主键', 
          `user_id` varchar(255) NOT NULL DEFAULT '' COMMENT '用户id', 
          `message_id` varchar(255) NOT NULL DEFAULT '' COMMENT '会话id', 
          `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '角色,有5种角色:system(系统),agent(智能体),Tool(工具),user(用户),summary(总结)', 
          `message` text NOT NULL COMMENT '对话', 
          `file_url_list` json DEFAULT NULL COMMENT '文件url列表', 
          `is_delete` int NOT NULL DEFAULT '0' COMMENT '是否删除,默认为0,1为软删除(用于删除违反法律法规的对话,保留证据,日后举报)', 
          `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间', 
          `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间', 
          PRIMARY KEY (`id`), 
          KEY `nro_message_id` (`message_id`), 
          KEY `nro_create_time` (`create_time`), 
          KEY `nro_user_id` (`user_id`) 
        ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='智能体对话列表'; 
        """
        self.db.execute(sql=sql)

    def save_memory(self, memory_list:list):
        if not memory_list:
            logger.info(f'空记忆列表不得存入')
        self.db.save(table=self.table_name,items=memory_list)

    def get_memory(self,user_id:str,message_id:str,start_time:str,limit:int,role:str='summary'):
        sql = f"""
            SELECT * FROM {self.table_name} WHERE user_id = %s AND message_id = %s AND create_time >= %s AND role = %s AND is_delete = 0 ORDER BY create_time DESC LIMIT %s
        """
        memory_list = self.db.read(sql=sql,value=[user_id,message_id,start_time,role,limit],return_dict=True) or []
        return memory_list





