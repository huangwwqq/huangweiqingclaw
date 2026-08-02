#!/usr/bin/env python3
# encoding: utf8

"""
Module Name: db_redis.py
Description: 高效操作Redis
Author: Peng
Email: lansehuluwa@gmail.com
Date: 2024-01-15
"""
import sys
sys.path.append('../')
sys.path = list(set(sys.path))
from typing import Union, List, Optional, Any
import redis
from setting.setting import *


class PoolRedis:
    """构建Redis连接池（长期持有，对应 DBUtils 的 PooledDB）"""
    def __new__(cls, concurrency: int = 1, **redis_info) -> redis.ConnectionPool:
        max_conn = 20 if concurrency < 20 else concurrency
        info = dict(
            max_connections=max_conn,
            decode_responses=True,
        )
        info.update(redis_info)
        return redis.ConnectionPool(**info)


class DBPoolRedis:
    """
    连接池操作Redis的封装

    设计原则：借-用-还
    每次操作从连接池借一个连接，用完后立马归还，连接池本身保持存活。

    用法：
        pool = PoolRedis(host='127.0.0.1', port=6379, db=0)
        db = DBPoolRedis(pool)

        db.set("key", "value")   # 借连接 → SET → 还连接
        db.get("key")            # 借连接 → GET → 还连接
        # ... 随时可以继续用，池子一直活着

        db.close()               # 释放空闲连接，但池子不毁，之后还能用
        db.destroy()             # 彻底销毁，之后不能再用了
    """
    def __init__(self, pool: redis.ConnectionPool):
        self.pool = pool

    def _connection(self) -> redis.Redis:
        """从连接池借一个Redis客户端（不会立即创建TCP连接，延迟到首次命令时创建）"""
        return redis.Redis(connection_pool=self.pool)

    def execute(self, command: str, retry_num: int = 3) -> Any:
        """
        执行任意Redis命令
        :param command: Redis命令字符串，如 "SET key value"、"GET key"、"HGETALL hash"
        :param retry_num: 重试次数
        :return: 命令执行结果
        """
        for _ in range(retry_num):
            r = self._connection()
            try:
                parts = command.strip().split()
                if not parts:
                    return None
                cmd = parts[0].upper()
                args = parts[1:]
                result = r.execute_command(cmd, *args)
                return result
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                r.close()  # 归还连接到池中
        logger.error({"msg": "最大重试次数", "command": command})
        return None

    def get(self, key: str) -> Optional[str]:
        r = self._connection()
        try:
            return r.get(key)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return None
        finally:
            r.close()

    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        r = self._connection()
        try:
            return r.set(key, value, ex=ex, nx=nx, xx=xx)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return False
        finally:
            r.close()

    def delete(self, *keys: str) -> int:
        r = self._connection()
        try:
            return r.delete(*keys)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def exists(self, *keys: str) -> int:
        r = self._connection()
        try:
            return r.exists(*keys)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def expire(self, key: str, seconds: int) -> bool:
        r = self._connection()
        try:
            return r.expire(key, seconds)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return False
        finally:
            r.close()

    def ttl(self, key: str) -> int:
        r = self._connection()
        try:
            return r.ttl(key)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return -2
        finally:
            r.close()

    def keys(self, pattern: str = "*") -> List[str]:
        r = self._connection()
        try:
            return r.keys(pattern)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return []
        finally:
            r.close()

    def hget(self, name: str, key: str) -> Optional[str]:
        r = self._connection()
        try:
            return r.hget(name, key)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return None
        finally:
            r.close()

    def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None) -> int:
        r = self._connection()
        try:
            return r.hset(name, key, value, mapping)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def hgetall(self, name: str) -> dict:
        r = self._connection()
        try:
            return r.hgetall(name)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return {}
        finally:
            r.close()

    def hdel(self, name: str, *keys: str) -> int:
        r = self._connection()
        try:
            return r.hdel(name, *keys)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def lpush(self, name: str, *values: Any) -> int:
        r = self._connection()
        try:
            return r.lpush(name, *values)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def rpush(self, name: str, *values: Any) -> int:
        r = self._connection()
        try:
            return r.rpush(name, *values)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        r = self._connection()
        try:
            return r.lrange(name, start, end)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return []
        finally:
            r.close()

    def sadd(self, name: str, *values: Any) -> int:
        r = self._connection()
        try:
            return r.sadd(name, *values)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return 0
        finally:
            r.close()

    def smembers(self, name: str) -> set:
        r = self._connection()
        try:
            return r.smembers(name)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.warning(f"{exc_type.__name__}: {e}")
            return set()
        finally:
            r.close()

    def test_connect(self):
        """测试连接"""
        r = self._connection()
        try:
            result = r.ping()
            logger.info(f"Redis连接测试: {result}")
            return result
        finally:
            r.close()

    def close(self):
        """
        释放连接池中所有空闲连接。
        连接池本身不销毁，之后仍可使用（会自动创建新连接）。
        对应 DBUtils 中 conn.close() 的语义——归还，非销毁。
        """
        self.pool.disconnect()

    def destroy(self):
        """
        彻底销毁连接池并释放所有资源。
        调用后该 DBPoolsRedis 实例不可再用。
        """
        self.pool.disconnect()
        self.pool = None
