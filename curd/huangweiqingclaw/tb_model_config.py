import sys
sys.path.append('../')
from common.db_mysql import *
from setting.setting import *

class TbModelConfig:

    def __init__(self,connect_data:dict):
        pool = PoolMysql(**connect_data)
        self.db = DBPoolMysql(pool)
        self.table_name = 'model_config'
        self._init_table()

    def _init_table(self):
        # 先判断表是否存在，如果存在则直接跳过
        check_sql = f"SHOW TABLES LIKE '{self.table_name}'"
        if self.db.read(sql=check_sql):
            return

        sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` ( 
          `id` int NOT NULL AUTO_INCREMENT COMMENT '主键', 
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
        ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 
        """
        self.db.execute(sql=sql)

    def save_model_config(self, model_config_list:list):
        unique_field_list = [
            'model_manufacturer',
            'model_name'
        ]
        if not model_config_list:
            logger.info(f'空记忆列表不得存入')
        self.db.save(table=self.table_name,items=model_config_list,unique_field_list=unique_field_list)

    def get_model_config(self,model_manufacturer:str,model_name:str):
        sql = f"""SELECT * FROM {self.table_name} WHERE model_manufacturer = %s AND model_name = %s"""
        data_list = self.db.read(sql=sql,value=[model_manufacturer,model_name],return_dict=True) or []
        return data_list[0] if data_list else dict()






