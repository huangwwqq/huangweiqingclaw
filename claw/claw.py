import json
import sys
import uuid
from datetime import datetime, timedelta
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
sys.path.append('../')
from llm_client import *
from curd.huangweiqingclaw.tb_agent_message import *
from common.common import *
from _model.model import *
from setting.setting import *
from tool.tool import *


class HuangwqClaw:

    def __init__(
            self,
            model_manufacturer: str,
            model_name: str,
            base_url: str = '',
            api_key: str = '',
            temperature: float = 0.7,
            **kwargs
    ):
        self.agent = self.load_agent(
            model_manufacturer=model_manufacturer,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )
        self.tb_agent_message_object = TbAgentMessage(huangweiqingclaw_mysql_config)

    def load_agent(
            self,
            model_manufacturer: str = '',
            model_name: str = '',
            base_url: str = '',
            api_key: str = '',
            temperature: float = 0.7,
            **kwargs
    ):
        """
        加载 Agent 实例
        """
        self_awareness_prompt = get_self_awareness()
        skills_prompt = get_skills_context()
        system_prompt = f'{self_awareness_prompt}\n{skills_prompt}'
        llm = LangChainLLMFactory.create(
            provider=model_manufacturer,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )
        agent_executor = create_agent(
            model=llm,
            tools=tool_list,
            system_prompt=system_prompt,
        )
        return agent_executor

    def _compress_text(self, data: str,) -> str:
        """
        通用压缩逻辑：支持压缩历史记录或过长的工具返回结果
        """
        # 设定阈值

        truncated_data = preliminary_compression(data)
        compress_prompt = (
            f"请将以下冗长的文本进行高度压缩摘要。\n"
            f"要求：严格保留关键参数、数据结果、错误信息或任务进度，删除无意义的冗余。直接输出摘要内容，不要废话。\n"
            f"待压缩内容：\n{truncated_data}"
        )
        try:
            res = self.agent.invoke(
                input={"messages": [{"role": "user", "content": compress_prompt}]},
                config={"recursion_limit": 5}
            )
            if res.get('messages'):
                compressed_text = res['messages'][-1].content
                return f"[已压缩]: {compressed_text}"
        except Exception as e:
            logger.error(f"压缩失败: {e}")

        return truncated_data

    def work(
            self,
            user_id: str,
            user_input: str,
            message_id: str = '',
            file_url_path_list: list = None
    ):
        """
        AI智能体工作逻辑
        """
        if not user_id:
            logger.warning(f'缺少用户id')
            return list()
        if not user_input:
            logger.warning(f'缺少用户输入')
            return list()
        if not message_id:
            message_id = str(uuid.uuid4())
            logger.info(f'生成新对话,对话id:{message_id}')

        # 1. 提取历史记忆并压缩
        start_time = (datetime.now() - timedelta(seconds=memory_time)).strftime("%Y-%m-%d %H:%M:%S")
        historical_dialogue = self.tb_agent_message_object.get_memory(
            user_id=user_id, message_id=message_id, start_time=start_time, limit=memory_limit, role='summary'
        )

        historical_msg_list = list()
        for msg in historical_dialogue:
            if not msg.get("message"):
                continue
            historical_msg = f'角色:{msg.get("role") or ""}\n消息:{msg.get("message") or ""}'
            historical_msg_list.append(historical_msg)

        historical_msg_data = self._compress_text('\n'.join(historical_msg_list))
        historical_prompt = f"以下是历史消息摘要:\n{historical_msg_data}\n"

        # 2. 构造当前输入
        file_url_path_msg = ", ".join(file_url_path_list[:file_list_max_length]) if file_url_path_list else ''
        now_user_input = f'用户id:{user_id}\n消息id:{message_id}\n用户输入:{user_input}'
        if file_url_path_msg:
            now_user_input += f'\n文件附件:{file_url_path_msg}'

        input_msg = f"历史背景:\n{historical_prompt}\n当前任务:\n{now_user_input}"

        # 3. 执行 Agent 并流式处理
        model_run_config = {"recursion_limit": max_react_step}
        message_list = list()

        # 预存用户输入
        user_msg = AgentMessage(user_id=user_id, message_id=message_id, role='user', message=user_input).__dict__
        if file_url_path_list is not None:
            user_msg['file_url_list'] = json.dumps(file_url_path_list)
        self.tb_agent_message_object.save_memory(memory_list=[user_msg])
        try:
            for chunk in self.agent.stream({"messages": [{"role": "user", "content": input_msg}]}, config=model_run_config,stream_mode="updates"):
                for node_name, node_state in chunk.items():
                    latest_msg = node_state["messages"][-1]
                    role, message = '', ''

                    # 情况 A: 模型的回复文本
                    if hasattr(latest_msg, "content") and latest_msg.content:
                        role = 'agent'
                        message = latest_msg.content
                        message = self._compress_text(message)

                    # 情况 B: 工具调用及其返回结果
                    if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                        role = 'tool'
                        raw_tool_data = json.dumps(latest_msg.tool_calls, ensure_ascii=False)
                        # --- 这里是关键：对工具返回的超长结果进行压缩 ---
                        message = self._compress_text(raw_tool_data)

                    if role:
                        msg_data = AgentMessage(user_id=user_id, message_id=message_id, role=role, message=message).__dict__
                        message_list.append(msg_data)
                        logger.info(f'记录消息 - 角色: {role}, 长度: {len(message)},msg:{message}')

            # 4. 存入数据库并生成总结
            self.tb_agent_message_object.save_memory(message_list)

            agent_message_str = '\n'.join([msg['message'] for msg in message_list if msg['role'] == 'agent'])
            summary_prompt = (
                "你是一个记忆管理专家。请根据本次对话，提取并更新一份‘核心记忆快照’。\n"
                "要求：\n"
                "1. 必须保留：用户提到的关键信息（如ID、姓名、偏好）、已执行成功的工具结果（如查询到的SQL数据总结、读取的文件路径）、当前任务所处的阶段。\n"
                "2. 剔除：无意义的寒暄、冗长的原始数据（仅保留关键数值）、重复的报错信息。\n"
                "3. 形式：使用精炼的列表或段落。\n\n"
                f"--- 当前对话输入 ---\n{user_input}\n"
                f"--- 智能体操作与回答 ---\n{agent_message_str}\n\n"
                "请提供最终的记忆摘要："
            )

            ai_summary_msg = ''
            ai_summary_data = self.agent.invoke(input={"messages": [{"role": "user", "content": summary_prompt}]})

            if ai_summary_data.get('messages'):
                content = ai_summary_data['messages'][-1].content
                if content:
                    ai_summary_msg = AgentMessage(user_id=user_id, message_id=message_id, role='summary',
                                                  message=content).__dict__
                    self.tb_agent_message_object.save_memory([ai_summary_msg])

            return {
                'user_id': user_id,
                'message_id': message_id,
                'ai_summary_msg': ai_summary_msg,
                'message_list': message_list,
                'error_code':0,
                'error_msg': ''
            }
        except Exception as e:
            return {
                'user_id': user_id,
                'message_id': message_id,
                'ai_summary_msg': '',
                'message_list': message_list,
                'error_code':2,
                'error_msg': f'{e}'
            }


if __name__ == '__main__':
    claw = HuangwqClaw(
        model_manufacturer='deepseek',
        model_name='deepseek-chat',
        base_url='https://api.deepseek.com',
        api_key='你的api_key'
    )
    print(claw.work(user_id='huangweiqing',user_input='你使用互联网搜索技能,搜索深圳百能信息技术有限公司,将搜索到的结果整合一下,然后给whatsapp号码:**********,使用这个session_id:huangweiqing,请求方式必须按照文档的来,发送一条文本信息,信息内容是刚刚整合的数据'))