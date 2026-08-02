import asyncio
import json
import sys
import os
from contextlib import asynccontextmanager
from typing import Any, List, Dict

sys.path.append('../')
from setting.setting import *
from pydantic import BaseModel, ConfigDict, create_model, Field
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from langchain_core.tools import StructuredTool



MCP_TRANSPORT_STDIO = 'stdio'
MCP_TRANSPORT_SSE = 'sse'
MCP_TRANSPORT_STREAMABLE = 'streamable'


class McpCompatible:
    """MCP 工具接入插件类，兼容 MCP API 接口和本地 MCP 服务（STDIO）"""

    def __init__(self, mcp_config: dict):
        self.mcp_config = mcp_config
        self.servers = mcp_config.get("mcpServers", {})

    def load_mcp_tools(self) -> List:
        """加载所有 MCP 服务器提供的工具，返回 LangChain 工具列表"""
        tools = []
        for server_name, server_config in self.servers.items():
            try:
                server_tools = self._load_server_tools(server_name, server_config)
                tools.extend(server_tools)
                logger.info(f'MCP服务器 [{server_name}] 加载成功，共 {len(server_tools)} 个工具')
            except Exception as e:
                logger.warning(f'MCP服务器 [{server_name}] 加载失败: {e}')
        return tools

    def _load_server_tools(self, server_name: str, server_config: dict) -> List:
        """加载单个 MCP 服务器的所有工具（自动检测 stdio/sse/streamable）"""
        return self._load_server_tools_unified(server_name, server_config)

    async def _list_tools_async(self, server_params: StdioServerParameters):
        """异步列出 MCP 服务器提供的所有工具定义"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    async def _call_tool_async(self, server_params: StdioServerParameters,
                               tool_name: str, arguments: dict) -> str:
        """异步调用 MCP 工具"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self._extract_result(result)

    def _extract_result(self, call_tool_result) -> str:
        """从 MCP CallToolResult 中提取文本内容"""
        contents = []
        for item in call_tool_result.content:
            if hasattr(item, 'text'):
                contents.append(item.text)
            elif hasattr(item, 'data'):
                contents.append(str(item.data))
            else:
                contents.append(str(item))
        return '\n'.join(contents) if contents else json.dumps(
            call_tool_result.model_dump(), ensure_ascii=False)

    @staticmethod
    def _make_dynamic_args_schema(input_schema: dict, tool_name: str) -> type:
        """根据 MCP inputSchema 动态构建 Pydantic args_schema"""
        properties = input_schema.get('properties', {})
        required_list = input_schema.get('required', [])

        field_defs = {}
        for pname, pinfo in properties.items():
            ptype = pinfo.get('type', 'string')
            pdesc = pinfo.get('description', '')
            default_val = pinfo.get('default')
            is_required = pname in required_list

            if is_required and default_val is None:
                field_defs[pname] = (Any, Field(description=pdesc))
            else:
                field_defs[pname] = (Any, Field(default=default_val, description=pdesc))

        if field_defs:
            DynamicSchema = create_model(
                f'MCPArgs_{tool_name}',
                __config__=ConfigDict(extra='allow'),
                **field_defs,
            )
        else:
            DynamicSchema = create_model(
                f'MCPArgs_{tool_name}',
                __config__=ConfigDict(extra='allow'),
            )
        return DynamicSchema

    def _build_tool(self, server_name: str, server_params: StdioServerParameters,
                    tool_def) -> StructuredTool:
        """将单个 MCP 工具定义包装为 LangChain StructuredTool"""
        tool_name = tool_def.name
        raw_desc = tool_def.description or ''
        input_schema = tool_def.inputSchema or {}

        full_desc = self._build_description(server_name, tool_name, raw_desc, input_schema)
        ArgsSchema = self._make_dynamic_args_schema(input_schema, tool_name)

        def _sync_run(**kwargs: Any) -> str:
            try:
                return asyncio.run(
                    self._call_tool_async(server_params, tool_name, kwargs)
                )
            except Exception as e:
                return f"MCP工具 [{tool_name}] 调用失败: {str(e)}"

        return StructuredTool(
            name=tool_name,
            description=full_desc,
            func=_sync_run,
            args_schema=ArgsSchema,
        )

    def _build_description(self, server_name: str, tool_name: str,
                           raw_desc: str, input_schema: dict) -> str:
        """构建带参数描述的详细工具描述"""
        desc_parts = [f'[MCP服务:{server_name}] {raw_desc}']

        properties = input_schema.get('properties', {})
        required_list = input_schema.get('required', [])

        if properties:
            desc_parts.append('\n可用参数:')
            for pname, pinfo in properties.items():
                req_mark = '(必填)' if pname in required_list else '(可选)'
                ptype = pinfo.get('type', 'any')
                pdesc = pinfo.get('description', '')
                default_val = pinfo.get('default')
                default_str = f' 默认值:{default_val}' if default_val is not None else ''
                enum_vals = pinfo.get('enum')
                enum_str = f' 可选值:{enum_vals}' if enum_vals else ''
                desc_parts.append(
                    f'  - {pname} ({ptype}) {req_mark}: {pdesc}{default_str}{enum_str}')

        return '\n'.join(desc_parts)

    def call_tool_direct(self, server_name: str, tool_name: str,
                         arguments: dict = None) -> str:
        """直接调用指定 MCP 工具（用于测试）"""
        if server_name not in self.servers:
            return f'MCP服务器 [{server_name}] 未在配置中找到'
        server_config = self.servers[server_name]
        server_params = StdioServerParameters(
            command=server_config.get('command'),
            args=server_config.get('args', []),
            env=server_config.get('env', None),
        )
        return asyncio.run(
            self._call_tool_async(server_params, tool_name, arguments or {})
        )

    def list_tools_direct(self, server_name: str) -> List:
        """直接列出指定 MCP 服务器的工具（用于测试）"""
        if server_name not in self.servers:
            logger.warning(f'MCP服务器 [{server_name}] 未在配置中找到')
            return []
        server_config = self.servers[server_name]
        server_params = StdioServerParameters(
            command=server_config.get('command'),
            args=server_config.get('args', []),
            env=server_config.get('env', None),
        )
        return asyncio.run(self._list_tools_async(server_params))

    # ========== SSE/Streamable 兼容扩展 (新增方法，不修改原有代码) ==========

    @staticmethod
    def _detect_transport_type(server_config: dict):
        """根据配置自动检测传输类型，返回 (transport_type, transport_params)"""
        transport_type = server_config.get('type', '').lower()
        if transport_type == MCP_TRANSPORT_SSE:
            return MCP_TRANSPORT_SSE, server_config.get('url', '')
        if transport_type == MCP_TRANSPORT_STREAMABLE:
            return MCP_TRANSPORT_STREAMABLE, server_config.get('url', '')
        if transport_type == MCP_TRANSPORT_STDIO or 'command' in server_config:
            return MCP_TRANSPORT_STDIO, StdioServerParameters(
                command=server_config.get('command'),
                args=server_config.get('args', []),
                env=server_config.get('env', None),
            )
        if 'url' in server_config:
            url = server_config.get('url', '')
            if url.startswith(('ws://', 'wss://')):
                return MCP_TRANSPORT_STREAMABLE, url
            return MCP_TRANSPORT_SSE, url
        return MCP_TRANSPORT_STDIO, StdioServerParameters(
            command=server_config.get('command'),
            args=server_config.get('args', []),
            env=server_config.get('env', None),
        )

    @staticmethod
    @asynccontextmanager
    async def _get_transport_context(transport_type: str, transport_params):
        """统一的传输层上下文管理器，支持 stdio / sse / streamable"""
        if transport_type == MCP_TRANSPORT_STDIO:
            async with stdio_client(transport_params) as (read, write):
                yield read, write
        elif transport_type == MCP_TRANSPORT_SSE:
            async with sse_client(url=transport_params) as (read, write):
                yield read, write
        elif transport_type == MCP_TRANSPORT_STREAMABLE:
            async with streamablehttp_client(url=transport_params) as (read, write, _):
                yield read, write
        else:
            raise ValueError(f'不支持的 MCP 传输类型: {transport_type}')

    async def _list_tools_async_unified(self, transport_type: str, transport_params) -> list:
        """统一的异步工具列表获取（支持 stdio/sse/streamable）"""
        async with self._get_transport_context(transport_type, transport_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    async def _call_tool_async_unified(self, transport_type: str, transport_params,
                                       tool_name: str, arguments: dict) -> str:
        """统一的异步工具调用（支持 stdio/sse/streamable）"""
        async with self._get_transport_context(transport_type, transport_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self._extract_result(result)

    def _load_server_tools_unified(self, server_name: str, server_config: dict) -> List:
        """统一的服务器工具加载（支持 stdio/sse/streamable）"""
        transport_type, transport_params = self._detect_transport_type(server_config)
        logger.info(f'MCP服务器 [{server_name}] 传输类型: {transport_type}')
        mcp_tool_defs = asyncio.run(
            self._list_tools_async_unified(transport_type, transport_params)
        )
        tools = []
        for tool_def in mcp_tool_defs:
            langchain_tool = self._build_tool_unified(
                server_name, transport_type, transport_params, tool_def
            )
            tools.append(langchain_tool)
        return tools

    def _build_tool_unified(self, server_name: str, transport_type: str,
                            transport_params, tool_def) -> StructuredTool:
        """统一的工具包装（支持 stdio/sse/streamable）"""
        tool_name = tool_def.name
        raw_desc = tool_def.description or ''
        input_schema = tool_def.inputSchema or {}

        full_desc = self._build_description(server_name, tool_name, raw_desc, input_schema)
        ArgsSchema = self._make_dynamic_args_schema(input_schema, tool_name)

        def _sync_run(**kwargs: Any) -> str:
            try:
                return asyncio.run(
                    self._call_tool_async_unified(
                        transport_type, transport_params, tool_name, kwargs
                    )
                )
            except Exception as e:
                return f"MCP工具 [{tool_name}] 调用失败: {str(e)}"

        return StructuredTool(
            name=tool_name,
            description=full_desc,
            func=_sync_run,
            args_schema=ArgsSchema,
        )

    def call_tool_direct_unified(self, server_name: str, tool_name: str,
                                 arguments: dict = None) -> str:
        """统一的直接工具调用（支持 stdio/sse/streamable）"""
        if server_name not in self.servers:
            return f'MCP服务器 [{server_name}] 未在配置中找到'
        server_config = self.servers[server_name]
        transport_type, transport_params = self._detect_transport_type(server_config)
        return asyncio.run(
            self._call_tool_async_unified(
                transport_type, transport_params, tool_name, arguments or {}
            )
        )

    def list_tools_direct_unified(self, server_name: str) -> List:
        """统一的直接工具列表（支持 stdio/sse/streamable）"""
        if server_name not in self.servers:
            logger.warning(f'MCP服务器 [{server_name}] 未在配置中找到')
            return []
        server_config = self.servers[server_name]
        transport_type, transport_params = self._detect_transport_type(server_config)
        return asyncio.run(
            self._list_tools_async_unified(transport_type, transport_params)
        )

