import os
import sys
sys.path.append('../')
from pydantic import SecretStr
from setting.setting import *
from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

class LangChainLLMFactory:
    """
    基于 LangChain 的大模型工厂类
    统一返回 LangChain 的 BaseChatModel 实例，完美兼容 LangChain 生态（LCEL、Agent、Memory 等）
    """
    # 预设各大平台的 Base URL 与 默认推荐模型

    @classmethod
    def create(
        cls, 
        provider: str, 
        api_key: Optional[str] = None,
        base_url:str = '',
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> BaseChatModel:
        """
        创建并返回一个 LangChain ChatModel 实例
        
        :param provider: 提供商名称 (openai, deepseek, qwen, doubao, gemini, ollama)
        :param api_key: API Key，如果不传，则默认尝试从环境变量 {PROVIDER}_API_KEY 获取
        :param model: 模型名称/接入点ID，如果不传则使用预设默认值
        :param temperature: 温度参数，控制生成的随机性
        :param kwargs: 传递给底层 ChatModel 的其他参数（如 max_tokens, streaming 等）
        :return: 继承自 BaseChatModel 的实例，支持 .invoke(), .stream() 及 LCEL 链式调用
        """
        provider = provider.lower()
        if not provider:
            raise ValueError(f"缺少模型厂商: 示例提供商名称 (openai, deepseek, qwen, doubao, gemini, ollama)")

        if not model_name:
            raise ValueError(f"缺少模型名称")

        if not base_url:
            raise ValueError(f"缺少 base_url")

        # ---------------- 1. 特殊处理 Ollama ----------------
        if provider == "ollama":
            return ChatOllama(
                base_url=base_url,
                model=model_name,
                temperature=temperature,
                **kwargs
            )
        if not api_key:
            raise ValueError(f"缺少 api_key。请传入 api_key 参数")
        api_key = SecretStr(api_key)
        # ---------------- 2. 特殊处理 Gemini (使用官方包) ----------------
        if provider == "gemini":
            # 移除可能会跟 ChatGoogleGenerativeAI 冲突的 base_url
            return ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=model_name,
                temperature=temperature,
                **kwargs
            )

        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=temperature,
            **kwargs
        )


# # ---------------- 使用示例 ----------------
# if __name__ == "__main__":
#     from langchain_core.messages import HumanMessage, SystemMessage
#     from langchain_core.prompts import ChatPromptTemplate
#     from langchain_core.output_parsers import StrOutputParser,JsonOutputParser
#
#     # # 定义测试消息
#     # messages = [
#     #     SystemMessage(content="你是一个精通 JS 逆向的资深安全专家。"),
#     #     HumanMessage(content="请用一句话解释什么是 JSVMP。")
#     # ]
#     #
#     # print("="*40)
#     #
#     # # ================= 示例 1: Ollama (本地调用) =================
#     # try:
#     #     # Ollama 无需 API Key，只需保证本地已启动 `ollama run llama3`
#     #     ollama_llm = LangChainLLMFactory.create(provider="ollama", model="deepseek-r1:7b")
#     #     print("【Ollama 响应】:")
#     #     print(ollama_llm.invoke(messages).content)
#     # except Exception as e:
#     #     print("Ollama 调用失败:", e)
#     #
#     # print("\n" + "="*40)
#
#     # ================= 示例 2: DeepSeek (LCEL 链式调用示例) =================
#     try:
#         # 假设通过环境变量获取 API Key 或手动传入
#         deepseek_llm = LangChainLLMFactory.create(
#             provider="deepseek",
#             api_key="你的apikey",
#             model_name = 'deepseek-chat',
#             base_url = 'https://api.deepseek.com'
#         )
#
#         # 使用 LangChain LCEL (LangChain Expression Language) 构建链
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", "你是一个暴躁小哥"),
#             ("human", "{user_input}")
#         ])
#
#         # 组装链: Prompt -> LLM -> 字符串解析器
#         chain = prompt | deepseek_llm | StrOutputParser()
#
#         print("【DeepSeek LCEL 链式响应】:")
#         print(chain.invoke({"user_input": "请你带入你自己,你的老板让你加班不给加班费"}))
#     except Exception as e:
#         print("DeepSeek 调用失败:", e)
#
#     print("\n" + "="*40)
#     #
    # # ================= 示例 3: 阿里云千问 Qwen (流式输出示例) =================
    # try:
    #     qwen_llm = LangChainLLMFactory.create(
    #         provider="qwen",
    #         api_key="your-qwen-api-key"
    #     )
    #     print("【Qwen 流式响应】:")
    #     for chunk in qwen_llm.stream(messages):
    #         print(chunk.content, end="", flush=True)
    #     print()
    # except Exception as e:
    #     print("Qwen 调用失败:", e)

