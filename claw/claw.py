import json
import sys
import uuid
from datetime import datetime, timedelta
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser,StrOutputParser
sys.path.append('../')
from llm_client import *
from curd.huangweiqingclaw.tb_agent_message import *
from curd.huangweiqingclaw.tb_self_awareness import *
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
            system_prompt:str = '',
            skill_folders:list = None,  # 手动加载技能列表
            **kwargs
    ):
        self.tb_self_awareness_object = TbSelfAwareness(huangweiqingclaw_mysql_config)
        self.tb_agent_message_object = TbAgentMessage(huangweiqingclaw_mysql_config)
        self.skill_folders = skill_folders
        self.agent, self.llm = self.load_agent(
            model_manufacturer=model_manufacturer,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            system_prompt=system_prompt,
            **kwargs
        )

    def load_agent(
            self,
            model_manufacturer: str = '',
            model_name: str = '',
            base_url: str = '',
            api_key: str = '',
            temperature: float = 0.7,
            system_prompt:str = '',
            **kwargs
    ):
        """
        加载 Agent 实例
        """

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
        return agent_executor, llm

    def _compress_text(self, data: str,) -> str:
        """
        通用压缩逻辑：支持压缩历史记录或过长的工具返回结果
        """
        truncated_data = preliminary_compression(data)
        compress_prompt = (
            "请将以下冗长的文本进行高度压缩摘要。\n"
            "要求：严格保留关键参数、数据结果、错误信息或任务进度，删除无意义的冗余。直接输出摘要内容，不要废话。\n"
            "要求：如果是用户输入的是空字符串,直接输出: 用户输入为空,无需压缩\n"
        )
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", compress_prompt),
                ("human", "{user_input}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"user_input": f'用户输入内容:{truncated_data}'})
            if result:
                return f"[已压缩]: {result}"
        except Exception as e:
            logger.error(f"压缩失败: {e}")

        return truncated_data

    def _extract_self_awareness(self, user_input: str) -> dict:
        field_desc = "\n".join(
            f"- {name}: {field_info.description or name}"
            for name, field_info in SelfAwareness.model_fields.items()
        )
        self_awareness_prompt = (
            "【核心约束】在明确用户身份信息之前，不做任何提取操作。如果用户输入不包含任何可识别的身份信息，"
            "所有字段必须保持为空字符串，严禁编造或猜测任何内容。\n"
            "\n"
            "你是一个信息提取助手。根据用户的自然语言输入，提取出以下字段信息，"
            "严格输出JSON格式，只输出JSON，不要包含任何其他文字。\n"
            "\n"
            "字段说明：\n"
            f"{field_desc}\n"
            "\n"
            "规则：\n"
            '1. 用户没有提到的字段，值设为空字符串 ""\n'
            "2. 只输出JSON对象，不要有任何解释、markdown标记或多余内容\n"
            "3. 提取信息要准确，不要猜测或编造用户未提及的信息\n"
            "4. 若用户输入完全不包含任何个人身份信息，所有字段全部返回空字符串"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", self_awareness_prompt),
            ("human", "{user_input}")
        ])
        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({"user_input": user_input})
        awareness = SelfAwareness(**result).__dict__
        return awareness

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

        # 查询用户自我认知
        self_awareness = self.tb_self_awareness_object.get_self_awareness(user_id)
        if not self_awareness:
            logger.info(f'用户 {user_id} 未建立自我认知，尝试从输入中提取')
            try:
                awareness_dict = self._extract_self_awareness(user_input)
                field_list = [
                    field_info.description
                    for field_name, field_info in SelfAwareness.model_fields.items() if field_name != "userid"
                ]
                error_msg = f'用户未建立自我认知，且输入中未包含有效身份信息，请先引导用户确认身份信息 需要建立以下字段:{",".join(field_list)}'
                if not awareness_dict.get('name'):
                    return WorkResponse(
                        user_id=user_id,
                        message_id=message_id,
                        error_code=1,
                        error_msg=error_msg
                    ).__dict__
                awareness_dict['userid'] = user_id
                self.tb_self_awareness_object.save_self_awareness([awareness_dict])
                self_awareness = awareness_dict
                logger.info(f'已从输入中提取并保存用户 {user_id} 的自我认知')
            except Exception as e:
                logger.error(f'提取自我认知失败: {e}')
                return WorkResponse(
                    user_id=user_id,
                    message_id=message_id,
                    error_code=1,
                    error_msg=f'提取用户自我认知失败: {e}'
                ).__dict__

        awareness_lines = [
            f"{k}: {v}" for k, v in self_awareness.items()
            if v and k not in ('id', 'is_delete', 'create_time', 'update_time')
        ]
        awareness_prompt = f"当前对话用户信息:\n" + "\n".join(awareness_lines)

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

        # 2. 借鉴 Kocoro 的做法：按需挑选相关技能正文，而不是把全部技能全文塞进 system prompt
        runtime_skills_prompt = get_skills_context(
            user_input=user_input,
            file_url_path_list=file_url_path_list,
            content_limit=2200,
            max_skills=3,
            skill_folders=self.skill_folders
        )

        # 3. 将附件按类型分流成上下文片段：文档提取文本、图片只保留元信息与路径
        attachment_context = build_attachment_context(file_url_path_list=file_url_path_list)

        # 4. 构造当前输入
        file_url_path_msg = ", ".join(file_url_path_list[:file_list_max_length]) if file_url_path_list else ''
        now_user_input = f'用户id:{user_id}\n消息id:{message_id}\n用户输入:{user_input}'
        if file_url_path_msg:
            now_user_input += f'\n文件附件:{file_url_path_msg}'

        input_sections = [
            awareness_prompt,
            f"历史背景:\n{historical_prompt}",
            f"技能上下文:\n{runtime_skills_prompt}",
            f"附件上下文:\n{attachment_context}" if attachment_context else "",
            f"当前任务:\n{now_user_input}",
        ]
        input_msg = "\n\n".join(section for section in input_sections if section)

        # 5. 执行 Agent 并流式处理
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

            ai_summary_msg = {}
            ai_summary_data = self.agent.invoke(input={"messages": [{"role": "user", "content": summary_prompt}]})

            if ai_summary_data.get('messages'):
                content = ai_summary_data['messages'][-1].content
                if content:
                    ai_summary_msg = AgentMessage(user_id=user_id, message_id=message_id, role='summary',
                                                  message=content).__dict__
                    self.tb_agent_message_object.save_memory([ai_summary_msg])

            return WorkResponse(
                user_id=user_id,
                message_id=message_id,
                ai_summary_msg=ai_summary_msg,
                message_list=message_list,
                error_code=0,
                error_msg=''
            ).__dict__
        except Exception as e:
            return WorkResponse(
                user_id=user_id,
                message_id=message_id,
                error_code=2,
                error_msg=f'{e}'
            ).__dict__


if __name__ == '__main__':
    claw = HuangwqClaw(
        model_manufacturer='deepseek',
        model_name='deepseek-v4-flash',
        base_url='https://api.deepseek.com',
        api_key='sk-f256e5e33e04466ab0da3a08b73f8cb4',
        # skill_folders=['xiaohongshutools']
    )
    print(
        claw.work(
            user_id='huangweiqing',
            # user_input = '我叫Mr.黄, 我27岁, 我生日是1999.6.8, 大专, 毕业于江门职业技术学院,在深圳海度科技优先公司作,我的职位是全栈开发工程师,职业是python程序员, 你就叫不眠蔡,和我对话就诙谐幽默点'
            user_input='使用小红书技能查找5篇关于"whatsapp"的文章 ,要有作者 点赞量 收藏量 评论数 前5条评论 文章标签 文章详情,用这个cookie:"abRequestId=80a9e0e0-6997-51da-a497-7000f70907f8; a1=19e68e087eem66vw1ofg8nf9wmzi5d0pcql3pmzsr50000117044; webId=c053ae62758602a1e09c00ceae74d05b; gid=yjdKYd8j0YSWyjdKYd8YWA6udd6KKhEylikY1MFIijE6uq2832f8UU888yyW84484j2Y8YWi; x-rednote-datactry=CN; x-rednote-holderctry=CN; x-user-id-ad-market.xiaohongshu.com=618ba6a0000000001000917b; customerClientId=354903240012881; access-token-ad-market.xiaohongshu.com=customer.ad_market.AT-68c517649580287576522759cfxsrvf3wus9sjmb; x-user-id-sxt.xiaohongshu.com=618ba6a0000000001000917b; x-user-id-pro.xiaohongshu.com=618ba6a0000000001000917b; x-user-id-creator.xiaohongshu.com=618ba6a0000000001000917b; x-user-id-pgy.xiaohongshu.com=618ba6a0000000001000917b; xsecappid=xhs-pc-web; ets=1783045071982; web_session=040069b0ffe5e812c12db75372384bb21df099; id_token=VjEAAM+FwFQSI2Vv5tRqic/ugvOPBoAdwtkjaeUEXWI/vuQ0huBhnGfJOBPDCZiswOnRUqPeiR4v+cClX3vCSpzNgKNZwmgAWp0NpxW2/hp4SuU8y0PFo6x8KaXzwODHl5gtWqU5; webBuild=6.34.4; loadts=1785073984231; acw_tc=0ad627c117850739845903688e38d5a951ac73b410bd87d66e41470d69fe5f; unread={%22ub%22:%226a6493340000000011006955%22%2C%22ue%22:%226a5d8693000000001102f0f6%22%2C%22uc%22:30}; websectiga=3633fe24d49c7dd0eb923edc8205740f10fdb18b25d424d2a2322c6196d2a4ad; sec_poison_id=71772a36-b362-47a8-bf00-848a7a2a6464"'
        )
    )
