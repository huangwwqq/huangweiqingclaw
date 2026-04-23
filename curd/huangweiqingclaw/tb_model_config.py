import sys
sys.path.append('../')
from common.db_mysql import *
from setting.setting import *

class TbModelConfig:

    def __init__(self,connect_data:dict):
        pool = PoolMysql(**connect_data)
        self.db = DBPoolMysql(pool)
        self.table_name = 'model_config'

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






