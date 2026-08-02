"""
redis的基本操作封装
"""
import redis
from setting.setting import *

class RedisObj:

    def __init__(self,host=REDISHOST,port=REDISPORT,db=REDISDB,password=REDISPASSWORD):
        self.redis_obj = redis.Redis(host=host,port=port,db=db,password=password)
        self.reset = 3

    def keys(self,key_name):
        """
        redis的keys操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.keys(key_name)
            except:
                ...
        logger.error(f'redis的keys操作失败,key:{key_name}')
        return []

    def set(self,key_name,data):
        """
        redis的set操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                self.redis_obj.set(key_name, data)
                return True
            except:
                ...
        logger.error(f'redis的set操作失败,key:{key_name},value:{data}')
        return False

    def lpush(self,key_name,data):
        """
        redis的lpush操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                self.redis_obj.lpush(key_name,data)
                return True
            except:
                ...
        logger.error(f'redis的lpush操作失败,key:{key_name},value:{data}')
        return False

    def rpush(self, key_name, data):
        """
        redis的rpush操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                self.redis_obj.rpush(key_name, data)
                return True
            except:
                ...
        logger.error(f'redis的rpush操作失败,key:{key_name},value:{data}')
        return False

    def lpop(self,key_name):
        """
        redis的lpop操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.lpop(key_name)
            except:
                ...
        logger.error(f'redis的lpop操作失败,key:{key_name}')
        return

    def rpop(self,key_name):
        """
        redis的rpop操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.rpop(key_name)
            except:
                ...
        logger.error(f'redis的rpop操作失败,key:{key_name}')
        return

    def get(self,key_name):
        """
        redis的get操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.get(key_name)
            except:
                ...
        logger.error(f'redis的get操作失败,key:{key_name}')
        return

    def zadd(self,key_name,data):
        """
        redis的zadd
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zadd(key_name,data)
            except:
                ...
        logger.error(f'redis的zadd操作失败,key:{key_name},data:{data}')
        return


    def zrangebyscore(self,key_name,max_conn,min_conn="-inf"):
        """
        redis的zrangebyscore操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zrangebyscore(key_name,min_conn,max_conn)
            except:
                ...
        logger.error(f'redis的zrangebyscore操作失败,key:{key_name}')
        return

    def zrevrange(self,key_name,start_index,end_index,withscores=False):
        """
        redis的zrevrange操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zrevrange(key_name,start=start_index,end=end_index,withscores=withscores)
            except:
                ...
        logger.error(f'redis的zrevrange操作失败,key:{key_name}')
        return

    def zpopmin(self,key_name,pop_number=1):
        """
        redis的zrevrange操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zpopmin(key_name,pop_number)
            except:
                ...
        logger.error(f'redis的zpopmin操作失败,key:{key_name}')
        return

    def sadd(self,key_name,value):
        """
        redis的sadd操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.sadd(key_name,value)
            except:
                ...
        logger.error(f'redis的sadd操作失败,key:{key_name}, value: {value}')
        return

    def spop(self,key_name):
        """
        redis的sadd操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.spop(key_name)
            except:
                ...
        logger.error(f'redis的spop操作失败,key:{key_name}')
        return

    def exists(self,key_name):
        """
        redis的exists操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.exists(key_name)
            except:
                ...
        logger.error(f'redis的exists操作失败,key:{key_name}')
        return

    def delete(self,key_name):
        """
        redis的delete操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                self.redis_obj.delete(key_name)
                return True
            except:
                ...
        logger.error(f'redis的delete操作失败,key:{key_name}')
        return False

    def zscore(self,key_name,member):
        """
        redis的zscore操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zscore(key_name,member)
            except:
                ...
        logger.error(f'redis的zscore操作失败,key:{key_name},value:{member}')
        return

    def zrem(self,key_name, member):
        """
        redis的zrem操作
        """
        reset = self.reset
        while reset:
            reset -= 1
            try:
                return self.redis_obj.zrem(key_name,member)
            except:
                ...
        logger.error(f'redis的zrem操作失败,key:{key_name},value:{member}')
        return