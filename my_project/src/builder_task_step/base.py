from __future__ import annotations

import logging
import os
import queue
import re
import torch
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from sentence_transformers import CrossEncoder

from aemo_representation_chain.base import AEMORepresentationChain


from task_engine_builder.base import TaskEngineBuilder
from vector.base import CollectionService
from vector.faiss_kb_service import FaissCollectionService

from aemo_representation_chain.prompts import FINAL_TEMPLATE
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda

class StructuredTaskStepStoryboard:
    """
    对任务进行规划，生成段落之间组成一个动态上下文
    任务：

        1、对任务按照提示词要求进行扩写，将扩写任务步骤收集 （src/dreamsboard/dreamsboard/engine/entity/task_step、src/dreamsboard/tests/test_kor/test_kor3.py）

        2、收集每个任务后存储到磁盘（src/dreamsboard/dreamsboard/engine/storage/task_step_store）

        3、对每个子任务载入会话场景，然后按照扩写任务步骤构建，MCTS任务 loader_task_step_iter_builder

    """

    start_task_context: str  # 初始任务上下文(这里是用户的问题)
    cross_encoder: CrossEncoder # 交叉编码器，用于文本相关性计算
    collection: CollectionService   # 向量数据库，用FAISS实现
    data_base: str
    llm_runable: Runnable[LanguageModelInput, BaseMessage]  # 主语言模型
    kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]  # 辅助语言模型（韩语任务专用）
    aemo_representation_chain: AEMORepresentationChain   # 情感表征链

    def __init__(
        self,
        start_task_context: str,
        llm_runable: Runnable[LanguageModelInput, BaseMessage],
        cross_encoder: CrossEncoder,
        collection: CollectionService,
        aemo_representation_chain: AEMORepresentationChain,
        data_base: str,
        kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]= None,
    ):
        """
        :param aemo_representation_chain: 情感表征链
        """
        self.start_task_context = start_task_context
        self.llm_runable = llm_runable
        self.cross_encoder = cross_encoder
        self.collection = collection
        self.aemo_representation_chain = aemo_representation_chain
        self.data_base = data_base
        self.kor_dreams_task_step_llm = kor_dreams_task_step_llm

    # 创建所有必要组件，包括基于任务内容哈希的存储路径、FAISS向量数据库服务、情感分析处理链、任务步骤存储系统
    @classmethod
    def form_builder(
        cls,
        start_task_context:str,
        llm_runable: Runnable[LanguageModelInput, BaseMessage], # 主模型
        cross_encoder_path: str,  # 交叉编码器
        embed_model_path: str,   # 嵌入模型
        data_base: str = "search_papers",  # 数据库名称
        kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage]
        | None = None,
    ) -> StructuredTaskStepStoryboard:
        # 情感表征链
        aemo_representation_chain = (
            # 在src\dreamsboard\dreamsboard\dreams\aemo_representation_chain\base.py中
            # 通过传入主题、主模型、辅助模型
            # 得到一个类，这个类里面的四个变量分别是主题、schema、主模型的处理链、辅助模型的抽取链
            AEMORepresentationChain.from_aemo_representation_chain(
                llm_runable=llm_runable,
                start_task_context=start_task_context,
                kor_dreams_task_step_llm=kor_dreams_task_step_llm,
            )
        )
        # FAISS向量库，适合超大规模向量搜索（chromadb适合中小规模和快速原型开发），纯向量索引（需额外存元数据）
        device = "cuda" if torch.cuda.is_available() else "cpu"
        collection = FaissCollectionService(
            kb_name="faq",
            embed_model=embed_model_path,
            vector_name="samples",  # 向量字段名
            device=device,
        )
        # 交叉编码器
        cross_encoder = CrossEncoder(
            cross_encoder_path,
            model_kwargs={"torch_dtype": "auto"},  # 自动选择计算精度（FP16/FP32）
            trust_remote_code=True,  # 允许加载社区自定义模型
        )

        return cls(
            llm_runable=llm_runable,
            kor_dreams_task_step_llm=kor_dreams_task_step_llm,
            cross_encoder=cross_encoder,
            collection=collection,
            data_base=data_base,
            aemo_representation_chain=aemo_representation_chain,
            start_task_context=start_task_context
        )

    # 任务加载与初始化
    def loader_task_step_iter_builder(
        self
    ) -> queue.Queue[TaskEngineBuilder]:
        """
        加载任务步骤迭代器
        :param allow_init: 是否初始化
        """
        iter_builder_queue = queue.Queue()
        print("开始获取主模型输出")
        # 生成情感表征上下文，就是aemo_representation_chain调用了主模型是生成链，即主模型对主题的输出，就是一个字典里面有个aemo_representation_context的键，对应的值是主模型的输出文本
        result = self.aemo_representation_chain.invoke_aemo_representation_context()
        # 清理特殊标记（如<think>标签)
        cleaned_text = re.sub(r'◁think▷.*?◁/think▷', '', result["aemo_representation_context"], flags=re.DOTALL)
        cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)
        # 定义要去除的前缀
        prefix = "<think>"

        # 如果字符串以指定前缀开头，则去除该前缀
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):]
        else:
            cleaned_text = cleaned_text
        print("***********************************主模型对主题的输出***************************")
        print(cleaned_text)
        print("*******************************************************************************")
        # 将处理好的主模型的输出，作为辅助模型抽取链的输入，即src\dreamsboard\dreamsboard\dreams\aemo_representation_chain\base.py中的第二个函数
        # 生成任务步骤迭代器，也就是一个列表里面放了多个字典，每个字典包括：初始任务主题、主模型生成文本、task_step_name、task_step_description、task_step_level
        print("开始获取辅助模型的抽取过程")
        task_step_list = self.aemo_representation_chain.invoke_kor_dreams_task_step_context(
                aemo_representation_context=cleaned_text
            )
        print("辅助模型抽取完毕")

        # 处理每个任务步骤
        for task_step in task_step_list:
           # 创建引擎构建器
            iter_builder_queue.put(
                TaskEngineBuilder(
                    llm_runable=self.llm_runable,
                    kor_dreams_task_step_llm=self.kor_dreams_task_step_llm,
                    cross_encoder=self.cross_encoder,
                    collection=self.collection,
                    start_task_context=self.start_task_context,
                    data_base=self.data_base,
                    task_step_name=task_step["task_step_name"],
                    task_step_description=task_step["task_step_description"],
                    task_step_level=task_step["task_step_level"],
                    aemo_representation_context=task_step["aemo_representation_context"]
                )
            )

        return iter_builder_queue

    @staticmethod
    def generate_summary(llm_runable: Runnable[LanguageModelInput, BaseMessage], # 主模型
                         content: str) -> str:
        """
        使用模型生成有条理的总结
        """

        prompt_template = PromptTemplate(
            input_variables=["content"],
            template=FINAL_TEMPLATE
        )
        # 通过这个模板和主题，得到模型的输出
        final_chain = prompt_template | llm_runable | StrOutputParser()
        def wrapper_output(_dict):
            return {
                # 其实这里就是返回一个字典，里面有个final_context的键，值是主模型的输出文本
                "final_context": _dict["final_context"],
            }
        final_chain = {
                            "final_context": final_chain,
                        } | RunnableLambda(wrapper_output)

        try:
            response = final_chain.invoke({"content": content})
            return response["final_context"]
        except Exception as e:
            return f"总结生成失败: {str(e)}"






