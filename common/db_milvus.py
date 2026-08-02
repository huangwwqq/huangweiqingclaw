#!/usr/bin/env python3
# encoding: utf8

"""
Module Name: db_milvus.py
Description: 高效操作Milvus数据库
Author: Trae
Date: 2024-04-27
"""
import sys
sys.path.append('../')
sys.path=list(set(sys.path))
import queue
from typing import Union, List, Dict, Optional, Tuple
from pymilvus import MilvusClient
from setting.setting import *


class PoolMilvus:
    """构建Milvus连接池"""
    def __init__(self, uri: str, token: str = "", pool_size: int = 5, db_name: str = "", timeout: Optional[float] = None, **kwargs):
        self.uri = uri
        self.token = token
        self.pool_size = pool_size
        self.db_name = db_name
        self.timeout = timeout
        self.kwargs = kwargs
        self.pool = queue.Queue(maxsize=pool_size)
        
        for _ in range(pool_size):
            client = MilvusClient(uri=uri, token=token, db_name=db_name, timeout=timeout, **kwargs)
            self.pool.put(client)
            
    def connection(self) -> MilvusClient:
        """获取一个连接"""
        return self.pool.get(block=True)
        
    def release(self, client: MilvusClient):
        """释放连接回连接池"""
        self.pool.put(client)

    def close(self):
        """关闭所有连接"""
        while not self.pool.empty():
            client = self.pool.get()
            client.close()


class DBPoolMilvus:
    """连接池操作Milvus的封装"""
    def __init__(self, pool: PoolMilvus):
        """
        初始化 DBPoolMilvus
        
        :param pool: PoolMilvus 实例，即 Milvus 的连接池
        """
        self.pool = pool

    def insert(self, collection_name: str, data: Union[Dict, List[Dict]], partition_name: str = '', timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> Optional[Dict]:
        """
        向指定的集合中插入数据。

        :param collection_name: 集合的名称。
        :param data: 要插入的数据，可以是单条记录(Dict)或多条记录的列表(List[Dict])。
        :param partition_name: (可选) 分区的名称，默认为空。
        :param timeout: (可选) 操作的超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :param kwargs: 其他 pymilvus 支持的参数。
        :return: 插入结果的字典，如果完全失败则返回 None。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                res = client.insert(collection_name=collection_name, data=data, partition_name=partition_name, timeout=timeout, **kwargs)
                return res
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "insert"})
        return None

    def upsert(self, collection_name: str, data: Union[Dict, List[Dict]], partition_name: str = '', timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> Optional[Dict]:
        """
        更新或插入数据到指定的集合中。如果主键存在则更新，否则插入。
        
        注意：
        1. 传入的 data 字典中【必须】包含该集合的 Primary Key (主键) 字段及其对应的值。
        2. Milvus 是通过这个主键字段的值来判断数据是否存在的。
           - 如果主键值存在，Milvus 会将该主键对应的整行数据替换为 data 中提供的新数据。
           - 如果主键值不存在，Milvus 会将 data 作为一条新记录插入。
        3. 因为是整行替换(Overwrite)，所以 data 中需要包含该行的所有必填字段(如向量字段)，
           不能只传需要更新的个别标量字段。

        :param collection_name: 集合的名称。
        :param data: 要插入或更新的数据，单条记录(Dict)或多条记录的列表(List[Dict])。
        :param partition_name: (可选) 分区的名称，默认为空。
        :param timeout: (可选) 操作的超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :param kwargs: 其他 pymilvus 支持的参数。
        :return: 更新/插入结果的字典，如果完全失败则返回 None。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                res = client.upsert(collection_name=collection_name, data=data, partition_name=partition_name, timeout=timeout, **kwargs)
                return res
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "upsert"})
        return None

    def search(self, collection_name: str, data: Union[List[list], list], filter: str = '', limit: int = 10, output_fields: Optional[List[str]] = None, search_params: Optional[dict] = None, partition_names: Optional[List[str]] = None, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> Optional[List[List[dict]]]:
        """
        在集合中进行向量相似度搜索。

        :param collection_name: 集合的名称。
        :param data: 待搜索的向量列表(可以是一个向量，也可以是多个向量的列表)。
        :param filter: (可选) 过滤条件表达式(布尔表达式)，默认为空。
        :param limit: (可选) 返回的相似结果数量，默认 10。
        :param output_fields: (可选) 随结果一并返回的标量字段列表。
        :param search_params: (可选) 搜索的特定参数配置字典。
        :param partition_names: (可选) 要搜索的分区名称列表。
        :param timeout: (可选) 操作的超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :param kwargs: 其他 pymilvus 支持的参数。
        :return: 包含相似结果列表的二维数组，如果完全失败则返回 None。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                res = client.search(collection_name=collection_name, data=data, filter=filter, limit=limit, output_fields=output_fields, search_params=search_params, partition_names=partition_names, timeout=timeout, **kwargs)
                return res
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "search"})
        return None

    def query(self, collection_name: str, filter: str = '', ids: Union[List, str, int, None] = None, output_fields: Optional[List[str]] = None, partition_names: Optional[List[str]] = None, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> Optional[List[dict]]:
        """
        通过标量过滤条件或主键(ids)查询集合中的数据。

        :param collection_name: 集合的名称。
        :param filter: (可选) 过滤条件表达式(布尔表达式)。
        :param ids: (可选) 指定要查询的主键 ID 或 ID 列表。
        :param output_fields: (可选) 随结果一并返回的标量字段列表。
        :param partition_names: (可选) 要查询的分区名称列表。
        :param timeout: (可选) 操作的超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :param kwargs: 其他 pymilvus 支持的参数。
        :return: 包含查询结果记录的列表，如果完全失败则返回 None。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                res = client.query(collection_name=collection_name, filter=filter, ids=ids, output_fields=output_fields, partition_names=partition_names, timeout=timeout, **kwargs)
                return res
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "query"})
        return None

    def delete(self, collection_name: str, ids: Union[list, str, int, None] = None, filter: Optional[str] = None, partition_name: Optional[str] = None, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> Optional[Dict]:
        """
        通过主键(ids)或标量过滤条件删除集合中的数据。

        :param collection_name: 集合的名称。
        :param ids: (可选) 指定要删除的主键 ID 或 ID 列表。
        :param filter: (可选) 过滤条件表达式(布尔表达式)。
        :param partition_name: (可选) 指定分区的名称。
        :param timeout: (可选) 操作的超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :param kwargs: 其他 pymilvus 支持的参数。
        :return: 删除操作的执行结果字典，如果完全失败则返回 None。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                res = client.delete(collection_name=collection_name, ids=ids, filter=filter, partition_name=partition_name, timeout=timeout, **kwargs)
                return res
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "delete"})
        return None

    def create_database(self, db_name: str, properties: Optional[dict] = None, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> bool:
        """
        创建数据库。
        注意：Milvus 默认存在一个名为 'default' 的数据库。

        :param db_name: 数据库名称。
        :param properties: (可选) 数据库属性配置。
        :param timeout: (可选) 操作超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :return: 成功返回 True，失败返回 False。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                client.create_database(db_name=db_name, properties=properties, timeout=timeout, **kwargs)
                return True
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "db_name": db_name, "op": "create_database"})
        return False

    def create_collection(self, collection_name: str, dimension: Optional[int] = None, primary_field_name: str = 'id', id_type: str = 'int', vector_field_name: str = 'vector', metric_type: str = 'COSINE', auto_id: bool = False, schema=None, index_params=None, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> bool:
        """
        创建集合 (建表)。
        支持快速创建（指定维度等基本参数）或高级创建（通过 schema 和 index_params 详细定义）。

        :param collection_name: 集合的名称。
        :param dimension: (可选) 向量的维度。如果使用快速创建模式，则必须提供。
        :param primary_field_name: 主键字段名，默认为 'id'。
        :param id_type: 主键类型，'int' (默认) 或 'string'。
        :param vector_field_name: 向量字段名，默认为 'vector'。
        :param metric_type: 距离度量方式，如 'COSINE', 'L2', 'IP'。
        :param auto_id: 是否自动生成主键，默认为 False。
        :param schema: (可选) 自定义的 CollectionSchema 对象，用于高级创建。
        :param index_params: (可选) 自定义的 IndexParams 对象，用于高级创建。
        :param timeout: (可选) 操作超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :return: 成功返回 True，失败返回 False。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                client.create_collection(
                    collection_name=collection_name, dimension=dimension, primary_field_name=primary_field_name,
                    id_type=id_type, vector_field_name=vector_field_name, metric_type=metric_type, auto_id=auto_id,
                    schema=schema, index_params=index_params, timeout=timeout, **kwargs
                )
                return True
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "create_collection"})
        return False

    def has_collection(self, collection_name: str, timeout: Optional[float] = None, retry_num: int = 3, **kwargs) -> bool:
        """
        检查集合是否存在。

        :param collection_name: 集合的名称。
        :param timeout: (可选) 操作超时时间(秒)。
        :param retry_num: (可选) 失败重试次数，默认 3 次。
        :return: 存在返回 True，不存在或查询失败返回 False。
        """
        for _ in range(retry_num):
            client = self.pool.connection()
            try:
                return client.has_collection(collection_name=collection_name, timeout=timeout, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warning(f"{exc_type.__name__}: {e}")
            finally:
                self.pool.release(client)
        logger.error({"msg": "最大重试次数", "collection": collection_name, "op": "has_collection"})
        return False

    def test_connect(self):
        client = self.pool.connection()
        try:
            res = client.list_collections()
            logger.info(res)
        finally:
            self.pool.release(client)

    def close(self):
        self.pool.close()

if __name__ == '__main__':
    from pymilvus import DataType
    pool = PoolMilvus(uri="http://localhost:19520", db_name="trade")
    db =  DBPoolMilvus(pool)

    # 2. 构建 schema：严格定义 4 个字段
    schema = MilvusClient.create_schema(enable_dynamic_field=False)

    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)  # 主键，自增
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=1024)  # 向量（dim 改成你的实际维度）
    schema.add_field("result", DataType.VARCHAR, max_length=65535)  # result 字段
    schema.add_field("file_url_path", DataType.VARCHAR, max_length=65535)  # result 字段

    # 3. 构建 HNSW 索引
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",
                           params={"M": 16, "efConstruction": 200})

    # 4. 调用 create_collection
    db.create_collection(collection_name="trade", schema=schema, index_params=index_params)