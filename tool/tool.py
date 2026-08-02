import json
import os
import sys
import requests
import uuid
sys.path.append('../')
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from common.db_mysql import *
from common.common import *
from setting.setting import *
from _model.model import *
from common.db_minio import PoolMinio, DBPoolMinio
from common.db_milvus import PoolMilvus, DBPoolMilvus
from common.db_redis import PoolRedis, DBPoolRedis
from pymilvus import DataType, MilvusClient
import subprocess
import locale
import re
from playwright.sync_api import sync_playwright
import urllib.parse
from common.mcp_compatible import McpCompatible


# --- Milvus 工具定义 ---
def _ensure_milvus_collection(db: DBPoolMilvus, collection_name: str):
    if not db.has_collection(collection_name):
        schema = MilvusClient.create_schema(enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=1024)
        schema.add_field("result", DataType.VARCHAR, max_length=65535)
        schema.add_field("file_url_path", DataType.VARCHAR, max_length=65535)
        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",params={"M": 16, "efConstruction": 200})
        db.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)

def _format_document_extract_result(tool_name: str, path: str, content: str, note: str = "") -> str:
    if not content.strip():
        return f"{tool_name} 提取完成，但未读取到有效文本内容: {path}"

    result_parts = [
        f"工具: {tool_name}",
        f"文件路径: {path}",
    ]
    if note:
        result_parts.append(f"说明: {note}")
    result_parts.append("提取结果:")
    result_parts.append(preliminary_compression(content.strip()))
    return "\n".join(result_parts)

@tool(args_schema=MySQLExecuteModel)
def execute_mysql_sql(sql: str, mysql_config:dict, database: str = None) -> str:
    """
    连接本地 MySQL 数据库并执行 SQL 语句的工具。
    默认使用 setting.setting 中的 mysql_config 作为基础配置。
    :param sql: 需要执行的完整的 SQL 语句 (如 SELECT, SHOW, INSERT, UPDATE 等)。
    :param database: 可选参数，指定要操作的数据库名。若需要切换库时填入此参数。
    :return: SQL 语句执行后的结果字符串表示。
    """
    try:
        # 获取并复制配置，避免修改全局变量
        if database:
            mysql_config['database'] = database

        # 1. 实例化连接池与封装操作类
        pool = PoolMysql(concurrency=1, **mysql_config)
        db = DBPoolMysql(pool)

        # 2. 根据 SQL 语句前缀判断是否为读操作
        sql_lower = sql.strip().lower()
        is_read_operation = sql_lower.startswith(('select', 'show', 'desc', 'explain'))

        if is_read_operation:
            # 执行查询，以字典格式返回
            result = db.read(sql, return_dict=True)
            db.close()
            if result is None:
                return "查询执行完成，但未返回任何数据或发生错误，请检查日志。"
            return f"查询成功，共返回 {len(result)} 条记录:\n{result}"
        else:
            # 执行写入/修改/删除
            success = db.execute(sql)
            db.close()
            if success:
                return "SQL 语句执行成功。"
            else:
                return "SQL 语句执行失败，详情请查看系统日志报错信息。"

    except Exception as e:
        return f"MySQL 工具执行期间发生异常: {str(e)}"


@tool(args_schema=RedisExecuteModel)
def execute_redis_command(command: str, redis_config: dict, db: int = None) -> str:
    """
    连接 Redis 数据库并执行 Redis 命令的工具。
    默认使用 setting.setting 中的 redis_config 作为基础配置。
    支持所有标准 Redis 命令，如 SET/GET/DEL/EXISTS/EXPIRE/TTL/KEYS/HGET/HSET/HGETALL/LPUSH/RPUSH/LRANGE/SADD/SMEMBERS 等。

    :param command: 需要执行的完整 Redis 命令字符串，如 "SET mykey myvalue"、"GET mykey"、"HGETALL myhash"
    :param redis_config: Redis 连接配置字典，包含 host、port、password、db 等
    :param db: 可选参数，指定要操作的 Redis 数据库编号。若需要切换库时填入此参数。
    :return: Redis 命令执行后的结果字符串表示。
    """
    try:
        conf = redis_config.copy()
        if db is not None:
            conf['db'] = db

        pool = PoolRedis(concurrency=1, **conf)
        db_redis = DBPoolRedis(pool)
        result = db_redis.execute(command)
        db_redis.close()
        if result is None:
            return f"命令执行完成: {command}\n返回结果: (nil)"
        return f"命令执行成功: {command}\n返回结果: {result}"
    except Exception as e:
        return f"Redis 工具执行期间发生异常: {str(e)}"


@tool(args_schema=RequestsModel)
def request_tool(
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,):
    """
    网络请求访问
    """

    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert
        )
        # 1. 根据响应头快速判断类型
        content_type = response.headers.get('Content-Type', '').lower()

        # 2. 如果是二进制（图片、PDF等），直接返回元数据，没必要 decode 乱码
        if any(t in content_type for t in ['image/', 'video/', 'audio/', 'application/pdf']):
            return f"[二进制文件] 类型: {content_type}, 大小: {len(response.content)} bytes"
        # 3. 正常获取文本内容
        result = response.text
        # --- 针对请求部分的“就地预处理” ---
        if 'application/json' in content_type:
            try:
                # 哪怕是 JSON，也要先格式化，压缩掉不必要的空格
                data_obj = response.json()
                result = json.dumps(data_obj, ensure_ascii=False, separators=(',', ':'))
            except:
                pass
        elif 'text/html' in content_type:
            # 暴力剔除网页里最占空间的 CSS 和 JS，保留核心文本
            result = re.sub(r'<(script|style).*?>.*?</\1>', '', result, flags=re.DOTALL | re.IGNORECASE)
            # 压缩连续换行和空格
            result = re.sub(r'\s+', ' ', result)
    except Exception as e:
        logger.warning(f'请求工具调用错误,error:{e}')
        return f'请求工具调用异常 url:{url} 请求方式:{method} 异常:{e}'
    return f'{preliminary_compression(result)}'




@tool(args_schema=ExecuteCliSchema)
def execute_cli_tool(command: str, cwd: str = "") -> str:
    """
    执行本地命令行工具。支持跨平台编码自动识别与超时保护。
    """
    try:
        cwd = cwd or ROOT_PATH
        # 1. 启动进程：增加环境变量支持，确保一些脚本能找到对应的 Python 解释器
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            timeout=120,
            text=False  # 我们手动处理解码，更安全
        )

        # 2. 智能解码函数：优先尝试 UTF-8，Windows 下兜底 GBK
        def smart_decode(data: bytes) -> str:
            if not data: return ""
            if isinstance(data, str):
                return data
            encodings = ['utf-8', 'gbk', locale.getpreferredencoding()]
            for enc in encodings:
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode('utf-8', errors='ignore')

        stdout = smart_decode(result.stdout).strip()
        stderr = smart_decode(result.stderr).strip()

        # 3. 构造结构化输出
        status = "成功" if result.returncode == 0 else f"失败 (退出码: {result.returncode})"

        output_parts = [f"--- 执行状态: {status} ---"]
        if stdout:
            output_parts.append(f"【标准输出】:\n{stdout}")
        if stderr:
            # 即使是成功状态，有些工具也会在 stderr 打印警告，这对 AI 纠错很有用
            output_parts.append(f"【标准错误/提示】:\n{stderr}")

        if not stdout and not stderr:
            return f"命令执行完成，无任何输出内容。退出码: {result.returncode}"

        # 4. 截断保护 (保留头部和尾部，中间省略，防止 AI 丢失关键错误信息)
        full_output = "\n".join(output_parts)
        if len(full_output) > 4000:
            return full_output[:2000] + "\n\n... (中间内容过长已省略) ...\n\n" + full_output[-1500:]

        return full_output

    except subprocess.TimeoutExpired:
        return "❌ 错误：执行超时（120秒）。请检查脚本是否进入死循环或正在等待用户输入。"
    except FileNotFoundError:
        return f"❌ 错误：在目录 '{cwd}' 下未找到可执行命令，请检查路径是否正确。"
    except Exception as e:
        return f"❌ 运行异常: {str(e)}"


@tool(args_schema=FileOperationModel)
def file_operation_tool(path: str, mode: str = "r", content: str = "", chunk_index: int = 0,chunk_size: int = 10000) -> str:
    """
    文件操作工具：支持读取、写入、追加。
    - 读取时支持分块返回，防止内容过长。
    - 写入/追加时若目录不存在会自动创建。
    """
    try:
        # 1. 写入/追加模式的处理逻辑
        if "w" in mode or "a" in mode:
            # 自动创建不存在的父目录
            dir_name = os.path.dirname(path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)

            # 执行写入或追加
            # 注意：如果 content 是字符串但用了 'wb'，需要编码，这里做简单处理
            write_data = content.encode('utf-8') if "b" in mode and isinstance(content, str) else content

            with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
                f.write(write_data)
            return f"文件操作成功：已以 {mode} 模式写入/追加到 {path}"

        # 2. 读取模式的处理逻辑
        else:
            if not os.path.exists(path):
                return f"错误：文件路径 {path} 不存在。"

            BINARY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
                                 '.ico', '.tiff', '.tif', '.svg',
                                 '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm',
                                 '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
                                 '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                                 '.zip', '.rar', '.7z', '.tar', '.gz',
                                 '.exe', '.dll', '.so', '.dylib'}
            _, ext = os.path.splitext(path)
            if ext.lower() in BINARY_EXTENSIONS:
                return (f"🚫 禁止读取二进制/媒体文件: {path}"
                        f"\n该文件为 {ext} 格式，属于二进制文件，读取只会得到乱码。"
                        f"\n如需使用该文件，请直接使用其路径，无需读取内容。")

            with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
                full_data = f.read()

            # 处理二进制读取后的显示问题
            if "b" in mode:
                full_data = str(full_data)

            # 分块逻辑
            total_length = len(full_data)
            total_chunks = (total_length + chunk_size - 1) // chunk_size

            if total_chunks == 0:
                return f"文件 {path} 内容为空。"

            if chunk_index >= total_chunks:
                return f"错误：请求块索引 {chunk_index} 越界。总块数: {total_chunks}。"

            start_idx = chunk_index * chunk_size
            end_idx = min(start_idx + chunk_size, total_length)
            chunk_content = full_data[start_idx:end_idx]

            meta = f"\n\n--- [第 {chunk_index + 1}/{total_chunks} 块，总长 {total_length}，模式 {mode}] ---"
            return chunk_content + meta

    except Exception as e:
        return f"文件操作异常: {str(e)}"







@tool(args_schema=DocumentExtractSchema)
def pdf_to_text_tool(path: str, pages: str = "all") -> str:
    """提取 PDF 文本内容。支持页码选择器：all、单页、范围。"""
    try:
        if not os.path.exists(path):
            return f"PDF 文件不存在: {path}"
        content = read_pdf(path, pages=pages)
        return _format_document_extract_result("pdf_to_text_tool", path, content, note=f"页码范围: {pages}")
    except Exception as e:
        return f"PDF 文本提取失败: {e}"


@tool(args_schema=DocumentExtractSchema)
def docx_to_text_tool(path: str) -> str:
    """提取 DOCX 文本内容。pages 参数保留兼容，但不会生效。"""
    try:
        if not os.path.exists(path):
            return f"DOCX 文件不存在: {path}"
        content = read_docx(path)
        return _format_document_extract_result("docx_to_text_tool", path, content, note="DOCX 提取不支持 pages 参数，已忽略")
    except Exception as e:
        return f"DOCX 文本提取失败: {e}"


@tool(args_schema=DocumentExtractSchema)
def xlsx_to_text_tool(path: str) -> str:
    """提取 XLSX 文本内容。pages 参数保留兼容，但不会生效。"""
    try:
        if not os.path.exists(path):
            return f"XLSX 文件不存在: {path}"
        content = read_xlsx(path)
        return _format_document_extract_result("xlsx_to_text_tool", path, content, note="XLSX 提取不支持 pages 参数，已忽略")
    except Exception as e:
        return f"XLSX 文本提取失败: {e}"


@tool(args_schema=DocumentExtractSchema)
def pptx_to_text_tool(path: str) -> str:
    """提取 PPTX 文本内容。pages 参数保留兼容，但不会生效。"""
    try:
        if not os.path.exists(path):
            return f"PPTX 文件不存在: {path}"
        content = read_pptx(path)
        return _format_document_extract_result("pptx_to_text_tool", path, content, note="PPTX 提取不支持 pages 参数，已忽略")
    except Exception as e:
        return f"PPTX 文本提取失败: {e}"




# --- MinIO 工具定义 ---
@tool(args_schema=MinioInsertSchema)
def minio_insert(bucket_name: str, object_name: str, file_path: str, custom_minio_config: dict = None) -> str:
    """minio 插入数据"""
    conf = minio_config.copy()
    if custom_minio_config:
        conf.update(custom_minio_config)
    pool = PoolMinio(concurrency=5, **conf)
    db = DBPoolMinio(pool)
    try:
        res = db.upload(bucket_name, object_name, file_path)
        return "MinIO 插入数据成功" if res else "MinIO 插入数据失败"
    finally:
        db.close()

@tool(args_schema=MinioUpdateSchema)
def minio_update(bucket_name: str, object_name: str, file_path: str, custom_minio_config: dict = None) -> str:
    """minio 修改数据"""
    conf = minio_config.copy()
    if custom_minio_config:
        conf.update(custom_minio_config)
    pool = PoolMinio(concurrency=5, **conf)
    db = DBPoolMinio(pool)
    try:
        res = db.upload(bucket_name, object_name, file_path)
        return "MinIO 修改数据成功" if res else "MinIO 修改数据失败"
    finally:
        db.close()

@tool(args_schema=MinioSearchSchema)
def minio_search(bucket_name: str, object_name: str, save_path: str = "", custom_minio_config: dict = None) -> str:
    """minio 查询数据"""
    conf = minio_config.copy()
    if custom_minio_config:
        conf.update(custom_minio_config)
    pool = PoolMinio(concurrency=5, **conf)
    db = DBPoolMinio(pool)
    result = ''
    try:
        if save_path:
            res = db.download(bucket_name, object_name, save_path)
            result = f"MinIO 查询并下载成功，路径: {save_path}" if res else "MinIO 下载失败"
        else:
            stat = db.stat(bucket_name, object_name)
            if stat:
                result = f"文件存在，大小: {stat.size} bytes, 修改时间: {stat.last_modified}"
            else:
                result = "文件不存在"
    except Exception as e:
        logger.info(f'minio 下载异常,异常原因:{e}')
        result = f'minio 下载异常,异常原因:{e}'
    db.close()
    return result

@tool(args_schema=MinioDeleteSchema)
def minio_delete(bucket_name: str, object_name: str, custom_minio_config: dict = None) -> str:
    """minio 删除数据"""
    conf = minio_config.copy()
    if custom_minio_config:
        conf.update(custom_minio_config)
    pool = PoolMinio(concurrency=5, **conf)
    db = DBPoolMinio(pool)
    try:
        res = db.delete(bucket_name, object_name)
        return "MinIO 删除数据成功" if res else "MinIO 删除数据失败"
    finally:
        db.close()

@tool(args_schema=MilvusInsertSchema)
def milvus_insert(collection_name: str, text: str, file_path: str = "", bucket_name: str = "default-bucket", object_name: str = "", db_name: str = "default", custom_milvus_config: dict = None, custom_minio_config: dict = None) -> str:
    """milvus 插入数据"""
    m_conf = milvus_config.copy()
    if custom_milvus_config:
        m_conf.update(custom_milvus_config)
    m_conf["db_name"] = db_name
    milvus_pool = PoolMilvus(**m_conf)
    db_milvus = DBPoolMilvus(milvus_pool)
    try:
        _ensure_milvus_collection(db_milvus, collection_name)
        
        file_url = ""
        if file_path:
            if not os.path.exists(file_path):
                return f"文件 {file_path} 不存在"
            minio_conf = minio_config.copy()
            if custom_minio_config:
                minio_conf.update(custom_minio_config)
            minio_pool = PoolMinio(concurrency=5, **minio_conf)
            db_minio = DBPoolMinio(minio_pool)
            try:
                obj_name = object_name or os.path.basename(file_path)
                upload_res = db_minio.upload(bucket_name, obj_name, file_path)
                if not upload_res:
                    return "MinIO 文件上传失败"
                file_url = f"http://{minio_conf.get('endpoint')}/{bucket_name}/{obj_name}"
            finally:
                db_minio.close()
                
        embed_res = embedding_text(text=text, **embedding_config)
        if embed_res.get('error_code') != 0 or not embed_res.get('vector'):
            return f"向量化失败: {embed_res.get('error_msg')}"
            
        vector = embed_res['vector']
        data = {"vector": vector, "result": text, "file_url_path": file_url}
        res = db_milvus.insert(collection_name, [data])
        return str(res) if res else "Milvus 插入失败"
    finally:
        db_milvus.close()

@tool(args_schema=MilvusUpdateSchema)
def milvus_update(collection_name: str, id: int, text: str, file_path: str = "", bucket_name: str = "default-bucket", object_name: str = "", db_name: str = "default", custom_milvus_config: dict = None, custom_minio_config: dict = None) -> str:
    """milvus 修改数据"""
    m_conf = milvus_config.copy()
    if custom_milvus_config:
        m_conf.update(custom_milvus_config)
    m_conf["db_name"] = db_name
    milvus_pool = PoolMilvus(**m_conf)
    db_milvus = DBPoolMilvus(milvus_pool)
    try:
        _ensure_milvus_collection(db_milvus, collection_name)
        
        file_url = ""
        if file_path:
            if not os.path.exists(file_path):
                return f"文件 {file_path} 不存在"
            minio_conf = minio_config.copy()
            if custom_minio_config:
                minio_conf.update(custom_minio_config)
            minio_pool = PoolMinio(concurrency=5, **minio_conf)
            db_minio = DBPoolMinio(minio_pool)
            try:
                obj_name = object_name or os.path.basename(file_path)
                upload_res = db_minio.upload(bucket_name, obj_name, file_path)
                if not upload_res:
                    return "MinIO 文件上传失败"
                file_url = f"http://{minio_conf.get('endpoint')}/{bucket_name}/{obj_name}"
            finally:
                db_minio.close()
                
        embed_res = embedding_text(text=text, **embedding_config)
        if embed_res.get('error_code') != 0 or not embed_res.get('vector'):
            return f"向量化失败: {embed_res.get('error_msg')}"
            
        vector = embed_res['vector']
        data = {"id": id, "vector": vector, "result": text, "file_url_path": file_url}
        res = db_milvus.upsert(collection_name, [data])
        return str(res) if res else "Milvus 修改失败"
    finally:
        db_milvus.close()

@tool(args_schema=MilvusSearchSchema)
def milvus_search(collection_name: str, text: str, limit: int = 10, db_name: str = "default", custom_milvus_config: dict = None) -> str:
    """milvus 查询数据"""
    m_conf = milvus_config.copy()
    if custom_milvus_config:
        m_conf.update(custom_milvus_config)
    m_conf["db_name"] = db_name
    milvus_pool = PoolMilvus(**m_conf)
    db_milvus = DBPoolMilvus(milvus_pool)
    try:
        _ensure_milvus_collection(db_milvus, collection_name)
        
        embed_res = embedding_text(text=text, **embedding_config)
        if embed_res.get('error_code') != 0 or not embed_res.get('vector'):
            return f"向量化失败: {embed_res.get('error_msg')}"
            
        vector = embed_res['vector']
        res = db_milvus.search(collection_name, data=[vector], limit=limit, output_fields=["id", "result", "file_url_path"])
        return str(res) if res is not None else "Milvus 查询失败"
    finally:
        db_milvus.close()

@tool(args_schema=MilvusDeleteSchema)
def milvus_delete(collection_name: str, id: int, db_name: str = "default", custom_milvus_config: dict = None) -> str:
    """milvus 删除数据"""
    m_conf = milvus_config.copy()
    if custom_milvus_config:
        m_conf.update(custom_milvus_config)
    m_conf["db_name"] = db_name
    milvus_pool = PoolMilvus(**m_conf)
    db_milvus = DBPoolMilvus(milvus_pool)
    try:
        _ensure_milvus_collection(db_milvus, collection_name)
        res = db_milvus.delete(collection_name, ids=[id])
        result = str(res) if res is not None else "Milvus 删除失败"
    except Exception as e:
        logger.info(f'Milvus 删除异常,异常为:{e}')
        result = f'Milvus 删除异常,异常为:{e}'
    db_milvus.close()
    return result

@tool(args_schema=UploadToKnowledgeBaseSchema)
def upload_to_knowledge_base(collection_name: str, file_path: str, db_name: str = "default", split_pattern: str = r"\n\n", chunk_size: int = 2000, custom_milvus_config: dict = None) -> str:
    """
    上传文件到知识库：读取文件内容 -> 按块切分 -> 为每一个文本块生成向量 -> 批量插入到 Milvus 中。
    """
    if not os.path.exists(file_path):
        return f"上传失败：文件 {file_path} 不存在"
        
    # 1. 尝试读取和切分文件内容 (依赖 common.py 中的 read_and_split_file)
    try:
        chunks = read_and_split_file(file_path=file_path, split_pattern=split_pattern, chunk_size=chunk_size)
        if not chunks:
            return "文件读取失败或内容为空"
    except Exception as e:
        return f"读取与切分文件时发生错误：{str(e)}"
        
    # 2. 检查并确保目标数据库存在
    m_conf = milvus_config.copy()
    if custom_milvus_config:
        m_conf.update(custom_milvus_config)
    try:
        # 先连 default，看目标 db 存不存在
        temp_client = MilvusClient(uri=m_conf.get('uri', 'http://localhost:19520'), token=m_conf.get('token', ''))
        dbs = temp_client.list_databases()
        if db_name not in dbs:
            temp_client.create_database(db_name)
            logger.info(f"成功创建数据库: {db_name}")
        temp_client.close()
    except Exception as e:
        logger.warning(f"检查或创建数据库 {db_name} 时发生异常: {e}")

    # 3. 准备向 Milvus 批量插入数据
    m_conf["db_name"] = db_name
    milvus_pool = PoolMilvus(**m_conf)
    db_milvus = DBPoolMilvus(milvus_pool)
    try:
        _ensure_milvus_collection(db_milvus, collection_name)
        
        insert_data_list = []
        for index, text_chunk in enumerate(chunks):
            # 将每个块转换为向量
            embed_res = embedding_text(text=text_chunk, **embedding_config)
            if embed_res.get('error_code') != 0 or not embed_res.get('vector'):
                logger.warning(f"第 {index} 块向量化失败: {embed_res.get('error_msg')}")
                continue
                
            vector = embed_res['vector']
            insert_data_list.append({
                "vector": vector,
                "result": text_chunk,
                "file_url_path": file_path  # 直接存本地路径，不再传MinIO
            })
            
        if not insert_data_list:
            insert_str = "所有内容块向量化失败，未能插入知识库"
        else:
            res = db_milvus.insert(collection_name, insert_data_list)
            if res:
                insert_str = f"文件处理成功：已切分为 {len(insert_data_list)} 个数据块并成功插入到 Milvus (db: {db_name}, collection: {collection_name}) 中。"
            else:
                insert_str = "Milvus 批量插入失败"
    except Exception as e:
        insert_str = f'Milvus 插入异常,异常为:{e}'

    db_milvus.close()
    return insert_str

@tool(args_schema=UrlDownloadSchema)
def url_download_tool(url: str, save_path: str = "") -> str:
    """
    从指定 URL 下载文件并保存到本地。
    支持自动识别文件类型，未指定文件名时自动以 UUID 命名。
    :param url: 要下载的文件 URL
    :param save_path: 保存路径。可以是完整文件路径(如 D:/img/photo.jpg)、
                      目录路径(如 D:/img/，末尾带斜杠)、或留空。
                      留空则默认保存到 setting 中 download_file_dir_path 配置目录，文件名自动生成。
    :return: 下载结果信息（路径、大小、类型）
    """
    try:
        content_type_map = {
            'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif',
            'image/webp': '.webp', 'image/bmp': '.bmp', 'image/svg+xml': '.svg',
            'video/mp4': '.mp4', 'video/webm': '.webm', 'audio/mpeg': '.mp3',
            'application/pdf': '.pdf', 'application/zip': '.zip',
            'text/html': '.html', 'text/plain': '.txt', 'application/json': '.json',
        }

        resp = requests.get(url, stream=True, timeout=120)
        if resp.status_code != 200:
            return f"下载失败: HTTP {resp.status_code}"

        content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()
        ext = content_type_map.get(content_type, '')
        if not ext:
            url_path = url.split('?')[0]
            _, url_ext = os.path.splitext(url_path)
            ext = url_ext if url_ext else '.bin'

        if not save_path:
            save_path = download_file_dir_path
        save_path = save_path.replace('\\', '/')

        if not os.path.splitext(save_path)[1]:
            if save_path.endswith('/'):
                save_path += str(uuid.uuid4()) + ext
            else:
                save_path = save_path + '/' + str(uuid.uuid4()) + ext

        dir_name = os.path.dirname(save_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)

        total_size = 0
        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)

        size_kb = total_size / 1024
        size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
        return f"下载成功: {save_path}, {size_str}, {content_type or ext}"
    except requests.exceptions.Timeout:
        return "下载超时（120秒）"
    except Exception as e:
        return f"下载异常: {str(e)}"


# 工具列表
tool_list = [
    execute_mysql_sql,
    execute_redis_command,
    request_tool,
    execute_cli_tool,
    file_operation_tool,
    pdf_to_text_tool,
    docx_to_text_tool,
    xlsx_to_text_tool,
    pptx_to_text_tool,
    minio_insert,
    minio_update,
    minio_search,
    minio_delete,
    milvus_insert,
    milvus_update,
    milvus_search,
    milvus_delete,
    upload_to_knowledge_base,
    url_download_tool
]
# --- MCP 工具加载 (新增) ---
try:
    mcp_compat = McpCompatible(mcp_tool_config)
    mcp_tools = mcp_compat.load_mcp_tools()
    tool_list.extend(mcp_tools)
except Exception as e:
    logger.warning(f'mcp工具列表加载异常,异常为:{e}')

logger.info(f'MCP工具与内置工具加载完成，共加载 {len(tool_list)} 个工具')
