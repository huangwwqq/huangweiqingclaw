import sys
sys.path.append('../')
from common.db_mysql import *
from setting.setting import *

class TbAgentMessage:

    def __init__(self,connect_data:dict):
        pool = PoolMysql(**connect_data)
        self.db = DBPoolMysql(pool)
        self.table_name = 'agent_message'

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





