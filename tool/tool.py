import os
import sys
import requests
sys.path.append('../')
from langchain_core.tools import tool
from common.db_mysql import *
from common.common import *
from setting.setting import *
from _model.model import *
import subprocess
import locale
import re
from playwright.sync_api import sync_playwright
import urllib.parse

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
def execute_cli_tool(command: str, cwd: str) -> str:
    """
    执行本地命令行工具。支持跨平台编码自动识别与超时保护。
    """
    try:
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
            encodings = ['utf-8', 'gbk', locale.getpreferredencoding()]
            for enc in encodings:
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode('utf-8', errors='replace')

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


@tool(args_schema=WebSearchModel)
def web_search_tool(keyword: str, max_results: int = 10) -> str:
    """
    基于 Playwright 的联网搜索工具。
    自动打开搜索引擎（默认百度，支持 Google），搜索关键词并提取结果。
    
    :param keyword: 搜索词

    :param max_results: 返回结果的最大数量
    :return: 包含标题、链接和摘要的搜索结果字符串
    """
    # 编码搜索词
    encoded_keyword = urllib.parse.quote(keyword)

    # 使用百度
    url = f"https://www.baidu.com/s?wd={encoded_keyword}"
    # 结果选择器 (Baidu)
    result_selector = "div.c-container"
    title_selector = "h3.t"
    link_selector = "h3.t > a, h3.t > div > a, a.c-title-a"

    try:
        with sync_playwright() as p:
            # 使用 Chromium，启动 headless 模式
            browser = p.chromium.launch(headless=True)
            # 配置请求头等，避免被反爬拦截
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # 访问 URL，等待网络空闲
            page.goto(url, wait_until="domcontentloaded", timeout=300000)
            
            # 检查是否遇到了反爬虫验证 (特别是 Google 的 unusual traffic)
            page_text = page.inner_text("body")
            if "unusual traffic" in page_text or "unusual traffic from your computer network" in page_text:
                browser.close()
                return f"搜索引擎触发了反爬虫验证，无法获取搜索结果。建议使用代理或更换搜索引擎。"

            # 等待搜索结果加载
            try:
                page.wait_for_selector(result_selector, timeout=100000)
            except Exception:
                # 即使超时，也尝试提取当前页面结果
                pass

            # 提取搜索结果
            elements = page.query_selector_all(result_selector)
            
            results = []
            for element in elements:
                if len(results) >= max_results:
                    break

                all_text = element.inner_text().strip() if element else ""
                title_el = element.query_selector(title_selector)
                link_el = element.query_selector(link_selector)
                
                title = title_el.inner_text().strip() if title_el else ""
                link = link_el.get_attribute("href") if link_el else ""
                snippet = all_text.replace(title, "", 1).strip() if title else all_text

                
                # 有些百度链接可能是在外层 div
                if not link and title_el:
                    try:
                        link_a = title_el.query_selector("a")
                        if link_a:
                            link = link_a.get_attribute("href")
                    except:
                        pass
                
                # 如果没有标题或链接，跳过
                if not title:
                    continue
                    
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet.replace("\n", " ")
                })
            
            browser.close()
            
            # 格式化输出
            if not results:
                return f"未找到 '{keyword}' 的搜索结果。这可能是因为搜索引擎的反爬虫机制或网络问题。"
                
            output_parts = [f"搜索结果: '{keyword}'"]
            for i, res in enumerate(results, 1):
                output_parts.append(f"{i}. {res['title']}\n   链接: {res['link']}\n   摘要: {res['snippet']}")
                
            return preliminary_compression("\n\n".join(output_parts))
            
    except Exception as e:
        return f"搜索工具执行异常: {str(e)}"

# 工具列表
tool_list = [
    execute_mysql_sql,
    request_tool,
    execute_cli_tool,
    file_operation_tool,
    web_search_tool
]



# @tool
# def playwright_close_session(session_id: str) -> str:
#     """
#     关闭并清理指定用户的 Playwright 浏览器实例释放资源。
#
#     :param session_id: 用户或会话的唯一标识，默认 "default"
#     :return: 执行结果信息
#     """
#     try:
#         if session_id in _PLAYWRIGHT_SESSIONS:
#             session = _PLAYWRIGHT_SESSIONS[session_id]
#             if session.get("browser"):
#                 session["browser"].close()
#             if session.get("playwright"):
#                 session["playwright"].stop()
#             del _PLAYWRIGHT_SESSIONS[session_id]
#             return f"成功清理会话 {session_id} 的浏览器资源"
#         return f"会话 {session_id} 不存在或已清理"
#     except Exception as e:
#         return f"清理会话失败: {str(e)}"
#
#
# @tool
# def playwright_get_html(url: str, session_id: str, wait_selector: str = None, clean: bool = True, chunk_index: int = 0, chunk_size: int = 10000) -> str:
#     """
#     使用 Playwright 获取页面 HTML 内容。如果当前页面已在目标 url，则不会重复跳转。
#     支持自动清洗无用标签以缩减长度，同时支持超长文本分块返回。
#
#     :param url: 目标网址
#     :param session_id:
#     :param wait_selector: (可选) 等待页面中某个 CSS 选择器出现后再返回源码
#     :param clean: (可选) 是否清理无用的标签（如script, style），默认 True
#     :param chunk_index: (可选) 文本块索引，默认 0
#     :param chunk_size: (可选) 每次返回的最大字符数，默认 10000 字符
#     :return: 网页的 HTML 源码片段及分块信息
#     """
#     page = _get_or_create_page(session_id)
#     try:
#         # 核心修改：判断当前页面 URL 是否与目标 URL 一致（或包含目标 URL）
#         # 避免在登录后、验证码滑动后等场景下被重新刷新页面
#         current_url = page.url
#         if not current_url or (url not in current_url and current_url not in url):
#             page.goto(url, wait_until="networkidle")
#
#         if wait_selector:
#             page.wait_for_selector(wait_selector, state="attached")
#
#         if clean:
#             # 在浏览器端执行 JS 清理无关紧要的标签
#             clean_js = """
#             () => {
#                 // 深度克隆 body，避免修改破坏真实页面的渲染和交互状态
#                 const clonedBody = document.body.cloneNode(true);
#                 const elementsToRemove = clonedBody.querySelectorAll('script, style, noscript, svg, path, iframe, canvas, video, audio');
#                 elementsToRemove.forEach(el => el.remove());
#
#                 const removeComments = (node) => {
#                     for (let i = 0; i < node.childNodes.length; i++) {
#                         const child = node.childNodes[i];
#                         if (child.nodeType === 8) {
#                             node.removeChild(child);
#                             i--;
#                         } else if (child.nodeType === 1) {
#                             removeComments(child);
#                         }
#                     }
#                 };
#                 removeComments(clonedBody);
#                 return clonedBody.outerHTML;
#             }
#             """
#             html_content = page.evaluate(clean_js)
#         else:
#             html_content = page.content()
#
#         # 分块逻辑
#         total_length = len(html_content)
#         total_chunks = (total_length + chunk_size - 1) // chunk_size
#
#         if total_chunks == 0:
#             return "页面内容为空"
#
#         if chunk_index >= total_chunks:
#             return f"错误：请求的块索引 {chunk_index} 超出范围。总块数: {total_chunks}。"
#
#         start_idx = chunk_index * chunk_size
#         end_idx = min(start_idx + chunk_size, total_length)
#         chunk_content = html_content[start_idx:end_idx]
#
#         meta_info = f"\n\n--- [HTML 截断信息: 当前返回第 {chunk_index + 1} 块 (共 {total_chunks} 块)，总字符数 {total_length}。如需后续内容请将 chunk_index 加 1 再次调用本工具] ---\n"
#
#         return chunk_content + meta_info
#
#     except Exception as e:
#         return f"获取页面失败: {str(e)}"
#
#
# @tool
# def playwright_click(selector: str, session_id: str) -> str:
#     """
#     使用 Playwright 点击页面上的某个元素。
#
#     :param selector: 元素的 CSS 选择器，例如 "#submit-btn" 或 ".login"
#     :param session_id: (可选) 用户会话标识，用于隔离不同用户的浏览器环境
#     :return: 执行结果信息
#     """
#     try:
#         page = _get_or_create_page(session_id)
#         page.click(selector)
#         return f"成功点击元素: {selector}"
#     except Exception as e:
#         return f"点击元素失败: {str(e)}"
#
#
# @tool
# def playwright_drag_and_drop(session_id: str,source_selector: str, target_selector: str = None, x_offset: int = 0, y_offset: int = 0) -> str:
#     """
#     使用 Playwright 执行拖动与释放操作（常用于滑动验证码等）。
#     支持拖动到目标元素，或者相对源元素按指定的像素偏移量拖动。
#
#     :param source_selector: 需要拖动的源元素 CSS 选择器
#     :param target_selector: (可选) 拖动到的目标元素 CSS 选择器
#     :param x_offset: (可选) 如果没有目标元素，在水平方向拖动的像素距离
#     :param y_offset: (可选) 如果没有目标元素，在垂直方向拖动的像素距离
#     :param session_id: (可选) 用户会话标识
#     :return: 执行结果信息
#     """
#     try:
#         page = _get_or_create_page(session_id)
#         if target_selector:
#             page.drag_and_drop(source_selector, target_selector)
#             return f"成功将 {source_selector} 拖动到 {target_selector}"
#         else:
#             # 相对偏移量拖动，需要模拟真实鼠标轨迹
#             box = page.locator(source_selector).bounding_box()
#             if not box:
#                 return f"找不到源元素: {source_selector}"
#
#             start_x = box["x"] + box["width"] / 2
#             start_y = box["y"] + box["height"] / 2
#
#             page.mouse.move(start_x, start_y)
#             page.mouse.down()
#             # 增加 steps 模拟滑动轨迹，避免瞬移被检测
#             page.mouse.move(start_x + x_offset, start_y + y_offset, steps=10)
#             page.mouse.up()
#             return f"成功将 {source_selector} 相对拖动了 x:{x_offset}, y:{y_offset}"
#     except Exception as e:
#         return f"拖拽操作失败: {str(e)}"
#
#
# @tool
# def playwright_scroll(session_id: str,delta_y: int = 500) -> str:
#     """
#     使用 Playwright 模拟鼠标滚轮向下滑动。
#
#     :param delta_y: 向下滚动的像素值，默认为 500
#     :param session_id: (可选) 用户会话标识
#     :return: 执行结果信息
#     """
#     try:
#         page = _get_or_create_page(session_id)
#         page.mouse.wheel(0, delta_y)
#         return f"成功向下滚动 {delta_y} 像素"
#     except Exception as e:
#         return f"滚动操作失败: {str(e)}"
#
# @tool
# def read_file(file_path:str, read_mode:str, chunk_index: int = 0, chunk_size: int = 10000):
#     """
#     读取文件
#     """
#     if not os.path.exists(file_path):
#         return f'文件路径:{file_path} 不存在'
#
#     if read_mode not in ['r', 'rb', 'r+', 'rb+']:
#         return '读取模式异常'
#
#     with open(file_path, read_mode) as p:
#         data = p.read()
#     data = str(data)[chunk_index*chunk_size:(chunk_index+1)*chunk_size]
#     return f'文件目录:{file_path} 读取模式:{read_mode} 读取结果:{data}'

# tools_list = [
#     execute_mysql_sql,
#     request_tool
# ]






