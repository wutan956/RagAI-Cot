# 任务引擎构建器核心类，用于构建任务引擎

# 3、对每个子任务载入会话场景，然后按照扩写任务步骤构建，MCTS任务

import logging
import threading
import re

from langchain_core.messages import HumanMessage
from langchain.schema import AIMessage
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.runnables import Runnable
from sentence_transformers import CrossEncoder

from common.callback import call_func

from task_step_to_question_chain.base import TaskStepToQuestionChain

from engine.generate.code_generate import (
    QueryProgramGenerator,
)

from engine.storage.storage_context import StorageContext

from vector.base import CollectionService
import uuid
import tiktoken  # 用于计算token数量
class TaskEngineBuilder:

    """TaskEngineBuilder 场景加载模块
                执行会话场景资源初始化，构建MCTS任务

    根据任务步骤，构建场景加载模块，生成资源文件csv
    根据每个任务，载入StructuredDreamsStoryboard 会话场景
    按照扩写任务步骤构建MCTS任务

                输入：
                        task_step_id
                        task_step_store: 任务存储器（SimpleTaskStepStore）
                        start_task_context： 起始任务
                        llm： 模型


    """


    cross_encoder: CrossEncoder
    data_base: str
    collection: CollectionService


    _llm_runable: Runnable[LanguageModelInput, BaseMessage]
    _kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]

    def __init__(
        self,
        task_step_level: str,
        task_step_description: str,
        task_step_name: str,
        aemo_representation_context:str,
        llm_runable: Runnable[LanguageModelInput, BaseMessage],
        cross_encoder: CrossEncoder,
        collection: CollectionService,
        start_task_context: str,
        data_base: str = "search_papers",
        kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]= None,
    ):
        self.start_task_context = start_task_context  # 命令行获取的任务主题
        self.data_base = data_base       # 指定外部数据源（如文献数据库）的名称
        self._llm_runable = llm_runable  # 主模型
        self.cross_encoder = cross_encoder  # 交叉编码器
        self.collection = collection  # 向量数据库
        self.client = None
        self.task_step_to_question_chain = None
        self._kor_dreams_task_step_llm = kor_dreams_task_step_llm  # 辅助模型
        self.task_step_name = task_step_name
        self.task_step_description = task_step_description
        self.task_step_level = task_step_level
        self.aemo_representation_context = aemo_representation_context

    @property
    def llm_runable(self) -> Runnable[LanguageModelInput, BaseMessage]:
        return self._llm_runable

    @llm_runable.setter
    def llm_runable(
        self, llm_runable: Runnable[LanguageModelInput, BaseMessage]
    ) -> None:
        self._llm_runable = llm_runable
    @property
    def kor_dreams_task_step_llm(self) -> Runnable[LanguageModelInput, BaseMessage]:
        return self._kor_dreams_task_step_llm

    @kor_dreams_task_step_llm.setter
    def kor_dreams_task_step_llm(
        self, kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]
    ) -> None:
        self._kor_dreams_task_step_llm = kor_dreams_task_step_llm


    def init_task_engine(self):
        """

        初始化任务引擎
        》TaskStepToQuestionChain
                输入：
                        client： 矢量库客户端
                        llm： 模型
                                        invoke_task_step_to_question：1、 对开始任务进行抽取，得到任务步骤，提示词所要求的输入拆分成子任务，
                                        invoke_task_step_question_context： 2、对每个子任务指令转换为子问题，召回问题前3条，对任务步骤进行抽取，得到任务步骤的上下文
                                        export_csv_file_path: 3、对召回内容与问题 导出csv文件

        """
        # 这里返回的不仅仅是一条链
        # 得到把任务步骤转成问题的多个chain
        self.task_step_to_question_chain = (
            TaskStepToQuestionChain.from_task_step_to_question_chain(
                start_task_context=self.start_task_context,
                llm_runable=self.llm_runable,
                collection=self.collection,
                cross_encoder=self.cross_encoder,
                data_base=self.data_base,
                task_step_name = self.task_step_name,
                task_step_description = self.task_step_description,
                task_step_level = self.task_step_level,
                aemo_representation_context = self.aemo_representation_context
            )
        )
        print("开始获取任务步骤提炼的问题：")
        # 调用完了，类中就多了第一条链的输出结果也就是将任务步骤转成一个问题 task_step_question
        self.task_step_to_question_chain.invoke_task_step_to_question()
        print("提炼问题完毕")
        print("开始获取检索结果")
        # 调用完了，任务节点中多出了task_step_question_context列表，里面每个元素都是自定义的TaskStepContext类型，代表重排后的前几个最优检索结果
        self.task_step_to_question_chain.invoke_task_step_question_context()
        print("检索结果获取完毕")



    def generate_step_answer(self) -> str:
        """
        生成当前任务的答案
        """
        # 需要传入resource_id，不然报错
        safe_resource_id = str(uuid.uuid4())
        # 传入task_step_question，异步调用AI生成
        print("结合检索内容，开始获取当前步骤的AI回复")
        results = call_func(
            self._get_ai_message,
            resource_id=safe_resource_id,
            kwargs={
                "llm_runable": self._kor_dreams_task_step_llm,   # 主模型是本地的，输入token有限，试一下辅助模型并发的时候能不能用
                "user_prompt": self.task_step_to_question_chain.task_step_question,
                "contexts":self.task_step_to_question_chain.task_step_question_context  # 把rag检索内容也传入
            }
        )
        print("结合检索内容后获取AI回复完毕")

        _ai_message = results[0]
        cleaned_text = re.sub(r'◁think▷.*?◁/think▷', '',_ai_message.content, flags=re.DOTALL)
        cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)
        # 定义要去除的前缀
        prefix = "<think>"

        # 如果字符串以指定前缀开头，则去除该前缀
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):]
        else:
            cleaned_text = cleaned_text
        self.task_step_to_question_chain.task_step_question_answer = cleaned_text   # 在task_step_store.json里面增加task_step_question_answer ，对应task_step_question

        # print("ai生成的回答：")
        # print(cleaned_text)
        return _ai_message.content

    @staticmethod
    def _get_ai_message(callback, **kwargs):
        # 现在将数据库检索内容和AI对当前步骤提出的问题，一起交给AI
        from langchain_core.messages import HumanMessage, SystemMessage

        contexts = kwargs.get("contexts", [])
        user_prompt = kwargs.get("user_prompt", "")

        # 构建上下文文本
        context_texts = []
        for i, context in enumerate(contexts, 1):
            context_texts.append(f"""
        参考文献 [{i}]:
        标题: {context.paper_title}
        片段ID: {context.chunk_id}
        相关度得分: {context.score:.3f}
        内容: {context.text}
        """)
        context_texts = ''.join(context_texts)

        encoding = tiktoken.get_encoding("cl100k_base")
        context_tokens = encoding.encode(context_texts)
        if len(context_tokens) > 4000:
            truncated_tokens = context_tokens[:4000]
            context_texts = encoding.decode(truncated_tokens)
        # 系统提示
        system_prompt = f"""你是一个专业的研究助手，请基于以下检索到的文献片段来回答用户的问题。

        检索到的相关文献片段：
        {context_texts}

        请根据这些文献内容，用中文总结后回答用户的问题。如果文献中没有相关信息，也可以不必聚焦于问题，而是对文献内容进行解析后回答。
        """

        # 构建消息
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"user:「{user_prompt}」")
        ]

        # 调用模型
        _ai_message = kwargs.get("llm_runable").invoke(messages)

        assert _ai_message is not None


        callback(_ai_message)  # 把汉堡递给顾客
