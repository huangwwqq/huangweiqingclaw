#!/usr/bin/env python3
# encoding: utf8

"""
Module Name: db_minio.py
Description: 高效操作Minio
"""

import sys
import os
sys.path.append('../')
import queue
from typing import Union, Optional
from minio import Minio
from minio.error import S3Error
from setting.setting import logger

class PooledMinio:
    """包装Minio客户端队列以实现类似PooledDB的接口"""
    def __init__(self, maxconnections=10, **minio_info):
        self.pool = queue.Queue(maxsize=maxconnections)
        for _ in range(maxconnections):
            self.pool.put(Minio(**minio_info))

    def connection(self):
        class ConnectionWrapper:
            def __init__(self, client, pool):
                self.client = client
                self._pool = pool
            def close(self):
                self._pool.put(self.client)
                
        client = self.pool.get(block=True)
        return ConnectionWrapper(client, self.pool)

    def close(self):
        while not self.pool.empty():
            self.pool.get()

class PoolMinio:
    """构建连接池"""
    def __new__(cls, concurrency: int = 1, **minio_info) -> PooledMinio:
        max_conn = 20 if concurrency < 20 else concurrency
        return PooledMinio(maxconnections=max_conn, **minio_info)

class DBPoolMinio:
    """连接池操作minio的封装"""
    def __init__(self, pool: PooledMinio):
        self.pool = pool

    def upload(self, bucket_name: str, object_name: str, file_path: str, retry_num: int = 3) -> bool:
        """上传文件（增/改）"""
        for _ in range(retry_num):
            conn = self.pool.connection()
            client = conn.client
            try:
                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)
                client.fput_object(bucket_name, object_name, file_path)
                return True
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                conn.close()
        logger.error({"msg": "最大重试次数", "action": "upload", "object": object_name})
        return False

    def download(self, bucket_name: str, object_name: str, file_path: str, retry_num: int = 3) -> bool:
        """下载文件（查）"""
        for _ in range(retry_num):
            conn = self.pool.connection()
            client = conn.client
            try:
                client.fget_object(bucket_name, object_name, file_path)
                return True
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                conn.close()
        logger.error({"msg": "最大重试次数", "action": "download", "object": object_name})
        return False

    def delete(self, bucket_name: str, object_name: str, retry_num: int = 3) -> bool:
        """删除文件（删）"""
        for _ in range(retry_num):
            conn = self.pool.connection()
            client = conn.client
            try:
                client.remove_object(bucket_name, object_name)
                return True
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return True
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                conn.close()
        logger.error({"msg": "最大重试次数", "action": "delete", "object": object_name})
        return False

    def delete_bucket(self, bucket_name: str, retry_num: int = 3) -> bool:
        """删除存储桶"""
        for _ in range(retry_num):
            conn = self.pool.connection()
            client = conn.client
            try:
                # 删除桶之前需要确保桶是空的，或者强制删除。Minio 客户端 remove_bucket 只能删除空桶
                if client.bucket_exists(bucket_name):
                    client.remove_bucket(bucket_name)
                return True
            except S3Error as e:
                if e.code == "NoSuchBucket":
                    return True
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                conn.close()
        logger.error({"msg": "最大重试次数", "action": "delete_bucket", "bucket": bucket_name})
        return False

    def stat(self, bucket_name: str, object_name: str, retry_num: int = 3):
        """查看文件状态"""
        for _ in range(retry_num):
            conn = self.pool.connection()
            client = conn.client
            try:
                return client.stat_object(bucket_name, object_name)
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return None
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                conn.close()
        logger.error({"msg": "最大重试次数", "action": "stat", "object": object_name})
        return None

    def close(self):
        self.pool.close()

if __name__ == '__main__':
    # 测试代码
    minio_config = {
        'endpoint': '127.0.0.1:9100',
        'access_key': 'minioadmin',
        'secret_key': 'minioadmin',
        'secure': False
    }
    pool = PoolMinio(concurrency=5, **minio_config)
    db_minio = DBPoolMinio(pool)
    
    bucket = "a-bucket"
    obj_name = "test/1.jpg"
    # local_file = os.path.join(os.path.dirname(__file__), "../test/1.jpg")
    # download_file = os.path.join(os.path.dirname(__file__), "../test/downloaded_1.jpg")
    #
    # # 增/改
    # print("Uploading...")
    # if db_minio.upload(bucket, obj_name, local_file):
    #     print("Upload successful.")
    #
    # # 查
    # print("Checking stat...")
    # stat = db_minio.stat(bucket, obj_name)
    # if stat:
    #     print(f"File size: {stat.size} bytes")

    # print("Downloading...")
    # if db_minio.download(bucket, obj_name, download_file):
    #     print("Download successful.")

    # # 删
    # print("Deleting...")
    # if db_minio.delete(bucket, obj_name):
    #     print("Delete successful.")

    # # 再次查以验证删除
    # print("Checking stat after delete...")
    # stat = db_minio.stat(bucket, obj_name)
    # if stat is None:
    #     print("File verified deleted.")
    # #
    # 删桶
    print("Deleting bucket...")
    if db_minio.delete_bucket(bucket):
        print("Bucket deleted successfully.")
        
    db_minio.close()
