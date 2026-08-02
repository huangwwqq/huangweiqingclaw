import sys
sys.path.append('../')
from common.db_mysql import *
from setting.setting import *

class TbSelfAwareness:

    def __init__(self,connect_data:dict):
        pool = PoolMysql(**connect_data)
        self.db = DBPoolMysql(pool)
        self.table_name = 'self_awareness'
        self._init_table()

    def _init_table(self):
        # 先判断表是否存在，如果存在则直接跳过
        check_sql = f"SHOW TABLES LIKE '{self.table_name}'"
        if self.db.read(sql=check_sql):
            return

        sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` ( 
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
        ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户自我认知表';
        """
        self.db.execute(sql=sql)

    def save_self_awareness(self, self_awareness_list:list):
        unique_field_list = [
            'userid',
        ]
        if not self_awareness_list:
            logger.info(f'空记忆列表不得存入')
            return
        self.db.save(table=self.table_name,items=self_awareness_list,unique_field_list=unique_field_list)

    def get_self_awareness(self,userid:str):
        sql = f"""SELECT * FROM {self.table_name} WHERE userid = %s"""
        data_list = self.db.read(sql=sql,value=[userid],return_dict=True) or []
        return data_list[0] if data_list else dict()






