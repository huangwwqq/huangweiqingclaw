#!/usr/bin/env python3
# encoding: utf8

"""
Module Name: db_mysql.py
Description: 高效操作数据库
Author: Peng
Email: lansehuluwa@gmail.com
Date: 2023-07-07
"""
import sys
sys.path.append('../')
sys.path=list(set(sys.path))
import asyncio
import json
import pymysql
import pymysql.cursors
from typing import Union, List, Tuple, Optional
from dbutils.pooled_db import PooledDB
from setting.setting import *


class DBMysql:
    """单个连接的pymysql封装"""

    def __init__(self, conn: pymysql.connections.Connection, **kwargs):
        self.name = kwargs.get('name', 'mysql')
        self.conn = conn


    def execute(self, sql: str, value: Union[list, tuple, None] = None, retry_num: int = 3) -> Union[int, None]:
        for _ in range(retry_num):
            try:
                self.conn.ping(reconnect=True)
                with self.conn.cursor() as cur:
                    cur.execute(sql, value)
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
        logger.error({"maximum_retry": retry_num, "sql": sql})

    def read(self, sql: str, value: Union[list, tuple, None] = None, retry_num: int = 3,
             return_dict: bool = False) -> Union[tuple, None]:
        """
        读取数据
        :param sql: 语句
        :param value: 拼接到语句的值，默认None
        :param retry_num: 重试次数，默认3
        :param return_dict: 返回每条数据格式，默认元组
        :return: tuple or None
        """
        cursor_class = pymysql.cursors.DictCursor if return_dict else pymysql.cursors.Cursor
        for _ in range(retry_num):
            try:
                self.conn.ping(reconnect=True)
                with self.conn.cursor(cursor_class) as cur:
                    cur.execute(sql, value)
                    data_raw = cur.fetchall()
                return tuple() if data_raw is None else data_raw
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
        logger.error({"msg": "最大重试次数", "sql": sql})

    def write(
            self, sql: str,
            insert_list: Union[List[List], Tuple[Tuple], List[Tuple], Tuple[List]],
            retry_num: int = 3
    ) -> Union[bool, None]:
        for _ in range(retry_num):
            self.conn.ping(reconnect=True)
            try:
                with self.conn.cursor() as cur:
                    cur.executemany(sql, insert_list)
                self.conn.ping(reconnect=True)
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
        logger.error({"maximum_retry": retry_num, "sql": sql})

    @staticmethod
    def id_iterator(
            min_id: int, max_id: int, batch_size: Union[int, None] = None, workers: Union[None, int] = None) -> tuple:
        step = batch_size if workers is None else (max_id - min_id) // workers
        yield from ((i, min(i + step - 1, max_id)) for i in range(min_id, max_id + 1, step))

    def read_id_range(self, table: str, id_name='aid', where: Union[None, str] = None) -> tuple:
        sql = f"select min({id_name}) min_id, max({id_name}) max_id from {table}"
        if where is not None:
            sql += f" where {where}"
        data_raw = self.read(sql)
        return (0, 0) if data_raw is None or len(data_raw) == 0 or data_raw[0] is None else data_raw[0]

    def save(self, table: str, items: Union[List[dict], Tuple[dict]], ignore: bool = False, info: bool = True):
        if info:
            logger.info({"len": len(items), "pre": json.dumps(items)[:50]})
        if len(items) == 0:
            return
        fields = items[0].keys()
        insert_str = ', '.join(fields)
        update_str = ', '.join([f'{field}=values({field})' for field in fields])
        sql = (f"insert into {table}({insert_str}) value({', '.join(['%s'] * len(fields))}) "
               f"on duplicate key update {update_str}")
        if ignore:
            sql = f"insert ignore into {table}({insert_str}) value({', '.join(['%s'] * len(fields))})"
        insert_list = [list(item.values()) for item in items]
        self.write(sql, insert_list)

    def close(self):
        self.conn.close()


class PoolMysql:
    """构建连接池"""
    def __new__(cls, concurrency: int = 1, **mysql_info) -> PooledDB:
        max_conn = 20 if concurrency < 20 else concurrency
        info = dict(
            blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待
            ping=1,  # 在每次获取连接时ping
            mincached=5,  # 初始化时，连接池中至少创建的空闲的连接，0表示不创建
            maxcached=10,  # 连接池中最多闲置的连接，0和None不限制
            maxconnections=max_conn,  # 连接池允许的最大连接数，0和None表示不限制连接数
        )
        info.update(mysql_info)
        return PooledDB(creator=pymysql, **info)


class DBPoolMysql:
    """连接池操作mysql的封装"""
    def __init__(self, pool: PooledDB):
        self.pool = pool

    def execute(self, sql: str, value: Union[list, tuple, None] = None, retry_num: int = 3, rollback: bool = False,
                debug=False) -> Union[int, None]:
        for _ in range(retry_num):
            conn = self.pool.connection()
            cursor = conn.cursor()
            try:
                if debug:
                    logger.debug(sql)
                cursor.execute(sql, value)
                conn.commit()
                return True
            except Exception as e:
                if rollback:
                    conn.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                cursor.close()
                conn.close()  # 将连接归还给连接池
        logger.error({"msg": "最大重试次数", "sql": sql})

    def read(self, sql: str, value: Union[list, tuple, None] = None, retry_num: int = 3,
             return_dict: bool = False) -> Union[tuple, None]:
        """
        读取数据
        :param sql: 语句
        :param value: 拼接到语句的值，默认None
        :param retry_num: 重试次数，默认3
        :param return_dict: 返回每条数据格式，默认元组
        :return: tuple or None
        """
        cursor_class = pymysql.cursors.DictCursor if return_dict else pymysql.cursors.Cursor
        for _ in range(retry_num):
            conn = self.pool.connection()
            cursor = conn.cursor(cursor_class)
            try:
                cursor.execute(sql, value)
                data_raw = cursor.fetchall()
                return data_raw if data_raw else tuple()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                cursor.close()
                conn.close()  # 将连接归还给连接池
        logger.error({"msg": "最大重试次数", "sql": sql})

    def write(self, sql: str,
              insert_list: Union[List[List], Tuple[Tuple], List[Tuple], Tuple[List]],
              retry_num: int = 3) -> Union[bool, None]:
        for _ in range(retry_num):
            conn = self.pool.connection()
            cursor = conn.cursor()
            try:
                cursor.executemany(sql, insert_list)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                cursor.close()
                conn.close()  # 将连接归还给连接池
        logger.error({"msg": "最大重试次数", "sql": sql})

    def save(self, table: str, items: Union[List[dict], Tuple[dict]], unique_field_list=None, ignore: bool = False):
        logger.info({"len": len(items), "pre": json.dumps(items)[:100]})
        if len(items) == 0:
            return
        fields = items[0].keys()
        insert_str = ', '.join(fields)
        update_str = ', '.join([f'{field}=values({field})' for field in fields]) if not unique_field_list else ', '.join([f'{field}=values({field})' for field in fields if field not in unique_field_list])
        sql = (f"insert into {table}({insert_str}) value({', '.join(['%s'] * len(fields))}) "
               f"on duplicate key update {update_str}")
        if ignore:
            sql = f"insert ignore into {table}({insert_str}) value({', '.join(['%s'] * len(fields))})"
        insert_list = [list(item.values()) for item in items]
        self.write(sql, insert_list)

    @staticmethod
    def id_iterator(min_id: int, max_id: int, batch_size: int) -> tuple:
        for i in range(min_id, max_id + 1, batch_size):
            yield i, min(i + batch_size - 1, max_id)

    def read_id_range(self, table: str, id_name='id', where: Union[None, str] = None) -> tuple:
        sql = f"select min({id_name}) min_id, max({id_name}) max_id from {table}"
        if where is not None:
            sql += f" where {where}"
        data_raw = self.read(sql)
        return (0, 0) if data_raw is None or len(data_raw) == 0 or data_raw[0] is None else data_raw[0]

    def test_connect(self):
        sql = "show tables;"
        logger.info(self.read(sql))

    def close(self):
        self.pool.close()


class AsyncDBPoolMysql:
    """异步使用连接池操作mysql的封装"""
    def __init__(self, pool: PooledDB):
        self.pool = pool
        self.__db_pool = DBPoolMysql(self.pool)

    async def execute(self, sql: str, value: Optional[Union[list, tuple]] = None, retry_num: int = 3) -> Optional[int]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.execute, sql, value, retry_num)

    async def read(self, sql: str, value: Optional[Union[list, tuple]] = None, retry_num: int = 3,
                   return_dict: bool = False) -> Optional[tuple]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.read, sql, value, retry_num, return_dict)

    async def write(self, sql: str,
                    insert_list: Union[List[List], Tuple[Tuple], List[Tuple], Tuple[List]],
                    retry_num: int = 3) -> Optional[bool]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.write, sql, insert_list, retry_num)

    async def save(self, table: str, items: Union[List[dict], Tuple[dict]]):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.save, table, items)

    async def read_id_range(self, table: str, id_name='aid', where: Union[None, str] = None) -> tuple:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.read_id_range, table, id_name, where)

    @staticmethod
    async def id_iterator_async(min_id: int, max_id: int, batch_size: int):
        for i in range(min_id, max_id + 1, batch_size):
            yield i, min(i + batch_size - 1, max_id)

    async def test_connect(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.__db_pool.test_connect)

    async def close(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.__db_pool.close)
